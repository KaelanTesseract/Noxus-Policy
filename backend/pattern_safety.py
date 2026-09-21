# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""Safe handling of "learned vendor patterns".

The pattern store is partly community-sourced (it is merged with a file from the
project's GitHub repository) and its "encryption" is only obfuscation with a public
key, so it has to be treated as untrusted input. The stored entries are regular
expressions that run against the full text of a user's document; a crafted one
(``(a+)+$`` and friends) can freeze a worker thread for hours (ReDoS).

Three layers keep that harmless:
1. ``is_safe_pattern`` accepts only simple patterns: bounded length, no nested or
   ambiguous repetition, no back-references, no look-arounds.
2. ``sanitize_pattern_db`` applies that filter (plus size caps and a field
   allowlist) whenever a pattern file is read, so bad entries never get used or
   written back.
3. ``apply_patterns`` runs the surviving patterns in a separate, resource-limited
   Python process with a hard timeout, so even a pattern that slips through the
   static checks cannot stall the API."""

import json
import os
import subprocess
import sys

try:  # Python 3.11+
    import re._parser as _sre_parse
    import re._constants as _sre_constants
except ImportError:  # pragma: no cover - older interpreters
    import sre_parse as _sre_parse
    import sre_constants as _sre_constants

MAX_PATTERN_LENGTH = 300
MAX_PATTERNS_PER_FIELD = 20
MAX_VENDORS = 2000
MAX_UNBOUNDED_REPEATS = 8
MAX_TEXT_CHARS = 100_000
MATCH_TIMEOUT_SECONDS = 5

# Fields a learned pattern may fill in. Everything else in a pattern file is ignored.
ALLOWED_FIELDS = ("regional_class", "type_class", "sf_class")

_REPEAT_OPS = {_sre_constants.MAX_REPEAT, _sre_constants.MIN_REPEAT}
if hasattr(_sre_constants, "POSSESSIVE_REPEAT"):
    _REPEAT_OPS.add(_sre_constants.POSSESSIVE_REPEAT)
_FORBIDDEN_OPS = {_sre_constants.ASSERT, _sre_constants.ASSERT_NOT, _sre_constants.GROUPREF}
if hasattr(_sre_constants, "GROUPREF_EXISTS"):
    _FORBIDDEN_OPS.add(_sre_constants.GROUPREF_EXISTS)
_MAXREPEAT = _sre_constants.MAXREPEAT


class _Unsafe(Exception):
    pass


def _contains_variable_repeat(subpattern) -> bool:
    for op, av in subpattern:
        if op in _REPEAT_OPS:
            lo, hi, inner = av
            if lo != hi and hi > 1:
                return True
            if _contains_variable_repeat(inner):
                return True
        elif op == _sre_constants.SUBPATTERN:
            if _contains_variable_repeat(av[-1]):
                return True
        elif op == _sre_constants.BRANCH:
            if any(_contains_variable_repeat(branch) for branch in av[1]):
                return True
        elif hasattr(_sre_constants, "ATOMIC_GROUP") and op == _sre_constants.ATOMIC_GROUP:
            if _contains_variable_repeat(av):
                return True
    return False


def _contains_branch(subpattern) -> bool:
    for op, av in subpattern:
        if op == _sre_constants.BRANCH:
            return True
        if op in _REPEAT_OPS and _contains_branch(av[2]):
            return True
        if op == _sre_constants.SUBPATTERN and _contains_branch(av[-1]):
            return True
    return False


def _walk(subpattern, counters: dict) -> None:
    for op, av in subpattern:
        if op in _FORBIDDEN_OPS:
            raise _Unsafe()
        if op in _REPEAT_OPS:
            lo, hi, inner = av
            if hi == _MAXREPEAT:
                counters["unbounded"] += 1
            if hi > 1:
                # (x+)+ / (x|y)* and friends: the classic exponential shapes.
                if _contains_variable_repeat(inner) or _contains_branch(inner):
                    raise _Unsafe()
            _walk(inner, counters)
        elif op == _sre_constants.SUBPATTERN:
            _walk(av[-1], counters)
        elif op == _sre_constants.BRANCH:
            for branch in av[1]:
                _walk(branch, counters)
        elif hasattr(_sre_constants, "ATOMIC_GROUP") and op == _sre_constants.ATOMIC_GROUP:
            _walk(av, counters)


def is_safe_pattern(pattern) -> bool:
    if not isinstance(pattern, str) or not pattern or len(pattern) > MAX_PATTERN_LENGTH:
        return False
    try:
        parsed = _sre_parse.parse(pattern)
        if parsed.state.groups < 2:  # group 0 is the whole match; we need a capture group
            return False
        counters = {"unbounded": 0}
        _walk(parsed, counters)
        return counters["unbounded"] <= MAX_UNBOUNDED_REPEATS
    except Exception:  # _Unsafe or an unparsable pattern
        return False


def sanitize_pattern_db(db) -> dict:
    """Returns a copy of a pattern file's content containing only well-formed
    entries with safe patterns for the allowed fields."""
    clean = {"_meta": {}, "vendors": {}}
    if not isinstance(db, dict):
        return clean
    meta = db.get("_meta")
    if isinstance(meta, dict):
        clean["_meta"] = {k: v for k, v in meta.items() if isinstance(k, str) and isinstance(v, (str, int, float))}
    vendors = db.get("vendors")
    if not isinstance(vendors, dict):
        return clean

    for vendor_key, entry in list(vendors.items())[:MAX_VENDORS]:
        if not isinstance(vendor_key, str) or not isinstance(entry, dict):
            continue
        aliases = entry.get("company_aliases", [])
        clean_entry = {
            "company_aliases": [a for a in aliases if isinstance(a, str) and len(a) <= 120][:20]
            if isinstance(aliases, list) else [],
            "patterns": {},
        }
        raw_patterns = entry.get("patterns")
        for field, pats in (raw_patterns.items() if isinstance(raw_patterns, dict) else []):
            if field not in ALLOWED_FIELDS or not isinstance(pats, list):
                continue
            safe = [p for p in pats if is_safe_pattern(p)][:MAX_PATTERNS_PER_FIELD]
            if safe:
                clean_entry["patterns"][field] = safe
        for extra_key in ("doc_types", "last_updated"):
            if isinstance(entry.get(extra_key), (str, int, float, list)):
                clean_entry[extra_key] = entry[extra_key]
        clean["vendors"][vendor_key] = clean_entry
    return clean


_RUNNER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pattern_runner.py")


def apply_patterns(text: str, patterns_by_field: dict) -> dict:
    """Runs learned patterns against ``text`` in an isolated process and returns
    {field: captured value} for every field where one of its patterns matched.
    Returns {} on any problem (timeout, crash, no usable pattern)."""
    jobs = {}
    for field, pats in patterns_by_field.items():
        if field in ALLOWED_FIELDS and isinstance(pats, list):
            safe = [p for p in pats if is_safe_pattern(p)][:MAX_PATTERNS_PER_FIELD]
            if safe:
                jobs[field] = safe
    if not jobs or not text:
        return {}

    payload = json.dumps({"text": text[:MAX_TEXT_CHARS], "jobs": jobs})
    env = {"PYTHONIOENCODING": "utf-8"}
    for keep in ("SYSTEMROOT", "PATH"):  # the interpreter on Windows won't start without these
        if keep in os.environ:
            env[keep] = os.environ[keep]
    try:
        proc = subprocess.run(
            [sys.executable, "-I", _RUNNER],
            input=payload, capture_output=True, text=True, encoding="utf-8",
            timeout=MATCH_TIMEOUT_SECONDS, env=env, cwd=os.path.dirname(_RUNNER),
        )
        if proc.returncode != 0:
            return {}
        result = json.loads(proc.stdout)
    except subprocess.TimeoutExpired:
        print("[LearningEngine] Learned patterns exceeded the time limit and were skipped.")
        return {}
    except Exception as e:
        print(f"[LearningEngine] Learned patterns could not be applied: {type(e).__name__}")
        return {}

    if not isinstance(result, dict):
        return {}
    return {f: v.strip() for f, v in result.items()
            if f in jobs and isinstance(v, str) and v.strip() and len(v) <= 64}

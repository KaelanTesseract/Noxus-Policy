# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""How the answer of the embedded language model is combined with the rules.

Measured on real letters (tools/eval_extraction.py --ai), the small model reads
worse than the rules - with the long instruction the insurer in 1 of 14 letters, the
start date in 10 of 14, the SF class in 5 of 14, and it needed half a minute per letter.
Asked only for the insurer and the policy number in a short instruction it manages the
insurer in 9 of 14 and the number in 12 of 14, in about 5 seconds. So the rules lead, and
the model is only asked when they found no insurer or no policy number. What it says must
stand in the document text as written, must look like an insurer / a policy number, and an
insurance broker ("Sie werden betreut von") is not an insurer.
"""

import datetime
import re
from typing import Optional

# Fields the model may fill when the rules found nothing, in the order they are checked.
FILLABLE_FIELDS = ("company", "insurance_number")
# Without these a letter cannot be assigned to a contract; only then is the model worth its
# half minute. (Missing dates are normal: many letters have none.)
GAP_FIELDS = ("company", "insurance_number")


def _squash(value: str) -> str:
    return re.sub(r"[\s\-/.:]", "", (value or "").lower())


def date_pattern(value) -> "re.Pattern":
    """Regex for a date as letters print it: 08.05.2018, 8.5.2018 or 8.5.18 - never as the
    beginning of a longer number ("31.12.20" must not match inside "31.12.2019")."""
    forms = {value.strftime("%d.%m.%Y"), f"{value.day}.{value.month}.{value.year}",
             f"{value.day}.{value.month}.{value.strftime('%y')}"}
    alternatives = "|".join(re.escape(form) for form in sorted(forms, key=len, reverse=True))
    return re.compile(r"(?<![0-9.])(?:" + alternatives + r")(?![0-9])")


def value_in_text(field: str, value, text: str) -> bool:
    """True if the value, in its written form, stands in the text."""
    if value in (None, "", []):
        return False
    haystack = text or ""
    if isinstance(value, (datetime.date, datetime.datetime)):
        return date_pattern(value).search(haystack) is not None
    needle = str(value)
    if field == "company":
        return needle.strip().lower() in haystack.lower()
    # numbers and classes: OCR and layout add or drop spaces and hyphens
    squashed_needle = _squash(needle)
    return len(squashed_needle) >= 2 and squashed_needle in _squash(haystack)


_GENERIC_NAME_WORDS = {"versicherungen", "versicherung", "gesellschaft", "gmbh", "kasse", "verein", "gruppe"}


def plausible(field: str, value, text: str) -> bool:
    """Does the value look like what the field holds? Only checked for what the model fills."""
    if value in (None, ""):
        return False
    value = str(value).strip()
    if field == "insurance_number":
        # a number has no spaces ("Versicherungsschein-Nummer", "K 500 09.17" are not numbers) and digits
        return not re.search(r"\s", value) and len(value) >= 6 and len(re.findall(r"\d", value)) >= 4
    if field == "company":
        words = [w for w in re.findall(r"[A-Za-zÄÖÜäöüß]{3,}", value) if w.lower() not in _GENERIC_NAME_WORDS]
        if len(value) < 4 or not words or re.search(r"\d{3}|\d\.\d", value):    # "Versicherungen", "IV-KFGK001 01.18"
            return False
        return not _is_broker(value, text)
    return True


def _is_broker(name: str, text: str) -> bool:
    """The name stands right behind "Sie werden betreut von": the broker, not the insurer."""
    lines = (text or "").splitlines()
    needle = name.strip().lower()
    for i, line in enumerate(lines):
        if re.search(r"(?i)betreut von", line):
            if needle in " ".join(lines[i:i + 6]).lower():
                return True
    return False


def has_gaps(data: dict) -> bool:
    return any(not data.get(field) for field in GAP_FIELDS)


def merge_ai_into_rules(rules: dict, ai: Optional[dict], text: str) -> dict:
    """``rules`` with the gaps filled from ``ai`` where the value is grounded in the text.
    ``ai_used`` is only true if something was actually taken, ``ai_fields`` says what."""
    taken = []
    for field in FILLABLE_FIELDS:
        if rules.get(field) or not ai:
            continue
        candidate = ai.get(field)
        if plausible(field, candidate, text) and value_in_text(field, candidate, text):
            rules[field] = candidate
            taken.append(field)
    rules["ai_used"] = bool(taken)
    rules["ai_fields"] = taken
    if taken:
        rules["ai_model"] = ai.get("ai_model")
    return rules

# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""Time-based one-time passwords (RFC 6238, as used by every authenticator app)
and single-use recovery codes for the second login factor. Standard library
only - the algorithm is small and a dependency would add attack surface for
no gain."""

import base64
import hashlib
import hmac
import secrets
import struct
import time
import urllib.parse
from typing import List, Optional

STEP_SECONDS = 30
DIGITS = 6
ISSUER = "Noxus Policy"
RECOVERY_CODE_COUNT = 8
# Codes are compared after dropping separators and case, so "ABCD-EFGH" and "abcdefgh" are the same.
_RECOVERY_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"  # no look-alikes (i, l, o, 0, 1)


def generate_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _code_for_step(secret_b32: str, step: int) -> str:
    padded = secret_b32.upper() + "=" * (-len(secret_b32) % 8)
    key = base64.b32decode(padded)
    digest = hmac.new(key, struct.pack(">Q", step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF) % (10 ** DIGITS)
    return str(number).zfill(DIGITS)


def verify_code(secret_b32: str, code: str, last_used_step: int = 0,
                now: Optional[float] = None, window: int = 1) -> Optional[int]:
    """Returns the matched time step if ``code`` is valid for the secret (allowing
    one step of clock drift either way), else None. A step at or below
    ``last_used_step`` is refused, so a code that was already accepted - for
    example one an attacker watched being typed - can't be replayed."""
    digits = "".join(ch for ch in (code or "") if ch.isdigit())
    if len(digits) != DIGITS:
        return None
    current = int((time.time() if now is None else now) // STEP_SECONDS)
    matched = None
    for candidate in range(current - window, current + window + 1):
        # Evaluate every candidate (no early exit) to keep timing independent of which one matches.
        if hmac.compare_digest(_code_for_step(secret_b32, candidate), digits) and candidate > last_used_step:
            matched = candidate
    return matched


def provisioning_uri(secret_b32: str, account: str) -> str:
    label = urllib.parse.quote(f"{ISSUER}:{account}")
    query = urllib.parse.urlencode({"secret": secret_b32, "issuer": ISSUER, "digits": DIGITS, "period": STEP_SECONDS})
    return f"otpauth://totp/{label}?{query}"


def _normalize_recovery(code: str) -> str:
    return "".join(ch for ch in (code or "").lower() if ch.isalnum())


def hash_recovery_code(code: str) -> str:
    # The codes are random with ~40 bits of entropy and single-use, so a fast hash is enough here.
    return hashlib.sha256(_normalize_recovery(code).encode()).hexdigest()


def generate_recovery_codes() -> List[str]:
    codes = []
    for _ in range(RECOVERY_CODE_COUNT):
        raw = "".join(secrets.choice(_RECOVERY_ALPHABET) for _ in range(8))
        codes.append(f"{raw[:4]}-{raw[4:]}")
    return codes


def consume_recovery_code(hashes: List[str], code: str) -> Optional[List[str]]:
    """If ``code`` matches one of the stored hashes, returns the list without it; else None."""
    target = hash_recovery_code(code)
    remaining, found = [], False
    for stored in hashes:
        if not found and hmac.compare_digest(stored, target):
            found = True
        else:
            remaining.append(stored)
    return remaining if found else None

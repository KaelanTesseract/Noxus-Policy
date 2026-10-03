# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""How the answer of the embedded language model is combined with the rules.

Measured on real letters (tools/eval_extraction.py --ai), the small model reads
worse than the rules: insurer right in 1 of 14 letters (it repeats the example from
its instructions), start date in 10 of 14, SF class in 8 of 12 - and it needs about
half a minute per letter. So the rules lead. The model is only asked when the rules
left a gap, and a value from it is accepted only if it stands in the document text
as written: a made-up policy number or a date that is not on the page never gets in.
"""

import datetime
import re
from typing import Optional

# Fields the model may fill when the rules found nothing, in the order they are checked.
FILLABLE_FIELDS = ("company", "insurance_number", "start_date", "end_date",
                   "sf_class", "regional_class", "type_class")
# Without these a letter cannot be assigned to a contract; only then is the model worth its
# half minute. (Missing dates are normal: many letters have none.)
GAP_FIELDS = ("company", "insurance_number")


def _squash(value: str) -> str:
    return re.sub(r"[\s\-/.:]", "", (value or "").lower())


def value_in_text(field: str, value, text: str) -> bool:
    """True if the value, in its written form, stands in the text."""
    if value in (None, "", []):
        return False
    haystack = text or ""
    if isinstance(value, (datetime.date, datetime.datetime)):
        # dd.mm.yyyy as printed; two-digit years and single-digit days are also common
        return (value.strftime("%d.%m.%Y") in haystack
                or f"{value.day}.{value.month}.{value.strftime('%y')}" in haystack
                or f"{value.day}.{value.month}.{value.year}" in haystack)
    needle = str(value)
    if field == "company":
        return needle.strip().lower() in haystack.lower()
    # numbers and classes: OCR and layout add or drop spaces and hyphens
    squashed_needle = _squash(needle)
    return len(squashed_needle) >= 2 and squashed_needle in _squash(haystack)


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
        if value_in_text(field, candidate, text):
            rules[field] = candidate
            taken.append(field)
    rules["ai_used"] = bool(taken)
    rules["ai_fields"] = taken
    if taken:
        rules["ai_model"] = ai.get("ai_model")
    return rules

# Copyright (c) 2026 Dennis Guse
# SPDX-License-Identifier: MIT
# See the LICENSE file in the project root.

"""Checks every extracted value against the document text.

A value the extractors return is only as good as its source. This module says, per
field, how far it can be trusted:

* ``gefunden``   - the value stands in the text as written (with page and line)
* ``berechnet``  - derived, not read: the cancellation date is always "end of the term
                   minus one month", an end date is "start plus one year" when the letter
                   names none
* ``unsicher``   - not found in the text (or only a guessed amount): please check

The result is shown in the upload dialog next to each field, and it matters most for the
dates: the reminders for cancellation deadlines are built on them.
"""

import datetime
import re
from typing import Optional


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


PAGE_MARKER = re.compile(r"^--- Page (\d+) ---$")
SNIPPET_CHARS = 90

# Fields that are checked, with how a value is looked up.
CHECKED_FIELDS = ("company", "insurance_number", "cost", "start_date", "end_date", "cancellation_date",
                  "sf_class", "regional_class", "type_class")
_CLASS_FIELDS = ("insurance_number", "sf_class", "regional_class", "type_class")


# What OCR mixes up: each character with the characters it is often read as.
_CONFUSABLE = {"0": "0oO", "o": "0oO", "5": "5sS", "s": "5sS", "1": "1iIlL|", "i": "1iIlL|", "l": "1iIlL|", "8": "8bB", "b": "8bB"}


def _fuzzy_pattern(value: str):
    """Regex for ``value`` as OCR may have written it: separators optional, 0/O, 5/S, 1/I/l, 8/B
    interchangeable, and not part of a longer word or number ("18" must not match "2018")."""
    chars = [c for c in (value or "").lower() if c not in " -/.:" + chr(9)]
    if len(chars) < 2:
        return None
    sep = r"[\s\-/.:]?"
    parts = ["[" + re.escape(_CONFUSABLE[c]) + "]" if c in _CONFUSABLE else re.escape(c) for c in chars]
    return re.compile("(?<![0-9a-zA-Z])" + sep.join(parts) + "(?![0-9a-zA-Z])", re.IGNORECASE)


def _german_amounts(value: float) -> list:
    plain = f"{value:.2f}".replace(".", ",")
    grouped = f"{value:,.2f}".replace(",", "#").replace(".", ",").replace("#", ".")
    return list({plain, grouped})


def _lines_with_pages(text: str):
    page = 1
    for raw in (text or "").splitlines():
        marker = PAGE_MARKER.match(raw.strip())
        if marker:
            page = int(marker.group(1))
            continue
        yield page, raw


def _locate(text: str, needles: list):
    """(page, line) of the first line that contains one of the needles, or None."""
    for page, raw in _lines_with_pages(text):
        if any(n and n in raw for n in needles):
            return page, raw.strip()
    return None


def _locate_fuzzy(text: str, value: str):
    pattern = _fuzzy_pattern(value)
    if pattern is None:
        return None
    for page, raw in _lines_with_pages(text):
        if pattern.search(raw):
            return page, raw.strip()
    return None


def _locate_sf_class(text: str, value: str):
    """"SF 5" is stored, the letter says "Schadenfreiheitsklasse : 5" - the class counts as
    found when its number stands behind SF / Schadenfreiheit(sklasse)."""
    number = re.sub(r"(?i)^\s*sf\s*", "", value).strip()
    if not number:
        return None
    pattern = re.compile(r"(?i)(?:\bsf\b|\bsf(?=\d)|schadenfreiheit)\D{0,40}?(?<!\d)" + re.escape(number) + r"(?!\d)")
    for page, raw in _lines_with_pages(text):
        if pattern.search(raw):
            return page, raw.strip()
    return None


def _locate_regional_class(text: str, value: str):
    """The extractor stores "R4" (normalised), the letter prints "Regionalklasse 4" - the class counts as
    found when its number stands behind the label. A number elsewhere on the page does not count."""
    found = _locate_fuzzy(text, value)
    if found:
        return found
    number = re.sub(r"(?i)^\s*r\s*", "", value).strip()
    if not number:
        return None
    pattern = re.compile(r"(?i)(?:regionalklasse|regionalkl\.?|\bregion\b)\D{0,40}?(?<![0-9a-zA-Z])" + re.escape(number) + r"(?![0-9a-zA-Z])")
    for page, raw in _lines_with_pages(text):
        if pattern.search(raw):
            return page, raw.strip()
    return None


def _check(field: str, value, text: str, data: dict) -> Optional[dict]:
    if value in (None, "", []):
        return None
    if field == "cancellation_date":
        # the extractors always compute it (end of the term minus one month), whatever the text says
        return {"status": "berechnet", "grund": "Ablauf minus ein Monat (übliche Kündigungsfrist), nicht aus dem Dokument gelesen"}
    found = None
    if field == "cost":
        found = _locate(text, _german_amounts(float(value)))
        if found and not data.get("cost_certain", True):
            return {"status": "unsicher", "grund": "Beitrag nur vermutet (erster passender Betrag im Dokument)",
                    "seite": found[0], "stelle": found[1][:SNIPPET_CHARS]}
    elif isinstance(value, (datetime.date, datetime.datetime)):
        pattern = date_pattern(value)
        found = next(((page, raw.strip()) for page, raw in _lines_with_pages(text) if pattern.search(raw)), None)
    elif field == "sf_class":
        found = _locate_sf_class(text, str(value))
    elif field == "regional_class":
        found = _locate_regional_class(text, str(value))
    elif field in _CLASS_FIELDS:
        found = _locate_fuzzy(text, str(value))
    elif value_in_text(field, value, text):
        found = _locate(text, [str(value).strip().lower()]) or _locate(text.lower(), [str(value).strip().lower()])
        if found is None:
            found = (1, "")

    if found:
        return {"status": "gefunden", "seite": found[0], "stelle": found[1][:SNIPPET_CHARS]}

    if field == "end_date" and data.get("start_date"):
        return {"status": "berechnet", "grund": "Aus dem Beginn berechnet (Verträge verlängern sich jährlich), im Dokument steht kein Ablaufdatum"}
    return {"status": "unsicher", "grund": "Wert steht nicht wörtlich im Dokument"}


def assess_fields(data: dict, text: str) -> dict:
    """{field: {"status": ..., "seite": ..., "stelle": ..., "grund": ...}} for every checked
    field that has a value."""
    result = {}
    for field in CHECKED_FIELDS:
        entry = _check(field, data.get(field), text, data)
        if entry is None:
            continue
        # The cancellation date is derived from the end date: if that is not read, neither is it
        if field == "cancellation_date" and entry["status"] == "berechnet" and result.get("end_date", {}).get("status") == "berechnet":
            entry["grund"] = "Ablauf minus ein Monat; der Ablauf selbst ist berechnet"
        result[field] = entry
    return result

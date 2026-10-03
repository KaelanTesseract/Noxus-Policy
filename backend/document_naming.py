# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""Readable names for uploaded documents.

Scanned files arrive with names like ``4ede58bb-136f-41c8-9d8f-83a9c3fc1f9e.pdf``.
The name is built only from parts that can be recognised reliably - the insurer,
the kind of letter and its date - never from a sentence picked out of the running
text (footers and data-protection notes used to end up as the "subject"), and never
with the policy number, because names appear in lists and downloads.

    "Itzehoer Kfz-Beitragsrechnung Januar 2021"
    "HUK24 Kfz-Versicherungsschein 24.07.2026"
    "Itzehoer Verbraucherinformationen"
"""

import datetime
import re
from typing import Optional

MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
          "September", "Oktober", "November", "Dezember"]
MAX_TITLE_LENGTH = 90
HEAD_LINES = 25          # where a document says what it is
DATE_LINES = 60          # the dates sit a little further down (after address block, barcodes, postage)
INFO_HEAD_LINES = 10     # information leaflets name themselves right at the top

# Kinds that read well with the category in front ("Kfz-Beitragsrechnung").
_PREFIXED = {"Beitragsrechnung", "Nachtrag", "Nachtrag zum Vertragsende", "Versicherungsschein", "Schadenvisitenkarten"}

_DATE = r"(\d{2})\.(\d{2})\.(\d{4})"


def _head(text: str, lines: int) -> str:
    kept = [line.strip() for line in (text or "").splitlines() if line.strip()]
    return "\n".join(kept[:lines])


def detect_kind(text: str) -> Optional[str]:
    """What kind of document this is, judged from its heading area only. A word in
    the running text of a long terms document ("... in der Beitragsrechnung ...")
    must not decide it."""
    info_head = _head(text, INFO_HEAD_LINES).lower()
    head = _head(text, HEAD_LINES)
    lowered = head.lower()

    has_product_sheet = "produktinformationsblatt" in info_head
    has_terms = "allgemeine bedingungen" in info_head
    if has_product_sheet and has_terms:
        return "Produktinformationsblatt und Bedingungen"
    if has_product_sheet:
        return "Produktinformationsblatt"
    if "verbraucherinformationen" in info_head:
        return "Verbraucherinformationen"
    if has_terms:
        return "Allgemeine Bedingungen"

    if "internationale versicherungskarte" in lowered or "international motor insurance card" in lowered:
        return "Grüne Karte"
    if "schadenvisitenkarte" in lowered:
        return "Schadenvisitenkarten"
    if re.search(r"^beitragsrechnung\b", lowered, re.M):
        return "Beitragsrechnung"
    if re.search(r"^(?:information zur |mitteilung zur )?(?:beitragsanpassung|beitragsänderung)\b", lowered, re.M):
        return "Beitragsanpassung"
    if re.search(r"^nachtrag\b", lowered, re.M):
        return "Nachtrag zum Vertragsende" if re.search(r"vertrag ist beendet", lowered) else "Nachtrag"
    if re.search(r"^versicherungsschein\s*[-–—]", lowered, re.M):
        return "Versicherungsschein"
    return None


def _month_year(day: str, month: str, year: str) -> Optional[str]:
    try:
        return f"{MONTHS[int(month) - 1]} {year}"
    except (ValueError, IndexError):
        return None


def _full_date(match) -> str:
    return f"{match.group(1)}.{match.group(2)}.{match.group(3)}"


def document_date(kind: Optional[str], text: str) -> Optional[str]:
    """The date that identifies this document: the billing month for an invoice, the
    effective or letter date for everything issued on a particular day."""
    head = _head(text, DATE_LINES)

    if kind == "Beitragsrechnung":
        m = re.search(r"Zeitraum\s+" + _DATE, head)
        return _month_year(*m.groups()) if m else None

    if kind in ("Nachtrag", "Nachtrag zum Vertragsende"):
        m = re.search(r"Beginn der Änderung\s*[^\d\n]{0,6}" + _DATE, head)
        if m:
            return _full_date(m)
        m = re.search(r"Ablauf\s+" + _DATE, head)
        return _full_date(m) if m else None

    if kind in ("Versicherungsschein", "Schadenvisitenkarten"):
        m = re.search(r"Gültig ab\s+" + _DATE, head) if kind == "Versicherungsschein" else None
        m = m or re.search(r"^[^\d\n]{2,40},\s*" + _DATE + r"\s*$", head, re.M)
        return _full_date(m) if m else None

    return None  # leaflets, the green card: no date in the name


def _display_company(company: Optional[str], text: str) -> Optional[str]:
    name = (company or "").strip()
    if not name or name.lower() in ("unbekannt", "none", "null"):
        return None
    # HUK24 policies are often recognised as HUK-COBURG; the letterhead says which it is.
    if name.lower().startswith("huk") and re.search(r"\bHUK24\b", _head(text, HEAD_LINES)):
        return "HUK24"
    return name[:40]


def suggest_title(company: Optional[str], category: Optional[str], text: str,
                  today: Optional[datetime.date] = None) -> str:
    kind = detect_kind(text)
    name = _display_company(company, text)

    if kind is None:
        today = today or datetime.date.today()
        parts = [name, f"Dokument vom {today.strftime('%d.%m.%Y')}"]
        return " ".join(p for p in parts if p)[:MAX_TITLE_LENGTH]

    label = kind
    clean_category = (category or "").strip()
    if kind in _PREFIXED and clean_category and clean_category.lower() not in ("sonstige", "sonstiges", "versicherung"):
        label = f"{clean_category}-{kind}"

    parts = [name, label, document_date(kind, text)]
    return " ".join(p for p in parts if p)[:MAX_TITLE_LENGTH]

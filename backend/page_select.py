# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""Which pages of a long PDF are read.

A policy of ten or more pages often has the premium table on page 6 or 7. Reading
"the first five and the last three pages" misses it, and scanning every page of a
scanned 60-page terms document costs a minute and a half for nothing. So:

* a PDF with a text layer is read completely (that is cheap) and the pages with the
  most contract data are kept (the first pages always: letterhead, subject);
* a scanned PDF is recognised page by page in small batches and stops as soon as a
  premium has been found, or the document turns out to be an information leaflet.
"""

import re

from llm_text import _score

MAX_TEXT_PAGES = 8          # pages of a text-layer PDF that are kept
KEEP_FIRST_PAGES = 3        # letterhead, subject, usually the premium
FIRST_OCR_PAGES = 5         # scanned PDF: pages recognised before the first check
OCR_BATCH_PAGES = 3         # ... then this many more at a time
MAX_OCR_PAGES = 15          # ... but never more than this

_PREMIUM = re.compile(r"(?i)(?:beitrag|prämie)[\s\S]{0,80}?\d{1,3}(?:\.\d{3})*,\d{2}\s*(?:€|eur)")


def page_score(text: str) -> int:
    """How much contract data (policy number, premium, dates, classes ...) a page carries."""
    return sum(_score(line) for line in (text or "").splitlines())


def choose_text_pages(page_texts: list, limit: int = MAX_TEXT_PAGES, keep_first: int = KEEP_FIRST_PAGES) -> list:
    """Indexes (0-based, in page order) of the pages to keep: the first ones, then the best
    scoring of the rest. A document with at most ``limit`` pages is kept whole."""
    count = len(page_texts)
    if count <= limit:
        return list(range(count))
    chosen = list(range(min(keep_first, count)))
    rest = sorted(range(len(chosen), count), key=lambda i: (-page_score(page_texts[i]), i))
    return sorted(chosen + rest[:max(0, limit - len(chosen))])


def has_premium(text: str) -> bool:
    """True once the text names a premium with an amount."""
    return bool(_PREMIUM.search(text or ""))


def split_pdftotext(raw: str) -> list:
    """pdftotext separates pages with a form feed (and ends the last one with it)."""
    pages = (raw or "").split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    return pages

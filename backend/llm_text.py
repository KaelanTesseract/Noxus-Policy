# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""Which parts of a document the embedded language model gets to read.

The model has a small context window. It used to be given the first 3000
characters, but the premium table, the deadlines and the classes of a letter often
stand further down. Instead the letterhead (company, policy number) is kept and the
lines that carry contract data are picked from the whole text.
"""

import re

HEAD_LINES = 30            # letterhead: insurer, policy number, subject
MAX_LINE_CHARS = 220       # a line is cut here (OCR sometimes glues a whole paragraph together)
CONTEXT_AFTER = 1          # a label is often followed by its value on the next line

# Lines that carry contract data, each with the weight it adds to the line.
_CLUES = [
    (re.compile(r"(?i)versicherungsschein|policen?-?nr|vertragsnummer|vsnr|schein-?nummer"), 3),
    (re.compile(r"(?i)beitrag|prämie|jahresbeitrag|zahlbeitrag|gesamtbeitrag"), 3),
    (re.compile(r"(?i)\d[\d.]*,\d{2}\s*(?:€|eur)"), 2),
    (re.compile(r"(?i)zahlungs(?:weise|periode)|monatlich|vierteljährlich|halbjährlich|jährlich"), 2),
    (re.compile(r"(?i)beginn|ablauf|laufzeit|vertragsdauer|gültig|hauptfälligkeit|kündig"), 2),
    (re.compile(r"(?i)regionalklasse|typklasse|schadenfreiheit|\bsf[-\s]?(?:klasse)?\s*\d|tarifgruppe"), 3),
    (re.compile(r"(?i)versichert sind|versicherungsschutz|haftpflicht|teilkasko|vollkasko|schutzbrief|fahrerschutz"), 1),
    (re.compile(r"\b\d{2}\.\d{2}\.\d{4}\b"), 1),
]


def _score(line: str) -> int:
    return sum(weight for pattern, weight in _CLUES if pattern.search(line))


def select_relevant_text(text: str, max_chars: int) -> str:
    """At most ``max_chars`` characters of ``text``: the letterhead plus the lines that
    look like contract data (with the line behind each), in their original order. A text
    that fits is returned unchanged."""
    lines = [line.strip()[:MAX_LINE_CHARS] for line in (text or "").splitlines() if line.strip()]
    if sum(len(line) + 1 for line in lines) <= max_chars:
        return "\n".join(lines)

    keep = set(range(min(HEAD_LINES, len(lines))))
    used = sum(len(lines[i]) + 1 for i in keep)

    # best lines first, so the budget is spent on the strongest evidence, wherever it stands
    candidates = sorted(
        (i for i in range(len(lines)) if i not in keep and _score(lines[i]) > 0),
        key=lambda i: (-_score(lines[i]), i),
    )
    for i in candidates:
        group = [j for j in range(i, min(i + 1 + CONTEXT_AFTER, len(lines))) if j not in keep]
        cost = sum(len(lines[j]) + 1 for j in group)
        if used + cost > max_chars:
            continue
        keep.update(group)
        used += cost
    return "\n".join(lines[i] for i in sorted(keep))

# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""Selection of the text lines the embedded model reads."""

import llm_text


def long_letter():
    head = ["Itzehoer Versicherungen", "Max Mustermann", "Beitragsrechnung zur Kfz-Versicherung"] + [f"Kopfzeile {i}" for i in range(40)]
    filler = [f"Dies ist ein Satz ohne Bedeutung Nummer {i}." for i in range(400)]
    middle = filler[:200] + [
        "Beitrag (inklusive Versicherungsteuer)",
        "62,48 €",
        "Regionalklasse R05 Typklasse 18",
        "Beginn der Änderung 01.01.2021",
    ] + filler[200:]
    return "\n".join(head + middle)


def test_a_short_text_is_returned_unchanged_apart_from_blank_lines():
    assert llm_text.select_relevant_text("a\n\n  b  \n", 1000) == "a\nb"


def test_the_budget_is_respected():
    assert len(llm_text.select_relevant_text(long_letter(), 3000)) <= 3000


def test_data_far_down_in_the_text_is_kept():
    picked = llm_text.select_relevant_text(long_letter(), 3000)
    for needle in ("62,48 €", "Regionalklasse R05", "Beginn der Änderung 01.01.2021"):
        assert needle in picked
    # the old approach (first 3000 characters) would have missed all of them
    assert "62,48" not in long_letter()[:3000]


def test_the_letterhead_is_always_kept_and_order_is_preserved():
    picked = llm_text.select_relevant_text(long_letter(), 3000).splitlines()
    assert picked[0] == "Itzehoer Versicherungen"
    assert picked.index("Regionalklasse R05 Typklasse 18") > picked.index("Beitrag (inklusive Versicherungsteuer)")


def test_the_value_on_the_line_behind_a_label_comes_along():
    picked = llm_text.select_relevant_text(long_letter(), 3000)
    assert "Beitrag (inklusive Versicherungsteuer)\n62,48 €" in picked


def test_very_long_lines_are_cut():
    picked = llm_text.select_relevant_text("x" * 5000, 10_000)
    assert len(picked) == llm_text.MAX_LINE_CHARS


def test_empty_input():
    assert llm_text.select_relevant_text("", 100) == ""
    assert llm_text.select_relevant_text(None, 100) == ""

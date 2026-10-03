# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""Policy numbers as other insurers print them: with spaces, behind a colon, below the label."""

import os
import re
import sys

import pytest

import ai_merge
import ocr

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
from synthetic_letters import LETTERS  # noqa: E402

NORMAL = [letter for letter in LETTERS if letter.get("group") == "synthetisch"]


def squash(value):
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


@pytest.mark.parametrize("letter", NORMAL, ids=[letter["company"] for letter in NORMAL])
def test_the_number_of_an_invented_letter_is_found(letter):
    assert squash(ocr.extract_insurance_data_regex(letter["text"])["insurance_number"]) == squash(letter["insurance_number"])


@pytest.mark.parametrize("text,expected", [
    ("Versicherungsschein-Nr. WG 5544-3321\nBeginn 01.02.2024", "WG 5544-3321"),
    ("Vertragsnummer\n7 123 456 789 0\nBeginn", "7 123 456 789 0"),
    ("Police: 12-3456789-0", "12-3456789-0"),
    ("Vertragsnummer: PH-4410-2288", "PH-4410-2288"),
    ("Versicherungsschein-Nr. 30.120.456-7", "30.120.456-7"),
    ("Versicherungsnummer: K 4455 6677 88 Beitrag", "K 4455 6677 88"),
    ("Police-Nr.\nWG/2018/00412", "WG/2018/00412"),
])
def test_a_number_behind_a_label_is_read_whatever_its_layout(text, expected):
    assert ocr.number_after_label(text) == expected


@pytest.mark.parametrize("text", [
    "Bitte geben Sie bei Rückfragen Ihre Versicherungsschein-Nummer an.",     # the label in a sentence
    "Police vom 01.01.2020",                                                 # a date is no number
    "Vertragsnummer Beginn 2024",                                            # a word ends it, too few digits
    "Versicherungsschein-Nr. AB 12",                                         # too few digits
])
def test_no_number_where_there_is_none(text):
    assert ocr.number_after_label(text) is None


def test_a_number_in_groups_counts_for_the_model_only_behind_a_label():
    behind = "Ihre Daten\nVersicherungsschein-Nr.\n00 8812 3345\n"
    assert ai_merge.plausible("insurance_number", "00 8812 3345", behind)
    corner = "K 500 09.17\nVerbraucherinformationen\nText ohne Bezeichnung\n"
    assert not ai_merge.plausible("insurance_number", "K 500 09.17", corner)

# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""The rules lead; the model only fills gaps with values that stand in the text."""

import datetime

import pytest

import ai_merge
import ocr

LETTER_WITHOUT_KNOWN_INSURER = """Nordlicht Assekuranz GmbH
Max Mustermann
Beitragsrechnung zur Kfz-Versicherung
Versicherungsschein-Nr. NL 4711-0815
Der Vertrag läuft vom 01.02.2024 bis 01.02.2025.
Gesamtbeitrag 45,60 €
"""


def test_values_are_grounded_in_the_text_as_written():
    text = "Policennummer LJ-23375 102-001, Beginn 08.05.2018, Nordlicht Assekuranz, SF 7"
    assert ai_merge.value_in_text("insurance_number", "LJ-23375102-001", text)      # space from OCR
    assert ai_merge.value_in_text("start_date", datetime.date(2018, 5, 8), text)
    assert ai_merge.value_in_text("company", "nordlicht assekuranz", text)
    assert ai_merge.value_in_text("sf_class", "SF7", text)
    assert not ai_merge.value_in_text("insurance_number", "XX-99999999-001", text)
    assert not ai_merge.value_in_text("start_date", datetime.date(2017, 5, 8), text)
    assert not ai_merge.value_in_text("company", "HUK-COBURG", text)
    assert not ai_merge.value_in_text("sf_class", "", text)
    assert not ai_merge.value_in_text("type_class", None, text)


def test_a_one_character_value_is_never_grounded():
    assert not ai_merge.value_in_text("type_class", "7", "Typklasse 17, 27, 37")


def test_the_rules_are_not_overwritten_and_made_up_values_stay_out():
    rules = {"company": "Itzehoer", "insurance_number": None, "start_date": None}
    ai = {"company": "HUK-COBURG", "insurance_number": "ZZ-1234567-1", "start_date": datetime.date(2020, 1, 1),
          "ai_model": "test"}
    merged = ai_merge.merge_ai_into_rules(rules, ai, "Itzehoer Beitragsrechnung vom 03.04.2019")
    assert merged["company"] == "Itzehoer"
    assert merged["insurance_number"] is None and merged["start_date"] is None
    assert merged["ai_used"] is False and merged["ai_fields"] == []


def test_a_grounded_value_fills_a_gap_and_is_reported():
    rules = {"company": None, "insurance_number": "A-1"}
    ai = {"company": "Nordlicht Assekuranz", "ai_model": "test"}
    merged = ai_merge.merge_ai_into_rules(rules, ai, "Nordlicht Assekuranz GmbH")
    assert merged["company"] == "Nordlicht Assekuranz"
    assert merged["ai_used"] is True and merged["ai_fields"] == ["company"]


def test_no_answer_from_the_model_changes_nothing():
    merged = ai_merge.merge_ai_into_rules({"company": None}, None, "text")
    assert merged["company"] is None and merged["ai_used"] is False


# ----- in the pipeline -------------------------------------------------------------------

def _model_must_not_run(text):
    raise AssertionError("the model must not run here")


def test_the_model_is_not_asked_when_the_rules_found_everything(monkeypatch):
    monkeypatch.setattr(ocr, "extract_with_mini_ai", _model_must_not_run)
    text = "Itzehoer Versicherungen\nBeitragsrechnung zur Kfz-Versicherungs-Nr. LJ-23375102-001\nGesamtbeitrag 62,48 €\n"
    data = ocr.extract_insurance_data(text)
    assert data["company"] == "Itzehoer" and data["insurance_number"] == "LJ-23375102-001"
    assert data["ai_used"] is False


def test_the_model_is_not_asked_about_information_documents(monkeypatch):
    monkeypatch.setattr(ocr, "extract_with_mini_ai", _model_must_not_run)
    data = ocr.extract_insurance_data("Verbraucherinformationen\nfür Kraftfahrtversicherungen\n" + "Text\n" * 30)
    assert data["doc_type"] == "Verbraucherinformationen" and data["ai_used"] is False


def test_the_model_is_not_asked_when_ai_is_switched_off(monkeypatch):
    monkeypatch.setattr(ocr, "extract_with_mini_ai", _model_must_not_run)

    class Setting:
        value = "false"

    class Query:
        def filter(self, *a):
            return self

        def first(self):
            return Setting()

    class Db:
        def query(self, *a):
            return Query()

    data = ocr.extract_insurance_data(LETTER_WITHOUT_KNOWN_INSURER, db=Db())
    assert data["ai_used"] is False


def test_a_gap_is_filled_by_the_model_only_with_what_the_letter_says(monkeypatch):
    seen = {}

    def fake_model(text):
        seen["asked"] = True
        return {"company": "Nordlicht Assekuranz", "insurance_number": "NL 4711-0815",
                "start_date": datetime.date(2022, 2, 1), "ai_model": "fake"}

    monkeypatch.setattr(ocr, "extract_with_mini_ai", fake_model)
    text = LETTER_WITHOUT_KNOWN_INSURER.replace("Versicherungsschein-Nr. NL 4711-0815\n", "")
    data = ocr.extract_insurance_data(text)
    assert seen.get("asked")
    assert data["company"] in ("Nordlicht Assekuranz", "Nordlicht Assekuranz GmbH")
    assert data["insurance_number"] in (None, "")          # not in the letter -> not accepted
    assert data["start_date"] != datetime.date(2022, 2, 1)  # not in the letter -> not accepted
    assert data["cost"] == 45.60


# ----- the model only suggests; what it says must look right ------------------------------------

LETTER_WITH_BROKER = """Itzehoer Versicherungen
Sie werden betreut von:
Flenker Brennecke GmbH
Große Bäckerstraße 9
Nachtrag zur Kraftfahrtversicherung LJ-23375102-001
"""


@pytest.mark.parametrize("field,value,ok", [
    ("company", "Itzehoer Versicherungen", True),
    ("company", "HUK24 AG", True),
    ("company", "Versicherungen", False),            # only a part of the name
    ("company", "IV-KFGK001 01.18", False),          # a form number
    ("company", "Flenker Brennecke GmbH", False),    # the broker
    ("company", "", False),
    ("insurance_number", "LJ-23375102-001", True),
    ("insurance_number", "669/246004-Q", True),
    ("insurance_number", "Versicherungsschein-Nummer", False),   # the label, no digits
    ("insurance_number", "K 500 09.17", False),                   # a form code with spaces
    ("insurance_number", "OD", False),
])
def test_the_model_suggestions_must_look_like_an_insurer_and_a_number(field, value, ok):
    assert ai_merge.plausible(field, value, LETTER_WITH_BROKER) is ok


def test_the_broker_is_never_taken_as_the_insurer():
    merged = ai_merge.merge_ai_into_rules({"company": None, "insurance_number": "LJ-23375102-001"},
                                          {"company": "Flenker Brennecke GmbH", "ai_model": "t"}, LETTER_WITH_BROKER)
    assert merged["company"] is None and merged["ai_used"] is False


def test_the_model_only_fills_company_and_policy_number():
    ai = {"company": "Nordlicht Assekuranz", "insurance_number": "NL-4711-0815", "start_date": datetime.date(2024, 2, 1),
          "sf_class": "SF 5", "ai_model": "t"}
    text = "Nordlicht Assekuranz GmbH\nNL-4711-0815\nBeginn 01.02.2024 SF 5"
    merged = ai_merge.merge_ai_into_rules({"company": None, "insurance_number": None, "start_date": None, "sf_class": None}, ai, text)
    assert merged["company"] == "Nordlicht Assekuranz" and merged["insurance_number"] == "NL-4711-0815"
    assert merged["start_date"] is None and merged["sf_class"] is None

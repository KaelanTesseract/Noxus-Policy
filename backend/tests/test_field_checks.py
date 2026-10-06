# Copyright (c) 2026 Dennis Guse
# SPDX-License-Identifier: MIT
# See the LICENSE file in the project root.

"""Every extracted value is checked against the document text."""

import datetime

import field_checks as fc
import ocr

RECHNUNG = """--- Page 1 ---
Itzehoer Versicherungen
Beitragsrechnung zur Kfz-Versicherungs-Nr. LJ-23375 102-001
01.01.2021 wird der monatliche Beitrag für den Zeitraum 01.01.2021 bis 31.01.2021 fällig.
Kfz-Haftpflicht RO5 18 SF1 (75%) 50,51 €
Gesamtbeitrag inkl. 19 % Versicherungssteuer (9,98 €) 62,48 €
--- Page 2 ---
Typklasse 18
"""


def test_found_values_come_with_page_and_line():
    checks = fc.assess_fields({"company": "Itzehoer", "cost": 62.48, "cost_certain": True,
                               "start_date": datetime.date(2021, 1, 1)}, RECHNUNG)
    assert checks["company"]["status"] == "gefunden" and checks["company"]["seite"] == 1
    assert checks["cost"]["status"] == "gefunden" and "62,48" in checks["cost"]["stelle"]
    assert checks["start_date"]["status"] == "gefunden"


def test_the_page_of_a_value_follows_the_page_markers():
    checks = fc.assess_fields({"type_class": "18"}, RECHNUNG.replace("Kfz-Haftpflicht RO5 18", "Kfz-Haftpflicht RO5 xx"))
    assert checks["type_class"]["seite"] == 2


def test_the_cancellation_date_is_always_marked_as_computed():
    text = "Ablauf 31.12.2021 und auch 30.11.2021 steht im Text"
    checks = fc.assess_fields({"end_date": datetime.date(2021, 12, 31), "cancellation_date": datetime.date(2021, 11, 30)}, text)
    assert checks["end_date"]["status"] == "gefunden"
    assert checks["cancellation_date"]["status"] == "berechnet"


def test_an_end_date_that_is_start_plus_a_year_is_marked_as_computed():
    checks = fc.assess_fields({"start_date": datetime.date(2021, 1, 1), "end_date": datetime.date(2021, 12, 31)}, RECHNUNG)
    assert checks["end_date"]["status"] == "berechnet"


def test_values_that_are_not_in_the_text_are_unsure():
    checks = fc.assess_fields({"company": "HUK-COBURG", "insurance_number": "ZZ-99999999-001",
                               "start_date": datetime.date(2019, 5, 5), "cost": 12.34}, RECHNUNG)
    for field in ("company", "insurance_number", "start_date", "cost"):
        assert checks[field]["status"] == "unsicher", field


def test_a_guessed_cost_is_unsure_even_though_the_amount_is_on_the_page():
    checks = fc.assess_fields({"cost": 50.51, "cost_certain": False}, RECHNUNG)
    assert checks["cost"]["status"] == "unsicher" and "vermutet" in checks["cost"]["grund"]


def test_ocr_confusions_do_not_make_a_class_unsure():
    # the page says RO5 (letter O), the extractor corrected it to R05
    assert fc.assess_fields({"regional_class": "R05"}, RECHNUNG)["regional_class"]["status"] == "gefunden"


def test_a_policy_number_with_an_ocr_space_is_found():
    assert fc.assess_fields({"insurance_number": "LJ-23375102-001"}, RECHNUNG)["insurance_number"]["status"] == "gefunden"


def test_the_sf_class_is_found_behind_its_label():
    letter = "Schadenfreiheitsklasse : 5 (5 schadenfreie Jahre)"
    assert fc.assess_fields({"sf_class": "SF 5"}, letter)["sf_class"]["status"] == "gefunden"
    assert fc.assess_fields({"sf_class": "SF 5"}, RECHNUNG)["sf_class"]["status"] == "unsicher"
    assert fc.assess_fields({"sf_class": "SF 1"}, RECHNUNG)["sf_class"]["status"] == "gefunden"   # "SF1 (75%)"


def test_fields_without_a_value_are_left_out():
    assert fc.assess_fields({"company": None, "cost": None}, RECHNUNG) == {}


def test_amounts_with_thousands_separators_are_found():
    assert fc.assess_fields({"cost": 1234.5, "cost_certain": True}, "Jahresbeitrag 1.234,50 €")["cost"]["status"] == "gefunden"


def test_the_pipeline_attaches_the_checks_and_the_certainty_of_the_cost():
    data = ocr.extract_insurance_data(RECHNUNG)
    assert data["cost"] == 62.48 and data["cost_certain"] is True
    assert data["field_checks"]["cost"]["status"] == "gefunden"
    assert data["field_checks"]["cancellation_date"]["status"] == "berechnet"


def test_a_cost_taken_from_the_first_amount_on_the_page_is_not_certain():
    text = "Itzehoer Versicherungen\nIhre Kfz-Versicherung\nWir danken 77,70 € für Ihr Vertrauen\n"
    data = ocr.extract_insurance_data(text)
    assert data["cost"] == 77.70 and data["cost_certain"] is False
    assert data["field_checks"]["cost"]["status"] == "unsicher"


def test_a_short_year_never_matches_inside_a_longer_one():
    # "31.12.20" is the short form of 31.12.2020 - it must not be found in "31.12.2019"
    checks = fc.assess_fields({"start_date": datetime.date(2019, 1, 1), "end_date": datetime.date(2020, 12, 31)},
                              "gültig bis 31.12.2019 und ab 01.01.2019")
    assert checks["end_date"]["status"] == "berechnet"
    assert checks["start_date"]["status"] == "gefunden"


def test_short_forms_of_a_date_are_still_found():
    assert fc.assess_fields({"start_date": datetime.date(2018, 5, 8)}, "Beginn 8.5.18 Uhr")["start_date"]["status"] == "gefunden"


# The extractor stores the regional class as "R4" (normalised), letters print just "4".
SCHEIN_REGIONALKLASSE = """Versicherungsschein
Schadenfreiheitsklasse     SF 12
Regionalklasse             4
Typklasse                  18
Beitrag 38,40 EUR, Vertrag 4 Jahre
"""


def test_a_regional_class_is_found_behind_its_label_even_without_the_r():
    entry = fc.assess_fields({"regional_class": "R4"}, SCHEIN_REGIONALKLASSE)["regional_class"]
    assert entry["status"] == "gefunden"
    assert entry["seite"] == 1 and "Regionalklasse" in entry["stelle"]


def test_the_regional_class_with_its_r_is_still_found():
    assert fc.assess_fields({"regional_class": "R4"}, "Regionalklasse R4\n")["regional_class"]["status"] == "gefunden"
    assert fc.assess_fields({"regional_class": "R4"}, "Regionalklasse: R 4\n")["regional_class"]["status"] == "gefunden"


def test_a_number_that_is_not_behind_the_label_does_not_count_as_the_regional_class():
    text = "Regionalklasse 14\nBeitrag 38,40 EUR, Vertrag 4 Jahre\n"
    assert fc.assess_fields({"regional_class": "R4"}, text)["regional_class"]["status"] == "unsicher"
    assert fc.assess_fields({"regional_class": "R4"}, "Typklasse 18\nKlasse 4\n")["regional_class"]["status"] == "unsicher"


def test_the_demo_letter_has_no_unsure_value_left():
    import ocr
    data = ocr.extract_insurance_data(SCHEIN_REGIONALKLASSE.replace("Versicherungsschein", "Nordlicht Versicherung AG\nVersicherungsschein\nVersicherungsbeginn 01.03.2019\nVertragsende 01.03.2027"))
    assert data["regional_class"] == "R4"
    assert data["field_checks"]["regional_class"]["status"] == "gefunden"

# Copyright (c) 2026 Dennis Guse
# SPDX-License-Identifier: MIT
# See the LICENSE file in the project root.

"""The end of the term under its different names, and what happens when the letter names none."""

import datetime

import pytest

import ocr
from field_checks import assess_fields

SCHEIN = """Nordlicht Versicherung AG                      Beispielstadt, 12.01.2026
Musterweg 1
12345 Beispielstadt

Versicherungsschein

Kfz-Versicherung für Ihr Fahrzeug - Vollkasko

Versicherungsnummer        NL-4411-8032
Versicherungsnehmer        Erika Mustermann, Musterstraße 12, 12345 Beispielstadt
Versicherungsbeginn        01.03.2019
{ende_zeile}
Zahlweise                  monatlich
Beitrag                    38,40 EUR monatlich
Schadenfreiheitsklasse     SF 12
Regionalklasse             4
Typklasse                  18
Selbstbeteiligung          Vollkasko 500 EUR

Die Versicherung verlängert sich jeweils um ein Jahr, wenn sie nicht spätestens einen Monat vor Ablauf schriftlich gekündigt wird.
"""

ENDE = datetime.date(2027, 3, 1)


@pytest.mark.parametrize("zeile", [
    "Vertragsende               01.03.2027",
    "Hauptfälligkeit            01.03.2027",
    "Hauptfälligkeit/Ablauf     01.03.2027",
    "Versicherungsende          01.03.2027",
    "Ablauftermin               01.03.2027",
    "Laufzeit bis               01.03.2027",
    "Vertragsende am 01.03.2027",
    # these worked before and must keep working
    "Versicherungsablauf        01.03.2027",
    "Vertragsablauf            01.03.2027",
    "Ablauf                     01.03.2027",
    "Ablauf:                    01.03.2027",
    "Gültig bis                 01.03.2027",
])
def test_the_end_of_the_term_is_read_under_each_name(zeile):
    data = ocr.extract_insurance_data(SCHEIN.format(ende_zeile=zeile))
    assert data["start_date"] == datetime.date(2019, 3, 1)
    assert data["end_date"] == ENDE
    assert data["cancellation_date"] == datetime.date(2027, 2, 1)
    checks = data["field_checks"]
    assert checks["end_date"]["status"] == "gefunden"
    assert checks["cancellation_date"]["status"] == "berechnet"


def test_the_rest_of_the_demo_letter_is_still_read():
    data = ocr.extract_insurance_data(SCHEIN.format(ende_zeile="Vertragsende               01.03.2027"))
    assert data["cost"] == 38.4
    assert data["sf_class"] == "SF 12"
    assert data["insurance_number"] == "NL-4411-8032"


def test_a_sentence_about_the_notice_period_is_no_end_date():
    text = SCHEIN.format(ende_zeile="Zahlweise                  monatlich")
    assert "vor Ablauf schriftlich" in text
    assert ocr.extract_insurance_data(text)["end_date"] != ENDE


# --- no end date in the letter: the next anniversary of the start, not a date long gone ----------

TODAY = datetime.date(2026, 10, 6)


@pytest.mark.parametrize("start,expected", [
    (datetime.date(2019, 3, 1), datetime.date(2027, 2, 28)),    # period 01.03.2026-28.02.2027 is running
    (datetime.date(2026, 3, 1), datetime.date(2027, 2, 28)),
    (datetime.date(2026, 10, 6), datetime.date(2027, 10, 5)),   # starts today: first period
    (datetime.date(2026, 10, 7), datetime.date(2027, 10, 6)),   # starts tomorrow: first period
    (datetime.date(2025, 10, 6), datetime.date(2027, 10, 5)),   # period ended yesterday: next one
    (datetime.date(2025, 10, 7), datetime.date(2026, 10, 6)),   # period ends today: still running
    (datetime.date(2020, 2, 29), datetime.date(2027, 2, 27)),   # leap day: 28.02. is the anniversary
])
def test_without_an_end_date_the_current_period_of_the_contract_ends(start, expected):
    _, end, notice = ocr.calculate_insurance_dates(start, None, None, "", today=TODAY)
    assert end == expected
    assert end >= TODAY
    assert notice == ocr.one_month_before(expected)


def test_a_stated_end_date_is_never_replaced_by_the_fallback():
    _, end, _ = ocr.calculate_insurance_dates(datetime.date(2019, 3, 1), datetime.date(2022, 6, 30), None, "", today=TODAY)
    assert end == datetime.date(2022, 6, 30)


def test_the_extractor_uses_the_running_period_and_says_so():
    text = SCHEIN.format(ende_zeile="Zahlweise                  vierteljährlich")
    data = ocr.extract_insurance_data(text)
    assert data["start_date"] == datetime.date(2019, 3, 1)
    assert data["end_date"] >= datetime.date.today()
    assert data["end_date"].month == 2 and data["end_date"].day in (28, 29)
    entry = data["field_checks"]["end_date"]
    assert entry["status"] == "berechnet"
    assert "kein Ablaufdatum" in entry["grund"]
    assert data["field_checks"]["cancellation_date"]["status"] == "berechnet"


def test_the_check_explains_the_fallback_without_claiming_one_year():
    entry = assess_fields({"start_date": datetime.date(2019, 3, 1), "end_date": datetime.date(2027, 2, 28)}, "kein Datum")["end_date"]
    assert entry["status"] == "berechnet"
    assert "Beginn plus ein Jahr" not in entry["grund"]

# Copyright (c) 2026 Dennis Guse
# SPDX-License-Identifier: MIT
# See the LICENSE file in the project root.

"""Suggested document names. The texts are invented but follow the layout of real
letters (Beitragsrechnung, Nachtrag, Versicherungsschein, information leaflets)."""

import datetime

import pytest

import document_naming as dn

BEITRAGSRECHNUNG = """IV-KFRE001 01.21
Itzehoer Versicherungen
Max Mustermann
Musterstraße 1
Beitragsrechnung zur Kfz-Versicherungs-Nr. XX-12345678-001
01.01.2021 wird der monatliche Beitrag für den Zeitraum 01.01.2021 bis 31.01.2021 fällig.
Gesamtbeitrag inkl. 19 % Versicherungssteuer (9,98 €) 62,48 €
"""

NACHTRAG = """FKF055 01.11.2017
Itzehoer Versicherungen
Nachtrag Versicherungsschein-Nummer
zur Kraftfahrtversicherung XX-12345678-001
Beginn der Änderung 08.05.2018 00:00 Uhr Ablauf 31.12.2018 24:00 Uhr
Beitrag (inklusive Versicherungsteuer) 43,40 €
"""

NACHTRAG_VERTRAGSENDE = """FKF054 01.11.2017
Nachtrag Versicherungsschein-Nummer
zur Kraftfahrtversicherung XX-12345678-001
Beginn der Änderung =, 00:00 Uhr Ablauf 08.05.2018 24:00 Uhr
Der zwischen uns geschlossene Vertrag ist beendet.
Erstattungsbeitrag (ohne Versicherungsteuer) vom 09.05.2018 bis 31.05.2018
"""

VERSICHERUNGSSCHEIN = """669246004Q
HUK24 AG, HUK-COBURG-Platz 1, 96440 Coburg
Max Mustermann
Coburg, 24.07.2026
Versicherungsschein - Kraftfahrtversicherung Nr. 669/246004-Q
Jahresbeitrag Gültig ab 24.07.2026 29,29 €
"""

SCHADENVISITENKARTE = """B024 Stand: 07.2019
HUK24, 96440 Coburg
Max Mustermann
Coburg, 24.07.2026
Kraftfahrtversicherung 669/246004-Q
Es gab einen Unfall mit Ihrem Fahrzeug? Wir helfen.
heute erhalten Sie Ihre Schadenvisitenkarten:
"""

PRODUKTINFO = """--- Page 1 ---
Produktinformationsblatt
Allgemeine Bedingungen für die Kfz-Versicherung (AKB)
Information zur Verwendung Ihrer Daten
Ein Folgebeitrag ist zu dem im Versicherungsschein oder in der Beitragsrechnung genannten Zeitpunkt zu zahlen.
"""

VERBRAUCHERINFO = """K500 09.17
Itzehoer Versicherungen
Verbraucherinformationen
für Kraftfahrtversicherungen
7. Gesamtpreis der Versicherung
"""

GRUENE_KARTE = """IV-KFGK001 01.18
Itzehoer
Max Mustermann
Wichtige Hinweise auf der Rückseite!
1. Internationale Versicherungskarte für Kraftverkehr
1. International Motor Insurance Card
"""

FOOTER_ONLY = """Seite 1
Ihre Daten werden zum im Betreff genannten Zweck gespeichert. Ausführliche Informationen zur Datenverarbeitung finden Sie im Internet.
"""


@pytest.mark.parametrize("text,company,category,expected", [
    (BEITRAGSRECHNUNG, "Itzehoer", "Kfz", "Itzehoer Kfz-Beitragsrechnung Januar 2021"),
    (NACHTRAG, "Itzehoer", "Kfz", "Itzehoer Kfz-Nachtrag 08.05.2018"),
    (NACHTRAG_VERTRAGSENDE, "Itzehoer", "Kfz", "Itzehoer Kfz-Nachtrag zum Vertragsende 08.05.2018"),
    (VERSICHERUNGSSCHEIN, "HUK-COBURG", "Kfz", "HUK24 Kfz-Versicherungsschein 24.07.2026"),
    (SCHADENVISITENKARTE, "HUK-COBURG", "Kfz", "HUK24 Kfz-Schadenvisitenkarten 24.07.2026"),
    (PRODUKTINFO, "HUK-COBURG", "Kfz", "HUK-COBURG Produktinformationsblatt und Bedingungen"),
    (VERBRAUCHERINFO, "Itzehoer", "Kfz", "Itzehoer Verbraucherinformationen"),
    (GRUENE_KARTE, "Itzehoer", "Kfz", "Itzehoer Grüne Karte"),
])
def test_names_follow_company_kind_and_date(text, company, category, expected):
    assert dn.suggest_title(company, category, text) == expected


def test_policy_numbers_never_appear_in_the_name():
    for text in (BEITRAGSRECHNUNG, NACHTRAG, VERSICHERUNGSSCHEIN, SCHADENVISITENKARTE):
        title = dn.suggest_title("Itzehoer", "Kfz", text)
        assert "12345678" not in title and "246004" not in title


def test_footer_sentences_are_never_used_as_a_name():
    title = dn.suggest_title(None, None, FOOTER_ONLY, today=datetime.date(2026, 10, 3))
    assert title == "Dokument vom 03.10.2026"
    assert "gespeichert" not in title


def test_other_categories_prefix_and_unknown_category_is_left_out():
    assert dn.suggest_title("Allianz", "Haftpflicht", BEITRAGSRECHNUNG) == "Allianz Haftpflicht-Beitragsrechnung Januar 2021"
    assert dn.suggest_title("Allianz", "Sonstige", BEITRAGSRECHNUNG) == "Allianz Beitragsrechnung Januar 2021"
    assert dn.suggest_title("Allianz", None, BEITRAGSRECHNUNG) == "Allianz Beitragsrechnung Januar 2021"


def test_missing_company_or_date_degrades_gracefully():
    assert dn.suggest_title(None, "Kfz", BEITRAGSRECHNUNG) == "Kfz-Beitragsrechnung Januar 2021"
    assert dn.suggest_title("Itzehoer", "Kfz", "Beitragsrechnung\nohne Datum") == "Itzehoer Kfz-Beitragsrechnung"


def test_a_mention_deep_in_the_text_does_not_decide_the_kind():
    # long terms documents mention "Beitragsrechnung" and "Versicherungsschein" in running text
    text = "Allgemeine Bedingungen\n" + "Zeile\n" * 40 + "Beitragsrechnung\nNachtrag zur Police\n"
    assert dn.detect_kind(text) == "Allgemeine Bedingungen"


def test_names_are_short_enough_for_lists():
    assert len(dn.suggest_title("Eine Sehr Lange Versicherungsgesellschaft " * 5, "Kfz", BEITRAGSRECHNUNG)) <= 90


def test_the_billing_month_is_found_below_a_long_letterhead():
    lines = ["Beitragsrechnung zur Kfz-Versicherungs-Nr. XX-12345678-001"] + [f"Kopfzeile {i}" for i in range(30)]
    lines.append("01.01.2019 wird der monatliche Beitrag für den Zeitraum 01.01.2019 bis 31.01.2019 fällig.")
    text = chr(10).join(lines)
    assert dn.suggest_title("Itzehoer", "Kfz", text) == "Itzehoer Kfz-Beitragsrechnung Januar 2019"

# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""Document kind -> document type, and amounts that must never be read wrongly.
The texts are invented but follow the layout of real letters."""

import pytest

import document_types as dt
import ocr

NACHTRAG_2015 = """FKF055 01.11.2015
Itzehoer Versicherungen
Nachtrag Versicherungsschein-Nummer
zur Kraftfahrtversicherung XX-12345678-001
Beginn der Änderung 01.03.2016 00:00 Uhr Ablauf 31.12.2016 24:00 Uhr
Zahlungsperiode monatlich
Ihr monatlicher Beitrag ohne Versicherungsteuer
Kfz-Haftpflicht 34,80 €
Teilkasko 7,00 €
41,80 €
Versicherungsteuer (19%) 7,94 €
Beitrag (inklusive Versicherungsteuer) 49,74 €
Der nächste Beitrag wird fällig am 01.03.2016.
Gesamtabrechnung
Versicherungsteuer (19%) 1,66- €
Zwischensumme 10,42- €
Ihr Konto für diesen Vertrag war
am 18.01.2016 ausgeglichen
Wir erstatten Ihnen in den nächsten Tagen 10,42- €
Das Guthaben von 10,42 € wird in den nächsten Tagen auf das Konto erstattet.
Zukünftig wird der monatliche Beitrag von 49,74 €, beginnend mit dem 01.03.2016,
mit der SEPA-Lastschrift eingezogen.
"""

NACHTRAG_2018 = """FKF055 01.11.2017
Itzehoer Versicherungen
Nachtrag Versicherungsschein-Nummer
zur Kraftfahrtversicherung XX-12345678-001
Beginn der Änderung 08.05.2018 00:00 Uhr Ablauf 31.12.2018 24:00 Uhr
Beitrag (inklusive Versicherungsteuer) 43,40 €
Der nächste Beitrag wird fällig am 01.06.2018.
Zwischensumme 31,44 €
Ihr Konto für diesen Vertrag hatte
am 04.05.2018 folgenden Stand Guthaben 40,33- €
Wir erstatten Ihnen in den nächsten Tagen 8,89- €
Zukünftig wird der monatliche Beitrag von 43,40 €, beginnend mit dem 01.06.2018,
"""

VERTRAGSENDE = """FKF054 01.11.2017
Itzehoer Versicherungen
Nachtrag Versicherungsschein-Nummer
zur Kraftfahrtversicherung XX-12345678-001
Beginn der Änderung =, 00:00 Uhr Ablauf 08.05.2018 24:00 Uhr
Zahlungsperiode monatlich
Der zwischen uns geschlossene Vertrag ist beendet.
Gesamtabrechnung
Erstattungsbeitrag (ohne Versicherungsteuer) vom 09.05.2018 bis 31.05.2018
Kfz-Haftpflicht 28,29- €
Teilkasko 5,60- €
33,89- €
Versicherungsteuer (19%) 6,44- €
Zwischensumme 40,33- €
Das Guthaben wird Ihrem Beitragskonto gutgeschrieben.
"""

BEITRAGSRECHNUNG = """IV-KFRE001 01.21
Itzehoer Versicherungen
Beitragsrechnung zur Kfz-Versicherungs-Nr. XX-12345678-001
01.01.2021 wird der monatliche Beitrag für den Zeitraum 01.01.2021 bis 31.01.2021 fällig.
Kfz-Haftpflicht R05 18 SF1 (75%) 50,51 €
Teilkasko R06 20 11,97 €
Gesamtbeitrag inkl. 19 % Versicherungssteuer (9,98 €) 62,48 €
Teilkasko mit 150 € Selbstbeteiligung
"""

HUK_POLICE = """669246004Q
HUK24 AG, HUK-COBURG-Platz 1, 96440 Coburg
Coburg, 24.07.2026
Versicherungsschein - Kraftfahrtversicherung Nr. 669/246004-Q
Wichtiger Hinweis Wir buchen den fälligen Erstbeitrag in Höhe von 29,26 € von Ihrem Konto ab.
Kfz-Haftpflichtversicherung 100 Mio. € Versicherungssumme für Personen-, Sach- und Ver- 17,95 €
Kaskoversicherung Teilkasko 150 € Selbstbeteiligung 11,34 €
Versicherter Fahrzeugwert 1.800,00 €
Jahresbeitrag Gültig ab 24.07.2026 29,29 €
Erstbeitrag (inkl. 19 % VerSt = 4,68 €) 29,26
Aktuelle Forderung von  29,26 €  frühestens ab 05.08.2026
"""

VERBRAUCHERINFO = """K500 09.17
Itzehoer Versicherungen
Verbraucherinformationen
für Kraftfahrtversicherungen
Regionalklasse 1 bis 12, Typklasse 10 bis 25, SF 1/2 bis SF 35
Bei Zahlungsverzug berechnen wir eine Mahngebühr von 3,00 €.
Die Kündigung ist zum Ablauf mit einer Frist von einem Monat möglich.
Gültig ab 01.01.2018 bis 31.12.2018
Kfz-Haftpflicht Teilkasko Vollkasko
"""

PRODUKTINFO = """--- Page 1 ---
Produktinformationsblatt
Allgemeine Bedingungen für die Kfz-Versicherung (AKB)
Ein Folgebeitrag ist zu dem im Versicherungsschein oder in der Beitragsrechnung genannten Zeitpunkt zu zahlen.
Der Beitrag beträgt 12,50 € monatlich. Beitragsanpassung ist möglich.
Teilkasko mit 150 € Selbstbeteiligung
"""

GRUENE_KARTE = """IV-KFGK001 01.18
Itzehoer
Wichtige Hinweise auf der Rückseite!
1. Internationale Versicherungskarte für Kraftverkehr
1. International Motor Insurance Card
Gültig vom 01.01.2018 bis 01.01.2019
"""

BEITRAGSANPASSUNG = """K123 01.20
Allianz Versicherungs-AG
Max Mustermann
Beitragsanpassung zu Ihrer Privathaftpflichtversicherung
Ihr neuer Beitrag beträgt ab dem 01.01.2021 jährlich 84,50 €.
Bisher zahlten Sie 79,00 €.
"""


def finalize(text, **fields):
    data = ocr.extract_insurance_data_regex(text)
    data.update(fields)
    return ocr.finalize_extraction(data, text)


# ----- Punkt 9: Dokumentart ------------------------------------------------------------

@pytest.mark.parametrize("text,kind,doc_type", [
    (HUK_POLICE, "Versicherungsschein", "Versicherungsschein / Polizze"),
    (BEITRAGSRECHNUNG, "Beitragsrechnung", "Beitragsrechnung"),
    (NACHTRAG_2018, "Nachtrag", "Nachtrag / Änderungsschein"),
    (VERTRAGSENDE, "Nachtrag zum Vertragsende", "Nachtrag / Änderungsschein"),
    (BEITRAGSANPASSUNG, "Beitragsanpassung", "Beitragsanpassung"),
    (VERBRAUCHERINFO, "Verbraucherinformationen", "Verbraucherinformationen"),
    (PRODUKTINFO, "Produktinformationsblatt und Bedingungen", "Kundeninformationen"),
    (GRUENE_KARTE, "Grüne Karte", "Sonstiges"),
])
def test_the_kind_of_letter_decides_the_document_type(text, kind, doc_type):
    result = finalize(text)
    assert result["document_kind"] == kind
    assert result["doc_type"] == doc_type


def test_the_insurance_type_is_kept_separately_from_the_document_type():
    result = finalize(BEITRAGSRECHNUNG)
    assert result["insurance_type"] == "Kfz-Versicherung"
    assert result["category"] == "Kfz"


@pytest.mark.parametrize("text", [VERBRAUCHERINFO, PRODUKTINFO, GRUENE_KARTE])
def test_information_documents_deliver_no_contract_data(text):
    result = finalize(text)
    assert dt.is_informational(result["doc_type"])
    for field in dt.CONTRACT_FIELDS:
        assert result.get(field) is None, field
    assert result["coverage_details"] == []
    assert not result.get("is_price_change")


def test_a_word_in_the_running_text_does_not_turn_an_information_document_into_a_price_change():
    # "Beitragsanpassung ist möglich" stands in the product sheet; the old rule made it one
    assert finalize(PRODUKTINFO)["doc_type"] == "Kundeninformationen"


def test_information_documents_keep_company_and_category():
    result = finalize(VERBRAUCHERINFO)
    assert result["company"] == "Itzehoer"
    assert result["category"] == "Kfz"


def test_unknown_letters_keep_the_default_type_and_their_data():
    text = "Itzehoer Versicherungen\nIhre Kfz-Versicherung\nBeitrag: 12,34 €\n"
    result = finalize(text)
    assert result["document_kind"] is None
    assert result["doc_type"] == dt.DEFAULT_DOC_TYPE
    assert result["cost"] == 12.34


@pytest.mark.parametrize("value,expected", [
    ("Sonstiges", True), ("Verbraucherinformationen", True), ("Kundeninformationen", True),
    ("Produktinformationsblatt", True), ("Beratungsprotokoll", True), ("sonstiges", True),
    ("Versicherungsschein / Polizze", False), ("Beitragsrechnung", False),
    ("Beitragsanpassung", False), ("Nachtrag / Änderungsschein", False), ("", False), (None, False),
])
def test_is_informational(value, expected):
    assert dt.is_informational(value) is expected


# ----- Punkt 10: Beträge ---------------------------------------------------------------

def test_the_future_monthly_premium_is_the_cost_not_the_credit():
    result = finalize(NACHTRAG_2015)
    assert result["cost"] == 49.74
    assert result["refund_amount"] == 10.42


def test_the_premium_including_tax_wins_over_credit_and_subtotal():
    result = finalize(NACHTRAG_2018)
    assert result["cost"] == 43.40
    assert result["refund_amount"] == 8.89


def test_a_terminated_contract_has_no_cost_but_a_refund():
    result = finalize(VERTRAGSENDE)
    assert result["cost"] is None
    assert result["new_cost"] is None
    assert result["refund_amount"] == 40.33


def test_total_premium_line_still_works_and_the_deductible_is_ignored():
    assert finalize(BEITRAGSRECHNUNG)["cost"] == 62.48
    assert finalize(BEITRAGSRECHNUNG)["refund_amount"] is None


def test_the_annual_premium_beats_the_first_payment():
    assert finalize(HUK_POLICE)["cost"] == 29.29


def test_cost_is_never_negative():
    assert ocr.extract_cost_fallback("Beitrag 12,00- €") is None
    assert ocr.extract_cost_fallback("Zwischensumme 10,42- €") is None
    assert ocr.extract_cost_fallback("Guthaben 40,33- €") is None


def test_a_negative_cost_from_the_model_is_dropped():
    result = finalize("Itzehoer Versicherungen\nIhre Kfz-Versicherung\n", cost=-40.33)
    assert result["cost"] is None


def test_refund_amount_prefers_what_is_actually_paid_out():
    text = "Zwischensumme 31,44 €\nGuthaben 40,33- €\nWir erstatten Ihnen in den nächsten Tagen 8,89- €\n"
    assert ocr.extract_refund_amount(text) == 8.89
    assert ocr.extract_refund_amount("Beitrag 12,00 €") is None
    assert ocr.extract_refund_amount("") is None


# ----- Schutz beim Hochladen ----------------------------------------------------------------

def _upload(client, headers, insurance_id, doc_type, extracted):
    import json
    return client.post(
        f"/api/documents?insurance_id={insurance_id}&original_filename=brief.pdf",
        headers=headers,
        data={"doc_type": doc_type, "custom_name": "Brief", "extracted_data": json.dumps(extracted)},
        files={"file": ("brief.pdf", b"%PDF-1.4 test", "application/pdf")},
    )


def test_an_information_document_never_changes_cost_or_premium_history(client, make_user):
    _, _, headers = make_user()
    created = client.post("/api/insurances", headers=headers, json={
        "name": "Kfz", "company": "Itzehoer", "category": "Kfz", "cost": 55.0, "payment_cycle": "monatlich"})
    assert created.status_code == 200, created.text
    ins_id = created.json()["id"]
    history_before = len(client.get(f"/api/insurances/{ins_id}", headers=headers).json()["premium_history"])

    # what an older client (or a wrong guess) could still deliver: a cost on an information document
    extracted = {"extracted_text": "Verbraucherinformationen", "doc_type": "Verbraucherinformationen",
                 "cost": 3.0, "new_cost": 3.0, "payment_cycle": "monatlich"}
    assert _upload(client, headers, ins_id, "Verbraucherinformationen", extracted).status_code == 200

    after = client.get(f"/api/insurances/{ins_id}", headers=headers).json()
    assert after["cost"] == 55.0
    assert len(after["premium_history"]) == history_before


def test_a_premium_letter_still_updates_cost_and_history(client, make_user):
    _, _, headers = make_user()
    ins_id = client.post("/api/insurances", headers=headers, json={
        "name": "Kfz", "company": "Itzehoer", "category": "Kfz", "cost": 55.0, "payment_cycle": "monatlich"}).json()["id"]
    extracted = {"extracted_text": "Beitragsrechnung", "doc_type": "Beitragsrechnung",
                 "cost": 62.48, "payment_cycle": "monatlich", "start_date": "2021-01-01"}
    assert _upload(client, headers, ins_id, "Beitragsrechnung", extracted).status_code == 200

    after = client.get(f"/api/insurances/{ins_id}", headers=headers).json()
    assert after["cost"] == 62.48
    assert any(h["cost"] == 62.48 for h in after["premium_history"])


# ----- Fehler, die der Prüfstand mit echten Dokumenten aufgedeckt hat -----------------------

def test_the_type_class_is_read_from_the_first_row_of_the_premium_table():
    text = "Itzehoer Versicherungen\nBeitragsrechnung zur Kfz-Versicherung\nKfz-Haftpflicht R05 18 SF 3 (65 %) 43,47 €\nTeilkasko R05 21 12,30 €\n"
    assert ocr.extract_insurance_data_regex(text)["type_class"] == "18"


def test_a_garbled_first_row_gives_no_type_class_rather_than_the_one_of_the_previous_year():
    text = ("Itzehoer Versicherungen\nBeitragsrechnung zur Kfz-Versicherung\nKfz-Haftpflicht R05 In SF7 (51%) 45,91€\n"
            "Beitragsvergleich\nKfz-Haftpflicht ROS 16 SF6 (53%) 40,87€ 39,32 € 45,91€\n")
    assert ocr.extract_insurance_data_regex(text).get("type_class") is None


def test_an_ocr_split_region_token_does_not_hide_the_type_class():
    text = "Itzehoer Versicherungen\nKfz-Haftpflicht — Ron 18 SF 8 (50 %) 32,95 €\n"
    assert ocr.extract_insurance_data_regex(text)["type_class"] == "18"


def test_a_balance_date_is_not_the_start_of_the_contract():
    text = "Nachtrag zur Kraftfahrtversicherung\nBeginn der Änderung --.--.---- 00:00 Uhr Ablauf 08.05.2018 24:00 Uhr\nIhr Konto für diesen Vertrag war\nam 30.04.2018 ausgeglichen\n"
    assert ocr.extract_insurance_data_regex(text)["start_date"] is None


def test_huk24_letters_name_huk24_not_huk_coburg():
    text = "HUK24 AG, HUK-COBURG-Platz 1, 96440 Coburg\nVersicherungsschein - Kraftfahrtversicherung Nr. 669/246004-Q\n"
    assert ocr.extract_insurance_data_regex(text)["company"] == "HUK24"
    assert ocr.extract_insurance_data_regex("HUK-COBURG Versicherungen\nBeitragsrechnung\n")["company"] == "HUK-COBURG"


def test_a_region_class_whose_digit_ocr_lost_is_skipped_for_the_next_mention():
    # "RO 18" is the current row with the 5 lost; the comparison row still says RO5
    text = "Kfz-Haftpflicht RO 18 SF3 (65 %) 43,47 €\nBeitragsvergleich\nKfz-Haftpflicht RO5 18 SF8 (50%) 32,95 €\n"
    assert ocr.extract_regionalklasse_fallback(text) == "R05"


def test_regional_classes_run_from_1_to_12():
    assert ocr.extract_regionalklasse_fallback("Regionalklasse R12") == "R12"
    assert ocr.extract_regionalklasse_fallback("Regionalklasse R13") is None
    assert ocr.extract_regionalklasse_fallback("Tarifgruppe R0") is None


# ----- Leistungen (versicherte Risiken) ----------------------------------------------------

POLICE_MIT_BOILERPLATE = """HUK24 AG, HUK-COBURG-Platz 1, 96440 Coburg
Versicherungsschein - Kraftfahrtversicherung Nr. 669/246004-Q
Versicherungsumfang
Kfz-Haftpflichtversicherung 100 Mio. € Versicherungssumme für Personen-, Sach- und Vermögensschäden 17,95 €
Kaskoversicherung Teilkasko 150 € Selbstbeteiligung 11,34 €
Jahresbeitrag Gültig ab 24.07.2026 29,29 €
Kontoauszug
Neue Buchungen: Erstbeitrag 29,26
""" + "Zeile mit Hinweisen zur Zahlung des Erstbeitrags.\n" * 10 + """In der Kfz-Haftpflichtversicherung, beim Autoschutzbrief, beim Fahrerschutz und beim Ausland-Schadenschutz
haben Sie vorläufigen Versicherungsschutz.
II Vollkasko - Schutz vor finanziellen Folgen bei Beschädigung
"""


def _coverage_keys(text):
    result = ocr.extract_insurance_data_regex(text)
    return sorted({k for item in result["coverage_details"] for k in
                   ("haftpflicht", "schutzbrief", "teilkasko", "vollkasko", "fahrerschutz", "ausland", "umwelt")
                   if k in item.split("(")[0].lower()})


def test_general_sections_do_not_add_coverages_to_a_policy():
    assert _coverage_keys(POLICE_MIT_BOILERPLATE) == ["haftpflicht", "teilkasko"]


def test_the_scope_ends_at_the_first_general_section_but_only_after_the_letterhead():
    text = "x" * 400 + "\nBesonders zu beachten:\nVollkasko Schutzbrief"
    assert ocr.coverage_scope(text) == "x" * 400 + "\n"
    short = "Besonders zu beachten:\nTeilkasko mit 150 € Selbstbeteiligung"
    assert ocr.coverage_scope(short) == short       # a heading at the very top is not a boundary


def test_a_compound_word_in_boilerplate_is_no_vollkasko():
    text = ("Itzehoer Versicherungen\nKfz-Haftpflicht\nTeilkasko mit 150 € Selbstbeteiligung\n"
            "Sie haben uns berechtigt, bei Beendigung eines Kfz-Haftpflicht- oder Vollkaskovertrags Daten zu übermitteln.\n")
    assert "vollkasko" not in _coverage_keys(text)
    assert "vollkasko" in _coverage_keys("Itzehoer\nVollkasko mit 500 € Selbstbeteiligung\n")


def test_a_terminated_contract_covers_nothing():
    text = ("Itzehoer Versicherungen\nNachtrag zur Kraftfahrtversicherung\nDer zwischen uns geschlossene Vertrag ist beendet.\n"
            "Erstattungsbeitrag\nKfz-Haftpflicht 28,29- €\nTeilkasko 5,60- €\nZwischensumme 40,33- €\n")
    assert ocr.extract_insurance_data(text)["coverage_details"] == []


def test_the_instruction_for_the_model_names_no_example_values():
    # the small model repeats examples: an insurer from the instruction showed up in letters of other
    # insurers, and the example coverages came back unchanged for every document
    prompt = ocr.build_ai_prompt("Beispieltext", with_prefill=False)
    for example in ("HUK", "Allianz", "AXA", "Schutzbrief", "Kfz-Haftpflichtversicherung", "SF 15", "Muster"):
        assert example not in prompt
    assert "coverage_details" not in prompt
    assert "coverage_details" not in ocr._answer_schema()["properties"]

# Copyright (c) 2026 Dennis Guse
# SPDX-License-Identifier: MIT
# See the LICENSE file in the project root.

"""Notice date, end of a terminated contract, and which letters may change the term of a contract."""

import datetime

import pytest

import document_types as dt
import ocr
import routers.documents as documents_router


@pytest.mark.parametrize("end,expected", [
    (datetime.date(2018, 12, 31), datetime.date(2018, 11, 30)),   # was 28.11.
    (datetime.date(2027, 7, 23), datetime.date(2027, 6, 23)),
    (datetime.date(2019, 3, 31), datetime.date(2019, 2, 28)),     # shorter month: its last day
    (datetime.date(2020, 3, 31), datetime.date(2020, 2, 29)),     # leap year
    (datetime.date(2021, 1, 31), datetime.date(2020, 12, 31)),    # into the previous year
    (datetime.date(2021, 5, 31), datetime.date(2021, 4, 30)),
    (datetime.date(2021, 8, 15), datetime.date(2021, 7, 15)),
])
def test_the_notice_date_is_one_month_before_the_end(end, expected):
    assert ocr.one_month_before(end) == expected


def test_the_extractor_uses_it():
    _, end, notice = ocr.calculate_insurance_dates(None, "2018-12-31", None, "")
    assert end == datetime.date(2018, 12, 31) and notice == datetime.date(2018, 11, 30)


VERTRAGSENDE = """Itzehoer Versicherungen
Nachtrag Versicherungsschein-Nummer
zur Kraftfahrtversicherung XX-12345678-001
Beginn der Änderung --.--.---- 00:00 Uhr Ablauf 08.05.2018 24:00 Uhr
Der zwischen uns geschlossene Vertrag ist beendet.
Zwischensumme 40,33- €
"""


def test_a_terminated_contract_keeps_its_end_but_has_no_notice_date():
    data = ocr.extract_insurance_data(VERTRAGSENDE)
    assert data["end_date"] == datetime.date(2018, 5, 8)
    assert data["cancellation_date"] is None
    assert data["start_date"] is None


@pytest.mark.parametrize("doc_type,start,end", [
    ("Versicherungsschein / Polizze", True, True),
    ("Nachtrag / Änderungsschein", False, True),
    ("Beitragsrechnung", False, False),
    ("Beitragsanpassung", False, False),
    ("Schadenmeldung", False, False),
    ("Sonstiges", False, False),
    (None, False, False),
])
def test_which_letters_may_change_the_term_of_a_contract(doc_type, start, end):
    assert dt.may_set_start(doc_type) is start
    assert dt.may_set_end(doc_type) is end


# ----- re-analysis of a stored document -------------------------------------------------------

def _setup(client, make_user, doc_type):
    _, _, headers = make_user()
    ins = client.post("/api/insurances", headers=headers, json={
        "name": "Kfz", "company": "Itzehoer", "category": "Kfz", "cost": 50.0,
        "start_date": "2015-01-01", "end_date": "2030-12-31", "cancellation_date": "2030-11-30"})
    assert ins.status_code == 200, ins.text
    ins_id = ins.json()["id"]
    doc = client.post(f"/api/documents?insurance_id={ins_id}&original_filename=brief.pdf", headers=headers,
                      data={"doc_type": doc_type, "custom_name": "Brief"},
                      files={"file": ("brief.pdf", b"%PDF-1.4 " + doc_type.encode(), "application/pdf")})
    assert doc.status_code == 200, doc.text
    return headers, ins_id, doc.json()["id"]


def _reanalyze(client, headers, doc_id, monkeypatch, extracted):
    monkeypatch.setattr(documents_router.ocr, "extract_text_from_file", lambda path: "Text")
    monkeypatch.setattr(documents_router.ocr, "extract_insurance_data", lambda text, db=None: dict(extracted))
    r = client.post(f"/api/documents/{doc_id}/reanalyze", headers=headers)
    assert r.status_code == 200, r.text


EXTRACTED = {"doc_type": "Beitragsrechnung", "cost": 62.48, "payment_cycle": "monatlich",
             "start_date": datetime.date(2021, 1, 1), "end_date": datetime.date(2021, 12, 31),
             "cancellation_date": datetime.date(2021, 11, 30)}


def test_an_invoice_changes_the_premium_but_not_the_term(client, make_user, monkeypatch):
    headers, ins_id, doc_id = _setup(client, make_user, "Beitragsrechnung")
    _reanalyze(client, headers, doc_id, monkeypatch, EXTRACTED)
    ins = client.get(f"/api/insurances/{ins_id}", headers=headers).json()
    assert ins["cost"] == 62.48
    assert (ins["start_date"], ins["end_date"], ins["cancellation_date"]) == ("2015-01-01", "2030-12-31", "2030-11-30")


def test_a_supplement_sets_the_end_but_not_the_start(client, make_user, monkeypatch):
    headers, ins_id, doc_id = _setup(client, make_user, "Nachtrag / Änderungsschein")
    _reanalyze(client, headers, doc_id, monkeypatch, dict(EXTRACTED, doc_type="Nachtrag / Änderungsschein"))
    ins = client.get(f"/api/insurances/{ins_id}", headers=headers).json()
    assert ins["start_date"] == "2015-01-01"
    assert (ins["end_date"], ins["cancellation_date"]) == ("2021-12-31", "2021-11-30")


def test_a_policy_sets_start_and_end(client, make_user, monkeypatch):
    headers, ins_id, doc_id = _setup(client, make_user, "Versicherungsschein / Polizze")
    _reanalyze(client, headers, doc_id, monkeypatch, dict(EXTRACTED, doc_type="Versicherungsschein / Polizze"))
    ins = client.get(f"/api/insurances/{ins_id}", headers=headers).json()
    assert (ins["start_date"], ins["end_date"]) == ("2021-01-01", "2021-12-31")


def test_a_letter_about_a_terminated_contract_clears_the_notice_date(client, make_user, monkeypatch):
    headers, ins_id, doc_id = _setup(client, make_user, "Nachtrag / Änderungsschein")
    ended = {"doc_type": "Nachtrag / Änderungsschein", "document_kind": "Nachtrag zum Vertragsende",
             "end_date": datetime.date(2018, 5, 8), "cancellation_date": None}
    _reanalyze(client, headers, doc_id, monkeypatch, ended)
    ins = client.get(f"/api/insurances/{ins_id}", headers=headers).json()
    assert ins["end_date"] == "2018-05-08" and ins["cancellation_date"] is None

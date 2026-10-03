# Copyright (c) 2026 Dennis Guse
# SPDX-License-Identifier: MIT
# See the LICENSE file in the project root.

"""A file that was uploaded before is recognised by its SHA-256 - for the same user only."""

import json
import os

import document_hash

PDF_A = b"%PDF-1.4 erste Datei"
PDF_B = b"%PDF-1.4 zweite Datei"


def _extract(client, headers, content):
    r = client.post("/api/documents/extract", headers=headers, files={"file": ("scan.pdf", content, "application/pdf")})
    assert r.status_code == 200, r.text
    return r.json()


def _store(client, headers, insurance_id, content, extracted=None):
    data = {"doc_type": "Beitragsrechnung", "custom_name": "Rechnung Januar"}
    if extracted is not None:
        data["extracted_data"] = json.dumps(extracted)
    r = client.post(f"/api/documents?insurance_id={insurance_id}&original_filename=scan.pdf", headers=headers,
                    data=data, files={"file": ("scan.pdf", content, "application/pdf")})
    assert r.status_code == 200, r.text
    return r.json()


def _insurance(client, headers, name="Kfz Itzehoer"):
    r = client.post("/api/insurances", headers=headers, json={"name": name, "company": "Itzehoer", "category": "Kfz", "cost": 50.0})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_a_new_file_is_no_duplicate_and_a_stored_one_is(client, make_user):
    _, _, headers = make_user()
    ins_id = _insurance(client, headers)
    assert _extract(client, headers, PDF_A)["duplicate"] is None

    stored = _store(client, headers, ins_id, PDF_A)
    duplicate = _extract(client, headers, PDF_A)["duplicate"]
    assert duplicate["document_id"] == stored["id"]
    assert duplicate["name"] == "Rechnung Januar"
    assert duplicate["insurance_id"] == ins_id and duplicate["insurance_name"] == "Kfz Itzehoer"
    assert duplicate["in_inbox"] is False

    assert _extract(client, headers, PDF_B)["duplicate"] is None   # other content is no duplicate


def test_another_users_file_is_never_reported(client, make_user):
    _, _, alice = make_user("alice")
    _, _, bob = make_user("bob")
    _store(client, alice, _insurance(client, alice), PDF_A)
    assert _extract(client, bob, PDF_A)["duplicate"] is None


def test_the_hint_is_not_stored_with_the_document(client, make_user):
    _, _, headers = make_user()
    ins_id = _insurance(client, headers)
    first = _store(client, headers, ins_id, PDF_A)
    hint = _extract(client, headers, PDF_A)
    assert hint["duplicate"] is not None
    hint["extracted_text"] = hint["extracted_text"] or "Text"   # the upload only reuses a non-empty extraction
    second = _store(client, headers, ins_id, PDF_A, extracted=hint)
    from database import SessionLocal
    import models
    db = SessionLocal()
    try:
        stored = json.loads(db.query(models.Document).get(second["id"]).ai_data)
    finally:
        db.close()
    assert "duplicate" not in stored
    assert first["id"] != second["id"]    # the user may keep both: it only warns


def test_the_inbox_marks_the_later_copy(client, make_user):
    _, _, headers = make_user()
    for _ in range(2):
        assert client.post("/api/inbox/upload", headers=headers, files={"file": ("brief.pdf", PDF_A, "application/pdf")}).status_code == 200
    assert client.post("/api/inbox/upload", headers=headers, files={"file": ("anders.pdf", PDF_B, "application/pdf")}).status_code == 200
    listed = {d["id"]: d for d in client.get("/api/inbox", headers=headers).json()}
    ids = sorted(listed)
    assert listed[ids[0]]["duplicate_of"] is None
    assert listed[ids[1]]["duplicate_of"]["document_id"] == ids[0] and listed[ids[1]]["duplicate_of"]["in_inbox"] is True
    assert listed[ids[2]]["duplicate_of"] is None


def test_documents_stored_before_the_feature_are_fingerprinted_at_start(client, make_user):
    _, _, headers = make_user()
    ins_id = _insurance(client, headers)
    stored = _store(client, headers, ins_id, PDF_A)

    from database import SessionLocal
    import models
    db = SessionLocal()
    try:
        doc = db.query(models.Document).get(stored["id"])
        expected = doc.file_hash
        doc.file_hash = None                      # as before the feature
        db.commit()
    finally:
        db.close()

    assert document_hash.backfill_missing_hashes(SessionLocal) >= 1
    db = SessionLocal()
    try:
        assert db.query(models.Document).get(stored["id"]).file_hash == expected == document_hash.sha256_bytes(PDF_A)
    finally:
        db.close()
    assert _extract(client, headers, PDF_A)["duplicate"]["document_id"] == stored["id"]


def test_a_missing_file_is_skipped_by_the_backfill(client, make_user):
    from database import SessionLocal
    import models
    db = SessionLocal()
    try:
        db.add(models.Document(filename="gibt-es-nicht.pdf", original_filename="x.pdf", file_hash=None))
        db.commit()
    finally:
        db.close()
    document_hash.backfill_missing_hashes(SessionLocal)   # must not raise

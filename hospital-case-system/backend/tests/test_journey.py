"""Full 8-role OPD journey driven by one QR code."""
from datetime import date

from app.services.local_ai import tiny_wav_bytes


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert "docs" in client.get("/api/v1").json()


def test_full_journey(client, headers):
    # 1. patient books
    docs = client.get("/api/v1/doctors", params={"department_id": 1}).json()
    assert docs and docs[0]["system"] == "ALLOPATHIC"
    slots = client.get(f"/api/v1/doctors/{docs[0]['id']}/slots", params={"date": date.today().isoformat()}).json()
    assert slots and slots[0]["available"] > 0
    r = client.post("/api/v1/appointments", headers=headers["patient"],
                    json={"doctor_id": docs[0]["id"], "slot_id": slots[0]["id"], "chief_complaint": "burning stomach after meals for 2 weeks"})
    assert r.status_code == 201, r.text
    appt = r.json()
    assert appt["qr_code"].startswith(f"AIIA-CK-{appt['id']}-AIIA-2026-00001-")
    assert appt["status"] == "BOOKED"
    code = appt["qr_code"]

    # 2. forged code is rejected; reception scans the real one (only check-in path)
    assert client.post("/api/v1/reception/scan", headers=headers["reception"], json={"code": "AIIA-CK-999-FAKE-1"}).status_code == 404
    r = client.post("/api/v1/reception/scan", headers=headers["reception"], json={"code": code})
    assert r.status_code == 200 and r.json()["status"] == "CHECKED_IN"
    assert client.post("/api/v1/reception/scan", headers=headers["reception"], json={"code": code}).status_code == 409
    board = client.get("/api/v1/reception/board", headers=headers["reception"]).json()
    assert any(a["id"] == appt["id"] for a in board["checked_in"])

    # 3. nurse vitals
    r = client.post(f"/api/v1/nurse/vitals/{appt['id']}", headers=headers["nurse"], json={"bp": "120/80", "pulse": 78, "temp": 98.6, "weight": 64})
    assert r.status_code == 201
    today = client.get("/api/v1/nurse/today", headers=headers["nurse"]).json()
    assert any(a["id"] == appt["id"] and not a["vitals_missing"] for a in today)

    # 4. doctor calls in -> encounter
    q = client.get("/api/v1/queue", headers=headers["doctor_allo"]).json()
    assert any(a["id"] == appt["id"] for a in q)
    r = client.patch(f"/api/v1/queue/{appt['id']}/call-next", headers=headers["doctor_allo"])
    assert r.status_code == 200
    enc_id = r.json()["encounter_id"]
    # other doctor cannot act on this queue item
    assert client.patch(f"/api/v1/queue/{appt['id']}/skip", headers=headers["doctor_ayu"]).status_code == 403

    # 5. honest STT: no key, no whisper -> provider none, no fabricated text
    r = client.post("/api/v1/voice/transcribe-audio", headers=headers["doctor_allo"], params={"language_code": "hi-IN"},
                    files={"audio_file": ("a.wav", tiny_wav_bytes(), "audio/wav")})
    assert r.status_code == 200
    body = r.json()
    assert body["mocked"] is False
    if body["provider"] == "none":
        assert body["text"] == "" and body["error"]
    assert client.post("/api/v1/voice/transcribe-chunk", headers=headers["doctor_allo"]).status_code == 400

    # 6. NLP + diagnosis + rx
    ents = client.post("/api/v1/nlp/extract-entities", headers=headers["doctor_allo"],
                       json={"text": "Burning pain in stomach after meals for 2 weeks, 6 out of 10, worse after spicy food", "encounter_id": enc_id}).json()
    assert ents["mocked"] is True and ents["severity"] == 6 and "stomach" in ents["site"]
    hits = client.get("/api/v1/terminology/search", headers=headers["doctor_allo"], params={"query": "acid", "system": "namaste"}).json()
    assert any(h["code"] == "NAM-AYU-0001" for h in hits)
    r = client.post("/api/v1/diagnoses", headers=headers["doctor_allo"], json={"encounter_id": enc_id, "namaste_code": "NAM-AYU-0001"})
    assert r.status_code == 201 and r.json()["dual_coded"] and len(r.json()["diagnoses"]) == 3
    r = client.post(f"/api/v1/prescriptions/{enc_id}", headers=headers["doctor_allo"],
                    json={"medications": [{"name": "Omeprazole 20mg", "dose": "20 mg", "frequency": "OD", "duration_days": 14}]})
    assert r.status_code == 201
    rx = r.json()
    enc = client.get(f"/api/v1/encounters/{enc_id}", headers=headers["doctor_allo"]).json()
    assert enc["patient"]["uhid"] == "AIIA-2026-00001" and len(enc["prescriptions"]) == 1

    # 7. lab
    lab = client.post("/api/v1/lab/orders", headers=headers["doctor_allo"], json={"encounter_id": enc_id, "test_name": "CBC"}).json()
    r = client.patch(f"/api/v1/lab/orders/{lab['id']}/result", headers=headers["lab"], json={"result_values": {"hemoglobin": 9.1}})
    assert r.json()["flagged_abnormal"] is True and r.json()["flags"]["hemoglobin"] == "LOW"

    # 8. pharmacy via same QR
    scan = client.post("/api/v1/pharmacy/scan", headers=headers["pharmacy"], json={"code": code}).json()
    assert scan["encounter_id"] == enc_id and scan["dispenses"]
    d = client.post(f"/api/v1/pharmacy/dispense/{scan['dispenses'][0]['id']}", headers=headers["pharmacy"]).json()
    assert d["status"] == "DISPENSED" and d["bill_id"]
    stock = {s["name"]: s for s in client.get("/api/v1/pharmacy/stock", headers=headers["pharmacy"]).json()}
    assert stock["Omeprazole 20mg"]["quantity"] == 150 - 14
    assert stock["Triphala Churna"]["low_stock"] is True

    # 9. billing
    bill = client.post(f"/api/v1/billing/generate/{enc_id}", headers=headers["billing"]).json()
    assert bill["total_amount"] >= 250
    paid = client.post(f"/api/v1/billing/pay/{bill['id']}", headers=headers["billing"]).json()
    assert paid["payment_status"] == "PAID" and paid["gateway"]["mocked"] is True

    # 10. discharge + FHIR
    r = client.post(f"/api/v1/discharge/{enc_id}", headers=headers["doctor_allo"], json={"instructions": "Avoid spicy food"})
    assert r.status_code == 201 and r.json()["fhir_bundle_id"]
    bundle = client.get(f"/api/v1/fhir/bundle/{enc_id}", headers=headers["patient"]).json()
    assert bundle["resourceType"] == "Bundle" and bundle["type"] == "document"
    systems = {c["system"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Condition" for c in e["resource"]["code"]["coding"]}
    assert len(systems) == 3

    # 11. patient sees own records; notifications flowed
    recs = client.get("/api/v1/patients/me/records", headers=headers["patient"]).json()
    assert recs["medicines"] and recs["reports"] and recs["bills"]
    notes = client.get("/api/v1/notifications/me", headers=headers["patient"]).json()
    assert any("your turn" in n["message"] for n in notes)
    # 12. admin audit trail
    log = client.get("/api/v1/audit-log", headers=headers["admin"]).json()
    assert {a["action"] for a in log} >= {"CHECKED_IN", "PRESCRIPTION_SIGNED", "BILL_PAID", "DISCHARGED"}
    assert client.get("/api/v1/audit-log", headers=headers["doctor_allo"]).status_code == 403

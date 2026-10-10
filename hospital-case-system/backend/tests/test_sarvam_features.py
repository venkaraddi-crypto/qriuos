"""Translate / TTS / OCR / scribe / admin key management fall back honestly and label mocks."""
from datetime import date


def _enc(client, headers):
    slots = client.get("/api/v1/doctors/1/slots", params={"date": date.today().isoformat()}).json()
    appt = client.post("/api/v1/appointments", headers=headers["patient"], json={"doctor_id": 1, "slot_id": slots[3]["id"]}).json()
    client.post("/api/v1/reception/scan", headers=headers["reception"], json={"code": appt["qr_code"]})
    return client.patch(f"/api/v1/queue/{appt['id']}/call-next", headers=headers["doctor_allo"]).json()["encounter_id"]


def test_scribe_flow(client, headers):
    enc_id = _enc(client, headers)
    # consent gate
    r = client.post(f"/api/v1/consultation/{enc_id}/start-recording", headers=headers["doctor_allo"], json={"consent_given": True})
    assert r.status_code == 403
    r = client.post(f"/api/v1/consultation/{enc_id}/start-recording", headers=headers["doctor_allo"],
                    json={"consent_given": True, "consent_acknowledged_by_patient": True})
    assert r.status_code == 200
    r = client.post(f"/api/v1/consultation/{enc_id}/stop-recording", headers=headers["doctor_allo"],
                    files={"audio_file": ("c.wav", b"RIFF" + b"\x00" * 100, "audio/wav")})
    body = r.json()
    assert body["diarized_transcript"] and body["provider"] in ("mock", "whisper", "sarvam")
    if body["provider"] == "mock":
        assert body["mocked"] is True
    t = client.get(f"/api/v1/consultation/{enc_id}/transcript", headers=headers["patient"]).json()
    assert t["consent_given"] is True and t["audio_retained"] is True
    d = client.post(f"/api/v1/consultation/{enc_id}/generate-soap-draft", headers=headers["doctor_allo"]).json()
    assert d["soap_subjective"] and d["follow_up_weeks"] == 2 and "llm_mocked" in d
    client.patch(f"/api/v1/note-drafts/{d['id']}", headers=headers["doctor_allo"], json={"soap_plan": "Avipattikar churna 3g BD"})
    a = client.post(f"/api/v1/note-drafts/{d['id']}/approve", headers=headers["doctor_allo"]).json()
    assert a["approved_by"] and a["soap_plan"].startswith("Avipattikar")
    enc = client.get(f"/api/v1/encounters/{enc_id}", headers=headers["doctor_allo"]).json()
    assert "P: Avipattikar" in enc["clinical_notes"]
    assert len(client.get(f"/api/v1/consultation/{enc_id}/note-drafts", headers=headers["doctor_allo"]).json()) == 1
    tr = client.post(f"/api/v1/summary/{enc_id}/translate", headers=headers["patient"], params={"lang": "hi-IN"}).json()
    assert tr["target_language"] == "hi-IN" and (tr["mocked"] is True or tr["provider"] == "sarvam")
    tts = client.post(f"/api/v1/summary/{enc_id}/tts", headers=headers["patient"], params={"lang": "hi-IN"}).json()
    assert "audio_base64" in tts


def test_voice_tts_endpoint(client, headers):
    r = client.post("/api/v1/voice/tts", headers=headers["patient"], json={"text": "Namaste", "language": "te-IN"})
    assert r.status_code == 200 and r.json()["language"] == "te-IN"


def test_document_digitize_chain(client, headers):
    text = b"LAB REPORT 12 Mar 2026\nHemoglobin 10.8 g/dL\nFasting glucose 128 mg/dL\nTab Omeprazole 20 mg OD 14 days"
    r = client.post("/api/v1/documents/digitize", headers=headers["patient"], files={"file": ("r.txt", text, "text/plain")})
    assert r.status_code == 200
    ex = r.json()["extracted"]
    assert r.json()["ocr"]["provider"] == "plain-text" and ex["document_date"] == "2026-03-12"
    labs = {l["test"]: l for l in ex["labs"]}
    assert labs["hemoglobin"]["flag"] == "LOW" and labs["fasting_glucose"]["flag"] == "HIGH"
    assert ex["medications"][0]["name"].lower().startswith("omeprazole") and ex["medications"][0]["frequency"] == "once daily"
    # image without OCR key -> labelled mock
    r = client.post("/api/v1/documents/digitize", headers=headers["patient"], files={"file": ("x.png", b"\x89PNG" + b"0" * 50, "image/png")})
    assert r.json()["ocr"]["mocked"] is True
    # doctor confirms into the chart
    r = client.post("/api/v1/documents/confirm", headers=headers["doctor_allo"],
                    json={"patient_id": 1, "labs": ex["labs"], "medications": ex["medications"], "document_date": ex["document_date"]})
    assert r.status_code == 200 and r.json()["labs"] == 2 and r.json()["medications"] == 1
    meds = client.get("/api/v1/patients/1/meds", headers=headers["doctor_allo"]).json()
    assert any(m["system"] == "IMPORTED" for m in meds)


def test_admin_ai_keys(client, headers):
    assert client.get("/api/v1/admin/ai-providers", headers=headers["doctor_allo"]).status_code == 403
    r = client.post("/api/v1/admin/ai-providers", headers=headers["admin"], json={"capability": "TRANSLATE", "api_key": "sk-sarvam-test-1234ABCD"})
    assert r.status_code == 201
    assert r.json()["api_key_masked"] == "••••••••ABCD" and "api_key" not in r.json()
    assert client.post("/api/v1/admin/ai-providers", headers=headers["admin"], json={"capability": "NOPE", "api_key": "x" * 20}).status_code == 400
    st = client.get("/api/v1/admin/ai-status", headers=headers["admin"]).json()
    assert st["capabilities"]["TRANSLATE"]["key_source"] == "admin" and st["capabilities"]["STT"]["key_source"] is None
    t = client.post("/api/v1/admin/ai-providers/test", headers=headers["admin"], json={"capability": "STT"}).json()
    assert t["ok"] is False
    client.delete(f"/api/v1/admin/ai-providers/{r.json()['id']}", headers=headers["admin"])
    assert client.get("/api/v1/admin/ai-status", headers=headers["admin"]).json()["capabilities"]["TRANSLATE"]["key_source"] is None
    pol = client.put("/api/v1/admin/retention-policy", headers=headers["admin"], json={"raw_audio_retention_days": 7}).json()
    assert pol["raw_audio_retention_days"] == 7
    assert client.get("/api/v1/admin/retention-policy", headers=headers["admin"]).json()["raw_audio_retention_days"] == 7
    assert client.put("/api/v1/admin/retention-policy", headers=headers["admin"], json={"raw_audio_retention_days": 0}).status_code == 400

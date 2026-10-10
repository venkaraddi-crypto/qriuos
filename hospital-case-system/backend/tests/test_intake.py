"""Patient pre-consult intake flow and doctor-side summaries."""
from datetime import date


def _appt(client, headers):
    slots = client.get("/api/v1/doctors/1/slots", params={"date": date.today().isoformat()}).json()
    return client.post("/api/v1/appointments", headers=headers["patient"], json={"doctor_id": 1, "slot_id": slots[2]["id"]}).json()


def test_intake_flow(client, headers):
    appt = _appt(client, headers)
    aid = appt["id"]
    cat = client.get("/api/v1/intake/question-catalog", headers=headers["patient"]).json()
    assert "severity" in cat["hpi_fields"] and "GI" in cat["categories"]
    # cannot submit without consent
    assert client.post(f"/api/v1/intake/{aid}/submit", headers=headers["patient"]).status_code == 409
    r = client.post(f"/api/v1/intake/{aid}/start", headers=headers["patient"],
                    json={"language": "hi-IN", "consent_items": {"store_history": True, "share_with_doctor": True}})
    assert r.json()["consent_recorded"] is True and r.json()["language_used"] == "hi-IN"
    c = client.post(f"/api/v1/intake/{aid}/complaints", headers=headers["patient"],
                    json={"complaint_text": "acidity and burning after meals", "duration_days": 14, "severity": 6}).json()
    assert c["category"] == "GI"
    q = client.get(f"/api/v1/intake/{aid}/adaptive-questions", headers=headers["patient"]).json()
    assert q["category"] == "GI" and q["questions"][0]["key"] == "site" and q["remaining"] == 12
    client.put(f"/api/v1/intake/{aid}/hpi", headers=headers["patient"],
               json={"answers": {"site": "upper abdomen", "onset": "gradually", "severity": "6", "timing": "after meals"}})
    q2 = client.get(f"/api/v1/intake/{aid}/adaptive-questions", headers=headers["patient"]).json()
    assert q2["remaining"] == 8 and all(x["key"] not in ("site", "onset") for x in q2["questions"])
    client.post(f"/api/v1/intake/{aid}/allergies", headers=headers["patient"], json={"substance": "Penicillin", "reaction": "rash", "severity": "moderate"})
    client.post(f"/api/v1/intake/{aid}/meds", headers=headers["patient"], json={"name": "Pantoprazole", "dose": "40 mg", "frequency": "OD"})
    client.post(f"/api/v1/intake/{aid}/past", headers=headers["patient"], json={"kind": "PMH", "text": "Hypertension", "year": 2019})
    assert client.post(f"/api/v1/intake/{aid}/past", headers=headers["patient"], json={"kind": "BAD", "text": "x"}).status_code == 400
    ros = client.put(f"/api/v1/intake/{aid}/ros", headers=headers["patient"],
                     json={"systems": {"GI": {"positive": True, "notes": "bloating"}, "CV": {"positive": False}}}).json()
    assert any(r["system"] == "GI" and r["positive"] for r in ros)
    sub = client.post(f"/api/v1/intake/{aid}/submit", headers=headers["patient"]).json()
    assert sub["status"] == "SUBMITTED" and sub["duration_sec"] is not None
    # revoke consent is honoured
    assert client.post(f"/api/v1/intake/{aid}/revoke-consent", headers=headers["patient"]).json()["consent_revoked_at"]

    # doctor side
    client.post("/api/v1/reception/scan", headers=headers["reception"], json={"code": appt["qr_code"]})
    enc_id = client.patch(f"/api/v1/queue/{aid}/call-next", headers=headers["doctor_allo"]).json()["encounter_id"]
    s = client.get(f"/api/v1/encounters/{enc_id}/intake-summary", headers=headers["doctor_allo"]).json()
    assert s["intake_status"] == "REVIEWED" and s["hpi"]["site"] == "upper abdomen" and s["allergies"][0]["substance"] == "Penicillin"
    h = client.get(f"/api/v1/encounters/{enc_id}/history-summary", headers=headers["doctor_allo"]).json()
    assert "Hypertension" in h["problem_representation"] and h["hpi_lines"][0].startswith("Site:")
    assert "Penicillin" in h["narrative"] and "GI" in h["ros_positive"][0]
    # other patients cannot read it
    other = client.post("/api/v1/auth/register", json={"name": "Other", "email": "other@demo.in", "password": "password123", "phone": "1"})
    assert other.status_code == 201
    tok = client.post("/api/v1/auth/login", json={"email": "other@demo.in", "password": "password123"}).json()["access_token"]
    assert client.get(f"/api/v1/intake/{aid}", headers={"Authorization": f"Bearer {tok}"}).status_code == 403
    assert client.get(f"/api/v1/encounters/{enc_id}", headers={"Authorization": f"Bearer {tok}"}).status_code == 403

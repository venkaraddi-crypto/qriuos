"""Prescription -> billing -> records -> lab -> discharge -> follow-up -> case-file, dates relative to today."""
from datetime import date, timedelta


def _book_and_consult(client, headers, complaint="knee pain and stiffness"):
    slots = client.get("/api/v1/doctors/2/slots", params={"date": date.today().isoformat()}).json()
    appt = client.post("/api/v1/appointments", headers=headers["patient"],
                       json={"doctor_id": 2, "slot_id": slots[-1]["id"], "chief_complaint": complaint}).json()
    client.post("/api/v1/reception/scan", headers=headers["reception"], json={"code": appt["qr_code"]})
    enc_id = client.patch(f"/api/v1/queue/{appt['id']}/call-next", headers=headers["doctor_ayu"]).json()["encounter_id"]
    return appt, enc_id


def test_interconnect(client, headers):
    appt, enc_id = _book_and_consult(client, headers)
    rx = client.post(f"/api/v1/prescriptions/{enc_id}", headers=headers["doctor_ayu"], json={"medications": [
        {"name": "Triphala Churna", "dose": "5 g", "frequency": "HS", "duration_days": 10, "quantity": 1},
        {"name": "Mahanarayan Taila", "dose": "local", "frequency": "BD", "duration_days": 10, "quantity": 1}]}).json()
    assert rx["id"]
    # prescription completes the appointment
    mine = {a["id"]: a for a in client.get("/api/v1/appointments/me", headers=headers["patient"]).json()}
    assert mine[appt["id"]]["status"] == "COMPLETED"
    # billing worklist sees it; bill contains medicines priced from stock
    bill = client.post(f"/api/v1/billing/generate/{enc_id}", headers=headers["billing"]).json()
    descs = [i["description"] for i in bill["line_items"]]
    assert descs[0] == "Consultation fee" and any("Triphala" in d for d in descs)
    assert bill["total_amount"] == 250 + 3.0 + 120.0
    pending = client.get("/api/v1/billing/pending", headers=headers["billing"]).json()
    assert any(b["id"] == bill["id"] for b in pending)
    # lab added after bill -> regenerate updates total
    lab = client.post("/api/v1/lab/orders", headers=headers["doctor_ayu"], json={"encounter_id": enc_id, "test_name": "ESR"}).json()
    bill2 = client.post(f"/api/v1/billing/generate/{enc_id}", headers=headers["billing"]).json()
    assert bill2["id"] == bill["id"] and bill2["total_amount"] == bill["total_amount"] + 150
    client.patch(f"/api/v1/lab/orders/{lab['id']}/result", headers=headers["lab"], json={"result_values": {"esr": 42}})
    by_patient = client.get("/api/v1/lab/orders", headers=headers["doctor_ayu"], params={"patient_id": 1}).json()
    assert any(l["id"] == lab["id"] and l["flagged_abnormal"] for l in by_patient)
    # discharge with follow-up and schedule it
    fu = date.today() + timedelta(days=14)
    client.post(f"/api/v1/discharge/{enc_id}", headers=headers["doctor_ayu"], json={"instructions": "Warm oil massage", "follow_up_date": fu.isoformat()})
    r = client.post("/api/v1/followup/schedule", headers=headers["doctor_ayu"],
                    json={"patient_id": 1, "doctor_id": 2, "date": fu.isoformat(), "note": "Review Sandhivata"})
    assert r.status_code == 201 and r.json()["type"] == "FOLLOWUP" and r.json()["date"] == fu.isoformat()
    # case file shows everything
    cf = client.get("/api/v1/case-file/1", headers=headers["doctor_ayu"]).json()
    types = {e["type"] for e in cf["events"]}
    assert {"APPOINTMENT", "ENCOUNTER", "PRESCRIPTION", "LAB", "BILL", "DISCHARGE"} <= types
    # patient summary
    s = client.get("/api/v1/patients/me/summary", headers=headers["patient"]).json()
    assert s["next_appointment"] is not None and s["pending_bills"] >= 1
    mine = client.get("/api/v1/appointments/me", headers=headers["patient"]).json()
    assert any(a["type"] == "FOLLOWUP" and a["date"] == fu.isoformat() for a in mine)
    # dispatch board
    d = client.get(f"/api/v1/encounters/{enc_id}/dispatch", headers=headers["doctor_ayu"]).json()
    assert d["medicine_to_pharmacy"] is True and d["pharmacy_pending_items"] == 2


def test_reschedule_and_cancel(client, headers):
    today = date.today()
    slots = client.get("/api/v1/doctors/1/slots", params={"date": (today + timedelta(days=1)).isoformat()}).json()
    appt = client.post("/api/v1/appointments", headers=headers["patient"], json={"doctor_id": 1, "slot_id": slots[0]["id"]}).json()
    before = client.get("/api/v1/doctors/1/slots", params={"date": (today + timedelta(days=1)).isoformat()}).json()[0]["available"]
    r = client.patch(f"/api/v1/appointments/{appt['id']}/reschedule", headers=headers["patient"], json={"slot_id": slots[1]["id"]})
    assert r.status_code == 200 and r.json()["slot_id"] == slots[1]["id"]
    after = client.get("/api/v1/doctors/1/slots", params={"date": (today + timedelta(days=1)).isoformat()}).json()[0]["available"]
    assert after == before + 1
    assert client.patch(f"/api/v1/appointments/{appt['id']}/cancel", headers=headers["patient"]).json()["status"] == "CANCELLED"


def test_walkin_emergency_front_of_queue(client, headers):
    r = client.post("/api/v1/reception/walkin", headers=headers["reception"],
                    json={"name": "Walk In", "phone": "9000000000", "doctor_id": 1, "emergency": True, "chief_complaint": "collapsed"})
    assert r.status_code == 201 and r.json()["token_number"] == "E" and r.json()["status"] == "CHECKED_IN"
    q = client.get("/api/v1/queue", headers=headers["doctor_allo"]).json()
    assert q[0]["token_number"] == "E"


def test_referral_doctor_creates_appointment(client, headers):
    appt, enc_id = _book_and_consult(client, headers, "fever")
    r = client.post(f"/api/v1/encounters/{enc_id}/refer", headers=headers["doctor_ayu"], json={"kind": "DOCTOR", "doctor_id": 1, "note": "needs allopathic opinion"})
    assert r.status_code == 201 and r.json()["new_appointment_id"]
    r = client.post(f"/api/v1/encounters/{enc_id}/refer", headers=headers["doctor_ayu"], json={"kind": "THERAPY", "therapy_name": "Janu Basti"})
    assert r.json()["therapy"]["name"] == "Janu Basti"
    sessions = client.get("/api/v1/nurse/therapy-sessions", headers=headers["nurse"]).json()
    assert any(s["therapy_name"] == "Janu Basti" for s in sessions)
    d = client.get(f"/api/v1/encounters/{enc_id}/dispatch", headers=headers["doctor_ayu"]).json()
    assert len(d["treatment_to_therapy"]) == 1 and len(d["file_to_departments"]) == 1

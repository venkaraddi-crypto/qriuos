"""SIH problem-statement checks: dual coding, Ayush assessments, FHIR, ABHA, analytics, admin."""
from datetime import date, timedelta

from app.services import dashavidha, fhir, prakriti
from app.services.terminology_data import CURATED


def test_terminology_triplets(client, headers):
    nam = client.get("/api/v1/terminology/search", headers=headers["doctor_ayu"], params={"query": "Amlapitta", "system": "namaste"}).json()
    tm2 = client.get("/api/v1/terminology/search", headers=headers["doctor_ayu"], params={"query": "Amlapitta", "system": "tm2"}).json()
    bio = client.get("/api/v1/terminology/search", headers=headers["doctor_ayu"], params={"query": "K29", "system": "biomedicine"}).json()
    assert nam[0]["code"] == "NAM-AYU-0001" and tm2[0]["code"] == "TM26.SA00" and bio[0]["code"] == "K29.7"
    t = client.post("/api/v1/terminology/translate", headers=headers["doctor_ayu"], json={"code": "TM26.SA00"}).json()
    assert t["namaste"]["term"] == "Amlapitta" and t["icd11_biomedicine"]["code"] == "K29.7"
    assert len(CURATED) >= 40 and len({c[0] for c in CURATED}) == len(CURATED)


def test_seeded_dual_coded_case(client, headers):
    tl = client.get("/api/v1/patients/4/timeline", headers=headers["doctor_ayu"]).json()
    enc = client.get(f"/api/v1/encounters/{tl[0]['encounter_id']}", headers=headers["doctor_ayu"]).json()
    assert {d["code"] for d in enc["diagnoses"]} == {"NAM-AYU-0001", "TM26.SA00", "K29.7"}
    assert enc["system"] == "AYURVEDA"


def test_ayush_assessments(client, headers):
    q = client.get("/api/v1/queue", headers=headers["doctor_ayu"]).json()
    target = next(a for a in q if a["uhid"] == "AIIA-2026-00004")
    enc_id = client.patch(f"/api/v1/queue/{target['id']}/call-next", headers=headers["doctor_ayu"]).json()["encounter_id"]
    answers = {t: 2 for t in prakriti.PITTA_TRAITS} | {t: 1 for t in prakriti.VATA_TRAITS} | {t: 0 for t in prakriti.KAPHA_TRAITS}
    r = client.post("/api/v1/ayush/prakriti-score", headers=headers["doctor_ayu"],
                    json={"answers": answers, "encounter_id": enc_id, "current_symptoms": "burning acidity sour"}).json()
    assert r["prakriti"]["dominant"] == "pitta" and r["vikriti"]["aggravated_dosha"] == "pitta"
    assert abs(r["prakriti"]["vata"] + r["prakriti"]["pitta"] + r["prakriti"]["kapha"] - 100) < 0.5
    client.post("/api/v1/ayush/ashtavidha", headers=headers["doctor_ayu"], json={"encounter_id": enc_id, "data": {"nadi": "pitta", "jihva": "coated"}})
    ref = client.get("/api/v1/ayush/dashavidha/reference", headers=headers["doctor_ayu"]).json()
    assert len(ref["parameters"]) == 10 and sum(p["scored"] for p in ref["parameters"]) == 8
    params = {p["key"]: "pravara" for p in ref["parameters"] if p["scored"]}
    d = client.post("/api/v1/ayush/dashavidha", headers=headers["doctor_ayu"],
                    json={"encounter_id": enc_id, "parameters": params, "ahara_vihara": {"meal_timing": "irregular"}}).json()
    assert d["bala_score"] == 100.0 and d["bala_label"] == "Pravara Bala" and d["advice"]
    enc = client.get(f"/api/v1/encounters/{enc_id}", headers=headers["doctor_ayu"]).json()
    assert enc["ayush"]["vikriti_dosha"] == "pitta" and enc["ayush"]["ashtavidha_data"]["nadi"] == "pitta"
    assert enc["ayush"]["ahara_vihara"]["meal_timing"] == "irregular"
    # FHIR includes prakriti observation and ayush dual coding
    client.post("/api/v1/diagnoses", headers=headers["doctor_ayu"], json={"encounter_id": enc_id, "namaste_code": "NAM-AYU-0001"})
    b = client.post(f"/api/v1/fhir/generate-bundle/{enc_id}", headers=headers["doctor_ayu"]).json()
    fhir.validate_bundle(b)
    obs = [e["resource"] for e in b["entry"] if e["resource"]["resourceType"] == "Observation"]
    assert any("Prakriti" in o["code"]["text"] for o in obs)
    conds = [e["resource"] for e in b["entry"] if e["resource"]["resourceType"] == "Condition"]
    assert {c["code"]["coding"][0]["system"] for c in conds} == set(fhir.FHIR_SYSTEMS.values())


def test_dashavidha_pure():
    assert dashavidha.assess_dashavidha({}, {})["bala_score"] == 0.0
    assert prakriti.score_prakriti({})["dominant"] == "vata"


def test_abha_mock_bridge(client, headers):
    init = client.post("/api/v1/abha/init-otp", headers=headers["patient"], json={"aadhaar_or_mobile": "9876500001"}).json()
    assert init["mocked"] is True and init["txn_id"]
    assert client.post("/api/v1/abha/verify-otp", headers=headers["patient"], json={"txn_id": init["txn_id"], "otp": "000000"}).status_code == 400
    v = client.post("/api/v1/abha/verify-otp", headers=headers["patient"], json={"txn_id": init["txn_id"], "otp": "123456"}).json()
    assert v["verified"] and client.get("/api/v1/patients/me/profile", headers=headers["patient"]).json()["abha_id"] == v["abha_id"]
    tl = client.get("/api/v1/patients/4/timeline", headers=headers["doctor_ayu"]).json()
    assert client.post("/api/v1/abha/link-care-context", headers=headers["doctor_ayu"], json={"encounter_id": tl[0]["encounter_id"]}).status_code == 409
    client.post("/api/v1/patients/me/abha", headers=headers["patient"], json={"abha_id": "91-0000-0000-0001"})
    assert client.get("/api/v1/auth/me", headers=headers["patient"]).json()["patient"]["abha_id"] == "91-0000-0000-0001"


def test_admin_and_analytics(client, headers):
    d = client.post("/api/v1/admin/departments", headers=headers["admin"], json={"name": "Rasayana", "system": "AYURVEDA"}).json()
    s = client.post("/api/v1/admin/staff", headers=headers["admin"],
                    json={"name": "Dr New", "email": "new-doc@demo.in", "password": "password123", "role": "DOCTOR", "department_id": d["id"]})
    assert s.status_code == 201
    staff = client.get("/api/v1/admin/staff", headers=headers["admin"]).json()
    newdoc = next(x for x in staff if x["email"] == "new-doc@demo.in")
    assert newdoc["doctor_profile"]["system"] == "AYURVEDA"
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    slot = client.post("/api/v1/admin/doctor-slots", headers=headers["admin"],
                       json={"doctor_id": newdoc["doctor_profile"]["id"], "date": tomorrow, "start_time": "16:00", "end_time": "17:00", "capacity": 5}).json()
    assert slot["available"] == 5
    assert client.get(f"/api/v1/doctors/{newdoc['doctor_profile']['id']}/slots", params={"date": tomorrow}).json()[0]["id"] == slot["id"]
    a = client.get("/api/v1/analytics/summary", headers=headers["admin"]).json()
    assert a["total_patients"] >= 9 and "ALLOPATHIC" in a["by_system"] and any(x["name"] == "Triphala Churna" for x in a["low_stock"])
    assert a["red_flags_today"] >= 1
    assert client.post("/api/v1/admin/staff", headers=headers["admin"], json={"name": "x", "email": "p@x.in", "password": "p", "role": "PATIENT"}).status_code == 400


def test_family_and_interactions(client, headers):
    fam = client.get("/api/v1/patients/me/family", headers=headers["patient"]).json()
    assert fam and fam[0]["name"] == "Sushila Krishnan" and fam[0]["relation"] == "Mother"
    r = client.post("/api/v1/patients/me/family", headers=headers["patient"], json={"name": "Ravi", "relation": "Son"})
    assert r.status_code == 201 and r.json()["uhid"].startswith("AIIA-2026-")
    f = client.post("/api/v1/prescriptions/check-interactions", headers=headers["doctor_allo"], json={"medications": ["Warfarin 5mg", "Aspirin 75mg"]}).json()
    assert f["flags"] and f["flags"][0]["severity"] == "HIGH"
    assert client.post("/api/v1/prescriptions/check-interactions", headers=headers["doctor_allo"], json={"medications": ["Paracetamol"]}).json()["flags"] == []

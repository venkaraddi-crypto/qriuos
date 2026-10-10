"""JWT + rotating refresh cookie, Aadhaar masking, Drive encryption & access control, sessions."""
import os

from app.api.v1.endpoints.drive import DRIVE_DIR
from app.core import crypto
from app.core.config import DEV_SECRET_KEY, Settings


def test_production_guard():
    import pytest
    with pytest.raises(RuntimeError):
        Settings(ENVIRONMENT="production", SECRET_KEY=DEV_SECRET_KEY, FIELD_ENCRYPTION_KEY="x").validate_for_environment()
    with pytest.raises(RuntimeError):
        Settings(ENVIRONMENT="prod", SECRET_KEY="a" * 40, FIELD_ENCRYPTION_KEY=None).validate_for_environment()
    Settings(ENVIRONMENT="production", SECRET_KEY="a" * 40, FIELD_ENCRYPTION_KEY="k").validate_for_environment()


def test_crypto_roundtrip():
    assert crypto.decrypt_key(crypto.encrypt_key("sk-123456789")) == "sk-123456789"
    assert crypto.mask_key("sk-123456789") == "••••••••6789"
    enc = crypto.encrypt_text("123412341234")
    assert enc.startswith("enc:") and crypto.decrypt_text(enc) == "123412341234"
    assert crypto.decrypt_text("legacy-plain") == "legacy-plain"
    assert crypto.decrypt_text("enc:garbage") is None
    assert crypto.decrypt_bytes(crypto.encrypt_bytes(b"blob")) == b"blob"


def test_auth_and_refresh(client):
    assert client.post("/api/v1/auth/login", json={"email": "patient@demo.in", "password": "wrong"}).status_code == 401
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer nope"}).status_code == 401
    r = client.post("/api/v1/auth/login", json={"email": "patient@demo.in", "password": "password123"})
    assert "arogya_refresh" in r.cookies
    old_cookie = r.cookies["arogya_refresh"]
    r2 = client.post("/api/v1/auth/refresh")
    assert r2.status_code == 200 and r2.json()["role"] == "PATIENT"
    assert r2.cookies["arogya_refresh"] != old_cookie
    # the rotated-out token is dead
    client.cookies.set("arogya_refresh", old_cookie)
    assert client.post("/api/v1/auth/refresh").status_code == 401
    client.cookies.clear()
    assert client.post("/api/v1/auth/logout").status_code == 200


def test_role_gate(client, headers):
    r = client.get("/api/v1/queue", headers=headers["nurse"])
    assert r.status_code == 403 and r.json()["detail"] == "Requires role: DOCTOR"
    assert client.get("/api/v1/reception/board", headers=headers["patient"]).status_code == 403


def test_aadhaar_masked(client, headers):
    assert client.patch("/api/v1/patients/me/profile", headers=headers["patient"], json={"aadhaar_no": "123"}).status_code == 400
    r = client.patch("/api/v1/patients/me/profile", headers=headers["patient"], json={"aadhaar_no": "9876 5432 1098"})
    assert r.json()["aadhaar_masked"] == "XXXX-XXXX-1098"
    assert "aadhaar_no" not in r.json()
    p = client.get("/api/v1/patients/me/profile", headers=headers["patient"]).json()
    assert p["aadhaar_masked"] == "XXXX-XXXX-1098"


def test_patient_isolation(client, headers):
    # patient 2 belongs to someone else
    assert client.get("/api/v1/patients/2/timeline", headers=headers["patient"]).status_code == 403
    assert client.get("/api/v1/patients/2/vitals-history", headers=headers["patient"]).status_code == 403
    assert client.get("/api/v1/case-file/2", headers=headers["patient"]).status_code == 403
    assert client.get("/api/v1/patients/1/timeline", headers=headers["patient"]).status_code == 200
    assert client.get("/api/v1/patients/2/timeline", headers=headers["doctor_allo"]).status_code == 200


def test_drive(client, headers):
    payload = b"%PDF-1.4 secret report"
    assert client.post("/api/v1/drive/documents", headers=headers["patient"], files={"file": ("x.exe", b"MZ", "application/x-msdownload")}).status_code == 415
    r = client.post("/api/v1/drive/documents", headers=headers["patient"], data={"category": "LAB_REPORT", "document_date": "2026-01-05"},
                    files={"file": ("report.pdf", payload, "application/pdf")})
    assert r.status_code == 201, r.text
    doc = r.json()
    assert doc["sha256"] and doc["category"] == "LAB_REPORT" and doc["document_date"] == "2026-01-05"
    # encrypted at rest
    stored = [f for f in os.listdir(DRIVE_DIR) if f.endswith(".bin")]
    assert stored
    with open(os.path.join(DRIVE_DIR, sorted(stored, key=lambda f: os.path.getmtime(os.path.join(DRIVE_DIR, f)))[-1]), "rb") as f:
        assert payload not in f.read()
    # owner downloads plaintext; unrelated staff cannot
    d = client.get(f"/api/v1/drive/documents/{doc['id']}/download", headers=headers["patient"])
    assert d.status_code == 200 and d.content == payload
    assert client.get(f"/api/v1/drive/documents/{doc['id']}/download", headers=headers["lab"]).status_code == 403
    # the patient's treating doctor can see it (has encounters with patient 1)
    assert client.get(f"/api/v1/drive/documents/{doc['id']}", headers=headers["doctor_allo"]).status_code == 200
    # explicit grant to lab user
    lab_user = client.get("/api/v1/auth/me", headers=headers["lab"]).json()["id"]
    g = client.post(f"/api/v1/drive/documents/{doc['id']}/grant-access", headers=headers["patient"], json={"user_id": lab_user, "reason": "compare"})
    assert g.status_code == 201
    assert client.get(f"/api/v1/drive/documents/{doc['id']}/download", headers=headers["lab"]).status_code == 200
    assert any(x["id"] == doc["id"] for x in client.get("/api/v1/drive/documents", headers=headers["patient"]).json())
    assert client.delete(f"/api/v1/drive/documents/{doc['id']}", headers=headers["lab"]).status_code == 403
    assert client.delete(f"/api/v1/drive/documents/{doc['id']}", headers=headers["patient"]).status_code == 200
    assert client.get(f"/api/v1/drive/documents/{doc['id']}", headers=headers["patient"]).status_code == 404
    acts = {a["action"] for a in client.get("/api/v1/audit-log", headers=headers["admin"]).json()}
    assert {"DRIVE_UPLOAD", "DRIVE_DOWNLOAD", "DRIVE_GRANT", "DRIVE_DELETE"} <= acts


def test_settings_and_sessions(client, headers):
    s = client.patch("/api/v1/settings/me", headers=headers["nurse"], json={"preferred_language": "ta-IN", "theme_preference": "dark"}).json()
    assert s["preferred_language"] == "ta-IN" and s["theme_preference"] == "dark"
    assert client.patch("/api/v1/settings/me", headers=headers["nurse"], json={"theme_preference": "neon"}).status_code == 400
    sess = client.get("/api/v1/settings/sessions", headers=headers["nurse"]).json()
    assert sess and sess[0]["active"]
    assert client.post("/api/v1/settings/change-password", headers=headers["nurse"], json={"current_password": "bad", "new_password": "longenough1"}).status_code == 400
    r = client.post("/api/v1/settings/change-password", headers=headers["nurse"], json={"current_password": "password123", "new_password": "longenough1"})
    assert r.json()["sessions_revoked"] >= 1
    assert client.post("/api/v1/auth/login", json={"email": "nurse@demo.in", "password": "longenough1"}).status_code == 200
    client.post("/api/v1/settings/change-password", headers=headers["nurse"], json={"current_password": "longenough1", "new_password": "password123"})

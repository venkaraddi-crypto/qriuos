"""Each test module gets its own temp SQLite DB; lifespan seeds it."""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

_db_path = os.path.join(tempfile.mkdtemp(prefix="arogya-test-"), "test.db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_db_path}"
os.environ["ENVIRONMENT"] = "test"
os.environ.pop("SARVAM_API_KEY", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

PASSWORD = "password123"


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def login(client: TestClient, email: str) -> dict:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def headers(client):
    return {
        "patient": login(client, "patient@demo.in"),
        "reception": login(client, "reception@demo.in"),
        "doctor_allo": login(client, "doctor-allo@demo.in"),
        "doctor_ayu": login(client, "doctor-ayu@demo.in"),
        "nurse": login(client, "nurse@demo.in"),
        "lab": login(client, "lab@demo.in"),
        "pharmacy": login(client, "pharmacy@demo.in"),
        "billing": login(client, "billing@demo.in"),
        "admin": login(client, "admin@demo.in"),
    }

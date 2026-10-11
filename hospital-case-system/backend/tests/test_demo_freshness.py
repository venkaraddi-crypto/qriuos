"""Demo freshness — the hospital must look 'live' no matter when the DB was seeded.

Regression for two real bugs found in live use:
1. Staff screens (doctor queue, reception board, nurse board) went empty the day
   after seeding because active appointments stayed on the seed date.
2. Reception could check in a future-dated appointment that the doctor's
   today-only queue then hid — desks fell out of sync.
"""
import asyncio
import sqlite3
from datetime import date, timedelta

from app.core.config import settings
from app.core.database import SessionLocal
from app.seed import refresh_demo_day


def _raw() -> sqlite3.Connection:
    return sqlite3.connect(settings.DATABASE_URL.split("sqlite+aiosqlite:///")[1])


def test_stale_active_appointments_roll_forward(client, headers):
    stale = (date.today() - timedelta(days=3)).isoformat()
    con = _raw()
    con.execute("UPDATE appointments SET date=? WHERE status IN ('BOOKED','CHECKED_IN','IN_CONSULTATION') AND date <= ?",
                (stale, date.today().isoformat()))
    con.execute("DELETE FROM doctor_slots WHERE date >= ?", (date.today().isoformat(),))
    con.commit()
    con.close()

    # doctor queue / boards are now empty (the bug)
    assert client.get("/api/v1/queue", headers=headers["doctor_allo"]).json() == []
    assert client.get("/api/v1/nurse/today", headers=headers["nurse"]).json() == []

    # boot-time refresh heals the demo data
    async def _run():
        async with SessionLocal() as db:
            await refresh_demo_day(db)
    asyncio.run(_run())

    queue = client.get("/api/v1/queue", headers=headers["doctor_allo"]).json()
    assert queue, "checked-in patients must reappear in the doctor queue"
    assert {a["status"] for a in queue} <= {"CHECKED_IN", "IN_CONSULTATION"}
    red = [a for a in queue if a["red_flag"]]
    assert red and queue[0]["id"] == red[0]["id"], "red-flag patient stays on top"

    board = client.get("/api/v1/reception/board", headers=headers["reception"]).json()
    assert board["checked_in"], "reception board must show checked-in patients"
    assert client.get("/api/v1/nurse/today", headers=headers["nurse"]).json()

    # slots were topped up for today so booking keeps working
    slots = client.get("/api/v1/doctors/1/slots", params={"date": date.today().isoformat()}).json()
    assert slots and slots[0]["available"] > 0


def test_scan_rejects_future_appointment(client, headers):
    con = _raw()
    row = con.execute("SELECT checkin_token FROM appointments WHERE date > ? AND status='BOOKED' LIMIT 1",
                      (date.today().isoformat(),)).fetchone()
    con.close()
    assert row, "seed should contain a future BOOKED appointment"
    r = client.post("/api/v1/reception/scan", headers=headers["reception"], json={"code": row[0]})
    assert r.status_code == 409
    assert "not scheduled for today" in r.json()["detail"]

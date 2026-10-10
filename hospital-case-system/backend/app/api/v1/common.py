"""Helpers shared across endpoint modules."""
from datetime import date, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Appointment, Department, DoctorProfile, Encounter, Patient, User

STAFF_ROLES = ("RECEPTION", "DOCTOR", "NURSE", "LAB", "PHARMACY", "BILLING", "ADMIN")
CONSULT_FEE = 250.0


def iso(v) -> str | None:
    if v is None:
        return None
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return str(v)


def age_of(dob: date | None) -> int | None:
    if not dob:
        return None
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


async def get_or_404(db: AsyncSession, model, pk: int, label: str = "Record"):
    obj = await db.get(model, pk)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{label} not found")
    return obj


async def patient_for_user(db: AsyncSession, user: User) -> Patient:
    p = (await db.execute(select(Patient).where(Patient.user_id == user.id))).scalars().first()
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No patient profile linked to this account")
    return p


async def doctor_for_user(db: AsyncSession, user: User) -> DoctorProfile:
    d = (await db.execute(select(DoctorProfile).where(DoctorProfile.user_id == user.id))).scalars().first()
    if d is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No doctor profile for this user")
    return d


async def assert_patient_access(db: AsyncSession, user: User, patient_id: int) -> None:
    """Patients may only see their own records; staff may see any."""
    if user.role == "PATIENT":
        p = await patient_for_user(db, user)
        if p.id != patient_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your record")


async def encounter_with_access(db: AsyncSession, user: User, encounter_id: int) -> Encounter:
    enc = await get_or_404(db, Encounter, encounter_id, "Encounter")
    await assert_patient_access(db, user, enc.patient_id)
    return enc


async def appointment_by_code(db: AsyncSession, code: str) -> Appointment:
    appt = (await db.execute(select(Appointment).where(Appointment.checkin_token == code.strip()))).scalars().first()
    if appt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown QR code")
    return appt


def patient_public(p: Patient) -> dict:
    return {"id": p.id, "uhid": p.uhid, "name": p.name, "gender": p.gender, "dob": iso(p.dob), "phone": p.phone,
            "abha_id": p.abha_id, "abha_address": p.abha_address, "age": age_of(p.dob)}


async def appointment_public(db: AsyncSession, a: Appointment) -> dict:
    patient = await db.get(Patient, a.patient_id)
    doctor = await db.get(DoctorProfile, a.doctor_id)
    doc_user = await db.get(User, doctor.user_id) if doctor else None
    dept = await db.get(Department, a.department_id)
    return {
        "id": a.id, "patient_id": a.patient_id, "patient_name": patient.name if patient else None,
        "uhid": patient.uhid if patient else None, "doctor_id": a.doctor_id,
        "doctor_name": doc_user.name if doc_user else None, "department_id": a.department_id,
        "department": dept.name if dept else None, "system": a.system, "mode": a.mode, "type": a.type,
        "date": iso(a.date), "slot_time": a.slot_time, "slot_id": a.slot_id, "token_number": a.token_number,
        "qr_code": a.checkin_token, "red_flag": a.red_flag, "status": a.status, "chief_complaint": a.chief_complaint,
    }

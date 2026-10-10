"""Referrals (therapy / department / doctor) and the end-of-consult dispatch board."""
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.common import doctor_for_user, encounter_with_access, get_or_404, iso
from app.core.database import get_db
from app.core.security import audit, get_current_user, require_roles
from app.models import Department, DoctorProfile, Encounter, Notification, Patient, PharmacyDispense, Prescription, Referral, TherapySession, User

router = APIRouter()


class ReferIn(BaseModel):
    kind: str  # THERAPY|DEPARTMENT|DOCTOR
    therapy_name: str | None = None
    scheduled_at: datetime | None = None
    department_id: int | None = None
    doctor_id: int | None = None
    note: str | None = None


async def _public(db: AsyncSession, r: Referral) -> dict:
    dept = await db.get(Department, r.to_department_id) if r.to_department_id else None
    doc = await db.get(DoctorProfile, r.to_doctor_id) if r.to_doctor_id else None
    doc_user = await db.get(User, doc.user_id) if doc else None
    ts = await db.get(TherapySession, r.therapy_session_id) if r.therapy_session_id else None
    return {"id": r.id, "encounter_id": r.encounter_id, "patient_id": r.patient_id, "kind": r.kind, "status": r.status, "note": r.note,
            "department": dept.name if dept else None, "department_id": r.to_department_id, "doctor_name": doc_user.name if doc_user else None,
            "therapy": {"id": ts.id, "name": ts.therapy_name, "scheduled_at": iso(ts.scheduled_at), "status": ts.status} if ts else None,
            "new_appointment_id": r.new_appointment_id, "created_at": iso(r.created_at)}


@router.post("/encounters/{encounter_id}/refer", status_code=201)
async def refer(encounter_id: int, body: ReferIn, user: User = Depends(require_roles("DOCTOR", "ADMIN")), db: AsyncSession = Depends(get_db)):
    enc = await get_or_404(db, Encounter, encounter_id, "Encounter")
    from_doc = enc.doctor_id
    r = Referral(encounter_id=enc.id, patient_id=enc.patient_id, from_doctor_id=from_doc, kind=body.kind, note=body.note)
    if body.kind == "THERAPY":
        if not body.therapy_name:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "therapy_name required")
        ts = TherapySession(patient_id=enc.patient_id, therapy_name=body.therapy_name,
                            scheduled_at=body.scheduled_at or datetime.combine(date.today() + timedelta(days=1), datetime.min.time().replace(hour=10)))
        db.add(ts)
        await db.flush()
        r.therapy_session_id = ts.id
        db.add(Notification(patient_id=enc.patient_id, message=f"Therapy {body.therapy_name} scheduled for {iso(ts.scheduled_at)}."))
    elif body.kind == "DEPARTMENT":
        if not body.department_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "department_id required")
        await get_or_404(db, Department, body.department_id, "Department")
        r.to_department_id = body.department_id
    elif body.kind == "DOCTOR":
        if not body.doctor_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "doctor_id required")
        doc = await get_or_404(db, DoctorProfile, body.doctor_id, "Doctor")
        r.to_doctor_id, r.to_department_id = doc.id, doc.department_id
        from app.api.v1.endpoints.core import _create_appointment
        patient = await db.get(Patient, enc.patient_id)
        appt = await _create_appointment(db, patient, doc, date.today() + timedelta(days=1), None, "09:00", "IN_PERSON", "NEW", body.note)
        r.new_appointment_id = appt.id
        db.add(Notification(patient_id=enc.patient_id, message=f"Referral appointment booked for {iso(appt.date)} (token {appt.token_number})."))
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "kind must be THERAPY|DEPARTMENT|DOCTOR")
    db.add(r)
    audit(db, user.id, "REFERRAL_CREATED", f"encounter:{enc.id}")
    await db.commit()
    return await _public(db, r)


@router.get("/encounters/{encounter_id}/referrals")
async def referrals_for(encounter_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await encounter_with_access(db, user, encounter_id)
    rows = (await db.execute(select(Referral).where(Referral.encounter_id == encounter_id))).scalars().all()
    return [await _public(db, r) for r in rows]


@router.get("/referrals/department/{department_id}")
async def referrals_dept(department_id: int, user: User = Depends(require_roles("DOCTOR", "ADMIN", "RECEPTION")), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Referral).where(Referral.to_department_id == department_id).order_by(Referral.id.desc()))).scalars().all()
    return [await _public(db, r) for r in rows]


@router.get("/encounters/{encounter_id}/dispatch")
async def dispatch(encounter_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    enc = await encounter_with_access(db, user, encounter_id)
    rx = (await db.execute(select(Prescription).where(Prescription.encounter_id == enc.id))).scalars().all()
    pending = 0
    for p in rx:
        pending += len((await db.execute(select(PharmacyDispense).where(PharmacyDispense.prescription_id == p.id,
                                                                       PharmacyDispense.status == "PENDING"))).scalars().all())
    refs = (await db.execute(select(Referral).where(Referral.encounter_id == enc.id))).scalars().all()
    therapy = [await _public(db, r) for r in refs if r.kind == "THERAPY"]
    depts = []
    for r in refs:
        if r.kind in ("DEPARTMENT", "DOCTOR") and r.to_department_id:
            d = await db.get(Department, r.to_department_id)
            depts.append({"id": r.id, "department": d.name if d else None, "status": r.status, "kind": r.kind,
                          "new_appointment_id": r.new_appointment_id})
    return {"medicine_to_pharmacy": bool(rx), "pharmacy_pending_items": pending, "treatment_to_therapy": therapy,
            "file_to_departments": depts}

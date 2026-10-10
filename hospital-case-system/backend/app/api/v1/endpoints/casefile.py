"""Patient summary, longitudinal case file, family members, interaction pre-check."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.common import assert_patient_access, get_or_404, iso, patient_for_user, patient_public
from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models import (
    Appointment, Bill, Diagnosis, DischargeSummary, Encounter, FamilyMember, LabOrder, NurseVitals, Patient, Prescription,
    Referral, TherapySession, User,
)

router = APIRouter()


@router.get("/patients/me/summary")
async def my_summary(user: User = Depends(require_roles("PATIENT")), db: AsyncSession = Depends(get_db)):
    p = await patient_for_user(db, user)
    today = date.today()
    nxt = (await db.execute(select(Appointment).where(Appointment.patient_id == p.id, Appointment.date >= today,
                                                      Appointment.status.in_(["BOOKED", "CHECKED_IN", "IN_CONSULTATION"]))
                            .order_by(Appointment.date, Appointment.slot_time))).scalars().first()
    visits = (await db.execute(select(Encounter).where(Encounter.patient_id == p.id))).scalars().all()
    pending = (await db.execute(select(Bill).join(Encounter, Encounter.id == Bill.encounter_id)
                                .where(Encounter.patient_id == p.id, Bill.payment_status == "PENDING"))).scalars().all()
    from app.api.v1.common import appointment_public
    return {"patient": patient_public(p), "next_appointment": await appointment_public(db, nxt) if nxt else None,
            "total_visits": len(visits), "pending_bills": len(pending),
            "pending_amount": round(sum(b.total_amount for b in pending), 2)}


@router.get("/case-file/{patient_id}")
async def case_file(patient_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role not in ("DOCTOR", "ADMIN", "NURSE", "PATIENT"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Requires role: DOCTOR/PATIENT")
    await assert_patient_access(db, user, patient_id)
    p = await get_or_404(db, Patient, patient_id, "Patient")
    events: list[dict] = []
    appts = (await db.execute(select(Appointment).where(Appointment.patient_id == p.id))).scalars().all()
    for a in appts:
        events.append({"type": "APPOINTMENT", "date": iso(a.date), "status": a.status, "system": a.system, "token": a.token_number,
                       "chief_complaint": a.chief_complaint, "appointment_id": a.id})
        for v in (await db.execute(select(NurseVitals).where(NurseVitals.appointment_id == a.id))).scalars().all():
            events.append({"type": "VITALS", "date": iso(v.recorded_at), "bp": v.bp, "pulse": v.pulse, "temp": v.temp, "weight": v.weight})
    for e in (await db.execute(select(Encounter).where(Encounter.patient_id == p.id))).scalars().all():
        dx = (await db.execute(select(Diagnosis).where(Diagnosis.encounter_id == e.id))).scalars().all()
        events.append({"type": "ENCOUNTER", "date": iso(e.timestamp), "encounter_id": e.id, "summary": e.summary,
                       "diagnoses": [{"code_system": d.code_system, "code": d.code, "term": d.display_term} for d in dx]})
        for rx in (await db.execute(select(Prescription).where(Prescription.encounter_id == e.id))).scalars().all():
            events.append({"type": "PRESCRIPTION", "date": iso(e.timestamp), "prescription_id": rx.id, "medications": rx.medications})
        for l in (await db.execute(select(LabOrder).where(LabOrder.encounter_id == e.id))).scalars().all():
            events.append({"type": "LAB", "date": iso(e.timestamp), "test_name": l.test_name, "status": l.status,
                           "result_values": l.result_values, "flagged_abnormal": l.flagged_abnormal})
        for b in (await db.execute(select(Bill).where(Bill.encounter_id == e.id))).scalars().all():
            events.append({"type": "BILL", "date": iso(e.timestamp), "bill_id": b.id, "total_amount": b.total_amount, "payment_status": b.payment_status})
        for d in (await db.execute(select(DischargeSummary).where(DischargeSummary.encounter_id == e.id))).scalars().all():
            events.append({"type": "DISCHARGE", "date": iso(e.timestamp), "instructions": d.instructions, "follow_up_date": iso(d.follow_up_date)})
        for r in (await db.execute(select(Referral).where(Referral.encounter_id == e.id))).scalars().all():
            events.append({"type": "REFERRAL", "date": iso(r.created_at), "kind": r.kind, "status": r.status, "note": r.note})
    for t in (await db.execute(select(TherapySession).where(TherapySession.patient_id == p.id))).scalars().all():
        events.append({"type": "THERAPY", "date": iso(t.scheduled_at), "therapy_name": t.therapy_name, "status": t.status})
    events.sort(key=lambda e: e.get("date") or "", reverse=True)
    return {"patient": patient_public(p), "events": events}


@router.get("/patients/me/family")
async def family_list(user: User = Depends(require_roles("PATIENT")), db: AsyncSession = Depends(get_db)):
    p = await patient_for_user(db, user)
    rows = (await db.execute(select(FamilyMember, Patient).join(Patient, Patient.id == FamilyMember.patient_id)
                             .where(FamilyMember.primary_patient_id == p.id))).all()
    return [{"id": f.id, "relation": f.relation, **patient_public(m)} for f, m in rows]


class FamilyIn(BaseModel):
    name: str
    relation: str
    dob: date | None = None
    gender: str | None = None
    phone: str | None = None
    uhid: str | None = None


@router.post("/patients/me/family", status_code=201)
async def family_add(body: FamilyIn, user: User = Depends(require_roles("PATIENT")), db: AsyncSession = Depends(get_db)):
    from app.api.v1.endpoints.core import _next_uhid
    p = await patient_for_user(db, user)
    member = None
    if body.uhid:
        member = (await db.execute(select(Patient).where(Patient.uhid == body.uhid.strip()))).scalars().first()
    if member is None:
        member = Patient(uhid=await _next_uhid(db), name=body.name.strip(), dob=body.dob, gender=body.gender, phone=body.phone or p.phone)
        db.add(member)
        await db.flush()
    f = FamilyMember(primary_patient_id=p.id, patient_id=member.id, relation=body.relation)
    db.add(f)
    await db.commit()
    return {"id": f.id, "relation": f.relation, **patient_public(member)}


class InteractionIn(BaseModel):
    medications: list[str]
    patient_id: int | None = None


@router.post("/prescriptions/check-interactions")
async def check_interactions(body: InteractionIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.api.v1.endpoints.ops import find_interactions
    from app.models import CurrentMedication
    names = [m for m in body.medications if m.strip()]
    if body.patient_id:
        current = (await db.execute(select(CurrentMedication).where(CurrentMedication.patient_id == body.patient_id,
                                                                    CurrentMedication.active.is_(True)))).scalars().all()
        names += [c.name for c in current]
    return {"flags": await find_interactions(db, names)}

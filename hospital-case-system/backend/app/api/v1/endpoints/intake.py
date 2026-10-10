"""Patient pre-consultation intake (consent, complaints, adaptive HPI, allergies/meds/past, ROS)."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.common import assert_patient_access, encounter_with_access, get_or_404, iso, patient_for_user, patient_public
from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models import (
    Allergy, Appointment, ChiefComplaint, CurrentMedication, Encounter, HistoryOfPresentIllness, LabOrder, PastHistory,
    PatientIntake, ReviewOfSystems, User,
)
from app.services import history_summary, question_engine

router = APIRouter()
ROS_SYSTEMS = ["GENERAL", "CV", "RESPIRATORY", "GI", "NEURO", "MUSCULOSKELETAL", "SKIN", "ENT", "GU", "PSYCHIATRIC", "ENDOCRINE"]


async def _appt_for(db: AsyncSession, user: User, appointment_id: int) -> Appointment:
    appt = await get_or_404(db, Appointment, appointment_id, "Appointment")
    await assert_patient_access(db, user, appt.patient_id)
    return appt


async def _intake(db: AsyncSession, appt: Appointment, create: bool = False) -> PatientIntake | None:
    row = (await db.execute(select(PatientIntake).where(PatientIntake.appointment_id == appt.id))).scalars().first()
    if row is None and create:
        row = PatientIntake(appointment_id=appt.id, patient_id=appt.patient_id)
        db.add(row)
        await db.flush()
    return row


def _intake_public(i: PatientIntake | None) -> dict | None:
    if i is None:
        return None
    return {"id": i.id, "appointment_id": i.appointment_id, "status": i.status, "language_used": i.language_used,
            "started_at": iso(i.started_at), "submitted_at": iso(i.submitted_at), "duration_sec": i.duration_sec,
            "consent_recorded": i.consent_recorded, "consent_items": i.consent_items,
            "consent_revoked_at": iso(i.consent_revoked_at)}


async def _gather(db: AsyncSession, appt: Appointment) -> dict:
    cc = (await db.execute(select(ChiefComplaint).where(ChiefComplaint.appointment_id == appt.id))).scalars().all()
    hpi = (await db.execute(select(HistoryOfPresentIllness).where(HistoryOfPresentIllness.appointment_id == appt.id))).scalars().all()
    al = (await db.execute(select(Allergy).where(Allergy.patient_id == appt.patient_id))).scalars().all()
    md = (await db.execute(select(CurrentMedication).where(CurrentMedication.patient_id == appt.patient_id, CurrentMedication.active.is_(True)))).scalars().all()
    ph = (await db.execute(select(PastHistory).where(PastHistory.patient_id == appt.patient_id))).scalars().all()
    ros = (await db.execute(select(ReviewOfSystems).where(ReviewOfSystems.appointment_id == appt.id))).scalars().all()
    return {
        "chief_complaints": [{"id": c.id, "complaint_text": c.complaint_text, "duration_days": c.duration_days, "severity": c.severity} for c in cc],
        "hpi": {h.field: h.text for h in hpi if h.text},
        "allergies": [{"id": a.id, "substance": a.substance, "reaction": a.reaction, "severity": a.severity} for a in al],
        "current_meds": [{"id": m.id, "name": m.name, "dose": m.dose, "frequency": m.frequency, "system": m.system} for m in md],
        "past": [{"id": p.id, "kind": p.kind, "text": p.text, "year": p.year} for p in ph],
        "ros": [{"system": r.system, "positive": r.positive, "notes": r.notes} for r in ros],
    }


@router.get("/intake/question-catalog")
async def question_catalog(user: User = Depends(get_current_user)):
    return question_engine.catalog()


@router.get("/intake/{appointment_id}")
async def get_intake(appointment_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    appt = await _appt_for(db, user, appointment_id)
    intake = await _intake(db, appt)
    return {"intake": _intake_public(intake), "appointment": {"id": appt.id, "date": iso(appt.date), "status": appt.status,
                                                                 "chief_complaint": appt.chief_complaint}, **(await _gather(db, appt))}


class StartIn(BaseModel):
    language: str = "en-IN"
    consent_items: dict | None = None


@router.post("/intake/{appointment_id}/start")
async def start_intake(appointment_id: int, body: StartIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    appt = await _appt_for(db, user, appointment_id)
    intake = await _intake(db, appt, create=True)
    intake.language_used = body.language
    intake.consent_items = body.consent_items or {}
    intake.consent_recorded = bool(body.consent_items) and all(bool(v) for v in body.consent_items.values())
    intake.consent_revoked_at = None
    intake.started_at = intake.started_at or datetime.utcnow()
    await db.commit()
    return _intake_public(intake)


@router.post("/intake/{appointment_id}/revoke-consent")
async def revoke_consent(appointment_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    appt = await _appt_for(db, user, appointment_id)
    intake = await _intake(db, appt)
    if intake is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Intake not started")
    intake.consent_recorded = False
    intake.consent_revoked_at = datetime.utcnow()
    await db.commit()
    return _intake_public(intake)


class ComplaintIn(BaseModel):
    complaint_text: str
    duration_days: int | None = None
    severity: int | None = None


@router.post("/intake/{appointment_id}/complaints", status_code=201)
async def add_complaint(appointment_id: int, body: ComplaintIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    appt = await _appt_for(db, user, appointment_id)
    await _intake(db, appt, create=True)
    c = ChiefComplaint(appointment_id=appt.id, patient_id=appt.patient_id, complaint_text=body.complaint_text.strip(),
                       duration_days=body.duration_days, severity=body.severity)
    db.add(c)
    if not appt.chief_complaint:
        appt.chief_complaint = body.complaint_text.strip()
    await db.commit()
    return {"id": c.id, "complaint_text": c.complaint_text, "duration_days": c.duration_days, "severity": c.severity,
            "category": question_engine.classify_complaint(c.complaint_text)}


@router.delete("/intake/{appointment_id}/complaints/{complaint_id}")
async def delete_complaint(appointment_id: int, complaint_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    appt = await _appt_for(db, user, appointment_id)
    c = await get_or_404(db, ChiefComplaint, complaint_id, "Complaint")
    if c.appointment_id != appt.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Complaint not found")
    await db.delete(c)
    await db.commit()
    return {"ok": True}


@router.get("/intake/{appointment_id}/adaptive-questions")
async def adaptive_questions(appointment_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    appt = await _appt_for(db, user, appointment_id)
    data = await _gather(db, appt)
    text = " ".join(c["complaint_text"] for c in data["chief_complaints"]) or (appt.chief_complaint or "")
    return question_engine.branch_for_complaint(text, list(data["hpi"].keys()))


class HPIIn(BaseModel):
    answers: dict[str, str]


@router.put("/intake/{appointment_id}/hpi")
async def put_hpi(appointment_id: int, body: HPIIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    appt = await _appt_for(db, user, appointment_id)
    await _intake(db, appt, create=True)
    for field, text in body.answers.items():
        row = (await db.execute(select(HistoryOfPresentIllness).where(HistoryOfPresentIllness.appointment_id == appt.id,
                                                                       HistoryOfPresentIllness.field == field))).scalars().first()
        if row is None:
            db.add(HistoryOfPresentIllness(appointment_id=appt.id, field=field, text=text))
        else:
            row.text, row.updated_at = text, datetime.utcnow()
    await db.commit()
    return (await _gather(db, appt))["hpi"]


class AllergyIn(BaseModel):
    substance: str
    reaction: str | None = None
    severity: str | None = None


@router.post("/intake/{appointment_id}/allergies", status_code=201)
async def add_allergy(appointment_id: int, body: AllergyIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    appt = await _appt_for(db, user, appointment_id)
    a = Allergy(patient_id=appt.patient_id, substance=body.substance.strip(), reaction=body.reaction, severity=body.severity)
    db.add(a)
    await db.commit()
    return {"id": a.id, "substance": a.substance, "reaction": a.reaction, "severity": a.severity}


class MedIn(BaseModel):
    name: str
    dose: str | None = None
    frequency: str | None = None
    system: str | None = None


@router.post("/intake/{appointment_id}/meds", status_code=201)
async def add_med(appointment_id: int, body: MedIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    appt = await _appt_for(db, user, appointment_id)
    m = CurrentMedication(patient_id=appt.patient_id, name=body.name.strip(), dose=body.dose, frequency=body.frequency, system=body.system)
    db.add(m)
    await db.commit()
    return {"id": m.id, "name": m.name, "dose": m.dose, "frequency": m.frequency, "system": m.system}


class PastIn(BaseModel):
    kind: str
    text: str
    year: int | None = None


@router.post("/intake/{appointment_id}/past", status_code=201)
async def add_past(appointment_id: int, body: PastIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    appt = await _appt_for(db, user, appointment_id)
    if body.kind not in ("PMH", "PSH", "FAMILY", "SOCIAL", "OBSTETRIC"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "kind must be PMH|PSH|FAMILY|SOCIAL|OBSTETRIC")
    p = PastHistory(patient_id=appt.patient_id, kind=body.kind, text=body.text.strip(), year=body.year)
    db.add(p)
    await db.commit()
    return {"id": p.id, "kind": p.kind, "text": p.text, "year": p.year}


class ROSIn(BaseModel):
    systems: dict[str, dict]  # {"GI": {"positive": true, "notes": "..."}}


@router.put("/intake/{appointment_id}/ros")
async def put_ros(appointment_id: int, body: ROSIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    appt = await _appt_for(db, user, appointment_id)
    await _intake(db, appt, create=True)
    for system, val in body.systems.items():
        if system not in ROS_SYSTEMS:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown ROS system {system}")
        row = (await db.execute(select(ReviewOfSystems).where(ReviewOfSystems.appointment_id == appt.id,
                                                              ReviewOfSystems.system == system))).scalars().first()
        if row is None:
            row = ReviewOfSystems(appointment_id=appt.id, system=system)
            db.add(row)
        row.positive = bool(val.get("positive"))
        row.notes = val.get("notes")
    await db.commit()
    return (await _gather(db, appt))["ros"]


@router.post("/intake/{appointment_id}/submit")
async def submit_intake(appointment_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    appt = await _appt_for(db, user, appointment_id)
    intake = await _intake(db, appt, create=True)
    if not intake.consent_recorded:
        raise HTTPException(status.HTTP_409_CONFLICT, "Consent must be recorded before submission")
    intake.status = "SUBMITTED"
    intake.submitted_at = datetime.utcnow()
    intake.duration_sec = int((intake.submitted_at - intake.started_at).total_seconds()) if intake.started_at else None
    await db.commit()
    return _intake_public(intake)


@router.get("/patients/{patient_id}/allergies")
async def patient_allergies(patient_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await assert_patient_access(db, user, patient_id)
    rows = (await db.execute(select(Allergy).where(Allergy.patient_id == patient_id))).scalars().all()
    return [{"id": a.id, "substance": a.substance, "reaction": a.reaction, "severity": a.severity} for a in rows]


@router.get("/patients/{patient_id}/meds")
async def patient_meds(patient_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await assert_patient_access(db, user, patient_id)
    rows = (await db.execute(select(CurrentMedication).where(CurrentMedication.patient_id == patient_id))).scalars().all()
    return [{"id": m.id, "name": m.name, "dose": m.dose, "frequency": m.frequency, "system": m.system, "active": m.active} for m in rows]


@router.get("/patients/{patient_id}/past")
async def patient_past(patient_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await assert_patient_access(db, user, patient_id)
    rows = (await db.execute(select(PastHistory).where(PastHistory.patient_id == patient_id))).scalars().all()
    return [{"id": p.id, "kind": p.kind, "text": p.text, "year": p.year} for p in rows]


async def _summary_for_encounter(db: AsyncSession, user: User, encounter_id: int) -> tuple[Encounter, Appointment, PatientIntake | None, dict]:
    enc = await encounter_with_access(db, user, encounter_id)
    appt = await get_or_404(db, Appointment, enc.appointment_id, "Appointment")
    intake = await _intake(db, appt)
    data = await _gather(db, appt)
    return enc, appt, intake, data


@router.get("/encounters/{encounter_id}/intake-summary")
async def intake_summary(encounter_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    enc, appt, intake, data = await _summary_for_encounter(db, user, encounter_id)
    if intake and intake.status == "SUBMITTED" and user.role == "DOCTOR":
        intake.status = "REVIEWED"
        await db.commit()
    return {"intake_status": intake.status if intake else None, "duration_sec": intake.duration_sec if intake else None,
            "language_used": intake.language_used if intake else None, **data}


@router.get("/encounters/{encounter_id}/history-summary")
async def encounter_history_summary(encounter_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    enc, appt, intake, data = await _summary_for_encounter(db, user, encounter_id)
    from app.models import Patient  # local import to avoid cycle noise
    patient = await db.get(Patient, enc.patient_id)
    labs = (await db.execute(select(LabOrder).where(LabOrder.encounter_id == enc.id))).scalars().all()
    data["lab_orders"] = [{"test_name": l.test_name, "status": l.status, "flagged_abnormal": l.flagged_abnormal} for l in labs]
    data["patient"] = patient_public(patient)
    if not data["chief_complaints"] and (enc.chief_complaint_raw or appt.chief_complaint):
        data["chief_complaints"] = [{"complaint_text": enc.chief_complaint_raw or appt.chief_complaint}]
    if not data["hpi"] and enc.extracted_entities:
        socrates_keys = {f for f, _ in history_summary.SOCRATES_ORDER}
        data["hpi"] = {k: (", ".join(v) if isinstance(v, list) else str(v))
                       for k, v in enc.extracted_entities.items() if v and k in socrates_keys}
    return history_summary.build_history_summary(data)

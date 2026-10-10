"""Nurse, lab, prescriptions, pharmacy, billing, discharge, follow-up, FHIR, ABHA, analytics, admin."""
import uuid
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.common import (
    CONSULT_FEE, STAFF_ROLES, appointment_by_code, appointment_public, assert_patient_access, encounter_with_access,
    get_or_404, iso, patient_for_user, patient_public,
)
from app.core.database import get_db
from app.core.security import audit, get_current_user, hash_password, require_roles
from app.models import (
    Appointment, AuditLog, AyushCaseRecord, Bill, Department, Diagnosis, DischargeSummary, DoctorProfile, DoctorSlot,
    DrugInteractionFlag, DrugInteractionPair, Encounter, LabOrder, Notification, NurseVitals, Patient, PharmacyDispense,
    Prescription, StockItem, TherapySession, User,
)
from app.services import fhir, mocks
from app.services.extraction import auto_flag_result_values, evaluate_result_values

router = APIRouter()


# ------------------------------------------------------------------ nurse
class VitalsIn(BaseModel):
    bp: str | None = None
    pulse: int | None = None
    temp: float | None = None
    weight: float | None = None


def _vitals_public(v: NurseVitals) -> dict:
    return {"id": v.id, "appointment_id": v.appointment_id, "bp": v.bp, "pulse": v.pulse, "temp": v.temp, "weight": v.weight,
            "recorded_at": iso(v.recorded_at)}


@router.post("/nurse/vitals/{appointment_id}", status_code=201)
async def record_vitals(appointment_id: int, body: VitalsIn, user: User = Depends(require_roles("NURSE", "DOCTOR", "ADMIN")),
                        db: AsyncSession = Depends(get_db)):
    appt = await get_or_404(db, Appointment, appointment_id, "Appointment")
    v = NurseVitals(appointment_id=appt.id, bp=body.bp, pulse=body.pulse, temp=body.temp, weight=body.weight, recorded_by=user.id)
    db.add(v)
    audit(db, user.id, "VITALS_RECORDED", f"appointment:{appt.id}")
    await db.commit()
    return _vitals_public(v)


@router.get("/nurse/today")
async def nurse_today(user: User = Depends(require_roles("NURSE", "ADMIN")), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Appointment).where(Appointment.date == date.today(),
                                                       Appointment.status.in_(["CHECKED_IN", "IN_CONSULTATION"])))).scalars().all()
    out = []
    for a in rows:
        v = (await db.execute(select(NurseVitals).where(NurseVitals.appointment_id == a.id))).scalars().first()
        d = await appointment_public(db, a)
        d["vitals"] = _vitals_public(v) if v else None
        d["vitals_missing"] = v is None
        out.append(d)
    return out


class TherapyIn(BaseModel):
    patient_id: int
    therapy_name: str
    scheduled_at: datetime


def _therapy_public(t: TherapySession, patient: Patient | None) -> dict:
    return {"id": t.id, "patient_id": t.patient_id, "patient_name": patient.name if patient else None,
            "uhid": patient.uhid if patient else None, "therapy_name": t.therapy_name, "scheduled_at": iso(t.scheduled_at),
            "status": t.status}


@router.get("/nurse/therapy-sessions")
async def therapy_list(user: User = Depends(require_roles("NURSE", "DOCTOR", "ADMIN")), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(TherapySession).order_by(TherapySession.scheduled_at))).scalars().all()
    return [_therapy_public(t, await db.get(Patient, t.patient_id)) for t in rows]


@router.post("/nurse/therapy-sessions", status_code=201)
async def therapy_create(body: TherapyIn, user: User = Depends(require_roles("NURSE", "DOCTOR", "ADMIN")), db: AsyncSession = Depends(get_db)):
    patient = await get_or_404(db, Patient, body.patient_id, "Patient")
    t = TherapySession(patient_id=patient.id, therapy_name=body.therapy_name, scheduled_at=body.scheduled_at)
    db.add(t)
    db.add(Notification(patient_id=patient.id, message=f"Therapy {body.therapy_name} scheduled for {body.scheduled_at.isoformat()}."))
    await db.commit()
    return _therapy_public(t, patient)


class TherapyPatch(BaseModel):
    status: str | None = None
    scheduled_at: datetime | None = None


@router.patch("/nurse/therapy-sessions/{session_id}")
async def therapy_patch(session_id: int, body: TherapyPatch, user: User = Depends(require_roles("NURSE", "DOCTOR", "ADMIN")),
                        db: AsyncSession = Depends(get_db)):
    t = await get_or_404(db, TherapySession, session_id, "Therapy session")
    if body.status:
        t.status = body.status
    if body.scheduled_at:
        t.scheduled_at = body.scheduled_at
    await db.commit()
    return _therapy_public(t, await db.get(Patient, t.patient_id))


# ------------------------------------------------------------------ lab
class LabOrderIn(BaseModel):
    encounter_id: int
    test_name: str


async def _lab_public(db: AsyncSession, l: LabOrder) -> dict:
    enc = await db.get(Encounter, l.encounter_id)
    patient = await db.get(Patient, enc.patient_id) if enc else None
    return {"id": l.id, "encounter_id": l.encounter_id, "patient_id": enc.patient_id if enc else None,
            "patient_name": patient.name if patient else None, "uhid": patient.uhid if patient else None,
            "test_name": l.test_name, "status": l.status, "result_values": l.result_values, "flagged_abnormal": l.flagged_abnormal,
            "flags": evaluate_result_values(l.result_values)}


@router.post("/lab/orders", status_code=201)
async def lab_order(body: LabOrderIn, user: User = Depends(require_roles("DOCTOR", "ADMIN")), db: AsyncSession = Depends(get_db)):
    await get_or_404(db, Encounter, body.encounter_id, "Encounter")
    l = LabOrder(encounter_id=body.encounter_id, test_name=body.test_name.strip())
    db.add(l)
    await db.commit()
    return await _lab_public(db, l)


@router.get("/lab/orders")
async def lab_orders(patient_id: int | None = None, user: User = Depends(require_roles("LAB", "DOCTOR", "ADMIN")),
                     db: AsyncSession = Depends(get_db)):
    q = select(LabOrder).order_by(LabOrder.id.desc())
    if patient_id:
        q = q.join(Encounter, Encounter.id == LabOrder.encounter_id).where(Encounter.patient_id == patient_id)
    rows = (await db.execute(q)).scalars().all()
    return [await _lab_public(db, l) for l in rows]


class LabResultIn(BaseModel):
    result_values: dict
    flagged_abnormal: bool | None = None


@router.patch("/lab/orders/{order_id}/result")
async def lab_result(order_id: int, body: LabResultIn, user: User = Depends(require_roles("LAB", "ADMIN")), db: AsyncSession = Depends(get_db)):
    l = await get_or_404(db, LabOrder, order_id, "Lab order")
    l.result_values = body.result_values
    l.flagged_abnormal = body.flagged_abnormal if body.flagged_abnormal is not None else auto_flag_result_values(body.result_values)
    l.status = "RESULT_READY"
    enc = await db.get(Encounter, l.encounter_id)
    if enc:
        db.add(Notification(patient_id=enc.patient_id, message=f"Your {l.test_name} report is ready."))
    audit(db, user.id, "LAB_RESULT_ENTERED", f"lab_order:{l.id}")
    await db.commit()
    return await _lab_public(db, l)


# ------------------------------------------------------------------ prescriptions / interactions
class MedicationIn(BaseModel):
    name: str
    dose: str | None = None
    frequency: str | None = None
    duration_days: int | None = None
    quantity: int | None = None


class PrescriptionIn(BaseModel):
    medications: list[MedicationIn]


def _norm(name: str) -> str:
    return name.lower().split()[0] if name.strip() else ""


async def find_interactions(db: AsyncSession, names: list[str]) -> list[dict]:
    pairs = (await db.execute(select(DrugInteractionPair))).scalars().all()
    flags = []
    stems = {n: _norm(n) for n in names if n.strip()}
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            for p in pairs:
                pa, pb = _norm(p.drug_a), _norm(p.drug_b)
                if {stems.get(a), stems.get(b)} == {pa, pb}:
                    flags.append({"medication_a": a, "medication_b": b, "severity": p.severity, "note": p.note})
    return flags


@router.post("/prescriptions/{encounter_id}", status_code=201)
async def sign_prescription(encounter_id: int, body: PrescriptionIn, user: User = Depends(require_roles("DOCTOR", "ADMIN")),
                            db: AsyncSession = Depends(get_db)):
    enc = await get_or_404(db, Encounter, encounter_id, "Encounter")
    if not body.medications:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "At least one medication required")
    meds = []
    for m in body.medications:
        qty = m.quantity
        if qty is None and m.duration_days:
            per_day = {"od": 1, "bd": 2, "tds": 3, "qid": 4}.get((m.frequency or "").lower().strip(), 1)
            qty = per_day * m.duration_days
        meds.append({"name": m.name.strip(), "dose": m.dose, "frequency": m.frequency, "duration_days": m.duration_days,
                     "quantity": qty or 1})
    rx = Prescription(encounter_id=enc.id, medications=meds, pdf_url=f"/rx/{enc.id}")
    db.add(rx)
    await db.flush()
    for m in meds:
        db.add(PharmacyDispense(prescription_id=rx.id, medication_name=m["name"], quantity=m["quantity"]))
    flags = await find_interactions(db, [m["name"] for m in meds])
    for f in flags:
        db.add(DrugInteractionFlag(prescription_id=rx.id, medication_a=f["medication_a"], medication_b=f["medication_b"],
                                   severity=f["severity"], note=f["note"]))
    appt = await db.get(Appointment, enc.appointment_id)
    if appt and appt.status in ("CHECKED_IN", "IN_CONSULTATION"):
        appt.status = "COMPLETED"
    db.add(Notification(patient_id=enc.patient_id, message="Your prescription is ready at the pharmacy."))
    audit(db, user.id, "PRESCRIPTION_SIGNED", f"prescription:{rx.id}")
    await db.commit()
    return {"id": rx.id, "encounter_id": enc.id, "medications": meds, "interaction_flags": flags, "pdf_url": rx.pdf_url}


# ------------------------------------------------------------------ pharmacy
async def _dispense_public(db: AsyncSession, d: PharmacyDispense) -> dict:
    rx = await db.get(Prescription, d.prescription_id)
    enc = await db.get(Encounter, rx.encounter_id) if rx else None
    patient = await db.get(Patient, enc.patient_id) if enc else None
    stock = (await db.execute(select(StockItem).where(StockItem.name.ilike(d.medication_name)))).scalars().first()
    return {"id": d.id, "prescription_id": d.prescription_id, "encounter_id": rx.encounter_id if rx else None,
            "patient_name": patient.name if patient else None, "uhid": patient.uhid if patient else None,
            "medication_name": d.medication_name, "quantity": d.quantity, "status": d.status,
            "in_stock": stock.quantity if stock else None}


@router.get("/pharmacy/queue")
async def pharmacy_queue(user: User = Depends(require_roles("PHARMACY", "ADMIN")), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(PharmacyDispense).where(PharmacyDispense.status == "PENDING").order_by(PharmacyDispense.id))).scalars().all()
    return [await _dispense_public(db, d) for d in rows]


class CodeIn(BaseModel):
    code: str


@router.post("/pharmacy/scan")
async def pharmacy_scan(body: CodeIn, user: User = Depends(require_roles("PHARMACY", "ADMIN")), db: AsyncSession = Depends(get_db)):
    appt = await appointment_by_code(db, body.code)
    enc = (await db.execute(select(Encounter).where(Encounter.appointment_id == appt.id))).scalars().first()
    if enc is None:
        return {"appointment": await appointment_public(db, appt), "dispenses": []}
    rows = (await db.execute(select(PharmacyDispense).join(Prescription, Prescription.id == PharmacyDispense.prescription_id)
                             .where(Prescription.encounter_id == enc.id))).scalars().all()
    return {"appointment": await appointment_public(db, appt), "encounter_id": enc.id,
            "dispenses": [await _dispense_public(db, d) for d in rows]}


async def _ensure_bill(db: AsyncSession, enc: Encounter) -> Bill:
    bill = (await db.execute(select(Bill).where(Bill.encounter_id == enc.id))).scalars().first()
    items = [{"description": "Consultation fee", "amount": CONSULT_FEE}]
    rxs = (await db.execute(select(Prescription).where(Prescription.encounter_id == enc.id))).scalars().all()
    for rx in rxs:
        for m in rx.medications or []:
            stock = (await db.execute(select(StockItem).where(StockItem.name.ilike(m["name"])))).scalars().first()
            price = stock.unit_price if stock else 10.0
            items.append({"description": f"{m['name']} x {m.get('quantity', 1)}", "amount": round(price * (m.get("quantity") or 1), 2)})
    labs = (await db.execute(select(LabOrder).where(LabOrder.encounter_id == enc.id))).scalars().all()
    for l in labs:
        items.append({"description": f"Lab: {l.test_name}", "amount": 150.0})
    total = round(sum(i["amount"] for i in items), 2)
    if bill is None:
        bill = Bill(encounter_id=enc.id, line_items=items, total_amount=total)
        db.add(bill)
    elif bill.payment_status == "PENDING":
        bill.line_items, bill.total_amount = items, total
    await db.flush()
    return bill


@router.post("/pharmacy/dispense/{dispense_id}")
async def dispense(dispense_id: int, user: User = Depends(require_roles("PHARMACY", "ADMIN")), db: AsyncSession = Depends(get_db)):
    d = await get_or_404(db, PharmacyDispense, dispense_id, "Dispense")
    if d.status == "DISPENSED":
        raise HTTPException(status.HTTP_409_CONFLICT, "Already dispensed")
    stock = (await db.execute(select(StockItem).where(StockItem.name.ilike(d.medication_name)))).scalars().first()
    low_stock = False
    if stock:
        stock.quantity = max(0, stock.quantity - d.quantity)
        low_stock = stock.quantity <= stock.reorder_level
    d.status = "DISPENSED"
    rx = await db.get(Prescription, d.prescription_id)
    enc = await db.get(Encounter, rx.encounter_id)
    bill = await _ensure_bill(db, enc)
    audit(db, user.id, "DISPENSED", f"dispense:{d.id}")
    await db.commit()
    out = await _dispense_public(db, d)
    out.update(low_stock=low_stock, bill_id=bill.id, bill_total=bill.total_amount)
    return out


def _stock_public(s: StockItem) -> dict:
    return {"id": s.id, "name": s.name, "quantity": s.quantity, "reorder_level": s.reorder_level, "unit_price": s.unit_price,
            "low_stock": s.quantity <= s.reorder_level}


@router.get("/pharmacy/stock")
async def stock_list(user: User = Depends(require_roles("PHARMACY", "ADMIN")), db: AsyncSession = Depends(get_db)):
    return [_stock_public(s) for s in (await db.execute(select(StockItem).order_by(StockItem.name))).scalars().all()]


class StockIn(BaseModel):
    name: str
    quantity: int = 0
    reorder_level: int = 10
    unit_price: float = 0.0


@router.post("/pharmacy/stock", status_code=201)
async def stock_create(body: StockIn, user: User = Depends(require_roles("PHARMACY", "ADMIN")), db: AsyncSession = Depends(get_db)):
    s = StockItem(name=body.name.strip(), quantity=body.quantity, reorder_level=body.reorder_level, unit_price=body.unit_price)
    db.add(s)
    await db.commit()
    return _stock_public(s)


class StockPatch(BaseModel):
    quantity: int | None = None
    reorder_level: int | None = None
    unit_price: float | None = None


@router.patch("/pharmacy/stock/{item_id}")
async def stock_patch(item_id: int, body: StockPatch, user: User = Depends(require_roles("PHARMACY", "ADMIN")), db: AsyncSession = Depends(get_db)):
    s = await get_or_404(db, StockItem, item_id, "Stock item")
    for f in ("quantity", "reorder_level", "unit_price"):
        v = getattr(body, f)
        if v is not None:
            setattr(s, f, v)
    await db.commit()
    return _stock_public(s)


# ------------------------------------------------------------------ billing
async def _bill_public(db: AsyncSession, b: Bill) -> dict:
    enc = await db.get(Encounter, b.encounter_id)
    patient = await db.get(Patient, enc.patient_id) if enc else None
    return {"id": b.id, "encounter_id": b.encounter_id, "patient_id": enc.patient_id if enc else None,
            "patient_name": patient.name if patient else None, "uhid": patient.uhid if patient else None,
            "line_items": b.line_items, "total_amount": b.total_amount, "payment_status": b.payment_status,
            "date": iso(enc.timestamp) if enc else None}


@router.post("/billing/generate/{encounter_id}")
async def billing_generate(encounter_id: int, user: User = Depends(require_roles("BILLING", "PHARMACY", "ADMIN")), db: AsyncSession = Depends(get_db)):
    enc = await get_or_404(db, Encounter, encounter_id, "Encounter")
    bill = await _ensure_bill(db, enc)
    await db.commit()
    return await _bill_public(db, bill)


@router.post("/billing/pay/{bill_id}")
async def billing_pay(bill_id: int, user: User = Depends(require_roles("BILLING", "ADMIN", "PATIENT")), db: AsyncSession = Depends(get_db)):
    b = await get_or_404(db, Bill, bill_id, "Bill")
    if b.payment_status == "PAID":
        raise HTTPException(status.HTTP_409_CONFLICT, "Already paid")
    enc = await db.get(Encounter, b.encounter_id)
    await assert_patient_access(db, user, enc.patient_id)
    b.payment_status = "PAID"
    db.add(Notification(patient_id=enc.patient_id, message=f"Payment of ₹{b.total_amount:.2f} received. Thank you."))
    audit(db, user.id, "BILL_PAID", f"bill:{b.id}")
    await db.commit()
    out = await _bill_public(db, b)
    out["gateway"] = {"mocked": True, "reference": f"MOCKPAY-{uuid.uuid4().hex[:10].upper()}"}
    return out


@router.get("/billing/pending")
async def billing_pending(user: User = Depends(require_roles("BILLING", "ADMIN")), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Bill).where(Bill.payment_status == "PENDING").order_by(Bill.id.desc()))).scalars().all()
    return [await _bill_public(db, b) for b in rows]


@router.get("/billing/worklist")
async def billing_worklist(user: User = Depends(require_roles("BILLING", "ADMIN")), db: AsyncSession = Depends(get_db)):
    """Completed encounters today without a bill + all pending bills."""
    today = date.today()
    encs = (await db.execute(select(Encounter).join(Appointment, Appointment.id == Encounter.appointment_id)
                             .where(Appointment.date >= today - timedelta(days=7), Appointment.status == "COMPLETED"))).scalars().all()
    unbilled = []
    for e in encs:
        if not (await db.execute(select(Bill.id).where(Bill.encounter_id == e.id))).first():
            p = await db.get(Patient, e.patient_id)
            unbilled.append({"encounter_id": e.id, "patient_name": p.name, "uhid": p.uhid, "date": iso(e.timestamp)})
    bills = (await db.execute(select(Bill).order_by(Bill.id.desc()).limit(50))).scalars().all()
    return {"unbilled": unbilled, "bills": [await _bill_public(db, b) for b in bills]}


# ------------------------------------------------------------------ FHIR
async def build_bundle_for(db: AsyncSession, enc: Encounter) -> dict:
    patient = await db.get(Patient, enc.patient_id)
    doctor = await db.get(DoctorProfile, enc.doctor_id)
    doc_user = await db.get(User, doctor.user_id)
    dept = await db.get(Department, doctor.department_id)
    appt = await db.get(Appointment, enc.appointment_id)
    dx = (await db.execute(select(Diagnosis).where(Diagnosis.encounter_id == enc.id))).scalars().all()
    vitals = (await db.execute(select(NurseVitals).where(NurseVitals.appointment_id == appt.id))).scalars().all()
    rx = (await db.execute(select(Prescription).where(Prescription.encounter_id == enc.id))).scalars().all()
    labs = (await db.execute(select(LabOrder).where(LabOrder.encounter_id == enc.id))).scalars().all()
    ayush = (await db.execute(select(AyushCaseRecord).where(AyushCaseRecord.encounter_id == enc.id))).scalars().first()
    bundle = fhir.build_encounter_bundle(
        patient_public(patient), doc_user.name, dept.name,
        {"timestamp": iso(enc.timestamp), "summary": enc.summary},
        [{"code_system": d.code_system, "code": d.code, "display_term": d.display_term} for d in dx],
        [{"bp": v.bp, "pulse": v.pulse, "temp": v.temp, "weight": v.weight} for v in vitals],
        [{"medications": p.medications} for p in rx],
        [{"test_name": l.test_name, "result_values": l.result_values} for l in labs],
        {"prakriti_vata": ayush.prakriti_vata, "prakriti_pitta": ayush.prakriti_pitta, "prakriti_kapha": ayush.prakriti_kapha} if ayush else None,
    )
    fhir.validate_bundle(bundle)
    enc.fhir_bundle_id = bundle["id"]
    enc.fhir_bundle = bundle
    return bundle


@router.post("/fhir/generate-bundle/{encounter_id}")
async def fhir_generate(encounter_id: int, user: User = Depends(require_roles("DOCTOR", "ADMIN")), db: AsyncSession = Depends(get_db)):
    enc = await get_or_404(db, Encounter, encounter_id, "Encounter")
    bundle = await build_bundle_for(db, enc)
    audit(db, user.id, "FHIR_BUNDLE_GENERATED", f"encounter:{enc.id}")
    await db.commit()
    return bundle


@router.get("/fhir/bundle/{encounter_id}")
async def fhir_get(encounter_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    enc = await encounter_with_access(db, user, encounter_id)
    if not enc.fhir_bundle:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No bundle generated yet")
    return enc.fhir_bundle


# ------------------------------------------------------------------ discharge / follow-up
class DischargeIn(BaseModel):
    instructions: str | None = None
    follow_up_date: date | None = None
    summary_text: str | None = None


@router.post("/discharge/{encounter_id}", status_code=201)
async def discharge(encounter_id: int, body: DischargeIn, user: User = Depends(require_roles("DOCTOR", "ADMIN")), db: AsyncSession = Depends(get_db)):
    enc = await get_or_404(db, Encounter, encounter_id, "Encounter")
    bundle = await build_bundle_for(db, enc)
    ds = DischargeSummary(encounter_id=enc.id, summary_text=body.summary_text or enc.summary, instructions=body.instructions,
                          follow_up_date=body.follow_up_date, fhir_bundle_id=bundle["id"])
    db.add(ds)
    appt = await db.get(Appointment, enc.appointment_id)
    if appt and appt.status != "CANCELLED":
        appt.status = "COMPLETED"
    db.add(Notification(patient_id=enc.patient_id, message="Your discharge summary is available in My Records."))
    audit(db, user.id, "DISCHARGED", f"encounter:{enc.id}")
    await db.commit()
    return {"id": ds.id, "encounter_id": enc.id, "summary_text": ds.summary_text, "instructions": ds.instructions,
            "follow_up_date": iso(ds.follow_up_date), "fhir_bundle_id": ds.fhir_bundle_id}


@router.get("/discharge/{encounter_id}")
async def discharge_get(encounter_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    enc = await encounter_with_access(db, user, encounter_id)
    ds = (await db.execute(select(DischargeSummary).where(DischargeSummary.encounter_id == enc.id).order_by(DischargeSummary.id.desc()))).scalars().first()
    if ds is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No discharge summary")
    return {"id": ds.id, "encounter_id": enc.id, "summary_text": ds.summary_text, "instructions": ds.instructions,
            "follow_up_date": iso(ds.follow_up_date), "fhir_bundle_id": ds.fhir_bundle_id}


class FollowUpIn(BaseModel):
    patient_id: int
    doctor_id: int
    date: date
    slot_time: str | None = None
    note: str | None = None


@router.post("/followup/schedule", status_code=201)
async def followup_schedule(body: FollowUpIn, user: User = Depends(require_roles("DOCTOR", "RECEPTION", "ADMIN")), db: AsyncSession = Depends(get_db)):
    from app.api.v1.endpoints.core import _create_appointment  # reuse token/QR logic
    patient = await get_or_404(db, Patient, body.patient_id, "Patient")
    doctor = await get_or_404(db, DoctorProfile, body.doctor_id, "Doctor")
    slot = None
    if body.slot_time:
        hh, mm = body.slot_time.split(":")
        slot = (await db.execute(select(DoctorSlot).where(DoctorSlot.doctor_id == doctor.id, DoctorSlot.date == body.date,
                                                          DoctorSlot.start_time == time(int(hh), int(mm))))).scalars().first()
        if slot and slot.booked_count < slot.capacity:
            slot.booked_count += 1
        else:
            slot = None
    appt = await _create_appointment(db, patient, doctor, body.date, slot, body.slot_time or "09:00", "IN_PERSON", "FOLLOWUP", body.note)
    db.add(Notification(patient_id=patient.id, message=f"Follow-up booked for {body.date.isoformat()} at {appt.slot_time}."))
    await db.commit()
    return await appointment_public(db, appt)


# ------------------------------------------------------------------ ABHA (mock bridge)
class AbhaInitIn(BaseModel):
    aadhaar_or_mobile: str


class AbhaVerifyIn(BaseModel):
    txn_id: str
    otp: str


class AbhaLinkIn(BaseModel):
    encounter_id: int


@router.post("/abha/init-otp")
async def abha_init(body: AbhaInitIn, user: User = Depends(get_current_user)):
    return mocks.abha_init_otp(body.aadhaar_or_mobile)


@router.post("/abha/verify-otp")
async def abha_verify(body: AbhaVerifyIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = mocks.abha_verify_otp(body.txn_id, body.otp)
    if not res.get("verified"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, res.get("error", "OTP failed"))
    if user.role == "PATIENT":
        p = await patient_for_user(db, user)
        p.abha_id, p.abha_address = res["abha_id"], res["abha_address"]
        await db.commit()
    return res


@router.post("/abha/link-care-context")
async def abha_link(body: AbhaLinkIn, user: User = Depends(require_roles("DOCTOR", "ADMIN")), db: AsyncSession = Depends(get_db)):
    enc = await get_or_404(db, Encounter, body.encounter_id, "Encounter")
    p = await db.get(Patient, enc.patient_id)
    if not p.abha_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Patient has no ABHA id")
    res = mocks.abha_link_care_context(p.abha_id, enc.id)
    enc.abha_care_context_ref = res["care_context_ref"]
    await db.commit()
    return res


class AbhaSetIn(BaseModel):
    abha_id: str
    abha_address: str | None = None


@router.post("/patients/me/abha")
async def set_my_abha(body: AbhaSetIn, user: User = Depends(require_roles("PATIENT")), db: AsyncSession = Depends(get_db)):
    p = await patient_for_user(db, user)
    p.abha_id, p.abha_address = body.abha_id.strip(), body.abha_address
    await db.commit()
    return patient_public(p)


# ------------------------------------------------------------------ analytics / audit / notifications
@router.get("/analytics/summary")
async def analytics(user: User = Depends(require_roles("ADMIN", "BILLING", "RECEPTION")), db: AsyncSession = Depends(get_db)):
    today = date.today()
    total_patients = (await db.execute(select(func.count(Patient.id)))).scalar_one()
    appts_today = (await db.execute(select(func.count(Appointment.id)).where(Appointment.date == today))).scalar_one()
    by_status = dict((await db.execute(select(Appointment.status, func.count(Appointment.id)).where(Appointment.date == today)
                                       .group_by(Appointment.status))).all())
    by_system = dict((await db.execute(select(Appointment.system, func.count(Appointment.id)).group_by(Appointment.system))).all())
    revenue = (await db.execute(select(func.coalesce(func.sum(Bill.total_amount), 0)).where(Bill.payment_status == "PAID"))).scalar_one()
    pending = (await db.execute(select(func.coalesce(func.sum(Bill.total_amount), 0)).where(Bill.payment_status == "PENDING"))).scalar_one()
    low = (await db.execute(select(StockItem).where(StockItem.quantity <= StockItem.reorder_level))).scalars().all()
    red = (await db.execute(select(func.count(Appointment.id)).where(Appointment.date == today, Appointment.red_flag.is_(True)))).scalar_one()
    top_dx = (await db.execute(select(Diagnosis.display_term, func.count(Diagnosis.id)).where(Diagnosis.code_system == "NAMASTE")
                               .group_by(Diagnosis.display_term).order_by(func.count(Diagnosis.id).desc()).limit(5))).all()
    return {"date": today.isoformat(), "total_patients": total_patients, "appointments_today": appts_today,
            "by_status": by_status, "by_system": by_system, "red_flags_today": red,
            "revenue_paid": float(revenue), "revenue_pending": float(pending),
            "low_stock": [{"name": s.name, "quantity": s.quantity, "reorder_level": s.reorder_level} for s in low],
            "top_namaste_diagnoses": [{"term": t, "count": c} for t, c in top_dx]}


@router.get("/audit-log")
async def audit_log(limit: int = 100, user: User = Depends(require_roles("ADMIN")), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(AuditLog, User).outerjoin(User, User.id == AuditLog.actor_id)
                             .order_by(AuditLog.id.desc()).limit(limit))).all()
    return [{"id": a.id, "actor_id": a.actor_id, "actor": u.name if u else None, "role": u.role if u else None,
             "action": a.action, "target_record": a.target_record, "timestamp": iso(a.timestamp)} for a, u in rows]


@router.get("/notifications/me")
async def my_notifications(user: User = Depends(require_roles("PATIENT")), db: AsyncSession = Depends(get_db)):
    p = await patient_for_user(db, user)
    rows = (await db.execute(select(Notification).where(Notification.patient_id == p.id).order_by(Notification.id.desc()).limit(50))).scalars().all()
    return [{"id": n.id, "message": n.message, "created_at": iso(n.created_at), "read": n.read} for n in rows]


@router.patch("/notifications/{notification_id}/read")
async def read_notification(notification_id: int, user: User = Depends(require_roles("PATIENT")), db: AsyncSession = Depends(get_db)):
    p = await patient_for_user(db, user)
    n = await get_or_404(db, Notification, notification_id, "Notification")
    if n.patient_id != p.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not yours")
    n.read = True
    await db.commit()
    return {"ok": True}


# ------------------------------------------------------------------ patient records / vitals history
@router.get("/patients/me/records")
async def my_records(user: User = Depends(require_roles("PATIENT")), db: AsyncSession = Depends(get_db)):
    p = await patient_for_user(db, user)
    encs = (await db.execute(select(Encounter).where(Encounter.patient_id == p.id).order_by(Encounter.timestamp.desc()))).scalars().all()
    medicines, reports, bills = [], [], []
    for e in encs:
        for rx in (await db.execute(select(Prescription).where(Prescription.encounter_id == e.id))).scalars().all():
            medicines.append({"prescription_id": rx.id, "encounter_id": e.id, "date": iso(e.timestamp), "medications": rx.medications,
                              "pdf_url": rx.pdf_url})
        for l in (await db.execute(select(LabOrder).where(LabOrder.encounter_id == e.id))).scalars().all():
            reports.append({"id": l.id, "encounter_id": e.id, "date": iso(e.timestamp), "test_name": l.test_name, "status": l.status,
                            "result_values": l.result_values, "flagged_abnormal": l.flagged_abnormal})
        for b in (await db.execute(select(Bill).where(Bill.encounter_id == e.id))).scalars().all():
            bills.append(await _bill_public(db, b))
        ds = (await db.execute(select(DischargeSummary).where(DischargeSummary.encounter_id == e.id))).scalars().first()
        if ds:
            reports.append({"id": f"discharge-{ds.id}", "encounter_id": e.id, "date": iso(e.timestamp), "test_name": "Discharge summary",
                            "status": "READY", "result_values": {"instructions": ds.instructions, "follow_up": iso(ds.follow_up_date)},
                            "flagged_abnormal": False})
    return {"medicines": medicines, "reports": reports, "bills": bills}


@router.get("/patients/{patient_id}/vitals-history")
async def vitals_history(patient_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await assert_patient_access(db, user, patient_id)
    rows = (await db.execute(select(NurseVitals).join(Appointment, Appointment.id == NurseVitals.appointment_id)
                             .where(Appointment.patient_id == patient_id).order_by(NurseVitals.recorded_at))).scalars().all()
    return [{"date": iso(v.recorded_at), "pulse": v.pulse, "bp": v.bp, "temp": v.temp, "weight": v.weight} for v in rows]


# ------------------------------------------------------------------ admin
class StaffIn(BaseModel):
    name: str
    email: str
    password: str
    role: str
    registration_number: str | None = None
    department_id: int | None = None
    specialty: str | None = None


@router.get("/admin/staff")
async def staff_list(user: User = Depends(require_roles("ADMIN")), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(User).where(User.role != "PATIENT").order_by(User.role, User.name))).scalars().all()
    out = []
    for u in rows:
        d = (await db.execute(select(DoctorProfile).where(DoctorProfile.user_id == u.id))).scalars().first()
        out.append({"id": u.id, "name": u.name, "email": u.email, "role": u.role, "registration_number": u.registration_number,
                    "doctor_profile": {"id": d.id, "department_id": d.department_id, "specialty": d.specialty, "system": d.system} if d else None})
    return out


@router.post("/admin/staff", status_code=201)
async def staff_create(body: StaffIn, user: User = Depends(require_roles("ADMIN")), db: AsyncSession = Depends(get_db)):
    if body.role not in STAFF_ROLES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"role must be one of {'/'.join(STAFF_ROLES)}")
    email = body.email.lower().strip()
    if (await db.execute(select(User.id).where(User.email == email))).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already exists")
    u = User(email=email, hashed_password=hash_password(body.password), role=body.role, name=body.name.strip(),
             registration_number=body.registration_number)
    db.add(u)
    await db.flush()
    if body.role == "DOCTOR":
        if not body.department_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "department_id required for doctors")
        dept = await get_or_404(db, Department, body.department_id, "Department")
        db.add(DoctorProfile(user_id=u.id, department_id=dept.id, specialty=body.specialty, system=dept.system))
    audit(db, user.id, "STAFF_CREATED", f"user:{u.id}")
    await db.commit()
    return {"id": u.id, "name": u.name, "email": u.email, "role": u.role}


class DepartmentIn(BaseModel):
    name: str
    system: str


@router.post("/admin/departments", status_code=201)
async def department_create(body: DepartmentIn, user: User = Depends(require_roles("ADMIN")), db: AsyncSession = Depends(get_db)):
    if body.system not in ("ALLOPATHIC", "AYURVEDA"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "system must be ALLOPATHIC or AYURVEDA")
    d = Department(name=body.name.strip(), system=body.system)
    db.add(d)
    await db.commit()
    return {"id": d.id, "name": d.name, "system": d.system}


class SlotIn(BaseModel):
    doctor_id: int
    date: date
    start_time: str
    end_time: str
    capacity: int = 10


@router.post("/admin/doctor-slots", status_code=201)
async def slot_create(body: SlotIn, user: User = Depends(require_roles("ADMIN")), db: AsyncSession = Depends(get_db)):
    await get_or_404(db, DoctorProfile, body.doctor_id, "Doctor")
    sh, sm = body.start_time.split(":")
    eh, em = body.end_time.split(":")
    s = DoctorSlot(doctor_id=body.doctor_id, date=body.date, start_time=time(int(sh), int(sm)), end_time=time(int(eh), int(em)),
                   capacity=body.capacity)
    db.add(s)
    await db.commit()
    return {"id": s.id, "doctor_id": s.doctor_id, "date": iso(s.date), "start_time": body.start_time, "end_time": body.end_time,
            "capacity": s.capacity, "available": s.capacity}

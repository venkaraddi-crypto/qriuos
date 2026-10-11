"""Auth, patient profile, booking, reception and doctor queue."""
import re
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.common import (
    STAFF_ROLES, appointment_by_code, appointment_public, doctor_for_user, get_or_404, iso, patient_for_user,
    patient_public,
)
from app.core.config import settings
from app.core.crypto import decrypt_text, encrypt_text
from app.core.database import get_db
from app.core.security import (
    audit, create_access_token, get_current_user, hash_password, hash_refresh_token, new_refresh_token,
    require_roles, verify_password,
)
from app.models import (
    Appointment, Department, DoctorProfile, DoctorSlot, Encounter, Notification, Patient, RefreshSession,
    SecurityEvent, User,
)
from app.services.nlp import RED_FLAG_KEYWORDS

router = APIRouter()
REFRESH_COOKIE = "arogya_refresh"
REFRESH_DAYS = 14


# ------------------------------------------------------------------ auth
class LoginIn(BaseModel):
    email: str
    password: str


class RegisterIn(BaseModel):
    name: str
    email: str
    password: str
    phone: str
    dob: date | None = None
    gender: str | None = None


async def _issue_refresh(db: AsyncSession, user: User, response: Response, request: Request) -> None:
    raw = new_refresh_token()
    db.add(RefreshSession(user_id=user.id, token_hash=hash_refresh_token(raw),
                          expires_at=datetime.utcnow() + timedelta(days=REFRESH_DAYS),
                          user_agent=(request.headers.get("user-agent") or "")[:255]))
    response.set_cookie(REFRESH_COOKIE, raw, httponly=True, samesite="lax", secure=settings.is_production,
                        max_age=REFRESH_DAYS * 86400, path="/api/v1/auth")


def _token_payload(user: User, token: str) -> dict:
    return {"access_token": token, "token_type": "bearer", "role": user.role, "name": user.name, "user_id": user.id}


@router.post("/auth/login")
async def login(body: LoginIn, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == body.email.lower().strip()))).scalars().first()
    ip = request.client.host if request.client else None
    if user is None or not verify_password(body.password, user.hashed_password):
        db.add(SecurityEvent(actor_id=user.id if user else None, event_type="LOGIN_FAILED", ip_address=ip, detail=body.email))
        await db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    await _issue_refresh(db, user, response, request)
    db.add(SecurityEvent(actor_id=user.id, event_type="LOGIN", ip_address=ip))
    await db.commit()
    return _token_payload(user, create_access_token(user.email, user.role))


@router.post("/auth/refresh")
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    raw = request.cookies.get(REFRESH_COOKIE)
    if not raw:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No refresh cookie")
    sess = (await db.execute(select(RefreshSession).where(RefreshSession.token_hash == hash_refresh_token(raw)))).scalars().first()
    if sess is None or sess.revoked_at is not None or sess.expires_at < datetime.utcnow():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh session invalid")
    user = await db.get(User, sess.user_id)
    sess.revoked_at = datetime.utcnow()
    await _issue_refresh(db, user, response, request)
    await db.commit()
    return _token_payload(user, create_access_token(user.email, user.role))


@router.post("/auth/logout")
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    raw = request.cookies.get(REFRESH_COOKIE)
    if raw:
        sess = (await db.execute(select(RefreshSession).where(RefreshSession.token_hash == hash_refresh_token(raw)))).scalars().first()
        if sess and sess.revoked_at is None:
            sess.revoked_at = datetime.utcnow()
            await db.commit()
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth")
    return {"ok": True}


async def _next_uhid(db: AsyncSession) -> str:
    n = (await db.execute(select(func.count(Patient.id)))).scalar_one()
    while True:
        uhid = f"AIIA-2026-{n + 1:05d}"
        if not (await db.execute(select(Patient.id).where(Patient.uhid == uhid))).first():
            return uhid
        n += 1


@router.post("/auth/register", status_code=201)
async def register(body: RegisterIn, db: AsyncSession = Depends(get_db)):
    email = body.email.lower().strip()
    if (await db.execute(select(User.id).where(User.email == email))).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    if len(body.password) < 6:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password must be at least 6 characters")
    user = User(email=email, hashed_password=hash_password(body.password), role="PATIENT", name=body.name.strip())
    db.add(user)
    await db.flush()
    patient = Patient(user_id=user.id, uhid=await _next_uhid(db), name=body.name.strip(), dob=body.dob,
                      gender=body.gender, phone=body.phone)
    db.add(patient)
    await db.commit()
    return {"uhid": patient.uhid, "name": patient.name, "email": user.email, "patient_id": patient.id}


@router.get("/auth/me")
async def me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    out = {"id": user.id, "email": user.email, "role": user.role, "name": user.name,
           "registration_number": user.registration_number, "preferred_language": user.preferred_language,
           "theme_preference": user.theme_preference}
    if user.role == "PATIENT":
        p = (await db.execute(select(Patient).where(Patient.user_id == user.id))).scalars().first()
        if p:
            out["patient"] = patient_public(p)
    return out


# ------------------------------------------------------------------ patient profile
class ProfilePatch(BaseModel):
    name: str | None = None
    phone: str | None = None
    dob: date | None = None
    gender: str | None = None
    aadhaar_no: str | None = None


def _mask_aadhaar(enc: str | None) -> str | None:
    raw = decrypt_text(enc)
    if not raw or len(raw) < 4:
        return None
    return f"XXXX-XXXX-{raw[-4:]}"


def _profile(p: Patient) -> dict:
    return {**patient_public(p), "aadhaar_masked": _mask_aadhaar(p.aadhaar_no)}


@router.get("/patients/me/profile")
async def my_profile(user: User = Depends(require_roles("PATIENT")), db: AsyncSession = Depends(get_db)):
    return _profile(await patient_for_user(db, user))


@router.patch("/patients/me/profile")
async def patch_profile(body: ProfilePatch, user: User = Depends(require_roles("PATIENT")), db: AsyncSession = Depends(get_db)):
    p = await patient_for_user(db, user)
    if body.aadhaar_no is not None:
        digits = re.sub(r"\D", "", body.aadhaar_no)
        if len(digits) != 12:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Aadhaar must be 12 digits")
        p.aadhaar_no = encrypt_text(digits)
        audit(db, user.id, "AADHAAR_UPDATED", f"patient:{p.id}")
    for f in ("name", "phone", "dob", "gender"):
        v = getattr(body, f)
        if v is not None:
            setattr(p, f, v)
    if body.name:
        user.name = body.name
    await db.commit()
    return _profile(p)


# ------------------------------------------------------------------ QR / staff lookup
class CodeIn(BaseModel):
    code: str


@router.post("/qr/lookup")
async def qr_lookup(body: CodeIn, user: User = Depends(require_roles(*STAFF_ROLES)), db: AsyncSession = Depends(get_db)):
    appt = await appointment_by_code(db, body.code)
    enc = (await db.execute(select(Encounter).where(Encounter.appointment_id == appt.id))).scalars().first()
    out = await appointment_public(db, appt)
    out["encounter_id"] = enc.id if enc else None
    return out


@router.post("/staff/identify")
async def staff_identify(body: CodeIn, db: AsyncSession = Depends(get_db)):
    u = (await db.execute(select(User).where(User.registration_number == body.code.strip(), User.role != "PATIENT"))).scalars().first()
    if u is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown staff badge")
    return {"email": u.email, "role": u.role, "name": u.name}


def _today() -> date:
    return date.today()


def _parse_date(v: str) -> date:
    try:
        return date.fromisoformat(v)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "date must be YYYY-MM-DD")


# ------------------------------------------------------------------ departments / doctors / slots
@router.get("/departments")
async def departments(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Department).order_by(Department.id))).scalars().all()
    return [{"id": d.id, "name": d.name, "system": d.system} for d in rows]


@router.get("/doctors")
async def doctors(department_id: int | None = None, db: AsyncSession = Depends(get_db)):
    q = select(DoctorProfile, User, Department).join(User, User.id == DoctorProfile.user_id).join(
        Department, Department.id == DoctorProfile.department_id)
    if department_id:
        q = q.where(DoctorProfile.department_id == department_id)
    return [{"id": d.id, "name": u.name, "specialty": d.specialty, "system": d.system, "department_id": d.department_id,
             "department": dep.name, "registration_number": u.registration_number}
            for d, u, dep in (await db.execute(q)).all()]


@router.get("/doctors/{doctor_id}/slots")
async def doctor_slots(doctor_id: int, date: str | None = None, db: AsyncSession = Depends(get_db)):
    day = _parse_date(date) if date else _today()
    rows = (await db.execute(select(DoctorSlot).where(DoctorSlot.doctor_id == doctor_id, DoctorSlot.date == day)
                             .order_by(DoctorSlot.start_time))).scalars().all()
    return [{"id": s.id, "date": iso(s.date), "start_time": s.start_time.strftime("%H:%M"),
             "end_time": s.end_time.strftime("%H:%M"), "capacity": s.capacity, "available": s.capacity - s.booked_count}
            for s in rows]


# ------------------------------------------------------------------ appointments
class BookIn(BaseModel):
    doctor_id: int
    slot_id: int
    chief_complaint: str | None = None
    mode: str = "IN_PERSON"
    type: str = "NEW"


def _has_red_flag(text: str | None) -> bool:
    low = (text or "").lower()
    return any(k in low for k in RED_FLAG_KEYWORDS)


async def _next_token(db: AsyncSession, doctor_id: int, day: date) -> str:
    n = (await db.execute(select(func.count(Appointment.id)).where(
        Appointment.doctor_id == doctor_id, Appointment.date == day, Appointment.token_number != "E"))).scalar_one()
    return str(n + 1)


async def _create_appointment(db: AsyncSession, patient: Patient, doctor: DoctorProfile, day: date, slot: DoctorSlot | None,
                              slot_time: str | None, mode: str, type_: str, complaint: str | None,
                              token: str | None = None) -> Appointment:
    token = token or await _next_token(db, doctor.id, day)
    appt = Appointment(patient_id=patient.id, doctor_id=doctor.id, department_id=doctor.department_id, system=doctor.system,
                       mode=mode, type=type_, date=day, slot_time=slot_time, slot_id=slot.id if slot else None,
                       token_number=token, red_flag=_has_red_flag(complaint), status="BOOKED", chief_complaint=complaint,
                       checkin_token=f"AIIA-CK-PENDING-{patient.uhid}-{datetime.utcnow().timestamp()}")
    db.add(appt)
    await db.flush()
    appt.checkin_token = f"AIIA-CK-{appt.id}-{patient.uhid}-{token}"
    return appt


@router.post("/appointments", status_code=201)
async def book(body: BookIn, user: User = Depends(require_roles("PATIENT")), db: AsyncSession = Depends(get_db)):
    patient = await patient_for_user(db, user)
    doctor = await get_or_404(db, DoctorProfile, body.doctor_id, "Doctor")
    # Row lock (no-op on SQLite, real on Postgres) + capacity check keeps double-booking out.
    slot = (await db.execute(select(DoctorSlot).where(DoctorSlot.id == body.slot_id).with_for_update())).scalars().first()
    if slot is None or slot.doctor_id != doctor.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Slot not found for this doctor")
    if slot.booked_count >= slot.capacity:
        raise HTTPException(status.HTTP_409_CONFLICT, "Slot is full")
    slot.booked_count += 1
    appt = await _create_appointment(db, patient, doctor, slot.date, slot, slot.start_time.strftime("%H:%M"),
                                     body.mode, body.type, body.chief_complaint)
    db.add(Notification(patient_id=patient.id, message=f"Appointment booked for {slot.date.isoformat()} at {appt.slot_time}. Token {appt.token_number}."))
    audit(db, user.id, "APPOINTMENT_BOOKED", f"appointment:{appt.id}")
    await db.commit()
    return await appointment_public(db, appt)


@router.get("/appointments/me")
async def my_appointments(user: User = Depends(require_roles("PATIENT")), db: AsyncSession = Depends(get_db)):
    patient = await patient_for_user(db, user)
    rows = (await db.execute(select(Appointment).where(Appointment.patient_id == patient.id)
                             .order_by(Appointment.date.desc(), Appointment.id.desc()))).scalars().all()
    return [await appointment_public(db, a) for a in rows]


@router.patch("/appointments/{appointment_id}/cancel")
async def cancel(appointment_id: int, user: User = Depends(require_roles("PATIENT", "RECEPTION")), db: AsyncSession = Depends(get_db)):
    appt = await get_or_404(db, Appointment, appointment_id, "Appointment")
    if user.role == "PATIENT" and (await patient_for_user(db, user)).id != appt.patient_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your appointment")
    if appt.status not in ("BOOKED",):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Cannot cancel an appointment in status {appt.status}")
    appt.status = "CANCELLED"
    if appt.slot_id:
        slot = await db.get(DoctorSlot, appt.slot_id)
        if slot and slot.booked_count > 0:
            slot.booked_count -= 1
    await db.commit()
    return await appointment_public(db, appt)


class RescheduleIn(BaseModel):
    slot_id: int


@router.patch("/appointments/{appointment_id}/reschedule")
async def reschedule(appointment_id: int, body: RescheduleIn, user: User = Depends(require_roles("PATIENT", "RECEPTION")),
                     db: AsyncSession = Depends(get_db)):
    appt = await get_or_404(db, Appointment, appointment_id, "Appointment")
    if user.role == "PATIENT" and (await patient_for_user(db, user)).id != appt.patient_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your appointment")
    if appt.status != "BOOKED":
        raise HTTPException(status.HTTP_409_CONFLICT, "Only BOOKED appointments can be rescheduled")
    new_slot = (await db.execute(select(DoctorSlot).where(DoctorSlot.id == body.slot_id).with_for_update())).scalars().first()
    if new_slot is None or new_slot.doctor_id != appt.doctor_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Slot not found for this doctor")
    if new_slot.booked_count >= new_slot.capacity:
        raise HTTPException(status.HTTP_409_CONFLICT, "Slot is full")
    if appt.slot_id:
        old = await db.get(DoctorSlot, appt.slot_id)
        if old and old.booked_count > 0:
            old.booked_count -= 1
    new_slot.booked_count += 1
    patient = await db.get(Patient, appt.patient_id)
    appt.slot_id, appt.date, appt.slot_time = new_slot.id, new_slot.date, new_slot.start_time.strftime("%H:%M")
    appt.token_number = await _next_token(db, appt.doctor_id, new_slot.date)
    appt.checkin_token = f"AIIA-CK-{appt.id}-{patient.uhid}-{appt.token_number}"
    await db.commit()
    return await appointment_public(db, appt)


# ------------------------------------------------------------------ reception
@router.get("/reception/board")
async def reception_board(user: User = Depends(require_roles("RECEPTION", "ADMIN")), db: AsyncSession = Depends(get_db)):
    today = date.today()
    rows = (await db.execute(select(Appointment).where(Appointment.date >= today)
                             .order_by(Appointment.date, Appointment.slot_time, Appointment.id))).scalars().all()
    checked_in = [await appointment_public(db, a) for a in rows if a.status in ("CHECKED_IN", "IN_CONSULTATION")]
    upcoming = [await appointment_public(db, a) for a in rows if a.status == "BOOKED"]
    return {"checked_in": checked_in, "upcoming": upcoming, "date": today.isoformat()}


@router.get("/reception/lookup")
async def reception_lookup(q: str, user: User = Depends(require_roles("RECEPTION", "ADMIN")), db: AsyncSession = Depends(get_db)):
    like = f"%{q.strip()}%"
    rows = (await db.execute(select(Patient).where((Patient.uhid.ilike(like)) | (Patient.name.ilike(like)) | (Patient.phone.ilike(like)))
                             .limit(20))).scalars().all()
    return [patient_public(p) for p in rows]


@router.post("/reception/scan")
async def reception_scan(body: CodeIn, user: User = Depends(require_roles("RECEPTION", "ADMIN")), db: AsyncSession = Depends(get_db)):
    appt = await appointment_by_code(db, body.code)
    if appt.date != date.today():
        raise HTTPException(status.HTTP_409_CONFLICT, "Appointment is not scheduled for today")
    if appt.status == "CHECKED_IN":
        raise HTTPException(status.HTTP_409_CONFLICT, "Already checked in")
    if appt.status != "BOOKED":
        raise HTTPException(status.HTTP_409_CONFLICT, f"Cannot check in from status {appt.status}")
    appt.status = "CHECKED_IN"
    audit(db, user.id, "CHECKED_IN", f"appointment:{appt.id}")
    db.add(Notification(patient_id=appt.patient_id, message=f"You are checked in. Token {appt.token_number}."))
    await db.commit()
    return await appointment_public(db, appt)


class ProcessIn(BaseModel):
    appointment_id: int
    action: str  # NO_SHOW | CANCEL


@router.post("/reception/process")
async def reception_process(body: ProcessIn, user: User = Depends(require_roles("RECEPTION", "ADMIN")), db: AsyncSession = Depends(get_db)):
    appt = await get_or_404(db, Appointment, body.appointment_id, "Appointment")
    if body.action == "NO_SHOW":
        appt.status = "NO_SHOW"
    elif body.action == "CANCEL":
        appt.status = "CANCELLED"
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "action must be NO_SHOW or CANCEL")
    await db.commit()
    return await appointment_public(db, appt)


class WalkinIn(BaseModel):
    name: str
    phone: str
    doctor_id: int
    dob: date | None = None
    gender: str | None = None
    chief_complaint: str | None = None
    emergency: bool = False
    uhid: str | None = None


@router.post("/reception/walkin", status_code=201)
async def walkin(body: WalkinIn, user: User = Depends(require_roles("RECEPTION", "ADMIN")), db: AsyncSession = Depends(get_db)):
    patient = None
    if body.uhid:
        patient = (await db.execute(select(Patient).where(Patient.uhid == body.uhid.strip()))).scalars().first()
    if patient is None:
        patient = Patient(uhid=await _next_uhid(db), name=body.name.strip(), dob=body.dob, gender=body.gender, phone=body.phone)
        db.add(patient)
        await db.flush()
    doctor = await get_or_404(db, DoctorProfile, body.doctor_id, "Doctor")
    today = date.today()
    token = "E" if body.emergency else None
    appt = await _create_appointment(db, patient, doctor, today, None, datetime.now().strftime("%H:%M"), "IN_PERSON", "NEW",
                                     body.chief_complaint, token=token)
    appt.status = "CHECKED_IN"
    if body.emergency:
        appt.red_flag = True
    audit(db, user.id, "WALKIN_REGISTERED", f"appointment:{appt.id}")
    await db.commit()
    return await appointment_public(db, appt)


# ------------------------------------------------------------------ doctor queue
def _queue_sort(a: Appointment) -> tuple:
    emergency = 0 if a.token_number == "E" else 1
    red = 0 if a.red_flag else 1
    try:
        tok = int(a.token_number or 0)
    except ValueError:
        tok = 0
    return (emergency, red, tok, a.id)


@router.get("/queue")
async def queue(user: User = Depends(require_roles("DOCTOR")), db: AsyncSession = Depends(get_db)):
    doctor = await doctor_for_user(db, user)
    rows = (await db.execute(select(Appointment).where(Appointment.doctor_id == doctor.id, Appointment.date == date.today(),
                                                       Appointment.status.in_(["CHECKED_IN", "IN_CONSULTATION"])))).scalars().all()
    rows.sort(key=_queue_sort)
    out = []
    for a in rows:
        d = await appointment_public(db, a)
        enc = (await db.execute(select(Encounter).where(Encounter.appointment_id == a.id))).scalars().first()
        d["encounter_id"] = enc.id if enc else None
        out.append(d)
    return out


async def _own_queue_item(db: AsyncSession, user: User, appointment_id: int) -> Appointment:
    doctor = await doctor_for_user(db, user)
    appt = await get_or_404(db, Appointment, appointment_id, "Appointment")
    if appt.doctor_id != doctor.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not in your queue")
    return appt


@router.patch("/queue/{appointment_id}/skip")
async def queue_skip(appointment_id: int, user: User = Depends(require_roles("DOCTOR")), db: AsyncSession = Depends(get_db)):
    appt = await _own_queue_item(db, user, appointment_id)
    # Push to the back by giving the next token number for the day.
    appt.token_number = await _next_token(db, appt.doctor_id, appt.date)
    patient = await db.get(Patient, appt.patient_id)
    appt.checkin_token = f"AIIA-CK-{appt.id}-{patient.uhid}-{appt.token_number}"
    await db.commit()
    return await appointment_public(db, appt)


@router.patch("/queue/{appointment_id}/no-show")
async def queue_no_show(appointment_id: int, user: User = Depends(require_roles("DOCTOR")), db: AsyncSession = Depends(get_db)):
    appt = await _own_queue_item(db, user, appointment_id)
    appt.status = "NO_SHOW"
    await db.commit()
    return await appointment_public(db, appt)


@router.patch("/queue/{appointment_id}/call-next")
async def queue_call_next(appointment_id: int, user: User = Depends(require_roles("DOCTOR")), db: AsyncSession = Depends(get_db)):
    appt = await _own_queue_item(db, user, appointment_id)
    if appt.status not in ("CHECKED_IN", "IN_CONSULTATION"):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Patient is {appt.status}, not checked in")
    enc = (await db.execute(select(Encounter).where(Encounter.appointment_id == appt.id))).scalars().first()
    if enc is None:
        enc = Encounter(appointment_id=appt.id, patient_id=appt.patient_id, doctor_id=appt.doctor_id,
                        chief_complaint_raw=appt.chief_complaint)
        db.add(enc)
        await db.flush()
    appt.status = "IN_CONSULTATION"
    db.add(Notification(patient_id=appt.patient_id, message=f"It is your turn — token {appt.token_number}. Please proceed to the doctor."))
    audit(db, user.id, "CONSULTATION_STARTED", f"encounter:{enc.id}")
    await db.commit()
    return {"encounter_id": enc.id, "appointment_id": appt.id, "status": appt.status}

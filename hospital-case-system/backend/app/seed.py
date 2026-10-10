"""Demo seed — runs once on an empty database."""
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import encrypt_text
from app.core.security import hash_password
from app.models import (
    Appointment, Department, DoctorProfile, DoctorSlot, DrugInteractionPair, Encounter, Diagnosis,
    FamilyMember, NurseVitals, Patient, Prescription, RetentionPolicy, StockItem, TerminologyCode,
    TherapySession, User,
)
from app.services.terminology_data import CURATED

DEMO_PASSWORD = "password123"

USERS = [
    ("patient@demo.in", "PATIENT", "Kamla Devi", None),
    ("reception@demo.in", "RECEPTION", "Reception Desk", "REC-001"),
    ("doctor-allo@demo.in", "DOCTOR", "Dr. Anjali Mehra", "DMC-45121"),
    ("doctor-ayu@demo.in", "DOCTOR", "Dr. Raghav Iyer", "CCIM-AYU-7788"),
    ("nurse@demo.in", "NURSE", "Sister Mary Thomas", "NRC-2201"),
    ("lab@demo.in", "LAB", "Lab Technician", "LAB-009"),
    ("pharmacy@demo.in", "PHARMACY", "Pharmacist Desk", "PH-310"),
    ("billing@demo.in", "BILLING", "Billing Counter", "BIL-02"),
    ("admin@demo.in", "ADMIN", "System Administrator", "ADM-01"),
]

DEPARTMENTS = [
    ("General Medicine", "ALLOPATHIC"),
    ("Orthopaedics", "ALLOPATHIC"),
    ("Paediatrics", "ALLOPATHIC"),
    ("Kayachikitsa", "AYURVEDA"),
    ("Panchakarma", "AYURVEDA"),
    ("Shalya Tantra", "AYURVEDA"),
]

PATIENTS = [
    ("Kamla Devi", date(1968, 4, 12), "Female", "9876500001", "91-1234-5678-0001"),
    ("Suresh Pawar", date(1975, 9, 3), "Male", "9876500002", None),
    ("Lakshmi Ammal", date(1957, 1, 21), "Female", "9876500003", "91-1234-5678-0003"),
    ("Vikram Singh Rathore", date(1990, 7, 30), "Male", "9876500004", None),
    ("Meena Kumari", date(1983, 11, 15), "Female", "9876500005", "91-1234-5678-0005"),
    ("Abdul Rahman", date(1962, 5, 8), "Male", "9876500006", None),
    ("Priya Nair", date(1995, 2, 27), "Female", "9876500007", None),
    ("Harbhajan Gill", date(1950, 12, 1), "Male", "9876500008", "91-1234-5678-0008"),
]

STOCK = [
    ("Paracetamol 500mg", 400, 50, 1.5),
    ("Triphala Churna", 18, 25, 3.0),
    ("Sitopaladi Churna", 60, 20, 4.0),
    ("Omeprazole 20mg", 150, 30, 2.5),
    ("Mahanarayan Taila", 12, 10, 120.0),
]

INTERACTIONS = [
    ("Warfarin", "Aspirin", "HIGH", "Increased bleeding risk."),
    ("Metformin", "Alcohol", "MODERATE", "Lactic acidosis risk."),
    ("Omeprazole", "Clopidogrel", "MODERATE", "Reduced antiplatelet effect."),
    ("Ibuprofen", "Lisinopril", "MODERATE", "Reduced antihypertensive effect, renal risk."),
    ("Triphala Churna", "Warfarin", "LOW", "Possible additive anticoagulant effect — monitor INR."),
    ("Ashwagandha", "Levothyroxine", "LOW", "May alter thyroid hormone levels."),
]


def _slots(doctor_id: int, days: int = 5) -> list[DoctorSlot]:
    out = []
    today = date.today()
    for d in range(days):
        day = today + timedelta(days=d)
        for h in (9, 10, 11, 14, 15):
            out.append(DoctorSlot(doctor_id=doctor_id, date=day, start_time=time(h, 0), end_time=time(h + 1, 0),
                                  capacity=10, booked_count=0))
    return out


def _appt(p: Patient, doc: DoctorProfile, dept: Department, token: str, status: str, day: date, slot: str = "09:00",
          red_flag: bool = False, complaint: str | None = None, type_: str = "NEW") -> Appointment:
    return Appointment(patient_id=p.id, doctor_id=doc.id, department_id=dept.id, system=doc.system, mode="IN_PERSON",
                       type=type_, date=day, slot_time=slot, token_number=token, red_flag=red_flag, status=status,
                       chief_complaint=complaint, checkin_token=f"AIIA-CK-SEED-{p.uhid}-{token}-{day.isoformat()}")



async def seed_if_empty(db: AsyncSession) -> None:
    if (await db.execute(select(User.id).limit(1))).first():
        return

    pw = hash_password(DEMO_PASSWORD)
    users = [User(email=e, hashed_password=pw, role=r, name=n, registration_number=reg) for e, r, n, reg in USERS]
    db.add_all(users)
    depts = [Department(name=n, system=s) for n, s in DEPARTMENTS]
    db.add_all(depts)
    await db.flush()
    by_email = {u.email: u for u in users}

    doc_allo = DoctorProfile(user_id=by_email["doctor-allo@demo.in"].id, department_id=depts[0].id,
                             specialty="Internal Medicine", system="ALLOPATHIC")
    doc_ayu = DoctorProfile(user_id=by_email["doctor-ayu@demo.in"].id, department_id=depts[3].id,
                            specialty="Kayachikitsa", system="AYURVEDA")
    db.add_all([doc_allo, doc_ayu])
    await db.flush()
    db.add_all(_slots(doc_allo.id) + _slots(doc_ayu.id))

    patients = []
    for i, (name, dob, gender, phone, abha) in enumerate(PATIENTS, start=1):
        patients.append(Patient(
            uhid=f"AIIA-2026-{i:05d}", name=name, dob=dob, gender=gender, phone=phone, abha_id=abha,
            abha_address=f"{name.split()[0].lower()}@abdm" if abha else None,
            aadhaar_no=encrypt_text(f"{200000000000 + i * 1111:012d}"),
            user_id=by_email["patient@demo.in"].id if i == 1 else None))
    db.add_all(patients)
    await db.flush()
    family = Patient(uhid="AIIA-2026-00009", name="Sushila Krishnan", dob=date(1946, 3, 9), gender="Female",
                     phone="9876500009")
    db.add(family)
    await db.flush()
    db.add(FamilyMember(primary_patient_id=patients[0].id, patient_id=family.id, relation="Mother"))

    today = date.today()
    appts = [
        _appt(patients[0], doc_allo, depts[0], "1", "BOOKED", today, "09:00",
              complaint="Burning in upper abdomen after meals for 2 weeks"),
        _appt(patients[1], doc_allo, depts[0], "2", "CHECKED_IN", today, "09:00", complaint="Fever and body ache 3 days"),
        _appt(patients[2], doc_allo, depts[0], "3", "CHECKED_IN", today, "10:00", red_flag=True,
              complaint="Chest pain radiating to left arm since morning, breathlessness"),
        _appt(patients[3], doc_ayu, depts[3], "1", "CHECKED_IN", today, "09:00", complaint="Sour belching, acidity, burning"),
        _appt(patients[4], doc_ayu, depts[3], "2", "BOOKED", today, "10:00", complaint="Knee pain, stiffness in mornings"),
        _appt(patients[7], doc_allo, depts[0], "4", "COMPLETED", today - timedelta(days=30), "11:00", complaint="Diabetes review"),
        _appt(patients[7], doc_allo, depts[0], "5", "COMPLETED", today - timedelta(days=90), "11:00", complaint="Diabetes review"),
        _appt(patients[7], doc_allo, depts[0], "6", "BOOKED", today + timedelta(days=2), "11:00",
              complaint="Follow-up", type_="FOLLOWUP"),
    ]
    db.add_all(appts)
    await db.flush()
    uhid_of = {p.id: p.uhid for p in patients}
    for a in appts:
        a.checkin_token = f"AIIA-CK-{a.id}-{uhid_of[a.patient_id]}-{a.token_number}"

    nurse_id = by_email["nurse@demo.in"].id
    db.add(NurseVitals(appointment_id=appts[1].id, bp="128/84", pulse=88, temp=100.4, weight=72.0, recorded_by=nurse_id))

    # Dual-coded Amlapitta case on the Ayurveda side
    enc = Encounter(appointment_id=appts[3].id, patient_id=patients[3].id, doctor_id=doc_ayu.id,
                    chief_complaint_raw="Sour belching, acidity, burning after meals",
                    summary="Amlapitta — Pitta predominant. Advised Pathya-Apathya; Avipattikar Churna.")
    db.add(enc)
    await db.flush()
    db.add_all([
        Diagnosis(encounter_id=enc.id, code_system="NAMASTE", code="NAM-AYU-0001", display_term="Amlapitta", is_primary=True),
        Diagnosis(encounter_id=enc.id, code_system="ICD11_TM2", code="TM26.SA00", display_term="Amlapitta disorder (TM2)"),
        Diagnosis(encounter_id=enc.id, code_system="ICD11_BIOMEDICINE", code="K29.7", display_term="Gastritis, unspecified"),
    ])
    # Multi-visit patient history
    for a, hb in ((appts[5], "7.2"), (appts[6], "7.8")):
        e = Encounter(appointment_id=a.id, patient_id=patients[7].id, doctor_id=doc_allo.id,
                      timestamp=datetime.combine(a.date, time(11, 0)),
                      chief_complaint_raw="Diabetes review", summary=f"T2DM review. HbA1c {hb}%. Continue Metformin.")
        db.add(e)
        await db.flush()
        db.add(Prescription(encounter_id=e.id, medications=[
            {"name": "Metformin 500mg", "dose": "500 mg", "frequency": "BD", "duration_days": 30, "quantity": 60}]))
        db.add(NurseVitals(appointment_id=a.id, bp="138/88", pulse=76, temp=98.4, weight=81.0, recorded_by=nurse_id,
                           recorded_at=datetime.combine(a.date, time(10, 45))))

    for nam, term, syn, tm2, tm2_term, bio, bio_term in CURATED:
        db.add_all([
            TerminologyCode(code_system="NAMASTE", code=nam, term=term, synonyms=syn, biomedicine_code=bio),
            TerminologyCode(code_system="ICD11_TM2", code=tm2, term=tm2_term, synonyms=term, biomedicine_code=bio),
            TerminologyCode(code_system="ICD11_BIOMEDICINE", code=bio, term=bio_term, synonyms=syn, biomedicine_code=bio),
        ])
    db.add_all([StockItem(name=n, quantity=q, reorder_level=r, unit_price=p) for n, q, r, p in STOCK])
    db.add(TherapySession(patient_id=patients[3].id, therapy_name="Abhyanga + Swedana",
                          scheduled_at=datetime.combine(today + timedelta(days=1), time(10, 0))))
    db.add_all([DrugInteractionPair(drug_a=a, drug_b=b, severity=s, note=n) for a, b, s, n in INTERACTIONS])
    db.add(RetentionPolicy(raw_audio_retention_days=30, updated_by=by_email["admin@demo.in"].id))
    await db.commit()

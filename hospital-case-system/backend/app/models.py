from datetime import date, datetime, time

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.utcnow()


# ---------------------------------------------------------------- Identity & scheduling
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))  # PATIENT|RECEPTION|DOCTOR|NURSE|LAB|PHARMACY|BILLING|ADMIN
    name: Mapped[str] = mapped_column(String(120))
    registration_number: Mapped[str | None] = mapped_column(String(60), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preferred_language: Mapped[str] = mapped_column(String(10), default="en-IN")
    theme_preference: Mapped[str] = mapped_column(String(10), default="system")
    notification_preferences: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class Patient(Base):
    __tablename__ = "patients"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    uhid: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    aadhaar_no: Mapped[str | None] = mapped_column(String(255), nullable=True)  # encrypted at rest
    abha_id: Mapped[str | None] = mapped_column(String(30), nullable=True)
    abha_address: Mapped[str | None] = mapped_column(String(60), nullable=True)
    name: Mapped[str] = mapped_column(String(120))
    dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)


class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    system: Mapped[str] = mapped_column(String(20))  # ALLOPATHIC|AYURVEDA


class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    specialty: Mapped[str | None] = mapped_column(String(120), nullable=True)
    system: Mapped[str] = mapped_column(String(20))


class DoctorSlot(Base):
    __tablename__ = "doctor_slots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctor_profiles.id"))
    date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    capacity: Mapped[int] = mapped_column(Integer, default=10)
    booked_count: Mapped[int] = mapped_column(Integer, default=0)


class Appointment(Base):
    __tablename__ = "appointments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctor_profiles.id"))
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    system: Mapped[str] = mapped_column(String(20))
    mode: Mapped[str] = mapped_column(String(20), default="IN_PERSON")  # IN_PERSON|TELE
    type: Mapped[str] = mapped_column(String(20), default="NEW")  # NEW|FOLLOWUP
    date: Mapped[date] = mapped_column(Date)
    slot_time: Mapped[str | None] = mapped_column(String(10), nullable=True)
    slot_id: Mapped[int | None] = mapped_column(ForeignKey("doctor_slots.id"), nullable=True)
    token_number: Mapped[str | None] = mapped_column(String(10), nullable=True)
    checkin_token: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    red_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="BOOKED")
    chief_complaint: Mapped[str | None] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------- Clinical
class Encounter(Base):
    __tablename__ = "encounters"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    appointment_id: Mapped[int] = mapped_column(ForeignKey("appointments.id"))
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctor_profiles.id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    chief_complaint_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_entities: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    clinical_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    speech_recording_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fhir_bundle_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    fhir_bundle: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    abha_care_context_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)


class AyushCaseRecord(Base):
    __tablename__ = "ayush_case_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    encounter_id: Mapped[int] = mapped_column(ForeignKey("encounters.id"))
    prakriti_vata: Mapped[float | None] = mapped_column(Float, nullable=True)
    prakriti_pitta: Mapped[float | None] = mapped_column(Float, nullable=True)
    prakriti_kapha: Mapped[float | None] = mapped_column(Float, nullable=True)
    vikriti_dosha: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ashtavidha_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    dashavidha_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ahara_vihara: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class Diagnosis(Base):
    __tablename__ = "diagnoses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    encounter_id: Mapped[int] = mapped_column(ForeignKey("encounters.id"))
    code_system: Mapped[str] = mapped_column(String(30))  # NAMASTE|ICD11_TM2|ICD11_BIOMEDICINE
    code: Mapped[str] = mapped_column(String(40))
    display_term: Mapped[str] = mapped_column(String(200))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)


class NurseVitals(Base):
    __tablename__ = "nurse_vitals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    appointment_id: Mapped[int] = mapped_column(ForeignKey("appointments.id"))
    bp: Mapped[str | None] = mapped_column(String(20), nullable=True)
    pulse: Mapped[int | None] = mapped_column(Integer, nullable=True)
    temp: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    recorded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class LabOrder(Base):
    __tablename__ = "lab_orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    encounter_id: Mapped[int] = mapped_column(ForeignKey("encounters.id"))
    test_name: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default="ORDERED")  # ORDERED|RESULT_READY
    result_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    flagged_abnormal: Mapped[bool] = mapped_column(Boolean, default=False)


class Prescription(Base):
    __tablename__ = "prescriptions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    encounter_id: Mapped[int] = mapped_column(ForeignKey("encounters.id"))
    medications: Mapped[list | None] = mapped_column(JSON, nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(String(255), nullable=True)


class PharmacyDispense(Base):
    __tablename__ = "pharmacy_dispenses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prescription_id: Mapped[int] = mapped_column(ForeignKey("prescriptions.id"))
    medication_name: Mapped[str] = mapped_column(String(120))
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")  # PENDING|DISPENSED


class StockItem(Base):
    __tablename__ = "stock_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    reorder_level: Mapped[int] = mapped_column(Integer, default=10)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0)


class Bill(Base):
    __tablename__ = "bills"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    encounter_id: Mapped[int] = mapped_column(ForeignKey("encounters.id"))
    line_items: Mapped[list | None] = mapped_column(JSON, nullable=True)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    payment_status: Mapped[str] = mapped_column(String(20), default="PENDING")  # PENDING|PAID


class DischargeSummary(Base):
    __tablename__ = "discharge_summaries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    encounter_id: Mapped[int] = mapped_column(ForeignKey("encounters.id"))
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    fhir_bundle_id: Mapped[str | None] = mapped_column(String(80), nullable=True)


class TherapySession(Base):
    __tablename__ = "therapy_sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    therapy_name: Mapped[str] = mapped_column(String(120))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    status: Mapped[str] = mapped_column(String(20), default="SCHEDULED")


class TerminologyCode(Base):
    __tablename__ = "terminology_codes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code_system: Mapped[str] = mapped_column(String(30), index=True)
    code: Mapped[str] = mapped_column(String(40), index=True)
    term: Mapped[str] = mapped_column(String(200))
    synonyms: Mapped[str | None] = mapped_column(Text, nullable=True)
    biomedicine_code: Mapped[str | None] = mapped_column(String(40), nullable=True)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    read: Mapped[bool] = mapped_column(Boolean, default=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(120))
    target_record: Mapped[str | None] = mapped_column(String(200), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


# ---------------------------------------------------------------- AI / scribe
class AIProviderConfig(Base):
    __tablename__ = "ai_provider_configs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(40))
    capability: Mapped[str] = mapped_column(String(20))  # STT|DIARIZED_STT|TRANSLATE|CHAT|TTS|OCR
    api_key_encrypted: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    added_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class RetentionPolicy(Base):
    __tablename__ = "retention_policies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_audio_retention_days: Mapped[int] = mapped_column(Integer, default=30)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ConsultationTranscript(Base):
    __tablename__ = "consultation_transcripts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    encounter_id: Mapped[int] = mapped_column(ForeignKey("encounters.id"))
    raw_audio_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    diarized_transcript: Mapped[list | None] = mapped_column(JSON, nullable=True)
    language_detected: Mapped[str | None] = mapped_column(String(20), nullable=True)
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    audio_deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ClinicalNoteDraft(Base):
    __tablename__ = "clinical_note_drafts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    encounter_id: Mapped[int] = mapped_column(ForeignKey("encounters.id"))
    soap_subjective: Mapped[str | None] = mapped_column(Text, nullable=True)
    soap_objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    soap_assessment: Mapped[str | None] = mapped_column(Text, nullable=True)
    soap_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(40), default="mock")
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


# ---------------------------------------------------------------- Case file / intake
class FamilyMember(Base):
    __tablename__ = "family_members"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    primary_patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    relation: Mapped[str] = mapped_column(String(40))


class DrugInteractionPair(Base):
    __tablename__ = "drug_interaction_pairs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    drug_a: Mapped[str] = mapped_column(String(120))
    drug_b: Mapped[str] = mapped_column(String(120))
    severity: Mapped[str] = mapped_column(String(20))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class DrugInteractionFlag(Base):
    __tablename__ = "drug_interaction_flags"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prescription_id: Mapped[int] = mapped_column(ForeignKey("prescriptions.id"))
    medication_a: Mapped[str] = mapped_column(String(120))
    medication_b: Mapped[str] = mapped_column(String(120))
    severity: Mapped[str] = mapped_column(String(20))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class Referral(Base):
    __tablename__ = "referrals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    encounter_id: Mapped[int] = mapped_column(ForeignKey("encounters.id"))
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    from_doctor_id: Mapped[int] = mapped_column(ForeignKey("doctor_profiles.id"))
    kind: Mapped[str] = mapped_column(String(20))  # THERAPY|DEPARTMENT|DOCTOR
    to_department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    to_doctor_id: Mapped[int | None] = mapped_column(ForeignKey("doctor_profiles.id"), nullable=True)
    new_appointment_id: Mapped[int | None] = mapped_column(ForeignKey("appointments.id"), nullable=True)
    therapy_session_id: Mapped[int | None] = mapped_column(ForeignKey("therapy_sessions.id"), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="OPEN")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ChiefComplaint(Base):
    __tablename__ = "chief_complaints"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    encounter_id: Mapped[int | None] = mapped_column(ForeignKey("encounters.id"), nullable=True)
    appointment_id: Mapped[int | None] = mapped_column(ForeignKey("appointments.id"), nullable=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    complaint_text: Mapped[str] = mapped_column(Text)
    duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    severity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class HistoryOfPresentIllness(Base):
    __tablename__ = "history_of_present_illness"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    encounter_id: Mapped[int | None] = mapped_column(ForeignKey("encounters.id"), nullable=True)
    appointment_id: Mapped[int | None] = mapped_column(ForeignKey("appointments.id"), nullable=True)
    field: Mapped[str] = mapped_column(String(40))  # SOCRATES key
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Allergy(Base):
    __tablename__ = "allergies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    encounter_id: Mapped[int | None] = mapped_column(ForeignKey("encounters.id"), nullable=True)
    substance: Mapped[str] = mapped_column(String(120))
    reaction: Mapped[str | None] = mapped_column(String(200), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)


class CurrentMedication(Base):
    __tablename__ = "current_medications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    encounter_id: Mapped[int | None] = mapped_column(ForeignKey("encounters.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(120))
    dose: Mapped[str | None] = mapped_column(String(60), nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(60), nullable=True)
    system: Mapped[str | None] = mapped_column(String(20), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class PastHistory(Base):
    __tablename__ = "past_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    encounter_id: Mapped[int | None] = mapped_column(ForeignKey("encounters.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(20))  # PMH|PSH|FAMILY|SOCIAL|OBSTETRIC
    text: Mapped[str] = mapped_column(Text)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ReviewOfSystems(Base):
    __tablename__ = "review_of_systems"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    encounter_id: Mapped[int | None] = mapped_column(ForeignKey("encounters.id"), nullable=True)
    appointment_id: Mapped[int | None] = mapped_column(ForeignKey("appointments.id"), nullable=True)
    system: Mapped[str] = mapped_column(String(30))
    positive: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class PatientIntake(Base):
    __tablename__ = "patient_intakes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    appointment_id: Mapped[int] = mapped_column(ForeignKey("appointments.id"), unique=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")  # DRAFT|SUBMITTED|REVIEWED
    language_used: Mapped[str | None] = mapped_column(String(10), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    consent_recorded: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_items: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    consent_revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# ---------------------------------------------------------------- Security / Drive
class RefreshSession(Base):
    __tablename__ = "refresh_sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)


class SecurityEvent(Base):
    __tablename__ = "security_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(60))
    ip_address: Mapped[str | None] = mapped_column(String(60), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class DocumentAsset(Base):
    __tablename__ = "document_assets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    encounter_id: Mapped[int | None] = mapped_column(ForeignKey("encounters.id"), nullable=True)
    category: Mapped[str] = mapped_column(String(40), default="OTHER")
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_filename: Mapped[str] = mapped_column(String(80), unique=True)
    mime_type: Mapped[str] = mapped_column(String(80))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    encrypted_storage_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ocr_status: Mapped[str] = mapped_column(String(20), default="PENDING")
    ocr_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    document_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class DocumentAccessGrant(Base):
    __tablename__ = "document_access_grants"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("document_assets.id"))
    granted_to_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

"""Voice, NLP, Ayush assessments, terminology, diagnoses, encounters, timeline."""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.common import (
    STAFF_ROLES, assert_patient_access, encounter_with_access, get_or_404, iso, patient_public,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models import (
    Appointment, AyushCaseRecord, Diagnosis, Encounter, LabOrder, Patient, Prescription, TerminologyCode, User,
)
from app.services import dashavidha, mocks, nlp, prakriti, sarvam_client
from app.services.terminology_data import CURATED

router = APIRouter()
CLINICAL = ("DOCTOR", "NURSE", "ADMIN")


# ------------------------------------------------------------------ voice
@router.post("/voice/transcribe-chunk")
async def transcribe_chunk(audio_file: UploadFile | None = File(None), user: User = Depends(get_current_user)):
    if audio_file is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "audio_file is required")
    data = await audio_file.read()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "empty audio")
    return mocks.transcribe_chunk(len(data))


@router.get("/voice/stt-status")
async def stt_status(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    key, source = await sarvam_client.resolve_key(db, "STT")
    provider = "sarvam" if key else "whisper-fallback"
    hint = ("Sarvam Saaras is active." if key else
            "No Sarvam key — local Whisper will be tried; add a key in Admin → AI settings or .env SARVAM_API_KEY.")
    return {"provider": provider, "sarvam_model": sarvam_client.CAP_MODEL["STT"], "fallback": "whisper" if key else "none",
            "key_source": source, "hint": hint, "languages": sarvam_client.SARVAM_LANGUAGES,
            "default_language": settings.SARVAM_STT_LANGUAGE, "modes": sorted(sarvam_client.STT_MODES)}


@router.post("/voice/transcribe-audio")
async def transcribe_audio(language_code: str = "unknown", mode: str = "transcribe",
                           audio_file: UploadFile = File(...), user: User = Depends(get_current_user),
                           db: AsyncSession = Depends(get_db)):
    data = await audio_file.read()
    if len(data) > settings.MAX_DOCUMENT_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "audio exceeds size limit")
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "empty audio")
    return await sarvam_client.transcribe_intake(db, data, language_code, mode, audio_file.filename or "audio.wav")


class TTSIn(BaseModel):
    text: str
    language: str = "en-IN"


@router.post("/voice/tts")
async def tts(body: TTSIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await sarvam_client.text_to_speech(db, body.text, body.language)


# ------------------------------------------------------------------ NLP
class ExtractIn(BaseModel):
    text: str
    encounter_id: int | None = None


@router.post("/nlp/extract-entities")
async def extract_entities(body: ExtractIn, user: User = Depends(require_roles(*CLINICAL)), db: AsyncSession = Depends(get_db)):
    ents = nlp.extract_entities(body.text)
    if body.encounter_id:
        enc = await get_or_404(db, Encounter, body.encounter_id, "Encounter")
        enc.chief_complaint_raw = body.text
        enc.extracted_entities = ents
        if ents["red_flags"]:
            appt = await db.get(Appointment, enc.appointment_id)
            if appt:
                appt.red_flag = True
        await db.commit()
    return ents


# ------------------------------------------------------------------ Ayush
async def _ayush_record(db: AsyncSession, encounter_id: int) -> AyushCaseRecord:
    await get_or_404(db, Encounter, encounter_id, "Encounter")
    rec = (await db.execute(select(AyushCaseRecord).where(AyushCaseRecord.encounter_id == encounter_id))).scalars().first()
    if rec is None:
        rec = AyushCaseRecord(encounter_id=encounter_id)
        db.add(rec)
        await db.flush()
    return rec


def _ayush_public(r: AyushCaseRecord | None) -> dict | None:
    if r is None:
        return None
    return {"prakriti_vata": r.prakriti_vata, "prakriti_pitta": r.prakriti_pitta, "prakriti_kapha": r.prakriti_kapha,
            "vikriti_dosha": r.vikriti_dosha, "ashtavidha_data": r.ashtavidha_data, "dashavidha_data": r.dashavidha_data,
            "ahara_vihara": r.ahara_vihara}


class PrakritiIn(BaseModel):
    answers: dict[str, int]
    encounter_id: int
    current_symptoms: str | None = None


@router.post("/ayush/prakriti-score")
async def prakriti_score(body: PrakritiIn, user: User = Depends(require_roles(*CLINICAL)), db: AsyncSession = Depends(get_db)):
    p = prakriti.score_prakriti(body.answers)
    v = prakriti.assess_vikriti(body.current_symptoms, p["dominant"])
    rec = await _ayush_record(db, body.encounter_id)
    rec.prakriti_vata, rec.prakriti_pitta, rec.prakriti_kapha = p["vata"], p["pitta"], p["kapha"]
    rec.vikriti_dosha = v["aggravated_dosha"]
    await db.commit()
    return {"prakriti": p, "vikriti": v}


class AshtavidhaIn(BaseModel):
    encounter_id: int
    data: dict


@router.post("/ayush/ashtavidha")
async def ashtavidha(body: AshtavidhaIn, user: User = Depends(require_roles(*CLINICAL)), db: AsyncSession = Depends(get_db)):
    rec = await _ayush_record(db, body.encounter_id)
    rec.ashtavidha_data = body.data
    await db.commit()
    return {"ok": True, "ashtavidha_data": rec.ashtavidha_data}


@router.get("/ayush/dashavidha/reference")
async def dashavidha_reference(user: User = Depends(get_current_user)):
    return dashavidha.reference()


class DashavidhaIn(BaseModel):
    encounter_id: int
    parameters: dict
    ahara_vihara: dict | None = None


@router.post("/ayush/dashavidha")
async def dashavidha_assess(body: DashavidhaIn, user: User = Depends(require_roles(*CLINICAL)), db: AsyncSession = Depends(get_db)):
    rec = await _ayush_record(db, body.encounter_id)
    result = dashavidha.assess_dashavidha(body.parameters, body.ahara_vihara)
    rec.dashavidha_data = {"parameters": body.parameters, **result}
    if body.ahara_vihara is not None:
        rec.ahara_vihara = body.ahara_vihara
    await db.commit()
    return result


# ------------------------------------------------------------------ terminology
@router.get("/terminology/search")
async def terminology_search(query: str, system: str = "namaste", user: User = Depends(get_current_user),
                             db: AsyncSession = Depends(get_db)):
    sys_map = {"namaste": "NAMASTE", "tm2": "ICD11_TM2", "icd11_tm2": "ICD11_TM2", "biomedicine": "ICD11_BIOMEDICINE",
               "icd11": "ICD11_BIOMEDICINE", "icd11_biomedicine": "ICD11_BIOMEDICINE"}
    cs = sys_map.get(system.lower(), system.upper())
    like = f"%{query.strip()}%"
    rows = (await db.execute(select(TerminologyCode).where(
        TerminologyCode.code_system == cs,
        or_(TerminologyCode.term.ilike(like), TerminologyCode.synonyms.ilike(like), TerminologyCode.code.ilike(like)))
        .limit(15))).scalars().all()
    return [{"code": r.code, "code_system": r.code_system, "term": r.term, "biomedicine_code": r.biomedicine_code} for r in rows]


class TranslateCodeIn(BaseModel):
    code: str


def _curated_for(code: str) -> tuple | None:
    for row in CURATED:
        if code in (row[0], row[3], row[5]):
            return row
    return None


@router.post("/terminology/translate")
async def terminology_translate(body: TranslateCodeIn, user: User = Depends(get_current_user)):
    row = _curated_for(body.code.strip())
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Code not in curated map")
    nam, term, _, tm2, tm2_term, bio, bio_term = row
    return {"namaste": {"code": nam, "term": term}, "icd11_tm2": {"code": tm2, "term": tm2_term},
            "icd11_biomedicine": {"code": bio, "term": bio_term}}


# ------------------------------------------------------------------ diagnoses
class DiagnosisIn(BaseModel):
    encounter_id: int
    namaste_code: str | None = None
    biomedicine_code: str | None = None
    is_primary: bool = True


def _dx_public(d: Diagnosis) -> dict:
    return {"id": d.id, "code_system": d.code_system, "code": d.code, "display_term": d.display_term, "is_primary": d.is_primary}


@router.post("/diagnoses", status_code=201)
async def add_diagnosis(body: DiagnosisIn, user: User = Depends(require_roles("DOCTOR", "ADMIN")), db: AsyncSession = Depends(get_db)):
    await get_or_404(db, Encounter, body.encounter_id, "Encounter")
    created: list[Diagnosis] = []
    dual = False
    if body.namaste_code:
        row = _curated_for(body.namaste_code.strip())
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "NAMASTE code not found")
        nam, term, _, tm2, tm2_term, bio, bio_term = row
        created = [
            Diagnosis(encounter_id=body.encounter_id, code_system="NAMASTE", code=nam, display_term=term, is_primary=body.is_primary),
            Diagnosis(encounter_id=body.encounter_id, code_system="ICD11_TM2", code=tm2, display_term=tm2_term, is_primary=False),
            Diagnosis(encounter_id=body.encounter_id, code_system="ICD11_BIOMEDICINE", code=bio, display_term=bio_term, is_primary=False),
        ]
        dual = True
    elif body.biomedicine_code:
        code = body.biomedicine_code.strip()
        tc = (await db.execute(select(TerminologyCode).where(TerminologyCode.code == code,
                                                             TerminologyCode.code_system == "ICD11_BIOMEDICINE"))).scalars().first()
        term = tc.term if tc else code
        created = [Diagnosis(encounter_id=body.encounter_id, code_system="ICD11_BIOMEDICINE", code=code, display_term=term,
                             is_primary=body.is_primary)]
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "namaste_code or biomedicine_code required")
    db.add_all(created)
    await db.commit()
    rows = (await db.execute(select(Diagnosis).where(Diagnosis.encounter_id == body.encounter_id))).scalars().all()
    return {"dual_coded": dual, "diagnoses": [_dx_public(d) for d in rows]}


# ------------------------------------------------------------------ encounters
async def encounter_detail(db: AsyncSession, enc: Encounter) -> dict:
    patient = await db.get(Patient, enc.patient_id)
    appt = await db.get(Appointment, enc.appointment_id)
    dx = (await db.execute(select(Diagnosis).where(Diagnosis.encounter_id == enc.id))).scalars().all()
    rx = (await db.execute(select(Prescription).where(Prescription.encounter_id == enc.id))).scalars().all()
    labs = (await db.execute(select(LabOrder).where(LabOrder.encounter_id == enc.id))).scalars().all()
    ayush = (await db.execute(select(AyushCaseRecord).where(AyushCaseRecord.encounter_id == enc.id))).scalars().first()
    return {
        "id": enc.id, "appointment_id": enc.appointment_id, "system": appt.system if appt else None,
        "doctor_id": enc.doctor_id, "token_number": appt.token_number if appt else None,
        "red_flag": appt.red_flag if appt else False, "timestamp": iso(enc.timestamp),
        "chief_complaint_raw": enc.chief_complaint_raw, "summary": enc.summary, "clinical_notes": enc.clinical_notes,
        "extracted_entities": enc.extracted_entities, "fhir_bundle_id": enc.fhir_bundle_id,
        "abha_care_context_ref": enc.abha_care_context_ref,
        "patient": {"id": patient.id, "name": patient.name, "uhid": patient.uhid, "gender": patient.gender,
                    "age": patient_public(patient)["age"], "abha_id": patient.abha_id},
        "diagnoses": [_dx_public(d) for d in dx],
        "prescriptions": [{"id": p.id, "medications": p.medications, "pdf_url": p.pdf_url} for p in rx],
        "lab_orders": [{"id": l.id, "test_name": l.test_name, "status": l.status, "result_values": l.result_values,
                        "flagged_abnormal": l.flagged_abnormal} for l in labs],
        "ayush": _ayush_public(ayush),
    }


@router.get("/encounters/{encounter_id}")
async def get_encounter(encounter_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    enc = await encounter_with_access(db, user, encounter_id)
    return await encounter_detail(db, enc)


class EncounterPatch(BaseModel):
    summary: str | None = None
    clinical_notes: str | None = None


@router.patch("/encounters/{encounter_id}")
async def patch_encounter(encounter_id: int, body: EncounterPatch, user: User = Depends(require_roles("DOCTOR", "ADMIN")),
                          db: AsyncSession = Depends(get_db)):
    enc = await get_or_404(db, Encounter, encounter_id, "Encounter")
    if body.summary is not None:
        enc.summary = body.summary
    if body.clinical_notes is not None:
        enc.clinical_notes = body.clinical_notes
    await db.commit()
    return await encounter_detail(db, enc)


@router.get("/patients/{patient_id}/timeline")
async def timeline(patient_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await assert_patient_access(db, user, patient_id)
    await get_or_404(db, Patient, patient_id, "Patient")
    encs = (await db.execute(select(Encounter).where(Encounter.patient_id == patient_id)
                             .order_by(Encounter.timestamp.desc()))).scalars().all()
    out = []
    for e in encs:
        appt = await db.get(Appointment, e.appointment_id)
        dx = (await db.execute(select(Diagnosis).where(Diagnosis.encounter_id == e.id))).scalars().all()
        out.append({"encounter_id": e.id, "date": iso(e.timestamp), "system": appt.system if appt else None,
                    "chief_complaint": e.chief_complaint_raw, "summary": e.summary,
                    "diagnoses": [d.display_term for d in dx if d.code_system == "NAMASTE" or d.is_primary or not dx]})
    return out

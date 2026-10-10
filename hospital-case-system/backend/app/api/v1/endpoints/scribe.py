"""Ambient scribe: consented recording → diarized transcript → SOAP draft → doctor approval."""
import json
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.common import encounter_with_access, get_or_404, iso
from app.core.config import settings
from app.core.database import get_db
from app.core.security import audit, get_current_user, require_roles
from app.models import ClinicalNoteDraft, ConsultationTranscript, Encounter, User
from app.services import local_ai, sarvam_client
from app.services.nlp import extract_entities

router = APIRouter()
AUDIO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))), "media", "audio")


def _draft_public(d: ClinicalNoteDraft) -> dict:
    return {"id": d.id, "encounter_id": d.encounter_id, "soap_subjective": d.soap_subjective, "soap_objective": d.soap_objective,
            "soap_assessment": d.soap_assessment, "soap_plan": d.soap_plan, "source": d.source, "approved_by": d.approved_by,
            "approved_at": iso(d.approved_at), "created_at": iso(d.created_at)}


class StartIn(BaseModel):
    consent_given: bool
    consent_acknowledged_by_patient: bool = False
    language_code: str = "unknown"


@router.post("/consultation/{encounter_id}/start-recording")
async def start_recording(encounter_id: int, body: StartIn, user: User = Depends(require_roles("DOCTOR", "ADMIN")), db: AsyncSession = Depends(get_db)):
    await get_or_404(db, Encounter, encounter_id, "Encounter")
    if not (body.consent_given and body.consent_acknowledged_by_patient):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Patient consent is required before recording")
    t = ConsultationTranscript(encounter_id=encounter_id, consent_given=True, language_detected=body.language_code)
    db.add(t)
    audit(db, user.id, "SCRIBE_RECORDING_STARTED", f"encounter:{encounter_id}")
    await db.commit()
    return {"transcript_id": t.id, "recording": True, "started_at": iso(t.recorded_at)}


@router.post("/consultation/{encounter_id}/stop-recording")
async def stop_recording(encounter_id: int, audio_file: UploadFile | None = File(None), language_code: str = "unknown",
                         user: User = Depends(require_roles("DOCTOR", "ADMIN")), db: AsyncSession = Depends(get_db)):
    await get_or_404(db, Encounter, encounter_id, "Encounter")
    t = (await db.execute(select(ConsultationTranscript).where(ConsultationTranscript.encounter_id == encounter_id)
                          .order_by(ConsultationTranscript.id.desc()))).scalars().first()
    if t is None or not t.consent_given:
        raise HTTPException(status.HTTP_409_CONFLICT, "Recording was not started with consent")
    data = await audio_file.read() if audio_file else b""
    if len(data) > settings.MAX_DOCUMENT_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "audio too large")
    if data:
        os.makedirs(AUDIO_DIR, exist_ok=True)
        path = os.path.join(AUDIO_DIR, f"{uuid.uuid4().hex}.bin")
        with open(path, "wb") as f:
            f.write(data)
        t.raw_audio_url = path
        result = await sarvam_client.diarize_consultation(db, data, language_code)
    else:
        result = {"provider": "none", "mocked": False, "diarized_transcript": [], "error": "No audio received"}
    t.diarized_transcript = result["diarized_transcript"]
    if result.get("language_detected"):
        t.language_detected = result["language_detected"]
    await db.commit()
    return {"transcript_id": t.id, "diarized_transcript": t.diarized_transcript, "provider": result.get("provider"),
            "mocked": result.get("mocked", False), "error": result.get("error") or result.get("sarvam_error"),
            "local_error": result.get("local_error")}


@router.get("/consultation/{encounter_id}/transcript")
async def get_transcript(encounter_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await encounter_with_access(db, user, encounter_id)
    t = (await db.execute(select(ConsultationTranscript).where(ConsultationTranscript.encounter_id == encounter_id)
                          .order_by(ConsultationTranscript.id.desc()))).scalars().first()
    if t is None:
        return {"transcript_id": None, "diarized_transcript": [], "consent_given": False}
    return {"transcript_id": t.id, "diarized_transcript": t.diarized_transcript or [], "consent_given": t.consent_given,
            "language_detected": t.language_detected, "recorded_at": iso(t.recorded_at), "audio_deleted_at": iso(t.audio_deleted_at),
            "audio_retained": bool(t.raw_audio_url)}


def _rule_based_soap(turns: list[dict], enc: Encounter) -> dict:
    patient_text = " ".join(t["text"] for t in turns if t.get("speaker", "").lower() in ("patient", "1", "speaker_1"))
    doctor_text = " ".join(t["text"] for t in turns if t.get("speaker", "").lower() in ("doctor", "0", "speaker_0"))
    ents = extract_entities(patient_text or enc.chief_complaint_raw or "")
    subjective = patient_text or enc.chief_complaint_raw or ""
    assessment_bits = [ents["chief_complaint"]] if ents["chief_complaint"] else []
    if ents["red_flags"]:
        assessment_bits.append("RED FLAGS: " + ", ".join(ents["red_flags"]))
    return {"subjective": subjective, "objective": "Vitals and examination as recorded.",
            "assessment": "; ".join(assessment_bits) or "Clinical impression pending.",
            "plan": doctor_text or "Plan to be completed by doctor."}


@router.post("/consultation/{encounter_id}/generate-soap-draft", status_code=201)
async def generate_soap(encounter_id: int, user: User = Depends(require_roles("DOCTOR", "ADMIN")), db: AsyncSession = Depends(get_db)):
    enc = await get_or_404(db, Encounter, encounter_id, "Encounter")
    t = (await db.execute(select(ConsultationTranscript).where(ConsultationTranscript.encounter_id == encounter_id)
                          .order_by(ConsultationTranscript.id.desc()))).scalars().first()
    turns = (t.diarized_transcript if t else None) or []
    transcript_text = "\n".join(f"{x.get('speaker')}: {x.get('text')}" for x in turns)
    soap, provider, mocked = None, "mock", True
    if turns:
        chat = await sarvam_client.chat(db, [
            {"role": "system", "content": "You are a clinical scribe. Reply ONLY with JSON keys subjective, objective, assessment, plan."},
            {"role": "user", "content": transcript_text}])
        if chat.get("content"):
            parsed = local_ai._parse_loose_json(chat["content"])
            if parsed and all(k in parsed for k in ("subjective", "objective", "assessment", "plan")):
                soap, provider, mocked = parsed, chat["provider"], False
    if soap is None:
        soap = _rule_based_soap(turns, enc)
    d = ClinicalNoteDraft(encounter_id=enc.id, soap_subjective=str(soap["subjective"]), soap_objective=str(soap["objective"]),
                          soap_assessment=str(soap["assessment"]), soap_plan=str(soap["plan"]), source=provider)
    db.add(d)
    await db.commit()
    return {**_draft_public(d), "follow_up_weeks": 2, "llm_mocked": mocked, "provider": provider}


class DraftPatch(BaseModel):
    soap_subjective: str | None = None
    soap_objective: str | None = None
    soap_assessment: str | None = None
    soap_plan: str | None = None


@router.patch("/note-drafts/{draft_id}")
async def patch_draft(draft_id: int, body: DraftPatch, user: User = Depends(require_roles("DOCTOR", "ADMIN")), db: AsyncSession = Depends(get_db)):
    d = await get_or_404(db, ClinicalNoteDraft, draft_id, "Draft")
    for f in ("soap_subjective", "soap_objective", "soap_assessment", "soap_plan"):
        v = getattr(body, f)
        if v is not None:
            setattr(d, f, v)
    await db.commit()
    return _draft_public(d)


@router.post("/note-drafts/{draft_id}/approve")
async def approve_draft(draft_id: int, user: User = Depends(require_roles("DOCTOR")), db: AsyncSession = Depends(get_db)):
    d = await get_or_404(db, ClinicalNoteDraft, draft_id, "Draft")
    d.approved_by, d.approved_at = user.id, datetime.utcnow()
    enc = await db.get(Encounter, d.encounter_id)
    enc.clinical_notes = (f"S: {d.soap_subjective}\nO: {d.soap_objective}\nA: {d.soap_assessment}\nP: {d.soap_plan}")
    if not enc.summary:
        enc.summary = d.soap_assessment
    audit(db, user.id, "SOAP_APPROVED", f"draft:{d.id}")
    await db.commit()
    return _draft_public(d)


@router.get("/consultation/{encounter_id}/note-drafts")
async def list_drafts(encounter_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await encounter_with_access(db, user, encounter_id)
    rows = (await db.execute(select(ClinicalNoteDraft).where(ClinicalNoteDraft.encounter_id == encounter_id).order_by(ClinicalNoteDraft.id.desc()))).scalars().all()
    return [_draft_public(d) for d in rows]


@router.post("/summary/{encounter_id}/translate")
async def translate_summary(encounter_id: int, lang: str = "hi-IN", user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    enc = await encounter_with_access(db, user, encounter_id)
    text = enc.summary or enc.clinical_notes or ""
    if not text:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Encounter has no summary yet")
    return await sarvam_client.translate_text(db, text, lang)


@router.post("/summary/{encounter_id}/tts")
async def tts_summary(encounter_id: int, lang: str = "en-IN", user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    enc = await encounter_with_access(db, user, encounter_id)
    text = enc.summary or enc.clinical_notes or ""
    if not text:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Encounter has no summary yet")
    return await sarvam_client.text_to_speech(db, text, lang)

"""Document digitisation: OCR chain → structured extraction → doctor confirmation."""
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.common import assert_patient_access, get_or_404, iso, patient_for_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import audit, get_current_user, require_roles
from app.models import CurrentMedication, DocumentAsset, Encounter, LabOrder, Patient, User
from app.services import sarvam_client
from app.services.extraction import extract_document

router = APIRouter()


async def _target_patient(db: AsyncSession, user: User, patient_id: int | None) -> Patient:
    if user.role == "PATIENT":
        return await patient_for_user(db, user)
    if not patient_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "patient_id required for staff uploads")
    return await get_or_404(db, Patient, patient_id, "Patient")


@router.post("/documents/digitize")
async def digitize(file: UploadFile = File(...), patient_id: int | None = Form(None), encounter_id: int | None = Form(None),
                   user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    patient = await _target_patient(db, user, patient_id)
    data = await file.read()
    if len(data) > settings.MAX_DOCUMENT_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "file too large")
    mime = file.content_type or "application/octet-stream"
    ocr = await sarvam_client.ocr_document(db, data, file.filename or "upload", mime)
    extracted = extract_document(ocr.get("text") or "", file.filename or "")
    audit(db, user.id, "DOCUMENT_DIGITIZED", f"patient:{patient.id}")
    await db.commit()
    return {"patient_id": patient.id, "encounter_id": encounter_id, "filename": file.filename, "ocr": {"provider": ocr.get("provider"),
            "mocked": ocr.get("mocked", False), "text": ocr.get("text")}, "extracted": extracted}


class ExtractIn(BaseModel):
    text: str
    filename: str = ""


@router.post("/documents/extract")
async def extract(body: ExtractIn, user: User = Depends(get_current_user)):
    return extract_document(body.text, body.filename)


class ConfirmIn(BaseModel):
    patient_id: int
    encounter_id: int | None = None
    labs: list[dict] = []
    medications: list[dict] = []
    document_date: str | None = None


@router.post("/documents/confirm")
async def confirm(body: ConfirmIn, user: User = Depends(require_roles("DOCTOR", "ADMIN", "PATIENT")), db: AsyncSession = Depends(get_db)):
    await assert_patient_access(db, user, body.patient_id)
    patient = await get_or_404(db, Patient, body.patient_id, "Patient")
    enc_id = body.encounter_id
    if enc_id is None:
        enc = (await db.execute(select(Encounter).where(Encounter.patient_id == patient.id).order_by(Encounter.id.desc()))).scalars().first()
        enc_id = enc.id if enc else None
    created = {"labs": 0, "medications": 0}
    if body.labs:
        if enc_id is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "No encounter to attach lab values to")
        values = {l["test"]: l["value"] for l in body.labs if l.get("test") is not None}
        flagged = any(l.get("flag") for l in body.labs)
        db.add(LabOrder(encounter_id=enc_id, test_name=f"Imported report {body.document_date or date.today().isoformat()}",
                        status="RESULT_READY", result_values=values, flagged_abnormal=flagged))
        created["labs"] = len(values)
    for m in body.medications:
        if not m.get("name"):
            continue
        db.add(CurrentMedication(patient_id=patient.id, encounter_id=enc_id, name=m["name"], dose=m.get("dose"),
                                 frequency=m.get("frequency"), system="IMPORTED"))
        created["medications"] += 1
    audit(db, user.id, "DOCUMENT_CONFIRMED", f"patient:{patient.id}")
    await db.commit()
    return {"ok": True, "encounter_id": enc_id, **created}


@router.get("/documents/for-patient/{patient_id}")
async def for_patient(patient_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await assert_patient_access(db, user, patient_id)
    rows = (await db.execute(select(DocumentAsset).where(DocumentAsset.owner_patient_id == patient_id, DocumentAsset.deleted_at.is_(None))
                             .order_by(DocumentAsset.id.desc()))).scalars().all()
    return [{"id": d.id, "category": d.category, "original_filename": d.original_filename, "mime_type": d.mime_type,
             "size_bytes": d.size_bytes, "ocr_status": d.ocr_status, "document_date": iso(d.document_date), "created_at": iso(d.created_at)}
            for d in rows]

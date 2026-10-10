"""Encrypted Medical Drive: upload, list, download, delete, grant access."""
import hashlib
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.common import get_or_404, iso, patient_for_user
from app.core.config import settings
from app.core.crypto import decrypt_bytes, encrypt_bytes
from app.core.database import get_db
from app.core.security import audit, get_current_user, require_roles
from app.models import DocumentAccessGrant, DocumentAsset, DoctorProfile, Encounter, Patient, User

router = APIRouter()
DRIVE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))), "media", "drive")
ALLOWED_MIME = {"application/pdf", "image/jpeg", "image/png", "image/webp", "text/plain"}
CATEGORIES = {"LAB_REPORT", "PRESCRIPTION", "DISCHARGE", "IMAGING", "INSURANCE", "ID", "OTHER"}


def _public(d: DocumentAsset) -> dict:
    return {"id": d.id, "owner_patient_id": d.owner_patient_id, "encounter_id": d.encounter_id, "category": d.category,
            "original_filename": d.original_filename, "mime_type": d.mime_type, "size_bytes": d.size_bytes, "sha256": d.sha256,
            "document_date": iso(d.document_date), "created_at": iso(d.created_at), "ocr_status": d.ocr_status}


async def _can_access(db: AsyncSession, user: User, doc: DocumentAsset) -> bool:
    if user.role == "ADMIN":
        return True
    if user.role == "PATIENT":
        p = await patient_for_user(db, user)
        return p.id == doc.owner_patient_id
    grant = (await db.execute(select(DocumentAccessGrant).where(DocumentAccessGrant.document_id == doc.id,
                                                                DocumentAccessGrant.granted_to_user_id == user.id))).scalars().first()
    if grant and (grant.expires_at is None or grant.expires_at > datetime.utcnow()):
        return True
    if user.role == "DOCTOR":
        d = (await db.execute(select(DoctorProfile).where(DoctorProfile.user_id == user.id))).scalars().first()
        if d:
            q = select(Encounter.id).where(Encounter.patient_id == doc.owner_patient_id, Encounter.doctor_id == d.id)
            if (await db.execute(q)).first():
                return True
    return False


async def _doc_with_access(db: AsyncSession, user: User, doc_id: int) -> DocumentAsset:
    doc = await get_or_404(db, DocumentAsset, doc_id, "Document")
    if doc.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    if not await _can_access(db, user, doc):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No access to this document")
    return doc


@router.post("/drive/documents", status_code=201)
async def upload(file: UploadFile = File(...), category: str = Form("OTHER"), patient_id: int | None = Form(None),
                 encounter_id: int | None = Form(None), document_date: str | None = Form(None),
                 user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == "PATIENT":
        owner = await patient_for_user(db, user)
    else:
        if not patient_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "patient_id required")
        owner = await get_or_404(db, Patient, patient_id, "Patient")
    mime = file.content_type or "application/octet-stream"
    if mime not in ALLOWED_MIME:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, f"Unsupported type {mime}")
    data = await file.read()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "empty file")
    if len(data) > settings.MAX_DOCUMENT_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "file too large")
    os.makedirs(DRIVE_DIR, exist_ok=True)
    stored = f"{uuid.uuid4().hex}.bin"
    with open(os.path.join(DRIVE_DIR, stored), "wb") as f:
        f.write(encrypt_bytes(data))
    doc_date = None
    if document_date:
        try:
            doc_date = datetime.fromisoformat(document_date).date()
        except ValueError:
            pass
    doc = DocumentAsset(owner_patient_id=owner.id, uploaded_by=user.id, encounter_id=encounter_id,
                        category=category if category in CATEGORIES else "OTHER", original_filename=file.filename or "upload",
                        stored_filename=stored, mime_type=mime, size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                        encrypted_storage_key="fernet:v1", ocr_status="NOT_RUN", document_date=doc_date)
    db.add(doc)
    audit(db, user.id, "DRIVE_UPLOAD", f"patient:{owner.id}")
    await db.commit()
    return _public(doc)


@router.get("/drive/documents")
async def list_docs(patient_id: int | None = None, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == "PATIENT":
        pid = (await patient_for_user(db, user)).id
    elif patient_id:
        pid = patient_id
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "patient_id required")
    rows = (await db.execute(select(DocumentAsset).where(DocumentAsset.owner_patient_id == pid, DocumentAsset.deleted_at.is_(None))
                             .order_by(DocumentAsset.id.desc()))).scalars().all()
    out = []
    for d in rows:
        if await _can_access(db, user, d):
            out.append(_public(d))
    return out


@router.get("/drive/documents/{doc_id}")
async def get_doc(doc_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    doc = await _doc_with_access(db, user, doc_id)
    grants = (await db.execute(select(DocumentAccessGrant, User).join(User, User.id == DocumentAccessGrant.granted_to_user_id)
                               .where(DocumentAccessGrant.document_id == doc.id))).all()
    out = _public(doc)
    out["grants"] = [{"id": g.id, "user_id": g.granted_to_user_id, "user_name": u.name, "role": u.role, "reason": g.reason,
                      "expires_at": iso(g.expires_at)} for g, u in grants]
    return out


@router.get("/drive/documents/{doc_id}/download")
async def download(doc_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    doc = await _doc_with_access(db, user, doc_id)
    path = os.path.join(DRIVE_DIR, doc.stored_filename)
    if not os.path.exists(path):
        raise HTTPException(status.HTTP_410_GONE, "Stored blob missing")
    with open(path, "rb") as f:
        data = decrypt_bytes(f.read())
    audit(db, user.id, "DRIVE_DOWNLOAD", f"document:{doc.id}")
    await db.commit()
    return Response(content=data, media_type=doc.mime_type,
                    headers={"Content-Disposition": f'attachment; filename="{doc.original_filename}"'})


@router.delete("/drive/documents/{doc_id}")
async def delete_doc(doc_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    doc = await _doc_with_access(db, user, doc_id)
    if user.role not in ("PATIENT", "ADMIN"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the owner or admin can delete")
    doc.deleted_at = datetime.utcnow()
    path = os.path.join(DRIVE_DIR, doc.stored_filename)
    if os.path.exists(path):
        os.remove(path)
    audit(db, user.id, "DRIVE_DELETE", f"document:{doc.id}")
    await db.commit()
    return {"ok": True}


class GrantIn(BaseModel):
    user_id: int
    reason: str | None = None
    expires_at: datetime | None = None


@router.post("/drive/documents/{doc_id}/grant-access", status_code=201)
async def grant(doc_id: int, body: GrantIn, user: User = Depends(require_roles("PATIENT", "ADMIN")), db: AsyncSession = Depends(get_db)):
    doc = await _doc_with_access(db, user, doc_id)
    target = await get_or_404(db, User, body.user_id, "User")
    g = DocumentAccessGrant(document_id=doc.id, granted_to_user_id=target.id, reason=body.reason, expires_at=body.expires_at, created_by=user.id)
    db.add(g)
    audit(db, user.id, "DRIVE_GRANT", f"document:{doc.id}->user:{target.id}")
    await db.commit()
    return {"id": g.id, "document_id": doc.id, "user_id": target.id, "user_name": target.name, "reason": g.reason, "expires_at": iso(g.expires_at)}

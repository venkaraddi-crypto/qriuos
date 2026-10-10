"""Per-user settings, password change, sessions, profile photo."""
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.common import iso
from app.core.database import get_db
from app.core.security import audit, get_current_user, hash_password, verify_password
from app.models import RefreshSession, User

router = APIRouter()
PHOTO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))), "media", "photos")


def _public(u: User) -> dict:
    return {"id": u.id, "name": u.name, "email": u.email, "role": u.role, "preferred_language": u.preferred_language,
            "theme_preference": u.theme_preference, "notification_preferences": u.notification_preferences or {},
            "photo_url": f"/api/v1/profile/photo/{u.id}" if u.photo_url else None}


@router.get("/settings/me")
async def get_settings(user: User = Depends(get_current_user)):
    return _public(user)


class SettingsPatch(BaseModel):
    name: str | None = None
    preferred_language: str | None = None
    theme_preference: str | None = None
    notification_preferences: dict | None = None


@router.patch("/settings/me")
async def patch_settings(body: SettingsPatch, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if body.theme_preference and body.theme_preference not in ("light", "dark", "system"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "theme must be light|dark|system")
    for f in ("name", "preferred_language", "theme_preference", "notification_preferences"):
        v = getattr(body, f)
        if v is not None:
            setattr(user, f, v)
    await db.commit()
    return _public(user)


class PasswordIn(BaseModel):
    current_password: str
    new_password: str


@router.post("/settings/change-password")
async def change_password(body: PasswordIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    if len(body.new_password) < 8:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "New password must be at least 8 characters")
    user.hashed_password = hash_password(body.new_password)
    rows = (await db.execute(select(RefreshSession).where(RefreshSession.user_id == user.id, RefreshSession.revoked_at.is_(None)))).scalars().all()
    for s in rows:
        s.revoked_at = datetime.utcnow()
    audit(db, user.id, "PASSWORD_CHANGED", f"user:{user.id}")
    await db.commit()
    return {"ok": True, "sessions_revoked": len(rows)}


@router.get("/settings/sessions")
async def sessions(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(RefreshSession).where(RefreshSession.user_id == user.id).order_by(RefreshSession.id.desc()).limit(20))).scalars().all()
    return [{"id": s.id, "created_at": iso(s.created_at), "expires_at": iso(s.expires_at), "revoked_at": iso(s.revoked_at),
             "user_agent": s.user_agent, "active": s.revoked_at is None and s.expires_at > datetime.utcnow()} for s in rows]


@router.delete("/settings/sessions/{session_id}")
async def revoke_session(session_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    s = await db.get(RefreshSession, session_id)
    if s is None or s.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    s.revoked_at = datetime.utcnow()
    await db.commit()
    return {"ok": True}


@router.post("/profile/photo")
async def upload_photo(file: UploadFile = File(...), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if (file.content_type or "") not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "JPEG/PNG/WebP only")
    data = await file.read()
    if len(data) > 2 * 1024 * 1024:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Photo must be under 2 MB")
    os.makedirs(PHOTO_DIR, exist_ok=True)
    ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[file.content_type]
    name = f"{uuid.uuid4().hex}.{ext}"
    with open(os.path.join(PHOTO_DIR, name), "wb") as f:
        f.write(data)
    user.photo_url = name
    await db.commit()
    return _public(user)


@router.get("/profile/photo/{user_id}")
async def get_photo(user_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    target = await db.get(User, user_id)
    if target is None or not target.photo_url:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No photo")
    path = os.path.join(PHOTO_DIR, target.photo_url)
    if not os.path.exists(path):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No photo")
    ext = target.photo_url.rsplit(".", 1)[-1]
    mime = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(ext, "application/octet-stream")
    with open(path, "rb") as f:
        return Response(content=f.read(), media_type=mime)

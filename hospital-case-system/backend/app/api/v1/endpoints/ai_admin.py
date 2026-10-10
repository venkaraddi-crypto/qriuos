"""Admin: AI provider keys (encrypted at rest), status, test, retention policy."""
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.common import iso
from app.core.config import settings
from app.core.crypto import decrypt_key, encrypt_key, mask_key
from app.core.database import get_db
from app.core.security import audit, require_roles
from app.models import AIProviderConfig, RetentionPolicy, User
from app.services import local_ai, sarvam_client

router = APIRouter()
CAPABILITIES = ["STT", "DIARIZED_STT", "TRANSLATE", "CHAT", "TTS", "OCR"]


def _public(c: AIProviderConfig) -> dict:
    try:
        masked = mask_key(decrypt_key(c.api_key_encrypted))
    except Exception:  # noqa: BLE001
        masked = "••••••••????"
    return {"id": c.id, "provider": c.provider, "capability": c.capability, "api_key_masked": masked, "is_active": c.is_active,
            "added_by": c.added_by, "added_at": iso(c.added_at)}


@router.get("/admin/ai-providers")
async def list_providers(user: User = Depends(require_roles("ADMIN")), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(AIProviderConfig).order_by(AIProviderConfig.capability, AIProviderConfig.id.desc()))).scalars().all()
    return [_public(c) for c in rows]


class ProviderIn(BaseModel):
    provider: str = "sarvam"
    capability: str
    api_key: str


@router.post("/admin/ai-providers", status_code=201)
async def add_provider(body: ProviderIn, user: User = Depends(require_roles("ADMIN")), db: AsyncSession = Depends(get_db)):
    if body.capability not in CAPABILITIES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"capability must be one of {CAPABILITIES}")
    if len(body.api_key.strip()) < 8:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "API key looks too short")
    olds = (await db.execute(select(AIProviderConfig).where(AIProviderConfig.capability == body.capability, AIProviderConfig.provider == body.provider))).scalars().all()
    for o in olds:
        o.is_active = False
    c = AIProviderConfig(provider=body.provider, capability=body.capability, api_key_encrypted=encrypt_key(body.api_key.strip()), added_by=user.id)
    db.add(c)
    audit(db, user.id, "AI_KEY_ADDED", f"{body.provider}:{body.capability}")
    await db.commit()
    return _public(c)


@router.delete("/admin/ai-providers/{config_id}")
async def remove_provider(config_id: int, user: User = Depends(require_roles("ADMIN")), db: AsyncSession = Depends(get_db)):
    c = await db.get(AIProviderConfig, config_id)
    if c is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Config not found")
    c.is_active = False
    audit(db, user.id, "AI_KEY_DISABLED", f"config:{c.id}")
    await db.commit()
    return {"ok": True}


@router.get("/admin/ai-status")
async def ai_status(user: User = Depends(require_roles("ADMIN")), db: AsyncSession = Depends(get_db)):
    caps = {}
    for cap in CAPABILITIES:
        key, source = await sarvam_client.resolve_key(db, cap)
        caps[cap] = {"provider": "sarvam" if key else "fallback", "key_source": source, "model": sarvam_client.CAP_MODEL[cap]}
    ollama_model = local_ai._pick_model()
    whisper_ok = local_ai._load_whisper() is not None
    return {"capabilities": caps, "local": {"ollama_model": ollama_model, "ollama_available": ollama_model is not None,
                                            "whisper_available": whisper_ok, "whisper_error": local_ai._whisper_error},
            "env_key_present": bool(settings.SARVAM_API_KEY), "stt_language_default": settings.SARVAM_STT_LANGUAGE}


class TestIn(BaseModel):
    capability: str = "STT"


@router.post("/admin/ai-providers/test")
async def test_provider(body: TestIn, user: User = Depends(require_roles("ADMIN")), db: AsyncSession = Depends(get_db)):
    key, source = await sarvam_client.resolve_key(db, body.capability)
    if not key:
        return {"ok": False, "reason": "No key configured for this capability", "key_source": None}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(f"{sarvam_client.SARVAM_BASE}/translate", headers={"api-subscription-key": key},
                                  json={"input": "Namaste", "source_language_code": "en-IN", "target_language_code": "hi-IN"})
        return {"ok": r.status_code == 200, "status_code": r.status_code, "key_source": source,
                "detail": r.text[:200] if r.status_code != 200 else "Sarvam reachable"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": f"{exc.__class__.__name__}: {exc}", "key_source": source}


@router.get("/admin/retention-policy")
async def get_retention(user: User = Depends(require_roles("ADMIN")), db: AsyncSession = Depends(get_db)):
    p = (await db.execute(select(RetentionPolicy).order_by(RetentionPolicy.id.desc()))).scalars().first()
    return {"raw_audio_retention_days": p.raw_audio_retention_days if p else 30, "updated_at": iso(p.updated_at) if p else None}


class RetentionIn(BaseModel):
    raw_audio_retention_days: int


@router.put("/admin/retention-policy")
async def put_retention(body: RetentionIn, user: User = Depends(require_roles("ADMIN")), db: AsyncSession = Depends(get_db)):
    if not 1 <= body.raw_audio_retention_days <= 365:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "retention must be 1..365 days")
    p = (await db.execute(select(RetentionPolicy).order_by(RetentionPolicy.id.desc()))).scalars().first()
    if p is None:
        p = RetentionPolicy()
        db.add(p)
    p.raw_audio_retention_days, p.updated_by, p.updated_at = body.raw_audio_retention_days, user.id, datetime.utcnow()
    audit(db, user.id, "RETENTION_UPDATED", f"{body.raw_audio_retention_days}d")
    await db.commit()
    return {"raw_audio_retention_days": p.raw_audio_retention_days, "updated_at": iso(p.updated_at)}

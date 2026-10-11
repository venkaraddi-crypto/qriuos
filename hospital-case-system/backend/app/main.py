import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.models import ConsultationTranscript, RetentionPolicy
from app.seed import refresh_demo_day, seed_if_empty

# Columns added after the first schema shipped; ALTERed in on legacy SQLite files.
_LEGACY_COLUMNS: list[tuple[str, str, str]] = [
    ("users", "photo_url", "VARCHAR(255)"),
    ("users", "preferred_language", "VARCHAR(10) DEFAULT 'en-IN'"),
    ("users", "theme_preference", "VARCHAR(10) DEFAULT 'system'"),
    ("users", "notification_preferences", "JSON"),
    ("ayush_case_records", "dashavidha_data", "JSON"),
    ("ayush_case_records", "ahara_vihara", "JSON"),
    ("encounters", "abha_care_context_ref", "VARCHAR(120)"),
    ("patient_intakes", "consent_items", "JSON"),
    ("patient_intakes", "consent_revoked_at", "DATETIME"),
    ("document_assets", "document_date", "DATE"),
]


async def _ensure_legacy_columns() -> None:
    async with engine.begin() as conn:
        for table, column, ddl in _LEGACY_COLUMNS:
            rows = (await conn.execute(text(f"PRAGMA table_info({table})"))).fetchall()
            existing = {r[1] for r in rows}
            if rows and column not in existing:
                await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))


async def _prepare_schema() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _ensure_legacy_columns()
    async with SessionLocal() as db:
        await seed_if_empty(db)
        await refresh_demo_day(db)


async def _purge_expired_audio() -> None:
    async with SessionLocal() as db:
        policy = (await db.execute(select(RetentionPolicy).order_by(RetentionPolicy.id.desc()))).scalars().first()
        days = policy.raw_audio_retention_days if policy else 30
        cutoff = datetime.utcnow() - timedelta(days=days)
        rows = (await db.execute(select(ConsultationTranscript).where(
            ConsultationTranscript.recorded_at < cutoff,
            ConsultationTranscript.audio_deleted_at.is_(None),
            ConsultationTranscript.raw_audio_url.is_not(None),
        ))).scalars().all()
        for t in rows:
            if t.raw_audio_url and os.path.exists(t.raw_audio_url):
                try:
                    os.remove(t.raw_audio_url)
                except OSError:
                    pass
            t.raw_audio_url = None
            t.audio_deleted_at = datetime.utcnow()
        if rows:
            await db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await _prepare_schema()
    await _purge_expired_audio()
    yield
    await engine.dispose()


app = FastAPI(title="ArogyaSetu — Patient Case-Taking Software", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/")
@app.get("/api/v1")
async def root() -> dict:
    return {"name": app.title, "version": app.version, "docs": "/docs"}


from app.api.v1.endpoints import (  # noqa: E402
    ai_admin, casefile, clinical, core, documents, drive, intake, ops, referrals, scribe,
)
from app.api.v1.endpoints import settings as settings_endpoint  # noqa: E402

# Literal paths must register before parameterised siblings.
app.include_router(core.router, prefix="/api/v1", tags=["core"])
app.include_router(casefile.router, prefix="/api/v1", tags=["casefile"])
app.include_router(ai_admin.router, prefix="/api/v1", tags=["ai-admin"])
app.include_router(scribe.router, prefix="/api/v1", tags=["scribe"])
app.include_router(referrals.router, prefix="/api/v1", tags=["referrals"])
app.include_router(intake.router, prefix="/api/v1", tags=["intake"])
app.include_router(settings_endpoint.router, prefix="/api/v1", tags=["settings"])
app.include_router(drive.router, prefix="/api/v1", tags=["drive"])
app.include_router(ops.router, prefix="/api/v1", tags=["ops"])
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
app.include_router(clinical.router, prefix="/api/v1", tags=["clinical"])

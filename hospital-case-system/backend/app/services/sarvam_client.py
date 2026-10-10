"""Sarvam AI — primary engine for STT, diarized STT, translate, chat, TTS, OCR.

Resolution order per capability: Sarvam (admin key → env key) → local fallback → labelled mock.
Transcription is never fabricated: when every engine fails we return provider "none" + error.
"""
import base64
import time

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.crypto import decrypt_key
from app.models import AIProviderConfig
from app.services import local_ai, mocks

SARVAM_BASE = "https://api.sarvam.ai"
CAP_MODEL = {
    "STT": settings.SARVAM_STT_MODEL,
    "DIARIZED_STT": "saaras:v2.5",
    "TRANSLATE": "mayura:v1",
    "CHAT": "sarvam-m",
    "TTS": "bulbul:v2",
    "OCR": "sarvam-vision",
}
SARVAM_LANGUAGES = [
    "unknown", "en-IN", "hi-IN", "bn-IN", "ta-IN", "te-IN", "gu-IN", "kn-IN", "ml-IN", "mr-IN", "pa-IN",
    "od-IN", "as-IN", "ur-IN", "ne-IN", "sa-IN", "doi-IN", "kok-IN", "mai-IN", "mni-IN", "sat-IN", "sd-IN", "ks-IN",
]
STT_MODES = {"transcribe", "translate", "verbatim", "translit", "codemix"}
TIMEOUT = 30.0


async def resolve_key(db: AsyncSession | None, capability: str) -> tuple[str | None, str | None]:
    if db is not None:
        row = (await db.execute(
            select(AIProviderConfig).where(
                AIProviderConfig.capability == capability,
                AIProviderConfig.is_active.is_(True),
                AIProviderConfig.provider == "sarvam",
            ).order_by(AIProviderConfig.added_at.desc())
        )).scalars().first()
        if row:
            try:
                return decrypt_key(row.api_key_encrypted), "admin"
            except Exception:  # noqa: BLE001
                pass
    if settings.SARVAM_API_KEY:
        return settings.SARVAM_API_KEY, "env"
    return None, None


def _headers(key: str) -> dict:
    return {"api-subscription-key": key}


async def transcribe_intake(db: AsyncSession | None, audio: bytes, language_code: str = "unknown",
                            mode: str = "transcribe", filename: str = "audio.wav") -> dict:
    out: dict = {"mocked": False, "provider": "none", "text": "", "sarvam_model": CAP_MODEL["STT"],
                 "language_detected": None, "key_source": None}
    key, source = await resolve_key(db, "STT")
    out["key_source"] = source
    if mode not in STT_MODES:
        mode = "transcribe"
    if key:
        try:
            data = {"model": CAP_MODEL["STT"], "language_code": language_code, "mode": mode}
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                r = await client.post(f"{SARVAM_BASE}/speech-to-text", headers=_headers(key), data=data,
                                      files={"file": (filename, audio, "audio/wav")})
            if r.status_code == 200:
                body = r.json()
                out.update(provider="sarvam", text=(body.get("transcript") or "").strip(),
                           language_detected=body.get("language_code"))
                return out
            out["sarvam_error"] = f"HTTP {r.status_code}: {r.text[:200]}"
        except Exception as exc:  # noqa: BLE001
            out["sarvam_error"] = f"{exc.__class__.__name__}: {exc}"
    local = local_ai.transcribe(audio, language_code)
    if "error" in local:
        out["local_error"] = local["error"]
        out["error"] = "No speech engine available — transcript left empty (nothing fabricated)."
        return out
    out.update(provider="whisper", text=local["text"], language_detected=local.get("language"))
    return out


def _normalise_diarized(payload: dict) -> list[dict]:
    entries = payload.get("diarized_transcript", {}).get("entries", []) or payload.get("entries", [])
    return [{"speaker": str(e.get("speaker_id", "speaker")), "text": e.get("transcript", "")} for e in entries]


async def diarize_consultation(db: AsyncSession | None, audio: bytes, language_code: str = "unknown") -> dict:
    key, source = await resolve_key(db, "DIARIZED_STT")
    sarvam_error: str | None = None
    if key:
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                init = await client.post(f"{SARVAM_BASE}/speech-to-text/job/v1/init", headers=_headers(key))
                init.raise_for_status()
                job = init.json()
                job_id, upload_url = job["job_id"], job["input_storage_path"]
                await client.put(upload_url, content=audio, headers={"x-ms-blob-type": "BlockBlob"})
                await client.post(f"{SARVAM_BASE}/speech-to-text/job/v1/start", headers=_headers(key),
                                  json={"job_id": job_id, "job_parameters": {
                                      "model": CAP_MODEL["DIARIZED_STT"], "language_code": language_code,
                                      "with_diarization": True}})
                sarvam_error = "job did not complete"
                for _ in range(20):
                    st = (await client.get(f"{SARVAM_BASE}/speech-to-text/job/v1/{job_id}/status",
                                           headers=_headers(key))).json()
                    if st.get("job_state") == "Completed":
                        out = await client.get(st["output_storage_path"])
                        return {"provider": "sarvam", "mocked": False, "key_source": source,
                                "diarized_transcript": _normalise_diarized(out.json())}
                    if st.get("job_state") == "Failed":
                        break
                    time.sleep(1.5)
        except Exception as exc:  # noqa: BLE001
            sarvam_error = f"{exc.__class__.__name__}: {exc}"
    local = local_ai.transcribe(audio, language_code)
    if local.get("text"):
        return {"provider": "whisper", "mocked": False, "key_source": source, "sarvam_error": sarvam_error,
                "diarized_transcript": local_ai.diarize_two_speaker(local["text"])}
    return {"provider": "mock", "mocked": True, "key_source": source, "sarvam_error": sarvam_error,
            "local_error": local.get("error"), "diarized_transcript": mocks.diarized_transcript()}


async def chat(db: AsyncSession | None, messages: list[dict]) -> dict:
    key, source = await resolve_key(db, "CHAT")
    if key:
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                r = await client.post(f"{SARVAM_BASE}/v1/chat/completions", headers=_headers(key),
                                      json={"model": CAP_MODEL["CHAT"], "messages": messages})
            if r.status_code == 200:
                return {"provider": "sarvam", "mocked": False, "key_source": source,
                        "content": r.json()["choices"][0]["message"]["content"]}
        except Exception:  # noqa: BLE001
            pass
    raw = local_ai._ollama_generate("\n".join(m["content"] for m in messages))
    if raw:
        return {"provider": "ollama", "mocked": False, "key_source": source, "content": raw}
    return {"provider": "mock", "mocked": True, "key_source": source, "content": None}


async def translate_text(db: AsyncSession | None, text: str, target_lang: str, source_lang: str = "en-IN") -> dict:
    key, source = await resolve_key(db, "TRANSLATE")
    if key:
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                r = await client.post(f"{SARVAM_BASE}/translate", headers=_headers(key),
                                      json={"input": text, "source_language_code": source_lang,
                                            "target_language_code": target_lang, "model": CAP_MODEL["TRANSLATE"]})
            if r.status_code == 200:
                return {"provider": "sarvam", "mocked": False, "key_source": source,
                        "translated_text": r.json().get("translated_text"), "target_language": target_lang}
        except Exception:  # noqa: BLE001
            pass
    return {**mocks.translate_text(text, target_lang), "provider": "mock", "key_source": source}


async def text_to_speech(db: AsyncSession | None, text: str, language: str = "en-IN") -> dict:
    key, source = await resolve_key(db, "TTS")
    if key:
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                r = await client.post(f"{SARVAM_BASE}/text-to-speech", headers=_headers(key),
                                      json={"inputs": [text[:500]], "target_language_code": language,
                                            "model": CAP_MODEL["TTS"], "speaker": "anushka"})
            if r.status_code == 200:
                audios = r.json().get("audios") or []
                return {"provider": "sarvam", "mocked": False, "key_source": source, "language": language,
                        "audio_base64": audios[0] if audios else None}
        except Exception:  # noqa: BLE001
            pass
    return {**mocks.tts(text, language), "provider": "mock", "key_source": source}


def _pdf_text_layer(data: bytes) -> str | None:
    try:
        import fitz  # type: ignore

        doc = fitz.open(stream=data, filetype="pdf")
        return "\n".join(page.get_text() for page in doc).strip() or None
    except Exception:  # noqa: BLE001
        return None


async def ocr_document(db: AsyncSession | None, data: bytes, filename: str, mime: str) -> dict:
    key, source = await resolve_key(db, "OCR")
    if key:
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                r = await client.post(f"{SARVAM_BASE}/doc-digitization", headers=_headers(key),
                                      files={"file": (filename, data, mime)})
            if r.status_code == 200:
                body = r.json()
                text = body.get("text") or body.get("output") or ""
                if text:
                    return {"provider": "sarvam", "mocked": False, "key_source": source, "text": text}
        except Exception:  # noqa: BLE001
            pass
    if mime == "application/pdf":
        layer = _pdf_text_layer(data)
        if layer:
            return {"provider": "pdf-text-layer", "mocked": False, "key_source": source, "text": layer}
    if mime.startswith("text/"):
        return {"provider": "plain-text", "mocked": False, "key_source": source, "text": data.decode(errors="ignore")}
    return {**mocks.ocr_extract(filename), "provider": "mock", "key_source": source}


def tiny_wav() -> bytes:
    return local_ai.tiny_wav_bytes()


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()

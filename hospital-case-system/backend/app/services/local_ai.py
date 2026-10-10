"""Local fallbacks: openai-whisper (STT) and Ollama (chat). Both optional."""
import io
import json
import os
import re
import tempfile

import httpx

OLLAMA_BASE = os.environ.get("OLLAMA_BASE", "http://localhost:11434")
PREFERRED_MODELS = ["gemma3", "gemma2", "gemma", "mistral", "llama3.1:8b", "llama3"]

_whisper_model = None
_whisper_error: str | None = None


def _load_whisper():
    global _whisper_model, _whisper_error
    if _whisper_model is not None or _whisper_error is not None:
        return _whisper_model
    try:
        import whisper  # type: ignore

        _whisper_model = whisper.load_model("base")
    except Exception as exc:  # noqa: BLE001
        _whisper_error = f"whisper unavailable: {exc.__class__.__name__}"
    return _whisper_model


def transcribe(audio_bytes: bytes, language: str | None = None) -> dict:
    model = _load_whisper()
    if model is None:
        return {"error": _whisper_error or "whisper unavailable"}
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            path = f.name
        kwargs = {}
        if language and language != "unknown":
            kwargs["language"] = language.split("-")[0]
        result = model.transcribe(path, **kwargs)
        os.unlink(path)
        return {"text": (result.get("text") or "").strip(), "language": result.get("language"), "provider": "whisper"}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"whisper failed: {exc}"}


def diarize_two_speaker(text: str) -> list[dict]:
    """Heuristic: alternate speakers on sentence boundaries, questions → doctor."""
    sentences = [s.strip() for s in re.split(r"(?<=[.?!])\s+", text or "") if s.strip()]
    turns: list[dict] = []
    speaker = "doctor"
    for s in sentences:
        if s.endswith("?"):
            speaker = "doctor"
        turns.append({"speaker": speaker, "text": s})
        speaker = "patient" if speaker == "doctor" else "doctor"
    return turns


def _pick_model() -> str | None:
    try:
        r = httpx.get(f"{OLLAMA_BASE}/api/tags", timeout=3)
        names = [m["name"] for m in r.json().get("models", [])]
    except Exception:  # noqa: BLE001
        return None
    for pref in PREFERRED_MODELS:
        for n in names:
            if n.startswith(pref):
                return n
    return names[0] if names else None


def _parse_loose_json(raw: str) -> dict | None:
    m = re.search(r"\{.*\}", raw or "", re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def _ollama_generate(prompt: str, timeout: float = 60) -> str | None:
    model = _pick_model()
    if not model:
        return None
    try:
        r = httpx.post(f"{OLLAMA_BASE}/api/generate",
                       json={"model": model, "prompt": prompt, "stream": False}, timeout=timeout)
        return r.json().get("response")
    except Exception:  # noqa: BLE001
        return None


SOAP_PROMPT = (
    "You are a clinical scribe. From the following doctor-patient transcript, write a SOAP note. "
    "Respond ONLY with JSON: {\"subjective\": str, \"objective\": str, \"assessment\": str, \"plan\": str}.\n\n"
)


def chat_soap(turns: list[dict]) -> dict | None:
    transcript = "\n".join(f"{t.get('speaker', '?').upper()}: {t.get('text', '')}" for t in turns)
    raw = _ollama_generate(SOAP_PROMPT + transcript)
    if raw is None:
        return None
    parsed = _parse_loose_json(raw)
    if parsed:
        parsed["provider"] = "ollama"
    return parsed


def summarize_intake(text: str) -> str | None:
    return _ollama_generate("Summarise this patient intake in 3 clinical sentences:\n" + text)


def tiny_wav_bytes() -> bytes:
    """A valid 0.1 s silent 16 kHz mono PCM WAV (handy for tests)."""
    import struct
    import wave

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(struct.pack("<" + "h" * 1600, *([0] * 1600)))
    return buf.getvalue()

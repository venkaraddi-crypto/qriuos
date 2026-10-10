"""Labelled mock stubs (every payload carries mocked: True) with real response shapes."""
import itertools
import uuid

MOCK_OTP = "123456"


def transcribe_chunk(audio_len: int, language: str = "en-IN") -> dict:
    return {
        "mocked": True,
        "text": "",
        "language_detected": language,
        "note": "Mock STT chunk — no speech engine configured; nothing was fabricated.",
        "bytes_received": audio_len,
    }


def abha_init_otp(aadhaar_or_mobile: str) -> dict:
    return {"mocked": True, "txn_id": f"txn-{uuid.uuid4().hex[:12]}", "message": f"OTP sent (mock). Use {MOCK_OTP}."}


def abha_verify_otp(txn_id: str, otp: str) -> dict:
    if otp != MOCK_OTP:
        return {"mocked": True, "verified": False, "error": "Invalid OTP"}
    suffix = uuid.uuid4().int % 10**10
    abha_id = f"91-{suffix // 10**6:04d}-{(suffix // 100) % 10**4:04d}-{suffix % 10**4:04d}"
    return {"mocked": True, "verified": True, "abha_id": abha_id, "abha_address": f"user{suffix % 10000}@abdm"}


def abha_link_care_context(abha_id: str, encounter_id: int) -> dict:
    return {"mocked": True, "linked": True, "care_context_ref": f"cc-{abha_id}-{encounter_id}"}


def diarized_transcript() -> list[dict]:
    return [
        {"speaker": "doctor", "text": "Namaste, what brings you in today?"},
        {"speaker": "patient", "text": "Burning in the upper stomach after meals for two weeks, worse with spicy food."},
        {"speaker": "doctor", "text": "Any vomiting or blood in stool?"},
        {"speaker": "patient", "text": "No vomiting, no blood. Some sour belching at night."},
        {"speaker": "doctor", "text": "We'll start Amlapitta management and review in two weeks."},
    ]


def translate_text(text: str, target_lang: str) -> dict:
    return {"mocked": True, "translated_text": f"[{target_lang}] {text}", "target_language": target_lang}


def tts(text: str, language: str) -> dict:
    return {"mocked": True, "audio_base64": None, "language": language, "note": "No TTS provider configured."}


_MOCK_EXTRACTIONS = itertools.cycle([
    "LAB REPORT  Date: 12 Mar 2026\nHemoglobin 10.8 g/dL\nFasting glucose 128 mg/dL\nHbA1c 6.9 %\nTSH 2.1 mIU/L",
    "Rx  05-02-2026\nTab Paracetamol 500 mg BD 5 days\nTab Omeprazole 20 mg OD 14 days\nSyp Sitopaladi 10 ml TDS 7 days",
    "DISCHARGE SUMMARY 20 Jan 2026\nAdmitted with acute gastritis. Creatinine 0.9 mg/dL. Tab Pantoprazole 40 mg OD 10 days.",
])


def ocr_extract(filename: str = "") -> dict:
    return {"mocked": True, "text": next(_MOCK_EXTRACTIONS), "filename": filename}

"""STT honesty + status surface without a Sarvam key."""
import asyncio

from app.services import sarvam_client
from app.services.local_ai import tiny_wav_bytes


def test_stt_status(client, headers):
    s = client.get("/api/v1/voice/stt-status", headers=headers["doctor_allo"]).json()
    assert s["sarvam_model"] == "saaras:v3" and "hi-IN" in s["languages"] and len(s["languages"]) >= 22
    assert s["default_language"] == "unknown" and "codemix" in s["modes"]


def test_transcribe_never_fabricates():
    out = asyncio.run(sarvam_client.transcribe_intake(None, tiny_wav_bytes(), "unknown", "bogus-mode"))
    assert out["mocked"] is False and out["key_source"] is None
    assert out["provider"] in ("none", "whisper")
    if out["provider"] == "none":
        assert out["text"] == "" and "error" in out and "local_error" in out


def test_size_limit(client, headers):
    big = b"0" * (15 * 1024 * 1024 + 1)
    r = client.post("/api/v1/voice/transcribe-audio", headers=headers["doctor_allo"], files={"audio_file": ("big.wav", big, "audio/wav")})
    assert r.status_code == 413


def test_normalise_diarized():
    turns = sarvam_client._normalise_diarized({"diarized_transcript": {"entries": [{"speaker_id": 0, "transcript": "hi"}]}})
    assert turns == [{"speaker": "0", "text": "hi"}]

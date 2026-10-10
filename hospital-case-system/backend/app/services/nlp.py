"""Rule-based SOCRATES entity extractor (labelled mocked: True)."""
import re

RED_FLAG_KEYWORDS = [
    "chest pain", "breathlessness", "shortness of breath", "blood", "bleeding",
    "unconscious", "seizure", "fits", "stroke", "paralysis", "severe headache",
    "stiff neck", "high fever", "vomiting blood", "black stool", "suicidal",
    "difficulty breathing", "fainting", "weakness on one side",
]

SOCRATES_FIELDS = [
    "site", "onset", "character", "radiation", "associations",
    "timing", "exacerbating_factors", "relieving_factors", "severity",
]

SITE_WORDS = [
    "head", "chest", "abdomen", "stomach", "back", "neck", "throat", "knee",
    "joint", "joints", "leg", "arm", "shoulder", "hip", "eye", "ear", "tooth",
    "lower back", "upper abdomen", "epigastric", "pelvic",
]
CHARACTER_WORDS = [
    "burning", "sharp", "dull", "throbbing", "stabbing", "cramping", "aching",
    "colicky", "pressure", "tight", "heavy", "pricking", "shooting",
]
TIMING_WORDS = [
    "morning", "night", "evening", "after meals", "before meals", "after eating",
    "continuous", "intermittent", "constant", "at rest", "on exertion", "daily",
]
ONSET_WORDS = ["sudden", "gradual", "suddenly", "gradually", "acute", "slowly"]
RADIATION_WORDS = ["radiates", "radiating", "spreads", "goes to", "moves to"]
ASSOCIATION_WORDS = [
    "nausea", "vomiting", "fever", "sweating", "dizziness", "bloating", "cough",
    "headache", "fatigue", "weakness", "loss of appetite", "constipation",
    "diarrhoea", "diarrhea", "palpitations", "acidity", "heartburn",
]
EXACERBATING_WORDS = [
    "worse after", "worsens", "aggravated by", "increases with", "worse on",
    "spicy food", "lying down", "walking", "stress", "cold weather",
]
RELIEVING_WORDS = [
    "better after", "relieved by", "improves with", "relief with", "rest",
    "antacid", "medication", "warm", "sleeping",
]

SEVERITY_RE = re.compile(r"(\d{1,2})\s*(?:out of|/)\s*10")
DURATION_RE = re.compile(
    r"(?:for|since|past|last)\s+(\d+|a|an|one|two|three|four|five|six|seven|ten)\s*"
    r"(days|day|weeks|week|months|month|years|year|hours|hour)",
    re.IGNORECASE,
)


def _find_all(text: str, words: list[str]) -> list[str]:
    found: list[str] = []
    for w in words:
        if w in text and w not in found:
            found.append(w)
    return found


def _first(text: str, words: list[str]) -> str | None:
    for w in words:
        if w in text:
            return w
    return None


def extract_entities(text: str) -> dict:
    raw = text or ""
    low = raw.lower()
    severity = None
    m = SEVERITY_RE.search(low)
    if m:
        severity = int(m.group(1))
    duration = None
    d = DURATION_RE.search(low)
    if d:
        duration = f"{d.group(1)} {d.group(2)}"
    red_flags = _find_all(low, RED_FLAG_KEYWORDS)
    chief = raw.strip().split(".")[0][:200] if raw.strip() else ""
    return {
        "chief_complaint": chief,
        "site": _find_all(low, SITE_WORDS),
        "onset": _first(low, ONSET_WORDS),
        "character": _find_all(low, CHARACTER_WORDS),
        "radiation": _first(low, RADIATION_WORDS),
        "associations": _find_all(low, ASSOCIATION_WORDS),
        "timing": _find_all(low, TIMING_WORDS),
        "exacerbating_factors": _find_all(low, EXACERBATING_WORDS),
        "relieving_factors": _find_all(low, RELIEVING_WORDS),
        "severity": severity,
        "duration": duration,
        "red_flags": red_flags,
        "mocked": True,
    }

"""Adaptive pre-consultation question engine (rule-based, deterministic)."""

HPI_FIELDS = [
    "site", "onset", "character", "radiation", "associations",
    "timing", "exacerbating_factors", "relieving_factors", "severity",
]

SEVERITY_Q = {
    "key": "severity",
    "type": "scale",
    "prompt": "On a scale of 0 to 10, how severe is it right now?",
    "options": [str(i) for i in range(0, 11)],
    "target": "hpi",
}

GENERIC_QUESTIONS = [
    {"key": "site", "type": "text", "prompt": "Where exactly do you feel the problem?", "options": [], "target": "hpi"},
    {"key": "onset", "type": "choice", "prompt": "How did it start?", "options": ["suddenly", "gradually"], "target": "hpi"},
    {"key": "character", "type": "text", "prompt": "How would you describe it (burning, dull, sharp…)?", "options": [], "target": "hpi"},
    {"key": "radiation", "type": "choice", "prompt": "Does it spread anywhere else?", "options": ["no", "yes — to another area"], "target": "hpi"},
    {"key": "associations", "type": "text", "prompt": "Any other symptoms along with it?", "options": [], "target": "hpi"},
    {"key": "timing", "type": "choice", "prompt": "When is it worst?", "options": ["morning", "after meals", "night", "continuous", "no pattern"], "target": "hpi"},
    {"key": "exacerbating_factors", "type": "text", "prompt": "What makes it worse?", "options": [], "target": "hpi"},
    {"key": "relieving_factors", "type": "text", "prompt": "What makes it better?", "options": [], "target": "hpi"},
    SEVERITY_Q,
]

COMPLAINT_CATEGORIES: dict[str, dict] = {
    "GI": {
        "keywords": ["acidity", "stomach", "abdomen", "burning", "heartburn", "vomit", "nausea", "gas", "bloating", "constipation", "loose", "diarrh", "indigestion", "amlapitta"],
        "extra": [
            {"key": "meal_timing", "type": "choice", "prompt": "Are your meal timings regular?", "options": ["regular", "irregular"], "target": "ahara_vihara"},
            {"key": "diet_type", "type": "choice", "prompt": "What is your usual diet?", "options": ["vegetarian", "mixed", "vegan"], "target": "ahara_vihara"},
            {"key": "bowel_habit", "type": "choice", "prompt": "How are your bowel movements?", "options": ["regular", "constipated", "loose"], "target": "ahara_vihara"},
        ],
    },
    "RESPIRATORY": {
        "keywords": ["cough", "breath", "wheeze", "asthma", "cold", "sneez", "phlegm", "chest congestion"],
        "extra": [
            {"key": "addictions", "type": "text", "prompt": "Do you smoke or use tobacco?", "options": [], "target": "ahara_vihara"},
            {"key": "sputum", "type": "choice", "prompt": "Is the cough dry or with sputum?", "options": ["dry", "with sputum", "with blood"], "target": "note"},
        ],
    },
    "MUSCULOSKELETAL": {
        "keywords": ["joint", "knee", "back", "neck", "stiff", "swelling", "arthritis", "sandhivata", "pain in leg"],
        "extra": [
            {"key": "exercise", "type": "choice", "prompt": "How often do you exercise?", "options": ["daily", "occasional", "none"], "target": "ahara_vihara"},
            {"key": "morning_stiffness", "type": "choice", "prompt": "Do you have morning stiffness lasting more than 30 minutes?", "options": ["yes", "no"], "target": "note"},
        ],
    },
    "FEVER": {
        "keywords": ["fever", "chills", "temperature", "jwara", "body ache"],
        "extra": [
            {"key": "fever_pattern", "type": "choice", "prompt": "Is the fever continuous or does it come and go?", "options": ["continuous", "intermittent", "evening rise"], "target": "note"},
            {"key": "travel", "type": "choice", "prompt": "Any recent travel or contact with a sick person?", "options": ["yes", "no"], "target": "note"},
        ],
    },
    "NEURO": {
        "keywords": ["headache", "migraine", "dizz", "giddiness", "numb", "tingling", "weakness", "seizure"],
        "extra": [
            {"key": "sleep_hours", "type": "text", "prompt": "How many hours do you sleep at night?", "options": [], "target": "ahara_vihara"},
            {"key": "stress_level", "type": "choice", "prompt": "How would you rate your stress?", "options": ["low", "moderate", "high"], "target": "ahara_vihara"},
        ],
    },
    "SKIN": {
        "keywords": ["rash", "itch", "skin", "eczema", "psoriasis", "patch", "boil"],
        "extra": [
            {"key": "diet_type", "type": "choice", "prompt": "What is your usual diet?", "options": ["vegetarian", "mixed", "vegan"], "target": "ahara_vihara"},
            {"key": "new_exposure", "type": "text", "prompt": "Any new soap, cosmetic, food or medicine recently?", "options": [], "target": "note"},
        ],
    },
}


def classify_complaint(text: str) -> str:
    low = (text or "").lower()
    best, best_score = "GENERAL", 0
    for cat, cfg in COMPLAINT_CATEGORIES.items():
        score = sum(1 for k in cfg["keywords"] if k in low)
        if score > best_score:
            best, best_score = cat, score
    return best


def branch_for_complaint(text: str, answered_fields: list[str] | set[str]) -> dict:
    answered = set(answered_fields or [])
    category = classify_complaint(text)
    pool = [q for q in GENERIC_QUESTIONS]
    if category in COMPLAINT_CATEGORIES:
        pool += COMPLAINT_CATEGORIES[category]["extra"]
    pending = [q for q in pool if q["key"] not in answered]
    return {
        "category": category,
        "questions": pending[:4],
        "remaining": len(pending),
        "complete": len(pending) == 0,
    }


def catalog() -> dict:
    return {
        "hpi_fields": HPI_FIELDS,
        "generic": GENERIC_QUESTIONS,
        "categories": {
            k: {"keywords": v["keywords"], "extra": v["extra"]} for k, v in COMPLAINT_CATEGORIES.items()
        },
    }

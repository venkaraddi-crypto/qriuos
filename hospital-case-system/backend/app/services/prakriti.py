"""Prakriti (constitution) scoring and Vikriti (current imbalance) assessment."""

VATA_TRAITS = ["thin_build", "dry_skin", "cold_intolerance", "irregular_appetite", "light_sleep", "quick_mind"]
PITTA_TRAITS = ["medium_build", "warm_body", "sharp_appetite", "early_greying", "irritability", "sweats_easily"]
KAPHA_TRAITS = ["heavy_build", "oily_skin", "slow_digestion", "deep_sleep", "calm_nature", "weight_gain"]

ALL_TRAITS = VATA_TRAITS + PITTA_TRAITS + KAPHA_TRAITS

_SYMPTOM_HINTS = {
    "vata": ["pain", "dry", "constipation", "anxiety", "insomnia", "bloating", "cracking", "cold", "tremor"],
    "pitta": ["burning", "acidity", "heartburn", "fever", "rash", "anger", "inflammation", "diarrhoea", "diarrhea", "sour"],
    "kapha": ["heaviness", "congestion", "cough", "mucus", "lethargy", "weight", "sluggish", "swelling", "phlegm"],
}


def score_prakriti(answers: dict[str, int]) -> dict:
    def total(traits: list[str]) -> int:
        return sum(int(answers.get(t, 0) or 0) for t in traits)

    v, p, k = total(VATA_TRAITS), total(PITTA_TRAITS), total(KAPHA_TRAITS)
    s = v + p + k
    if s == 0:
        return {"vata": 33.3, "pitta": 33.3, "kapha": 33.4, "dominant": "vata"}
    pct = {
        "vata": round(100 * v / s, 1),
        "pitta": round(100 * p / s, 1),
        "kapha": round(100 * k / s, 1),
    }
    dominant = max(pct, key=lambda d: pct[d])
    return {**pct, "dominant": dominant}


def assess_vikriti(current_symptoms: str | None, dominant: str) -> dict:
    low = (current_symptoms or "").lower()
    scores = {d: sum(1 for w in words if w in low) for d, words in _SYMPTOM_HINTS.items()}
    best = max(scores, key=lambda d: scores[d])
    if scores[best] == 0:
        return {
            "aggravated_dosha": dominant,
            "rationale": "No specific symptom cues; assuming constitutional dosha is aggravated.",
        }
    matched = [w for w in _SYMPTOM_HINTS[best] if w in low]
    return {
        "aggravated_dosha": best,
        "rationale": f"Symptoms ({', '.join(matched)}) indicate {best} aggravation.",
    }

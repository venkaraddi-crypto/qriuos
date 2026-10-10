"""Dashavidha Pariksha — ten-fold examination (Charaka Vimana Sthana 8)."""

GRADES = {"pravara": 3, "madhyama": 2, "avara": 1}
GRADE_LABELS = {"pravara": "Pravara (excellent)", "madhyama": "Madhyama (moderate)", "avara": "Avara (poor)"}

# (key, label, description, scored)
DASHAVIDHA_PARAMETERS = [
    ("prakriti", "Prakriti", "Constitution (from Prakriti assessment)", False),
    ("vikriti", "Vikriti", "Current morbidity / dosha imbalance", False),
    ("sara", "Sara", "Tissue excellence (dhatu sara)", True),
    ("samhanana", "Samhanana", "Body compactness / build", True),
    ("pramana", "Pramana", "Body proportions (anguli pramana)", True),
    ("satmya", "Satmya", "Habituation / adaptability", True),
    ("sattva", "Sattva", "Mental strength", True),
    ("ahara_shakti", "Ahara Shakti", "Digestive and intake capacity (abhyavaharana / jarana)", True),
    ("vyayama_shakti", "Vyayama Shakti", "Exercise capacity", True),
    ("vaya", "Vaya", "Age-related strength (bala, madhya, vriddha)", True),
]

AHARA_VIHARA_FIELDS = [
    ("diet_type", "Diet type", "choice", ["vegetarian", "mixed", "vegan"]),
    ("meal_timing", "Meal timing regularity", "choice", ["regular", "irregular"]),
    ("water_intake", "Water intake (litres/day)", "text", []),
    ("sleep_hours", "Sleep (hours/night)", "text", []),
    ("exercise", "Exercise habit", "choice", ["daily", "occasional", "none"]),
    ("addictions", "Tobacco / alcohol / caffeine", "text", []),
    ("bowel_habit", "Bowel habit", "choice", ["regular", "constipated", "loose"]),
    ("stress_level", "Stress level", "choice", ["low", "moderate", "high"]),
]


def reference() -> dict:
    return {
        "grades": [{"key": k, "label": GRADE_LABELS[k], "score": v} for k, v in GRADES.items()],
        "parameters": [
            {"key": k, "label": lbl, "description": d, "scored": s} for k, lbl, d, s in DASHAVIDHA_PARAMETERS
        ],
        "ahara_vihara": [
            {"key": k, "label": lbl, "type": t, "options": o} for k, lbl, t, o in AHARA_VIHARA_FIELDS
        ],
    }


def assess_dashavidha(parameters: dict | None, ahara_vihara: dict | None) -> dict:
    parameters = parameters or {}
    scored_keys = [k for k, _, _, s in DASHAVIDHA_PARAMETERS if s]
    total = 0
    counted = 0
    for k in scored_keys:
        grade = str(parameters.get(k, "") or "").lower()
        if grade in GRADES:
            total += GRADES[grade]
            counted += 1
    max_score = 3 * len(scored_keys)
    bala_score = round(100 * total / max_score, 1) if counted else 0.0
    if bala_score >= 75:
        label = "Pravara Bala"
    elif bala_score >= 45:
        label = "Madhyama Bala"
    else:
        label = "Avara Bala"
    av = ahara_vihara or {}
    advice: list[str] = []
    if av.get("meal_timing") == "irregular":
        advice.append("Regularise meal timings (Ahara kala).")
    if av.get("exercise") == "none":
        advice.append("Introduce graded daily Vyayama appropriate to Bala.")
    if av.get("stress_level") == "high":
        advice.append("Recommend Sattvavajaya (mind-calming) practices.")
    if av.get("bowel_habit") == "constipated":
        advice.append("Address Apana Vata — fibre, warm water, Triphala at night.")
    return {
        "bala_score": bala_score,
        "bala_label": label,
        "parameters_scored": counted,
        "parameters_total": len(scored_keys),
        "advice": advice,
    }

"""Builds a clinician-facing problem representation from intake + history data."""

SOCRATES_ORDER = [
    ("site", "Site"),
    ("onset", "Onset"),
    ("character", "Character"),
    ("radiation", "Radiation"),
    ("associations", "Associated symptoms"),
    ("timing", "Timing"),
    ("exacerbating_factors", "Exacerbating factors"),
    ("relieving_factors", "Relieving factors"),
    ("severity", "Severity"),
]

PAST_ORDER = [("PMH", "Past medical"), ("PSH", "Past surgical"), ("FAMILY", "Family"),
              ("SOCIAL", "Social"), ("OBSTETRIC", "Obstetric")]


def build_history_summary(data: dict) -> dict:
    patient = data.get("patient") or {}
    complaints = data.get("chief_complaints") or []
    hpi = data.get("hpi") or {}
    allergies = data.get("allergies") or []
    meds = data.get("current_meds") or []
    past = data.get("past") or []
    ros = data.get("ros") or []
    labs = data.get("lab_orders") or []

    age = patient.get("age")
    who = f"{age}-year-old " if age else ""
    gender = (patient.get("gender") or "").lower()
    who += f"{gender} " if gender else ""
    cc = "; ".join(
        f"{c.get('complaint_text')}" + (f" × {c.get('duration_days')} d" if c.get("duration_days") else "")
        for c in complaints
    ) or "no recorded complaint"
    pmh = [p.get("text") for p in past if p.get("kind") == "PMH" and p.get("text")]
    problem = f"{who}patient presenting with {cc}"
    if pmh:
        problem += f", on a background of {', '.join(pmh)}"
    problem += "."

    hpi_lines = [f"{label}: {hpi[key]}" for key, label in SOCRATES_ORDER if hpi.get(key)]
    ros_positive = [r.get("system") + (f" ({r.get('notes')})" if r.get("notes") else "") for r in ros if r.get("positive")]
    investigations = [
        f"{l.get('test_name')}: {l.get('status')}" + (" — ABNORMAL" if l.get("flagged_abnormal") else "")
        for l in labs
    ]

    parts = [problem]
    if hpi_lines:
        parts.append("HPI — " + "; ".join(hpi_lines) + ".")
    if allergies:
        parts.append("Allergies: " + ", ".join(
            f"{a.get('substance')}" + (f" ({a.get('reaction')})" if a.get("reaction") else "") for a in allergies) + ".")
    else:
        parts.append("No known allergies recorded.")
    if meds:
        parts.append("Current medications: " + ", ".join(
            f"{m.get('name')} {m.get('dose') or ''} {m.get('frequency') or ''}".strip() for m in meds) + ".")
    for kind, label in PAST_ORDER:
        items = [p.get("text") for p in past if p.get("kind") == kind and p.get("text")]
        if items and kind != "PMH":
            parts.append(f"{label} history: {', '.join(items)}.")
    if ros_positive:
        parts.append("Positive ROS: " + ", ".join(ros_positive) + ".")
    if investigations:
        parts.append("Investigations: " + "; ".join(investigations) + ".")

    return {
        "problem_representation": problem,
        "hpi_lines": hpi_lines,
        "ros_positive": ros_positive,
        "investigations": investigations,
        "narrative": " ".join(parts),
    }

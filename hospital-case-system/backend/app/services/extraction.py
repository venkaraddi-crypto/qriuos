"""Document digitisation: classify, pull labs/medications/dates from OCR text."""
import re
from datetime import date

# test_key -> (low, high, unit)
LAB_REFERENCE_RANGES: dict[str, tuple[float, float, str]] = {
    "hemoglobin": (12.0, 17.0, "g/dL"),
    "fasting_glucose": (70.0, 100.0, "mg/dL"),
    "postprandial_glucose": (70.0, 140.0, "mg/dL"),
    "hba1c": (4.0, 5.7, "%"),
    "total_cholesterol": (0.0, 200.0, "mg/dL"),
    "ldl": (0.0, 100.0, "mg/dL"),
    "hdl": (40.0, 100.0, "mg/dL"),
    "triglycerides": (0.0, 150.0, "mg/dL"),
    "creatinine": (0.6, 1.3, "mg/dL"),
    "urea": (7.0, 20.0, "mg/dL"),
    "tsh": (0.4, 4.0, "mIU/L"),
    "sgpt": (7.0, 56.0, "U/L"),
    "sgot": (10.0, 40.0, "U/L"),
    "wbc": (4000.0, 11000.0, "/µL"),
    "platelets": (150000.0, 450000.0, "/µL"),
    "esr": (0.0, 20.0, "mm/hr"),
    "uric_acid": (3.5, 7.2, "mg/dL"),
    "vitamin_d": (30.0, 100.0, "ng/mL"),
    "vitamin_b12": (200.0, 900.0, "pg/mL"),
}

LAB_ALIASES: dict[str, str] = {
    "hb": "hemoglobin", "haemoglobin": "hemoglobin", "hemoglobin": "hemoglobin",
    "fbs": "fasting_glucose", "fasting blood sugar": "fasting_glucose", "fasting glucose": "fasting_glucose",
    "ppbs": "postprandial_glucose", "post prandial": "postprandial_glucose", "pp glucose": "postprandial_glucose",
    "hba1c": "hba1c", "glycated hemoglobin": "hba1c",
    "total cholesterol": "total_cholesterol", "cholesterol": "total_cholesterol",
    "ldl": "ldl", "hdl": "hdl", "triglycerides": "triglycerides", "tg": "triglycerides",
    "creatinine": "creatinine", "serum creatinine": "creatinine",
    "urea": "urea", "blood urea": "urea",
    "tsh": "tsh", "sgpt": "sgpt", "alt": "sgpt", "sgot": "sgot", "ast": "sgot",
    "wbc": "wbc", "total leucocyte count": "wbc", "tlc": "wbc",
    "platelets": "platelets", "platelet count": "platelets",
    "esr": "esr", "uric acid": "uric_acid",
    "vitamin d": "vitamin_d", "vit d": "vitamin_d", "25-oh vitamin d": "vitamin_d",
    "vitamin b12": "vitamin_b12", "vit b12": "vitamin_b12", "b12": "vitamin_b12",
}

_NUM_RE = re.compile(r"[-+]?\d+(?:[.,]\d+)?")
_FREQ_TOKENS = {"od": "once daily", "bd": "twice daily", "bid": "twice daily", "tds": "thrice daily",
                "tid": "thrice daily", "qid": "four times daily", "hs": "at bedtime", "sos": "as needed",
                "once daily": "once daily", "twice daily": "twice daily", "thrice daily": "thrice daily"}
_MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
_DATE_RE = re.compile(
    r"(\d{1,2})[\s\-/]*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s\-/,]*(\d{4})", re.IGNORECASE)
_DATE_NUM_RE = re.compile(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})")


def parse_numeric(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    m = _NUM_RE.search(str(value))
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", "."))
    except ValueError:
        return None


def flag_for(test_key: str, value) -> str | None:
    """Returns 'HIGH', 'LOW' or None."""
    key = LAB_ALIASES.get(test_key.lower().strip(), test_key.lower().strip().replace(" ", "_"))
    rng = LAB_REFERENCE_RANGES.get(key)
    num = parse_numeric(value)
    if rng is None or num is None:
        return None
    low, high, _ = rng
    if num < low:
        return "LOW"
    if num > high:
        return "HIGH"
    return None


def evaluate_result_values(result_values: dict | None) -> dict[str, str]:
    flags: dict[str, str] = {}
    for k, v in (result_values or {}).items():
        f = flag_for(k, v)
        if f:
            flags[k] = f
    return flags


def auto_flag_result_values(result_values: dict | None) -> bool:
    return bool(evaluate_result_values(result_values))


def extract_document_date(text: str) -> str | None:
    m = _DATE_RE.search(text or "")
    if m:
        d, mon, y = int(m.group(1)), _MONTHS[m.group(2).lower()[:3]], int(m.group(3))
        try:
            return date(y, mon, d).isoformat()
        except ValueError:
            return None
    m = _DATE_NUM_RE.search(text or "")
    if m:
        d, mon, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return date(y, mon, d).isoformat()
        except ValueError:
            return None
    return None


def _classify(text: str, filename: str = "") -> str:
    low = f"{text} {filename}".lower()
    if any(k in low for k in ["discharge", "summary of admission"]):
        return "DISCHARGE"
    if any(k in low for k in ["x-ray", "xray", "ultrasound", "mri", "ct scan", "radiolog", "impression:"]):
        return "IMAGING"
    if any(k in low for k in ["rx", "tab.", "tab ", "cap.", "syrup", "prescription", " od", " bd", " tds"]):
        return "PRESCRIPTION"
    if any(k in low for k in LAB_ALIASES) or "report" in low or "mg/dl" in low:
        return "LAB_REPORT"
    return "OTHER"


def _extract_labs(text: str) -> list[dict]:
    labs: list[dict] = []
    seen: set[str] = set()
    for line in (text or "").splitlines():
        low = line.lower()
        for alias, key in sorted(LAB_ALIASES.items(), key=lambda kv: -len(kv[0])):
            if alias in low and key not in seen:
                after = low.split(alias, 1)[1]
                num = parse_numeric(after)
                if num is None:
                    continue
                rng = LAB_REFERENCE_RANGES.get(key)
                labs.append({
                    "test": key,
                    "value": num,
                    "unit": rng[2] if rng else "",
                    "flag": flag_for(key, num),
                    "source_line": line.strip()[:120],
                })
                seen.add(key)
                break
    return labs


_MED_RE = re.compile(
    r"(?:tab|cap|syp|syrup|tablet|capsule)\.?\s+([A-Za-z][A-Za-z0-9\- ]{2,40}?)\s+(\d+\s?(?:mg|ml|g))?",
    re.IGNORECASE,
)


def _extract_medications(text: str) -> list[dict]:
    meds: list[dict] = []
    for line in (text or "").splitlines():
        m = _MED_RE.search(line)
        if not m:
            continue
        low = line.lower()
        freq = None
        for tok, label in _FREQ_TOKENS.items():
            if re.search(rf"\b{re.escape(tok)}\b", low):
                freq = label
                break
        dur = re.search(r"(\d+)\s*(?:days|day|d)\b", low)
        meds.append({
            "name": m.group(1).strip(),
            "dose": (m.group(2) or "").strip(),
            "frequency": freq,
            "duration_days": int(dur.group(1)) if dur else None,
            "source_line": line.strip()[:120],
        })
    return meds


def extract_document(text: str, filename: str = "") -> dict:
    # Always run both extractors — real-world scans mix labs and medications.
    labs = _extract_labs(text)
    meds = _extract_medications(text)
    doc_type = _classify(text, filename)
    if doc_type in {"PRESCRIPTION", "OTHER"} and len(labs) > len(meds):
        doc_type = "LAB_REPORT"
    elif doc_type in {"LAB_REPORT", "OTHER"} and len(meds) > len(labs):
        doc_type = "PRESCRIPTION"
    hits = len(labs) + len(meds)
    confidence = 0.2 if not text else min(0.95, 0.4 + 0.1 * hits)
    return {
        "type": doc_type,
        "labs": labs,
        "medications": meds,
        "document_date": extract_document_date(text),
        "confidence": round(confidence, 2),
    }


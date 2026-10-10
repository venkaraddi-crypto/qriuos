"""Shape contracts the frontend relies on."""
from app.services import question_engine
from app.services.history_summary import build_history_summary
from app.services.nlp import SOCRATES_FIELDS, extract_entities


def test_question_engine_contract():
    out = question_engine.branch_for_complaint("cough with phlegm for 5 days", [])
    assert out["category"] == "RESPIRATORY"
    for q in out["questions"]:
        assert set(q) == {"key", "type", "prompt", "options", "target"}
        assert q["type"] in ("text", "scale", "choice") and q["target"] in ("hpi", "ahara_vihara", "note")
    done = question_engine.branch_for_complaint("cough", question_engine.HPI_FIELDS + ["addictions", "sputum"])
    assert done["complete"] is True and done["questions"] == []
    assert question_engine.classify_complaint("random words") == "GENERAL"


def test_nlp_contract():
    e = extract_entities("Sudden chest pain radiating to left arm since 2 hours, 9/10, with sweating")
    assert e["mocked"] is True and e["onset"] == "sudden" and e["severity"] == 9
    assert "chest pain" in e["red_flags"] and "sweating" in e["associations"] and e["duration"] == "2 hours"
    for f in SOCRATES_FIELDS:
        assert f in e
    assert extract_entities("")["chief_complaint"] == ""


def test_history_summary_contract():
    out = build_history_summary({"patient": {"age": 45, "gender": "Female"},
                                 "chief_complaints": [{"complaint_text": "headache", "duration_days": 3}],
                                 "hpi": {"severity": "7", "site": "temporal"},
                                 "past": [{"kind": "PMH", "text": "migraine"}, {"kind": "FAMILY", "text": "father: stroke"}],
                                 "ros": [{"system": "NEURO", "positive": True}]})
    assert out["problem_representation"].startswith("45-year-old female patient presenting with headache × 3 d, on a background of migraine.")
    assert out["hpi_lines"] == ["Site: temporal", "Severity: 7"]  # SOCRATES order, not input order
    assert "Family history: father: stroke." in out["narrative"] and "No known allergies" in out["narrative"]
    assert set(out) == {"problem_representation", "hpi_lines", "ros_positive", "investigations", "narrative"}

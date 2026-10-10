"""FHIR R4 document bundle builder with dual-coded (NAMASTE + ICD-11) Conditions."""
import uuid
from datetime import datetime

FHIR_SYSTEMS = {
    "NAMASTE": "https://namaste.ayush.gov.in/fhir/CodeSystem/namaste",
    "ICD11_TM2": "http://id.who.int/icd/release/11/mms/tm2",
    "ICD11_BIOMEDICINE": "http://id.who.int/icd/release/11/mms",
}


def _ref(res: dict) -> dict:
    return {"reference": f"{res['resourceType']}/{res['id']}"}


def _entry(res: dict) -> dict:
    return {"fullUrl": f"urn:uuid:{res['id']}", "resource": res}


def _obs(code_text: str, value, unit: str | None, subject: dict, enc: dict, when: str) -> dict:
    res = {
        "resourceType": "Observation",
        "id": str(uuid.uuid4()),
        "status": "final",
        "code": {"text": code_text},
        "subject": subject,
        "encounter": enc,
        "effectiveDateTime": when,
    }
    if isinstance(value, (int, float)):
        res["valueQuantity"] = {"value": value, "unit": unit or ""}
    else:
        res["valueString"] = str(value)
    return res


def _patient_resource(patient: dict) -> dict:
    pat = {
        "resourceType": "Patient",
        "id": str(uuid.uuid4()),
        "identifier": [{"system": "urn:aiia:uhid", "value": patient.get("uhid")}],
        "name": [{"text": patient.get("name")}],
        "gender": (patient.get("gender") or "unknown").lower(),
    }
    if patient.get("abha_id"):
        pat["identifier"].append({"system": "https://healthid.ndhm.gov.in", "value": patient["abha_id"]})
    if patient.get("dob"):
        pat["birthDate"] = str(patient["dob"])
    return pat


def _condition(d: dict, subject: dict, enc_ref: dict) -> dict:
    system = FHIR_SYSTEMS.get(d.get("code_system"), d.get("code_system"))
    return {
        "resourceType": "Condition",
        "id": str(uuid.uuid4()),
        "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
        "code": {"coding": [{"system": system, "code": d.get("code"), "display": d.get("display_term")}],
                 "text": d.get("display_term")},
        "subject": subject,
        "encounter": enc_ref,
    }


def _med_request(m: dict, subject: dict, enc_ref: dict) -> dict:
    dosage = f"{m.get('dose') or ''} {m.get('frequency') or ''} × {m.get('duration_days') or '?'} days".strip()
    return {
        "resourceType": "MedicationRequest",
        "id": str(uuid.uuid4()),
        "status": "active",
        "intent": "order",
        "medicationCodeableConcept": {"text": m.get("name")},
        "subject": subject,
        "encounter": enc_ref,
        "dosageInstruction": [{"text": dosage}],
    }


def build_encounter_bundle(
    patient: dict,
    doctor_name: str,
    department_name: str,
    encounter: dict,
    diagnoses: list[dict],
    vitals: list[dict],
    prescriptions: list[dict],
    lab_orders: list[dict],
    ayush: dict | None,
) -> dict:
    when = encounter.get("timestamp") or datetime.utcnow().isoformat()
    pat = _patient_resource(patient)
    prac = {"resourceType": "Practitioner", "id": str(uuid.uuid4()), "name": [{"text": doctor_name}]}
    enc = {
        "resourceType": "Encounter",
        "id": str(uuid.uuid4()),
        "status": "finished",
        "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "AMB"},
        "serviceType": {"text": department_name},
        "subject": _ref(pat),
        "participant": [{"individual": _ref(prac)}],
        "period": {"start": when},
    }
    subject, enc_ref = _ref(pat), _ref(enc)
    entries = [_entry(pat), _entry(prac), _entry(enc)]

    conditions = [_condition(d, subject, enc_ref) for d in diagnoses]
    entries += [_entry(c) for c in conditions]

    observations: list[dict] = []
    for v in vitals:
        for key, unit in [("bp", "mmHg"), ("pulse", "/min"), ("temp", "°F"), ("weight", "kg")]:
            if v.get(key) not in (None, ""):
                observations.append(_obs(key.upper(), v[key], unit, subject, enc_ref, when))
    for l in lab_orders:
        for k, val in (l.get("result_values") or {}).items():
            observations.append(_obs(f"{l.get('test_name')} — {k}", val, None, subject, enc_ref, when))
    if ayush and ayush.get("prakriti_vata") is not None:
        observations.append(_obs(
            "Prakriti (Vata/Pitta/Kapha %)",
            f"{ayush.get('prakriti_vata')}/{ayush.get('prakriti_pitta')}/{ayush.get('prakriti_kapha')}",
            None, subject, enc_ref, when))
    entries += [_entry(o) for o in observations]

    med_reqs = [_med_request(m, subject, enc_ref) for p in prescriptions for m in (p.get("medications") or [])]
    entries += [_entry(m) for m in med_reqs]

    comp = {
        "resourceType": "Composition",
        "id": str(uuid.uuid4()),
        "status": "final",
        "type": {"text": "OPD consultation note"},
        "subject": subject,
        "encounter": enc_ref,
        "date": when,
        "author": [_ref(prac)],
        "title": f"OPD visit — {department_name}",
        "section": [
            {"title": "Summary", "text": {"status": "generated", "div": f"<div>{encounter.get('summary') or ''}</div>"}},
            {"title": "Diagnoses", "entry": [_ref(c) for c in conditions]},
            {"title": "Observations", "entry": [_ref(o) for o in observations]},
            {"title": "Medications", "entry": [_ref(m) for m in med_reqs]},
        ],
    }
    entries.insert(0, _entry(comp))
    return {
        "resourceType": "Bundle",
        "id": str(uuid.uuid4()),
        "type": "document",
        "timestamp": datetime.utcnow().isoformat(),
        "entry": entries,
    }


def validate_bundle(bundle: dict) -> None:
    if bundle.get("resourceType") != "Bundle":
        raise ValueError("resourceType must be Bundle")
    if bundle.get("type") != "document":
        raise ValueError("Bundle.type must be document")
    entries = bundle.get("entry") or []
    if not entries or entries[0]["resource"].get("resourceType") != "Composition":
        raise ValueError("first entry must be a Composition")
    types = {e["resource"].get("resourceType") for e in entries}
    for required in ("Patient", "Practitioner", "Encounter"):
        if required not in types:
            raise ValueError(f"missing {required} resource")
    for e in entries:
        if "id" not in e["resource"]:
            raise ValueError("every resource needs an id")

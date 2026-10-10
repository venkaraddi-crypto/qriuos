export interface DiagnosisRow { id: number; code_system: string; code: string; display_term: string; is_primary: boolean }
export interface TerminologyHit { code: string; code_system: string; term: string; biomedicine_code?: string | null }
export interface LabOrderRow { id: number; test_name: string; status: string; result_values: Record<string, unknown> | null; flagged_abnormal: boolean }
export interface Medication { name: string; dose: string; frequency: string; duration_days: number | ""; quantity?: number | "" }
export interface PrakritiResult { vata: number; pitta: number; kapha: number; dominant: string }
export interface SttStatus { provider: string; sarvam_model: string; fallback: string; hint: string; languages: string[]; default_language: string; modes?: string[]; key_source?: string | null }
export interface Department { id: number; name: string; system: string }
export interface VitalsRow { date: string; pulse: number | null; bp: string | null; temp?: number | null; weight?: number | null }
export interface TimelineEntry { encounter_id: number; date: string; system: string | null; chief_complaint: string | null; summary: string | null; diagnoses: string[] }
export interface Dispatch {
  medicine_to_pharmacy: boolean;
  pharmacy_pending_items: number;
  treatment_to_therapy: { id: number; therapy: { name: string; scheduled_at: string; status: string } | null; note: string | null }[];
  file_to_departments: { id: number; department: string | null; status: string; kind: string; new_appointment_id: number | null }[];
}
export interface SocratesEntities {
  chief_complaint: string; site: string[]; onset: string | null; character: string[]; radiation: string | null; associations: string[];
  timing: string[]; exacerbating_factors: string[]; relieving_factors: string[]; severity: number | null; duration: string | null;
  red_flags: string[]; mocked: boolean;
}
export interface AyushRecord {
  prakriti_vata: number | null; prakriti_pitta: number | null; prakriti_kapha: number | null; vikriti_dosha: string | null;
  ashtavidha_data: Record<string, string> | null; dashavidha_data: Record<string, unknown> | null; ahara_vihara: Record<string, string> | null;
}
export interface Encounter {
  id: number; appointment_id: number; system: string | null; doctor_id: number; token_number: string | null; red_flag: boolean; timestamp: string;
  chief_complaint_raw: string | null; summary: string | null; clinical_notes: string | null; extracted_entities: SocratesEntities | null;
  fhir_bundle_id: string | null; abha_care_context_ref: string | null;
  patient: { id: number; name: string; uhid: string; gender: string | null; age: number | null; abha_id: string | null };
  diagnoses: DiagnosisRow[]; prescriptions: { id: number; medications: Medication[] | null; pdf_url: string | null }[];
  lab_orders: LabOrderRow[]; ayush: AyushRecord | null;
}
export interface IntakeSummary {
  intake_status: string | null; duration_sec: number | null; language_used: string | null;
  chief_complaints: { id?: number; complaint_text: string; duration_days: number | null; severity: number | null }[];
  hpi: Record<string, string>; allergies: { substance: string; reaction: string | null; severity: string | null }[];
  current_meds: { name: string; dose: string | null; frequency: string | null; system?: string | null }[];
  past: { kind: string; text: string; year: number | null }[]; ros: { system: string; positive: boolean; notes: string | null }[];
}

export const LANG_LABELS: Record<string, string> = {
  unknown: "Auto-detect", "en-IN": "English", "hi-IN": "Hindi", "bn-IN": "Bengali", "ta-IN": "Tamil", "te-IN": "Telugu", "gu-IN": "Gujarati",
  "kn-IN": "Kannada", "ml-IN": "Malayalam", "mr-IN": "Marathi", "pa-IN": "Punjabi", "od-IN": "Odia", "as-IN": "Assamese", "ur-IN": "Urdu",
  "ne-IN": "Nepali", "sa-IN": "Sanskrit", "doi-IN": "Dogri", "kok-IN": "Konkani", "mai-IN": "Maithili", "mni-IN": "Manipuri", "sat-IN": "Santali",
  "sd-IN": "Sindhi", "ks-IN": "Kashmiri", "brx-IN": "Bodo",
};
export const languageLabel = (code: string) => LANG_LABELS[code] ?? code;

export const ASHTAVIDHA_FIELDS: { key: string; label: string; hint: string }[] = [
  { key: "nadi", label: "Nadi (pulse)", hint: "vata / pitta / kapha / mixed" },
  { key: "mutra", label: "Mutra (urine)", hint: "colour, frequency" },
  { key: "mala", label: "Mala (stool)", hint: "consistency, frequency" },
  { key: "jihva", label: "Jihva (tongue)", hint: "coated / clean / cracked" },
  { key: "shabda", label: "Shabda (speech/sounds)", hint: "" },
  { key: "sparsha", label: "Sparsha (touch/skin)", hint: "warm / cold / dry" },
  { key: "drik", label: "Drik (eyes)", hint: "" },
  { key: "akriti", label: "Akriti (build)", hint: "" },
];

export const LAB_TESTS = ["CBC", "HbA1c", "Lipid profile", "LFT", "RFT", "Thyroid profile"];
export const EMPTY_MEDICATION: Medication = { name: "", dose: "", frequency: "BD", duration_days: 5, quantity: "" };

export const formatClock = (sec: number) => `${String(Math.floor(sec / 60)).padStart(2, "0")}:${String(sec % 60).padStart(2, "0")}`;

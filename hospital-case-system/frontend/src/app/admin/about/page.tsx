"use client";
import Shell from "@/components/Shell";

const ROWS: { feature: string; status: "real" | "fallback" | "mock"; note: string }[] = [
  { feature: "Appointment booking, tokens, QR check-in", status: "real", note: "Row-locked slot capacity; one QR drives reception → doctor → nurse → pharmacy → billing." },
  { feature: "JWT auth + rotating refresh cookie, RBAC", status: "real", note: "HS256 access token (12 h), HTTP-only refresh cookie, per-endpoint role gates." },
  { feature: "Aadhaar / API-key encryption, Medical Drive", status: "real", note: "Fernet at rest; masked in responses; downloads audited." },
  { feature: "NAMASTE ↔ ICD-11 TM2 ↔ Biomedicine dual coding", status: "real", note: "Curated 42-term map; one NAMASTE pick writes three Condition codes." },
  { feature: "FHIR R4 document bundle", status: "real", note: "Patient, Practitioner, Encounter, Condition, Observation, MedicationRequest, Composition; validated." },
  { feature: "Prakriti / Vikriti / Ashtavidha / Dashavidha", status: "real", note: "Deterministic scoring from questionnaire answers." },
  { feature: "Drug interaction check", status: "real", note: "Seeded pair table; stem-matched against prescription + current meds." },
  { feature: "Lab abnormal flagging, document extraction", status: "real", note: "Reference ranges + alias matching; regex medication parser." },
  { feature: "Speech-to-text (Sarvam Saaras)", status: "fallback", note: "Sarvam with key → local Whisper → provider 'none' with error. Transcripts are never fabricated." },
  { feature: "Diarized consultation transcript", status: "fallback", note: "Sarvam batch job → Whisper two-speaker heuristic → labelled mock transcript." },
  { feature: "SOAP drafting", status: "fallback", note: "Sarvam-M → Ollama → rule-based draft (flagged as rule-based)." },
  { feature: "Translation / TTS", status: "fallback", note: "Sarvam Mayura / Bulbul → labelled mock." },
  { feature: "OCR", status: "fallback", note: "Sarvam Vision → PDF text layer → plain text → labelled mock sample." },
  { feature: "SOCRATES entity extractor", status: "mock", note: "Rule-based keyword extractor, always labelled mocked: true." },
  { feature: "ABDM / ABHA bridge", status: "mock", note: "OTP 123456; swap ABDM_BASE_URL for the sandbox — shapes already match." },
  { feature: "Payment gateway", status: "mock", note: "Returns MOCKPAY reference; bill is marked PAID." },
];

const BADGE: Record<string, string> = { real: "badge badge-green", fallback: "badge badge-amber", mock: "badge" };

export default function About() {
  return (
    <Shell portal="staff" title="About ArogyaSetu">
      <section className="card">
        <p className="text-sm muted">ArogyaSetu v0.1.0 — integrated Allopathic + Ayurveda OPD case-taking. This table states honestly which capabilities are real, which fall back, and which are mocked.</p>
        <table className="mt-3 w-full text-sm">
          <thead><tr className="border-b hr text-left"><th className="py-1">Capability</th><th>Status</th><th>Notes</th></tr></thead>
          <tbody>
            {ROWS.map((r) => (
              <tr key={r.feature} className="border-b hr align-top">
                <td className="py-1 pr-2">{r.feature}</td>
                <td className="pr-2"><span className={BADGE[r.status]}>{r.status.toUpperCase()}</span></td>
                <td className="muted">{r.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-3 text-xs muted">Backend: FastAPI · SQLAlchemy async · SQLite. Frontend: Next.js 14 · Tailwind. Demo logins: nine *@demo.in accounts, password password123.</p>
      </section>
    </Shell>
  );
}

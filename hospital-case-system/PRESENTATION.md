# ArogyaSetu — Presentation Map

> Patient Case-Taking Software for Indian OPDs — voice-first, QR-driven, bilingual (Ayurveda + Allopathy), built on the ABDM/ABHA vision.

Everything below maps a demo step → screen → API → database table, so you can present any slice of the system end-to-end.

---

## 1. One-liner / Problem

**"From a 7-minute verbal complaint in any Indian language, to a structured, coded, shareable medical record — in one OPD visit, driven by one QR code."**

Problems addressed:
1. Doctors spend most of consultation time *writing*, not listening.
2. Patient history is retold at every desk (reception → nurse → doctor → lab → pharmacy).
3. Ayurvedic terminology has no computational mapping to biomedicine.
4. Rural/low-literacy patients can't fill forms — the app must *listen and speak* instead.

---

## 2. System Architecture

```
┌──────────────── Next.js 14 frontend (localhost:3000) ────────────────┐
│  Patient portal        Staff portal (8 roles)      Admin portal      │
│  book/intake/QR/drive  reception·doctor·nurse·lab  analytics·AI keys │
│  family·records        pharmacy·billing            audit·security    │
└──────────────┬──────────────────────────────────────────┬──────────┘
               │  JSON (JWT Bearer) + multipart uploads   │
               ▼                                          ▼
┌──────────────── FastAPI backend (localhost:8000) ───────────────────┐
│  /api/v1 — 11 routers, 128 endpoints                               │
│  core · clinical · intake · ops · documents · drive · casefile ·    │
│  scribe · referrals · ai_admin · settings                           │
│                                                                    │
│  Services: SOCRATES NLP · Prakriti/Dashavidha · terminology        │
│  (NAMASTE↔ICD-11) · FHIR R4 bundles · adaptive question engine ·    │
│  OCR/lab extraction · history summary                              │
│                                                                    │
│  AI chain (per capability, honest fallbacks):                      │
│   Sarvam AI (STT/translate/chat/TTS/OCR) → Whisper/Ollama → mock   │
│                                                                    │
│  Security: JWT + rotating refresh cookie · Fernet (Aadhaar, Drive, │
│  AI keys) · RBAC per role · audit log                              │
└──────────────────────────┬─────────────────────────────────────────┘
                           ▼
      SQLite (async) — 39 tables, seeded demo hospital
      Encrypted blob store — backend/media/drive/{uuid}.bin
```

---

## 3. Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Backend | FastAPI + SQLAlchemy 2 async + Pydantic v2 | async, typed, auto /docs |
| DB | SQLite via aiosqlite (swap-ready Postgres) | zero-config demo, prod-ready ORM |
| Auth | python-jose HS256 JWT + httpOnly rotating refresh (passlib pbkdf2) | stateless API + revocable sessions |
| Crypto | Fernet (cryptography) | Aadhaar, Drive blobs, AI keys at rest |
| AI | Sarvam AI primary; openai-whisper + Ollama local fallback | Indian languages; offline-capable |
| Standards | FHIR R4 bundles; NAMASTE ↔ ICD-11 TM2 ↔ ICD-11 dual coding | ABDM interoperability |
| Frontend | Next.js 14, React 18, Tailwind, zustand, jsQR, qrcode | SSR portals, tiny state, QR scan/generate |
| Tests | pytest + TestClient, 33 tests | every role journey + security |

---

## 4. Data Model Map (39 tables → 8 domains)

**Identity & access:** `users` → `patients` / `doctor_profiles` → `departments` · `refresh_sessions` · `security_events` · `audit_logs` · `notifications`

**Scheduling (QR thread):** `doctor_slots` → `appointments` (holds `checkin_token` = `AIIA-CK-{id}-{UHID}-{token}`) → `encounters` · `therapy_sessions`

**Clinical record:** `encounters` → `diagnoses` (dual-coded ×3 rows) · `prescriptions` → `pharmacy_dispenses` · `lab_orders` · `nurse_vitals` · `bills` · `discharge_summaries` · `ayush_case_records` (prakriti/ashtavidha/dashavidha)

**Pre-consult intake (patient-entered):** `patient_intakes` → `chief_complaints` · `history_of_present_illness` (SOCRATES fields) · `allergies` · `current_medications` · `past_history` · `review_of_systems`

**AI / scribe:** `consultation_transcripts` (diarized, consent-tracked, auto-purged) · `clinical_note_drafts` (SOAP, approval workflow) · `ai_provider_configs` · `retention_policies`

**Paper → digital:** `document_assets` (sha256 + Fernet blob) → `document_access_grants` · `terminology_codes` · `drug_interaction_pairs` → `drug_interaction_flags`

**Case file / family:** `family_members` · `referrals`

Key FK spine to draw on a slide:
`users → patients → appointments → encounters → {diagnoses, prescriptions, lab_orders, bills, discharge_summaries, transcripts}`

---

## 5. The QR Journey (hero demo flow — one code, five desks)

| Step | Actor | Screen | API | Table writes |
|---|---|---|---|---|
| 1. Book | Patient | /patient/book-appointment (6 steps) | POST /appointments | `appointments` (row-locked token) |
| 2. Slip | Patient | /patient/slip/[id] — QR + token | GET /appointments/me | — |
| 3. Pre-consult | Patient | /intake/[id] (voice, consent-gated) | POST /intake/{id}/start … /submit | intake domain (§4) |
| 4. Check-in | Reception | /reception/checkin (camera scan) | POST /reception/scan | status → CHECKED_IN |
| 5. Vitals | Nurse | /nurse/vitals (scan) | POST /nurse/vitals/{id} | `nurse_vitals` |
| 6. Call in | Doctor | /doctor/queue (red-flag first) | PATCH /queue/{id}/call-next | `encounters` created |
| 7. Consult | Doctor | /doctor/consultation/[id] (13 cards) | see §6 | §6 |
| 8. Pharmacy | Pharmacy | /pharmacy/dispense (scan) | POST /pharmacy/dispense/{id} | `pharmacy_dispenses`, `stock_items`, `bills` |
| 9. Bill | Billing | /billing/bills | POST /billing/pay/{id} | `bills` PAID |
| 10. Discharge | Doctor | /discharge/summary/[id] | POST /discharge/{enc} | `discharge_summaries`, FHIR bundle |

Forged/guessed codes return 404 — the QR is the only check-in path (no manual override).

---

## 6. Consultation Screen Map (13 cards)

| Card | What it does | API |
|---|---|---|
| PatientHeader | identity, red-flag banner, prior visits, case file | GET /patients/{id}/timeline |
| HistorySummaryPanel | auto-narrative of intake, insertable into notes | GET /encounters/{id}/history-summary |
| IntakeSummaryCard | everything patient entered pre-visit | GET /encounters/{id}/intake-summary |
| VoiceIntakePanel | record + waveform + Sarvam STT → text → SOCRATES | POST /voice/transcribe-audio, /nlp/extract-entities |
| SocratesCard | Site·Onset·Character·Radiation·Assoc·Timing·Exacerb·Reliev·Severity·Duration | saved to `encounters.extracted_entities` |
| VitalsTrendCard | pulse sparkline across visits | GET /patients/{id}/vitals-history |
| AyurvedaAssessmentCard | 18-trait prakriti %, vikriti, ashtavidha, dashavidha (Bala) | POST /ayush/prakriti-score, /ayush/ashtavidha, /ayush/dashavidha |
| AmbientScribeCard | consent → diarized recording → SOAP draft → doctor approves | /consultation/{id}/start·stop-recording, generate-soap-draft, note-drafts/{id}/approve |
| DiagnosisCard | debounced terminology search; one NAMASTE pick = 3 coded rows | POST /diagnoses, /terminology/search |
| PrescriptionCard | med rows, interaction check on sign | POST /prescriptions/{enc} |
| LabOrdersCard | order → result → auto abnormal flag | POST /lab/orders, PATCH /lab/orders/{id}/result |
| DispatchCard | auto→pharmacy, refer→therapy/department/doctor | POST /encounters/{id}/refer, GET …/dispatch |
| SummaryNotesCard | save notes, generate FHIR, print ℞, end→discharge | PATCH /encounters/{id}, POST /fhir/generate-bundle/{enc} |

---

## 7. AI Pipeline & Honesty Policy (differentiator slide)

Per capability (STT, diarized STT, translate, chat, TTS, OCR):
1. **Sarvam AI** (key from admin-configured encrypted store, else env) — 22 Indic languages, Saaras v3.
2. **Local fallback** — Whisper STT / Ollama (gemma/mistral/llama3.1) chat, on the same machine.
3. **Labelled mock** — only if both fail; response carries `mocked: true` / `provider: "none"` + the real error.

**Never fabricates:** if no engine can transcribe, the API returns an error — tests assert this (honest-STT test).
Admin's /admin/about page shows a live **real vs mocked table**.

Mocked-by-design (labelled): ABDM bridge (OTP 123456), payment gateway, rule-based SOCRATES extractor, OCR without key/text layer.

---

## 8. Security Model

- JWT access (12 h) + httpOnly **rotating refresh cookie** (revocable via /settings/sessions).
- RBAC: `require_roles(...)` on every staff route; patient vs staff portal isolation in frontend.
- Ownership guards: patients read only their own encounters/timeline/FHIR/case-file (403 otherwise — tested).
- Encryption at rest: Aadhaar (masked `XXXX-XXXX-1234` in API), Drive blobs (Fernet, no public /media), AI provider keys (masked `••••••••abcd`).
- Audit log for sensitive actions (ADMIN viewable); security_events for logins.
- Retention policy auto-purges raw consultation audio (default 30 days) at startup.
- Production mode refuses to boot with dev secret / missing encryption key.

---

## 9. Demo Script (≈7 minutes)

1. **patient@demo.in** — book appointment → QR slip. (30 s)
2. /intake/[id] — consent checklist → complaint in own words (type or voice) → adaptive questions branch by complaint → submit. (90 s)
3. **reception@demo.in** — scan the QR (or paste code) → checked in. (30 s)
4. **nurse@demo.in** — scan → vitals. (20 s)
5. **doctor-allo@demo.in** — queue shows red-flag patient first → Call in → consultation: intake summary already filled → record voice → SOCRATES extracted → pick "Amlapitta" → 3 codes (NAM-AYU-0001 / TM26.SA00 / K29.7) → prescribe (interaction flag) → dispatch → FHIR bundle. (3 min)
6. **pharmacy@demo.in** scan + dispense → **billing@demo.in** pay. (45 s)
7. Back to **patient@demo.in** — My Records + Case File timeline + Drive. (30 s)
8. **admin@demo.in** — analytics, AI status, audit, About (real vs mocked). (30 s)

---

## 10. Headline Numbers

- **39** database tables · **128** API endpoints · **34** frontend routes
- **33** automated tests, all passing · **8** roles · **6** UI languages · **22** STT languages
- **3-way dual coding** NAMASTE ↔ ICD-11 TM2 ↔ ICD-11 (42 curated terms)
- FHIR R4 document bundles per encounter; zero data fabrication in the AI layer

## 11. Pitch Points (USPs)

1. **One QR, whole hospital** — check-in to discharge, no repeated history.
2. **Listens in 22 languages, speaks back** — Sarvam STT/TTS, voice-first intake for low-literacy patients.
3. **Doctor writes less** — ambient scribe → SOAP draft → one-click approve (doctor stays signer of record).
4. **Ayurveda is computable** — prakriti scoring, dashavidha Bala, 3-way terminology mapping in the same record as biomedicine.
5. **Honest AI** — real/fallback/mock always labelled; nothing invented.
6. **ABDM-ready** — ABHA linking (mocked bridge), FHIR bundles, care-context references.
7. **Privacy by design** — encryption at rest, granular consent, audio auto-purge, audit trail, masked identifiers.

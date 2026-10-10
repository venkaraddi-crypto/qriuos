# ArogyaSetu — Patient Case-Taking Software

Integrated Allopathic + Ayurveda OPD case-taking for the All India Institute of Ayurveda.
One QR code drives the whole visit: booking → reception check-in → nurse vitals → doctor consultation
(voice intake, SOCRATES, Prakriti/Vikriti, dual-coded NAMASTE ↔ ICD-11 diagnosis, ambient scribe) →
pharmacy → billing → discharge with a FHIR R4 bundle.

## Run it

```bash
# backend  (http://localhost:8000, docs at /docs)
cd backend && python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest
.venv/bin/uvicorn app.main:app --reload --port 8000

# frontend (http://localhost:3000)
cd frontend && npm install && npm run dev

# tests
cd backend && .venv/bin/pytest tests/ -q
```

Demo logins (password `password123`): `patient@demo.in`, `reception@demo.in`, `doctor-allo@demo.in`,
`doctor-ayu@demo.in`, `nurse@demo.in`, `lab@demo.in`, `pharmacy@demo.in`, `billing@demo.in`, `admin@demo.in`.
The database is seeded on first start (8 patients, 2 doctors with 5 days of slots, checked-in patients
holding tokens 2/3, a red-flag chest-pain case, a dual-coded Amlapitta case, a multi-visit diabetic).

## Configuration (`backend/.env`, see `.env.example`)

| Key | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./hospital.db` | any SQLAlchemy async URL |
| `SECRET_KEY` | dev value | must be ≥32 chars in production |
| `FIELD_ENCRYPTION_KEY` | derived from SECRET_KEY | Fernet key; required in production |
| `ENVIRONMENT` | `development` | `production` enables the guards above |
| `SARVAM_API_KEY` | unset | enables Sarvam STT/diarization/translate/chat/TTS/OCR |
| `SARVAM_STT_MODEL` | `saaras:v3` | supports `mode=codemix` |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | |

Optional local AI: `pip install openai-whisper` (STT fallback), run Ollama (SOAP fallback), `pip install pymupdf` (PDF text layer).

## Layout

```
backend/app
  core/        config, database, security (JWT + refresh), crypto (Fernet)
  models.py    39 tables
  seed.py      demo data
  services/    nlp, prakriti, dashavidha, terminology_data, question_engine, extraction,
               history_summary, fhir, sarvam_client, local_ai, mocks
  api/v1/endpoints/  core, clinical, intake, ops, documents, drive, casefile, scribe,
                     referrals, ai_admin, settings
backend/tests  8 suites — full 8-role journey, data interconnect, intake, contracts,
               Sarvam STT/features, security & Drive, SIH compliance
frontend/src
  app/         34 routes (patient portal, staff portals, printable ℞ / slip / discharge)
  components/  Shell, CameraScanner, CaseFile, DocumentDigitizer, ConsentGate,
               AdaptiveHistory, consultation/* (13 cards)
  lib/         api.ts (fetch + refresh), i18n.tsx (6 languages)
  store/       auth.ts (zustand)
```

## Honesty about AI

Every AI capability resolves **Sarvam (admin key → env key) → local fallback → labelled mock**.
Speech transcription is *never* fabricated: with no engine available the API returns `provider: "none"`
and an error, and the UI says so. Mocked components (SOCRATES extractor, OCR sample, ABDM bridge with OTP
`123456`, payment gateway) all carry `mocked: true`. Admin → About lists the real-vs-mocked table.

## Security

JWT access tokens + rotating HTTP-only refresh cookie; per-endpoint role gates; patients can read only their
own encounters/timeline/vitals/FHIR; Aadhaar encrypted and masked; Medical Drive blobs Fernet-encrypted with
owner / treating-doctor / explicit-grant / admin access and audited downloads; audit log for sensitive actions;
raw consultation audio purged after the configurable retention period.

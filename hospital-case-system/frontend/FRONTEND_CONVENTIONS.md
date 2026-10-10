# Frontend conventions (for contributors / sub-agents)

Stack: Next 14 app router, React 18, TypeScript strict, Tailwind. No other deps besides `zustand`, `jsqr`, `qrcode`.

## Every page
- File: `src/app/<route>/page.tsx`, starts with `"use client";`.
- Wrap content in `<Shell portal="patient"|"staff" title="…" tint?="allo"|"ayu">` from `@/components/Shell`.
- Fetch via `import { get, post, patch, put, del, upload, downloadFile } from "@/lib/api"` — paths are relative to `/api/v1`, e.g. `get("/queue")`.
  Errors throw `Error(detail)`; show `(e as Error).message` in a `<p className="text-sm" style={{color:"#A03A2A"}}>`.
- Icons: `import { IconMic, IconAlert, IconQr, IconCheck, IconX, IconPlus, IconPrint, IconFile, IconUser, IconCalendar, IconBell, IconLock, IconSpeaker, IconArrow } from "@/components/icons"`. No emoji.
- QR scanning: `<CameraScanner onScan={(code)=>…} label="…" />` from `@/components/CameraScanner` (includes manual-entry fallback).
- Dynamic routes read `useParams()` from `next/navigation`.

## Design tokens (globals.css utility classes)
`.card`, `.tint-allo`, `.tint-ayu`, `.input`, `.btn-primary`, `.btn-ghost`, `.badge`, `.badge-red/-green/-amber`, `.tab-active`, `.wavebar`, `.label`, `.muted`, `.mono`, `.serif`, `.hr`, `.no-print`.
Headings use `className="serif"`. IDs/tokens/vitals use `className="mono"`. Paper background, hairline borders, no shadows/gradients.

## Backend contract highlights (JSON unless noted)
- Login: `POST /auth/login {email,password}` → `{access_token, role, name}`. Store handles it (`useAuth().login`).
- Reception: `GET /reception/board` → `{checked_in[], upcoming[]}`; `POST /reception/scan {code}` (409 if already); `POST /reception/walkin {name,phone,doctor_id,dob?,gender?,chief_complaint?,emergency}`; `GET /doctors`.
- Doctor: `GET /queue` → appointment rows + `encounter_id`; `PATCH /queue/{id}/call-next` → `{encounter_id}`; `/skip`, `/no-show`.
- Nurse: `GET /nurse/today` (rows have `vitals_missing`), `POST /nurse/vitals/{appointment_id} {bp,pulse,temp,weight}`, `GET|POST|PATCH /nurse/therapy-sessions`.
- Lab: `GET /lab/orders?patient_id`, `PATCH /lab/orders/{id}/result {result_values, flagged_abnormal?}`.
- Pharmacy: `GET /pharmacy/queue`, `POST /pharmacy/scan {code}` → `{appointment, encounter_id, dispenses[]}`, `POST /pharmacy/dispense/{id}`, `GET|POST|PATCH /pharmacy/stock`.
- Billing: `GET /billing/worklist` → `{unbilled[], bills[]}`, `POST /billing/generate/{encounter_id}`, `POST /billing/pay/{bill_id}`.
- Patient: `GET /patients/me/summary`, `GET /appointments/me`, `PATCH /appointments/{id}/cancel|reschedule {slot_id}`, `GET /doctors/{id}/slots?date=`, `GET /patients/me/records` → `{medicines[],reports[],bills[]}`, `GET /notifications/me`, `GET /case-file/{patient_id}` → `{patient, events[{type,date,…}]}`, `GET|POST /patients/me/family`, `GET /patients/me/profile`, `PATCH /patients/me/profile {aadhaar_no?,…}`.
- Drive: `upload("/drive/documents", {file, category, document_date?})`, `GET /drive/documents`, `downloadFile("/drive/documents/{id}/download", name)`, `DELETE /drive/documents/{id}`, `POST /drive/documents/{id}/grant-access {user_id, reason, expires_at?}`.
- Documents: `upload("/documents/digitize", {file})` → `{ocr:{provider,mocked,text}, extracted:{type,labs[],medications[],document_date,confidence}}`; `POST /documents/confirm {patient_id, encounter_id?, labs, medications, document_date}`.
- Intake: `GET /intake/{appointment_id}`, `POST /intake/{id}/start {language, consent_items}`, `POST …/complaints {complaint_text,duration_days,severity}`, `GET …/adaptive-questions` → `{category, questions[{key,type,prompt,options,target}], remaining, complete}`, `PUT …/hpi {answers}`, `POST …/allergies|meds|past`, `PUT …/ros {systems:{GI:{positive,notes}}}`, `POST …/submit`, `POST /voice/tts {text,language}` → `{audio_base64|null, mocked}`.
- Admin: `GET|POST /admin/staff`, `POST /admin/departments {name,system}`, `POST /admin/doctor-slots {doctor_id,date,start_time,end_time,capacity}`, `GET /analytics/summary`, `GET /audit-log`, `GET|PUT /admin/retention-policy`, `GET|POST|DELETE /admin/ai-providers`, `GET /admin/ai-status`, `POST /admin/ai-providers/test {capability}`.
- Settings: `GET|PATCH /settings/me`, `POST /settings/change-password {current_password,new_password}`, `GET /settings/sessions`, `DELETE /settings/sessions/{id}`, `upload("/profile/photo",{file})`.
- Encounter: `GET /encounters/{id}` (see `src/components/consultation/types.ts` → `Encounter`), `GET /discharge/{id}`, `GET /fhir/bundle/{id}`.

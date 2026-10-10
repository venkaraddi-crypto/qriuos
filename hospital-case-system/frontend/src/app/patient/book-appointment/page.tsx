"use client";
import Link from "next/link";
import QRCode from "qrcode";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { get, post } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

interface Dept { id: number; name: string; system: string }
interface Doc { id: number; name: string; specialty: string | null; department: string }
interface Slot { id: number; date: string; start_time: string; end_time: string; capacity: number; available: number }
interface Appt { id: number; qr_code: string; token_number: string; date: string; slot_time: string; doctor_name: string; department: string }

const STEPS = ["System", "Mode & type", "Department", "Doctor", "Slot", "Confirm"];

function nextDays(n: number) {
  return Array.from({ length: n }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() + i);
    return d.toISOString().slice(0, 10);
  });
}

export default function BookAppointment() {
  const { t } = useI18n();
  const [step, setStep] = useState(0);
  const [system, setSystem] = useState<"ALLOPATHIC" | "AYURVEDA" | null>(null);
  const [mode, setMode] = useState<"IN_PERSON" | "TELE">("IN_PERSON");
  const [type, setType] = useState<"NEW" | "FOLLOWUP">("NEW");
  const [depts, setDepts] = useState<Dept[]>([]);
  const [dept, setDept] = useState<Dept | null>(null);
  const [docs, setDocs] = useState<Doc[]>([]);
  const [doc, setDoc] = useState<Doc | null>(null);
  const [day, setDay] = useState(nextDays(1)[0]);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [slot, setSlot] = useState<Slot | null>(null);
  const [complaint, setComplaint] = useState("");
  const [appt, setAppt] = useState<Appt | null>(null);
  const [qr, setQr] = useState<string>("");
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => { get<Dept[]>("/departments").then(setDepts).catch((e) => setErr(e.message)); }, []);
  useEffect(() => { if (dept) get<Doc[]>(`/doctors?department_id=${dept.id}`).then(setDocs).catch((e) => setErr(e.message)); }, [dept]);
  useEffect(() => { if (doc) get<Slot[]>(`/doctors/${doc.id}/slots?date=${day}`).then(setSlots).catch((e) => setErr(e.message)); }, [doc, day]);
  useEffect(() => { if (appt) QRCode.toDataURL(appt.qr_code, { margin: 1, width: 220 }).then(setQr); }, [appt]);

  const book = async () => {
    if (!doc || !slot) return;
    setErr(null);
    try {
      const a = await post<Appt>("/appointments", { doctor_id: doc.id, slot_id: slot.id, chief_complaint: complaint || null, mode, type });
      setAppt(a);
      setStep(5);
    } catch (e) { setErr((e as Error).message); }
  };

  const tint = system === "AYURVEDA" ? "ayu" : system ? "allo" : undefined;

  return (
    <Shell portal="patient" title={t("book_appointment")} tint={tint}>
      <ol className="mb-4 flex flex-wrap gap-2 text-xs">
        {STEPS.map((s, i) => <li key={s} className={`badge ${i === step ? "badge-amber" : i < step ? "badge-green" : ""}`}>{i + 1}. {s}</li>)}
      </ol>
      {err && <p className="mb-3 text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
      {step === 0 && (
        <div className="grid gap-3 md:grid-cols-2">
          {(["ALLOPATHIC", "AYURVEDA"] as const).map((s) => (
            <button key={s} className={`card text-left ${s === "AYURVEDA" ? "tint-ayu" : "tint-allo"}`} onClick={() => { setSystem(s); setStep(1); }}>
              <h2 className="serif text-xl">{s === "ALLOPATHIC" ? "Allopathic" : "Ayurveda"}</h2>
              <p className="text-sm muted">{s === "ALLOPATHIC" ? "General medicine, orthopaedics, paediatrics" : "Kayachikitsa, Panchakarma, Shalya Tantra"}</p>
            </button>
          ))}
        </div>
      )}
      {step === 1 && (
        <div className="card space-y-4">
          <div><span className="label">Mode</span>
            <div className="flex gap-2">{(["IN_PERSON", "TELE"] as const).map((m) => <button key={m} className={mode === m ? "btn-primary" : "btn-ghost"} onClick={() => setMode(m)}>{m === "IN_PERSON" ? "In person" : "Tele-consult"}</button>)}</div></div>
          <div><span className="label">Visit type</span>
            <div className="flex gap-2">{(["NEW", "FOLLOWUP"] as const).map((m) => <button key={m} className={type === m ? "btn-primary" : "btn-ghost"} onClick={() => setType(m)}>{m === "NEW" ? "New" : "Follow-up"}</button>)}</div></div>
          <label className="block"><span className="label">Chief complaint (optional)</span>
            <textarea className="input" rows={2} value={complaint} onChange={(e) => setComplaint(e.target.value)} placeholder="e.g. burning in stomach after meals for two weeks" /></label>
          <div className="flex gap-2"><button className="btn-ghost" onClick={() => setStep(0)}>Back</button><button className="btn-primary" onClick={() => setStep(2)}>Next</button></div>
        </div>
      )}
      {step === 2 && (
        <div className="grid gap-2 md:grid-cols-3">
          {depts.filter((d) => d.system === system).map((d) => (
            <button key={d.id} className="card text-left hover:underline" onClick={() => { setDept(d); setStep(3); }}><h3 className="serif text-lg">{d.name}</h3></button>
          ))}
          <button className="btn-ghost md:col-span-3 w-fit" onClick={() => setStep(1)}>Back</button>
        </div>
      )}
      {step === 3 && (
        <div className="grid gap-2 md:grid-cols-2">
          {docs.length === 0 && <p className="muted">No doctors in this department yet.</p>}
          {docs.map((d) => (
            <button key={d.id} className="card text-left" onClick={() => { setDoc(d); setStep(4); }}>
              <h3 className="serif text-lg">{d.name}</h3><p className="text-sm muted">{d.specialty || d.department}</p>
            </button>
          ))}
          <button className="btn-ghost md:col-span-2 w-fit" onClick={() => setStep(2)}>Back</button>
        </div>
      )}
      {step === 4 && doc && (
        <div className="card space-y-3">
          <div className="flex flex-wrap gap-1">
            {nextDays(7).map((d) => <button key={d} className={`badge ${day === d ? "badge-amber" : ""}`} onClick={() => { setDay(d); setSlot(null); }}>{d.slice(5)}</button>)}
          </div>
          <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
            {slots.length === 0 && <p className="muted col-span-full text-sm">No slots on this day.</p>}
            {slots.map((s) => (
              <button key={s.id} disabled={s.available <= 0} className={`card text-center ${slot?.id === s.id ? "ring-1 ring-clay" : ""} ${s.available <= 0 ? "opacity-40" : ""}`} onClick={() => setSlot(s)}>
                <span className="mono">{s.start_time}</span><br /><span className="text-xs muted">{s.available} left</span>
              </button>
            ))}
          </div>
          <div className="flex gap-2"><button className="btn-ghost" onClick={() => setStep(3)}>Back</button><button className="btn-primary" disabled={!slot} onClick={book}>Confirm booking</button></div>
        </div>
      )}
      {step === 5 && appt && (
        <div className="card mx-auto max-w-md text-center space-y-2">
          <h2 className="serif text-2xl">Appointment confirmed</h2>
          <p>{appt.date} · <span className="mono">{appt.slot_time}</span> · {appt.doctor_name}</p>
          <p className="text-sm muted">{appt.department}</p>
          <p className="text-sm">{t("token")}</p><p className="mono text-4xl">{appt.token_number}</p>
          {qr && <img src={qr} alt="Appointment QR code" className="mx-auto" />}
          <p className="mono text-xs muted">{appt.qr_code}</p>
          <p className="text-xs muted">Show this QR at reception to check in. Nurse, pharmacy and billing scan the same code.</p>
          <div className="flex justify-center gap-2 pt-2">
            <Link className="btn-ghost" href={`/patient/slip/${appt.id}`}>Print slip</Link>
            <Link className="btn-primary" href={`/intake/${appt.id}`}>Start pre-consult intake</Link>
          </div>
        </div>
      )}
    </Shell>
  );
}

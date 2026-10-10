"use client";
import { useEffect, useState } from "react";
import { get, patch, post } from "@/lib/api";

interface Therapy { id: number; patient_name: string | null; uhid: string | null; therapy_name: string; scheduled_at: string; status: string }

export default function TherapyPanel({ onMessage }: { onMessage: (m: string) => void }) {
  const [therapies, setTherapies] = useState<Therapy[]>([]);
  const [form, setForm] = useState({ patient_id: "", therapy_name: "Abhyanga + Swedana", scheduled_at: "" });
  const [err, setErr] = useState<string | null>(null);
  const load = () => get<Therapy[]>("/nurse/therapy-sessions").then(setTherapies).catch((e) => setErr(e.message));
  useEffect(() => { void load(); }, []);

  const schedule = async (e: React.FormEvent) => {
    e.preventDefault(); setErr(null);
    try {
      await post("/nurse/therapy-sessions", { patient_id: Number(form.patient_id), therapy_name: form.therapy_name, scheduled_at: new Date(form.scheduled_at).toISOString() });
      onMessage("Therapy scheduled"); void load();
    } catch (ex) { setErr((ex as Error).message); }
  };

  return (
    <div className="space-y-4">
      <section className="card">
        <h3 className="serif">Therapy sessions</h3>
        <ul className="text-sm">
          {therapies.length === 0 && <li className="muted">None scheduled.</li>}
          {therapies.map((t) => (
            <li key={t.id} className="flex items-center justify-between gap-2 border-b py-1 hr">
              <span>{t.therapy_name} — {t.patient_name} <span className="mono muted">{t.scheduled_at.slice(0, 16).replace("T", " ")}</span></span>
              <select className="input w-auto py-0.5 text-xs" value={t.status} onChange={(e) => patch(`/nurse/therapy-sessions/${t.id}`, { status: e.target.value }).then(load)}>
                <option>SCHEDULED</option><option>DONE</option><option>CANCELLED</option>
              </select>
            </li>
          ))}
        </ul>
      </section>
      <form onSubmit={schedule} className="card space-y-2">
        <h3 className="serif">Schedule therapy</h3>
        <input className="input" type="number" placeholder="Patient ID" value={form.patient_id} onChange={(e) => setForm({ ...form, patient_id: e.target.value })} required />
        <input className="input" value={form.therapy_name} onChange={(e) => setForm({ ...form, therapy_name: e.target.value })} required />
        <input className="input" type="datetime-local" value={form.scheduled_at} onChange={(e) => setForm({ ...form, scheduled_at: e.target.value })} required />
        {err && <p className="text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
        <button className="btn-primary">Schedule</button>
      </form>
    </div>
  );
}

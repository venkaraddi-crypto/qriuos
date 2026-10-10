"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { get, post } from "@/lib/api";

interface Doc { id: number; name: string; department: string; system: string }
interface Appt { id: number; patient_name: string; uhid: string; token_number: string; qr_code: string; doctor_name: string; status: string }

export default function Walkin() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [form, setForm] = useState({ name: "", phone: "", dob: "", gender: "", doctor_id: "", chief_complaint: "", emergency: false, uhid: "" });
  const [created, setCreated] = useState<Appt | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { get<Doc[]>("/doctors").then(setDocs).catch((e) => setErr(e.message)); }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setErr(null);
    try {
      const a = await post<Appt>("/reception/walkin", { ...form, doctor_id: Number(form.doctor_id), dob: form.dob || null, gender: form.gender || null, uhid: form.uhid || null, chief_complaint: form.chief_complaint || null });
      setCreated(a);
    } catch (ex) { setErr((ex as Error).message); }
  };
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => setForm({ ...form, [k]: e.target.value });

  return (
    <Shell portal="staff" title="Walk-in registration">
      <div className="grid gap-4 md:grid-cols-2">
        <form onSubmit={submit} className="card space-y-2">
          <input className="input mono" placeholder="Existing UHID (optional)" value={form.uhid} onChange={set("uhid")} />
          <input className="input" placeholder="Patient name" value={form.name} onChange={set("name")} required />
          <input className="input" placeholder="Phone" value={form.phone} onChange={set("phone")} required />
          <div className="grid grid-cols-2 gap-2">
            <input className="input" type="date" value={form.dob} onChange={set("dob")} aria-label="Date of birth" />
            <select className="input" value={form.gender} onChange={set("gender")} aria-label="Gender"><option value="">Gender…</option><option>Female</option><option>Male</option><option>Other</option></select>
          </div>
          <select className="input" value={form.doctor_id} onChange={set("doctor_id")} required>
            <option value="">Doctor…</option>{docs.map((d) => <option key={d.id} value={d.id}>{d.name} — {d.department} ({d.system})</option>)}
          </select>
          <textarea className="input" rows={2} placeholder="Chief complaint" value={form.chief_complaint} onChange={set("chief_complaint")} />
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.emergency} onChange={(e) => setForm({ ...form, emergency: e.target.checked })} /> Emergency — token E, front of queue</label>
          {err && <p className="text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
          <button className="btn-primary">Register & check in</button>
        </form>
        {created && (
          <div className="card space-y-1">
            <h2 className="serif text-xl">{created.patient_name}</h2>
            <p className="mono text-sm">{created.uhid}</p>
            <p>Token <span className="mono text-3xl">{created.token_number}</span> {created.token_number === "E" && <span className="badge badge-red ml-2">EMERGENCY</span>}</p>
            <p className="text-sm">{created.doctor_name} · <span className="badge">{created.status}</span></p>
            <p className="mono text-xs muted">{created.qr_code}</p>
          </div>
        )}
      </div>
    </Shell>
  );
}

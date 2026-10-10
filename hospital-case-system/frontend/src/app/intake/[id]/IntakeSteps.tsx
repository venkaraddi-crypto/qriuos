"use client";
import { useState } from "react";
import { del, post, put } from "@/lib/api";
import { IconX } from "@/components/icons";

export interface Complaint { id: number; complaint_text: string; duration_days: number | null; severity: number | null }
const ROS = ["GENERAL", "CV", "RESPIRATORY", "GI", "NEURO", "MUSCULOSKELETAL", "SKIN", "ENT", "GU", "PSYCHIATRIC", "ENDOCRINE"];
export const Err = ({ e }: { e: string | null }) => (e ? <p className="text-sm" style={{ color: "#A03A2A" }}>{e}</p> : null);

export function ComplaintsStep({ aid, initial, onNext }: { aid: number; initial: Complaint[]; onNext: () => void }) {
  const [rows, setRows] = useState<Complaint[]>(initial);
  const [f, setF] = useState({ complaint_text: "", duration_days: "", severity: "5" });
  const [err, setErr] = useState<string | null>(null);
  const add = async (e: React.FormEvent) => {
    e.preventDefault(); setErr(null);
    try {
      const c = await post<Complaint>(`/intake/${aid}/complaints`, { complaint_text: f.complaint_text, duration_days: f.duration_days ? Number(f.duration_days) : null, severity: Number(f.severity) });
      setRows([...rows, c]); setF({ complaint_text: "", duration_days: "", severity: "5" });
    } catch (ex) { setErr((ex as Error).message); }
  };
  const remove = async (id: number) => { try { await del(`/intake/${aid}/complaints/${id}`); setRows(rows.filter((r) => r.id !== id)); } catch (ex) { setErr((ex as Error).message); } };
  return (
    <section className="card space-y-3">
      <h2 className="serif text-xl">What brings you in today?</h2>
      <ul className="text-sm">{rows.map((r) => <li key={r.id} className="flex items-center justify-between border-b py-1 hr"><span>{r.complaint_text} <span className="muted">{r.duration_days ? `· ${r.duration_days} d` : ""} {r.severity != null ? `· ${r.severity}/10` : ""}</span></span><button className="btn-ghost px-1 py-0.5" onClick={() => remove(r.id)} aria-label="Remove"><IconX size={12} /></button></li>)}</ul>
      <form onSubmit={add} className="space-y-2">
        <input className="input" placeholder="Describe the problem in your own words" value={f.complaint_text} onChange={(e) => setF({ ...f, complaint_text: e.target.value })} required />
        <div className="flex flex-wrap gap-2">
          <input className="input w-32" type="number" min={0} placeholder="Days" value={f.duration_days} onChange={(e) => setF({ ...f, duration_days: e.target.value })} />
          <label className="flex items-center gap-2 text-sm">Severity <input type="range" min={0} max={10} value={f.severity} onChange={(e) => setF({ ...f, severity: e.target.value })} /> <span className="mono">{f.severity}</span></label>
          <button className="btn-ghost">Add</button>
        </div>
      </form>
      <Err e={err} />
      <button className="btn-primary" disabled={rows.length === 0} onClick={onNext}>Continue</button>
    </section>
  );
}

export function RosStep({ aid, onNext }: { aid: number; onNext: () => void }) {
  const [s, setS] = useState<Record<string, { positive: boolean; notes: string }>>({});
  const [err, setErr] = useState<string | null>(null);
  const save = async () => {
    setErr(null);
    try { await put(`/intake/${aid}/ros`, { systems: Object.fromEntries(Object.entries(s).map(([k, v]) => [k, { positive: v.positive, notes: v.notes || null }])) }); onNext(); } catch (ex) { setErr((ex as Error).message); }
  };
  return (
    <section className="card space-y-3">
      <h2 className="serif text-xl">Any other symptoms?</h2>
      <div className="grid gap-2 text-sm md:grid-cols-2">
        {ROS.map((k) => (
          <div key={k} className="flex items-center gap-2">
            <label className="flex w-40 items-center gap-2"><input type="checkbox" checked={Boolean(s[k]?.positive)} onChange={(e) => setS({ ...s, [k]: { positive: e.target.checked, notes: s[k]?.notes || "" } })} /> {k}</label>
            <input className="input py-1" placeholder="notes" value={s[k]?.notes || ""} onChange={(e) => setS({ ...s, [k]: { positive: s[k]?.positive || false, notes: e.target.value } })} />
          </div>
        ))}
      </div>
      <Err e={err} />
      <button className="btn-primary" onClick={save}>Continue</button>
    </section>
  );
}

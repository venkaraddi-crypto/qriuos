"use client";
import { useState } from "react";
import { post } from "@/lib/api";
import { Err } from "./IntakeSteps";

export default function BackgroundStep({ aid, onNext }: { aid: number; onNext: () => void }) {
  const [al, setAl] = useState({ substance: "", reaction: "", severity: "" });
  const [md, setMd] = useState({ name: "", dose: "", frequency: "" });
  const [ph, setPh] = useState({ kind: "PMH", text: "", year: "" });
  const [log, setLog] = useState<string[]>([]);
  const [err, setErr] = useState<string | null>(null);

  const run = async (path: string, body: Record<string, unknown>, label: string) => {
    setErr(null);
    try { await post(`/intake/${aid}/${path}`, body); setLog((l) => [...l, label]); } catch (ex) { setErr((ex as Error).message); }
  };
  const submitAllergy = (e: React.FormEvent) => { e.preventDefault(); void run("allergies", { substance: al.substance, reaction: al.reaction || null, severity: al.severity || null }, `Allergy: ${al.substance}`); setAl({ substance: "", reaction: "", severity: "" }); };
  const submitMed = (e: React.FormEvent) => { e.preventDefault(); void run("meds", { name: md.name, dose: md.dose || null, frequency: md.frequency || null }, `Medicine: ${md.name}`); setMd({ name: "", dose: "", frequency: "" }); };
  const submitPast = (e: React.FormEvent) => { e.preventDefault(); void run("past", { kind: ph.kind, text: ph.text, year: ph.year ? Number(ph.year) : null }, `${ph.kind}: ${ph.text}`); setPh({ ...ph, text: "", year: "" }); };

  return (
    <section className="card space-y-4">
      <h2 className="serif text-xl">Allergies, medicines & past history</h2>
      <p className="text-sm muted">Add what applies; leave blank if none.</p>
      <div className="grid gap-3 text-sm md:grid-cols-3">
        <form className="space-y-1" onSubmit={submitAllergy}>
          <p className="label">Allergy</p>
          <input className="input" placeholder="Substance" value={al.substance} onChange={(e) => setAl({ ...al, substance: e.target.value })} required />
          <input className="input" placeholder="Reaction" value={al.reaction} onChange={(e) => setAl({ ...al, reaction: e.target.value })} />
          <select className="input" value={al.severity} onChange={(e) => setAl({ ...al, severity: e.target.value })}><option value="">Severity…</option><option>mild</option><option>moderate</option><option>severe</option></select>
          <button className="btn-ghost">Add allergy</button>
        </form>
        <form className="space-y-1" onSubmit={submitMed}>
          <p className="label">Current medicine</p>
          <input className="input" placeholder="Name" value={md.name} onChange={(e) => setMd({ ...md, name: e.target.value })} required />
          <input className="input" placeholder="Dose" value={md.dose} onChange={(e) => setMd({ ...md, dose: e.target.value })} />
          <input className="input" placeholder="How often" value={md.frequency} onChange={(e) => setMd({ ...md, frequency: e.target.value })} />
          <button className="btn-ghost">Add medicine</button>
        </form>
        <form className="space-y-1" onSubmit={submitPast}>
          <p className="label">Past history</p>
          <select className="input" value={ph.kind} onChange={(e) => setPh({ ...ph, kind: e.target.value })}><option>PMH</option><option>PSH</option><option>FAMILY</option><option>SOCIAL</option><option>OBSTETRIC</option></select>
          <input className="input" placeholder="Details" value={ph.text} onChange={(e) => setPh({ ...ph, text: e.target.value })} required />
          <input className="input" type="number" placeholder="Year" value={ph.year} onChange={(e) => setPh({ ...ph, year: e.target.value })} />
          <button className="btn-ghost">Add history</button>
        </form>
      </div>
      {log.length > 0 && <ul className="text-xs muted">{log.map((l, i) => <li key={i}>Saved — {l}</li>)}</ul>}
      <Err e={err} />
      <button className="btn-primary" onClick={onNext}>Continue</button>
    </section>
  );
}

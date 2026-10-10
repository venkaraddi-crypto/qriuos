"use client";
import { useState } from "react";
import { post } from "@/lib/api";
import { IconPlus, IconX } from "@/components/icons";
import { EMPTY_MEDICATION, type Medication } from "./types";

interface Flag { medication_a: string; medication_b: string; severity: string; note?: string | null }
interface Props { encounterId: number; patientId: number; onSigned: (prescriptionId: number) => void }

const FREQS = ["OD", "BD", "TDS", "QID", "HS", "SOS"];

export default function PrescriptionCard({ encounterId, patientId, onSigned }: Props) {
  const [rows, setRows] = useState<Medication[]>([{ ...EMPTY_MEDICATION }]);
  const [flags, setFlags] = useState<Flag[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const update = (i: number, k: keyof Medication, v: string) => setRows(rows.map((r, j) => (j === i ? { ...r, [k]: k === "duration_days" || k === "quantity" ? (v === "" ? "" : Number(v)) : v } : r)));

  const check = async () => {
    try {
      const r = await post<{ flags: Flag[] }>("/prescriptions/check-interactions", { medications: rows.map((m) => m.name).filter(Boolean), patient_id: patientId });
      setFlags(r.flags); setMsg(r.flags.length ? `${r.flags.length} interaction flag(s)` : "No interactions found");
    } catch (e) { setErr((e as Error).message); }
  };

  const sign = async () => {
    const meds = rows.filter((m) => m.name.trim());
    if (meds.length === 0) { setErr("Add at least one medication"); return; }
    setBusy(true); setErr(null);
    try {
      const r = await post<{ id: number; interaction_flags: Flag[] }>(`/prescriptions/${encounterId}`, { medications: meds.map((m) => ({ ...m, duration_days: m.duration_days === "" ? null : m.duration_days, quantity: m.quantity === "" ? null : m.quantity })) });
      setFlags(r.interaction_flags); setMsg(`Prescription #${r.id} signed — sent to pharmacy.`); onSigned(r.id);
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  };

  return (
    <section className="card space-y-2">
      <h3 className="serif text-lg">Prescription</h3>
      <div className="space-y-1">
        {rows.map((m, i) => (
          <div key={i} className="grid grid-cols-[2fr_1fr_1fr_1fr_auto] gap-1">
            <input className="input" placeholder="Medicine" value={m.name} onChange={(e) => update(i, "name", e.target.value)} aria-label="Medicine" />
            <input className="input" placeholder="Dose" value={m.dose} onChange={(e) => update(i, "dose", e.target.value)} aria-label="Dose" />
            <select className="input" value={m.frequency} onChange={(e) => update(i, "frequency", e.target.value)} aria-label="Frequency">{FREQS.map((f) => <option key={f}>{f}</option>)}</select>
            <input className="input" type="number" min={1} placeholder="Days" value={m.duration_days} onChange={(e) => update(i, "duration_days", e.target.value)} aria-label="Days" />
            <button className="btn-ghost px-2" onClick={() => setRows(rows.filter((_, j) => j !== i))} aria-label="Remove"><IconX size={14} /></button>
          </div>
        ))}
      </div>
      <div className="flex flex-wrap gap-2">
        <button className="btn-ghost" onClick={() => setRows([...rows, { ...EMPTY_MEDICATION }])}><IconPlus size={14} /> Add row</button>
        <button className="btn-ghost" onClick={check}>Check interactions</button>
        <button className="btn-primary" onClick={sign} disabled={busy}>Sign prescription</button>
      </div>
      {flags.map((f, i) => (
        <p key={i} className="text-sm"><span className={`badge ${f.severity === "HIGH" ? "badge-red" : "badge-amber"}`}>{f.severity}</span> {f.medication_a} + {f.medication_b}{f.note ? ` — ${f.note}` : ""}</p>
      ))}
      {msg && <p className="text-xs muted">{msg}</p>}
      {err && <p className="text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
    </section>
  );
}

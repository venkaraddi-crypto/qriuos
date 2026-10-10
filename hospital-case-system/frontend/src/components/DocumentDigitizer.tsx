"use client";
import { useState } from "react";
import { post, upload } from "@/lib/api";
import { IconX } from "@/components/icons";

interface Lab { test: string; value: number | string; unit: string; flag: string | null }
interface Med { name: string; dose: string; frequency: string | null; duration_days: number | null }
interface Digitized { ocr: { provider: string; mocked: boolean; text: string | null }; extracted: { type: string; labs: Lab[]; medications: Med[]; document_date: string | null; confidence: number } }
interface Props { patientId: number; encounterId?: number; title: string }

export default function DocumentDigitizer({ patientId, encounterId, title }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [res, setRes] = useState<Digitized | null>(null);
  const [labs, setLabs] = useState<Lab[]>([]);
  const [meds, setMeds] = useState<Med[]>([]);
  const [date, setDate] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const run = async (e: React.FormEvent) => {
    e.preventDefault(); if (!file) return; setBusy(true); setErr(null); setMsg(null);
    try {
      const r = await upload<Digitized>("/documents/digitize", { file, patient_id: String(patientId), encounter_id: encounterId != null ? String(encounterId) : undefined });
      setRes(r); setLabs(r.extracted.labs); setMeds(r.extracted.medications); setDate(r.extracted.document_date || "");
    } catch (ex) { setErr((ex as Error).message); } finally { setBusy(false); }
  };
  const confirm = async () => {
    setErr(null);
    try {
      const r = await post<{ labs: number; medications: number }>("/documents/confirm", { patient_id: patientId, encounter_id: encounterId ?? null, labs, medications: meds, document_date: date || null });
      setMsg(`${r.labs} lab value(s) and ${r.medications} medication(s) added to the chart.`); setRes(null); setFile(null);
    } catch (ex) { setErr((ex as Error).message); }
  };

  return (
    <section className="card space-y-3">
      <h3 className="serif text-lg">{title}</h3>
      <form onSubmit={run} className="flex flex-wrap items-end gap-2">
        <input className="input w-auto" type="file" accept=".pdf,image/*,.txt" onChange={(e) => setFile(e.target.files?.[0] || null)} required />
        <button className="btn-primary" disabled={!file || busy}>{busy ? "Reading…" : "Digitize"}</button>
      </form>
      {err && <p className="text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
      {msg && <p className="text-sm" style={{ color: "#4A6B3A" }}>{msg}</p>}
      {res && (
        <div className="space-y-3 text-sm">
          <p className="text-xs muted">OCR via {res.ocr.provider}{res.ocr.mocked && <span className="badge badge-amber ml-1">MOCKED OCR</span>} · type <span className="badge">{res.extracted.type}</span> · confidence <span className="mono">{res.extracted.confidence}</span></p>
          <label className="block"><span className="label">Document date</span><input className="input w-auto" type="date" value={date} onChange={(e) => setDate(e.target.value)} /></label>
          <div>
            <p className="label">Lab values</p>
            {labs.length === 0 && <p className="muted">None found.</p>}
            {labs.map((l, i) => (
              <div key={i} className="mb-1 flex items-center gap-1">
                <input className="input mono w-40" value={l.test} onChange={(e) => setLabs(labs.map((x, j) => (j === i ? { ...x, test: e.target.value } : x)))} />
                <input className="input mono w-24" value={String(l.value)} onChange={(e) => setLabs(labs.map((x, j) => (j === i ? { ...x, value: e.target.value } : x)))} />
                <span className="muted w-16">{l.unit}</span>
                {l.flag && <span className={`badge ${l.flag === "HIGH" ? "badge-red" : "badge-amber"}`}>{l.flag}</span>}
                <button className="btn-ghost px-1 py-0.5" onClick={() => setLabs(labs.filter((_, j) => j !== i))} aria-label="Remove"><IconX size={12} /></button>
              </div>
            ))}
          </div>
          <div>
            <p className="label">Medications</p>
            {meds.length === 0 && <p className="muted">None found.</p>}
            {meds.map((m, i) => (
              <div key={i} className="mb-1 flex items-center gap-1">
                <input className="input w-40" value={m.name} onChange={(e) => setMeds(meds.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)))} />
                <input className="input w-20" value={m.dose} onChange={(e) => setMeds(meds.map((x, j) => (j === i ? { ...x, dose: e.target.value } : x)))} placeholder="dose" />
                <input className="input w-28" value={m.frequency || ""} onChange={(e) => setMeds(meds.map((x, j) => (j === i ? { ...x, frequency: e.target.value } : x)))} placeholder="frequency" />
                <input className="input mono w-16" type="number" value={m.duration_days ?? ""} onChange={(e) => setMeds(meds.map((x, j) => (j === i ? { ...x, duration_days: e.target.value ? Number(e.target.value) : null } : x)))} placeholder="days" />
                <button className="btn-ghost px-1 py-0.5" onClick={() => setMeds(meds.filter((_, j) => j !== i))} aria-label="Remove"><IconX size={12} /></button>
              </div>
            ))}
          </div>
          {res.ocr.text && <details className="text-xs"><summary className="cursor-pointer muted">Raw text</summary><pre className="mono mt-1 max-h-40 overflow-auto border p-2 hr">{res.ocr.text}</pre></details>}
          <button className="btn-primary" onClick={confirm}>Confirm into chart</button>
        </div>
      )}
    </section>
  );
}

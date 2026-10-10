"use client";
import Link from "next/link";
import { useState } from "react";
import { patch, post } from "@/lib/api";
import { IconPrint } from "@/components/icons";

interface Props {
  encounterId: number;
  summary: string;
  notes: string;
  onSummaryChange: (v: string) => void;
  onNotesChange: (v: string) => void;
  hasPrescription: boolean;
  statusMessage: string | null;
  onSaved: (msg: string) => void;
}

export default function SummaryNotesCard({ encounterId, summary, notes, onSummaryChange, onNotesChange, hasPrescription, statusMessage, onSaved }: Props) {
  const [bundle, setBundle] = useState<Record<string, unknown> | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const save = async () => {
    setErr(null);
    try { await patch(`/encounters/${encounterId}`, { summary, clinical_notes: notes }); onSaved("Summary & notes saved"); } catch (e) { setErr((e as Error).message); }
  };
  const fhir = async () => {
    setErr(null);
    try { setBundle(await post<Record<string, unknown>>(`/fhir/generate-bundle/${encounterId}`)); onSaved("FHIR bundle generated"); } catch (e) { setErr((e as Error).message); }
  };

  return (
    <section className="card space-y-2">
      <h3 className="serif text-lg">Summary & clinical notes</h3>
      <label className="block text-sm"><span className="label">Summary (patient-facing)</span>
        <textarea className="input" rows={3} value={summary} onChange={(e) => onSummaryChange(e.target.value)} /></label>
      <label className="block text-sm"><span className="label">Clinical notes</span>
        <textarea className="input" rows={5} value={notes} onChange={(e) => onNotesChange(e.target.value)} /></label>
      <div className="flex flex-wrap gap-2">
        <button className="btn-primary" onClick={save}>Save</button>
        <button className="btn-ghost" onClick={fhir}>Generate FHIR bundle</button>
        {hasPrescription && <Link className="btn-ghost" href={`/rx/${encounterId}`} target="_blank"><IconPrint size={14} /> Print ℞</Link>}
        <Link className="btn-ghost" href={`/discharge/summary/${encounterId}`}>End consultation → discharge</Link>
      </div>
      {statusMessage && <p className="text-xs muted">{statusMessage}</p>}
      {err && <p className="text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
      {bundle && (
        <details className="text-xs">
          <summary className="cursor-pointer muted">FHIR Bundle {String(bundle.id)} · {(bundle.entry as unknown[])?.length ?? 0} resources</summary>
          <pre className="mono mt-1 max-h-64 overflow-auto border p-2 hr">{JSON.stringify(bundle, null, 2)}</pre>
        </details>
      )}
    </section>
  );
}

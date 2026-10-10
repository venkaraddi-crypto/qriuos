"use client";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { get } from "@/lib/api";
import { IconLeaf, IconPrint } from "@/components/icons";
import type { Encounter } from "@/components/consultation/types";

export default function RxPrint() {
  const { id } = useParams<{ id: string }>();
  const [enc, setEnc] = useState<Encounter | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { get<Encounter>(`/encounters/${id}`).then(setEnc).catch((e) => setErr(e.message)); }, [id]);

  if (err) return <main className="p-6 text-sm" style={{ color: "#A03A2A" }}>{err}</main>;
  if (!enc) return <main className="p-6 muted">Loading…</main>;
  const meds = enc.prescriptions.flatMap((p) => p.medications || []);
  return (
    <main id="main-content" className="mx-auto max-w-2xl p-8">
      <header className="mb-6 flex items-start justify-between border-b pb-4 hr">
        <div>
          <h1 className="serif flex items-center gap-2 text-2xl"><IconLeaf size={24} /> All India Institute of Ayurveda</h1>
          <p className="text-sm muted">OPD prescription · {enc.system}</p>
        </div>
        <button className="btn-ghost no-print" onClick={() => window.print()}><IconPrint size={16} /> Print</button>
      </header>
      <dl className="mb-6 grid grid-cols-2 gap-x-6 gap-y-1 text-sm">
        <dt className="muted">Patient</dt><dd>{enc.patient.name} ({enc.patient.gender || "—"}, {enc.patient.age ?? "—"} y)</dd>
        <dt className="muted">UHID</dt><dd className="mono">{enc.patient.uhid}</dd>
        <dt className="muted">Date</dt><dd className="mono">{enc.timestamp.slice(0, 10)}</dd>
        <dt className="muted">Encounter</dt><dd className="mono">#{enc.id}</dd>
      </dl>
      {enc.diagnoses.length > 0 && (
        <section className="mb-6">
          <h2 className="serif text-lg">Diagnosis</h2>
          <ul className="text-sm">{enc.diagnoses.map((d) => <li key={d.id}><span className="mono">{d.code}</span> — {d.display_term} <span className="muted">({d.code_system})</span></li>)}</ul>
        </section>
      )}
      <section className="mb-6">
        <h2 className="serif text-3xl">℞</h2>
        <table className="w-full text-sm">
          <thead><tr className="border-b hr text-left"><th className="py-1">Medicine</th><th>Dose</th><th>Frequency</th><th>Days</th><th>Qty</th></tr></thead>
          <tbody>{meds.map((m, i) => <tr key={i} className="border-b hr"><td className="py-1">{m.name}</td><td>{m.dose}</td><td>{m.frequency}</td><td className="mono">{m.duration_days}</td><td className="mono">{m.quantity}</td></tr>)}</tbody>
        </table>
      </section>
      {enc.summary && <section className="mb-6"><h2 className="serif text-lg">Advice</h2><p className="text-sm">{enc.summary}</p></section>}
      <footer className="mt-12 text-sm">
        <p className="border-t pt-2 hr">Doctor&apos;s signature</p>
        {enc.fhir_bundle_id && <p className="mono text-xs muted">FHIR {enc.fhir_bundle_id}</p>}
      </footer>
    </main>
  );
}

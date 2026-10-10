"use client";
import { useEffect, useState } from "react";
import { get, post } from "@/lib/api";
import type { DiagnosisRow, TerminologyHit } from "./types";

interface Props { encounterId: number; isAyurveda: boolean; diagnoses: DiagnosisRow[]; onChanged: (rows: DiagnosisRow[]) => void }

export default function DiagnosisCard({ encounterId, isAyurveda, diagnoses, onChanged }: Props) {
  const [q, setQ] = useState("");
  const [system, setSystem] = useState<"namaste" | "biomedicine">(isAyurveda ? "namaste" : "biomedicine");
  const [hits, setHits] = useState<TerminologyHit[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!q.trim()) { setHits([]); return; }
    const id = setTimeout(() => {
      get<TerminologyHit[]>(`/terminology/search?query=${encodeURIComponent(q)}&system=${system}`).then(setHits).catch((e) => setErr(e.message));
    }, 250);
    return () => clearTimeout(id);
  }, [q, system]);

  const add = async (h: TerminologyHit) => {
    setErr(null);
    try {
      const body = h.code_system === "NAMASTE" ? { encounter_id: encounterId, namaste_code: h.code } : { encounter_id: encounterId, biomedicine_code: h.code };
      const r = await post<{ dual_coded: boolean; diagnoses: DiagnosisRow[] }>("/diagnoses", body);
      onChanged(r.diagnoses); setQ(""); setHits([]);
    } catch (e) { setErr((e as Error).message); }
  };

  const badge = (cs: string) => cs === "NAMASTE" ? "badge badge-amber" : cs === "ICD11_TM2" ? "badge" : "badge badge-green";

  return (
    <section className="card space-y-2">
      <h3 className="serif text-lg">Diagnosis (dual-coded)</h3>
      <div className="flex gap-2">
        <select className="input w-auto" value={system} onChange={(e) => setSystem(e.target.value as "namaste" | "biomedicine")} aria-label="Code system">
          <option value="namaste">NAMASTE</option><option value="biomedicine">ICD-11 Biomedicine</option>
        </select>
        <input className="input" placeholder="Search term, synonym or code…" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>
      {hits.length > 0 && (
        <ul className="max-h-40 overflow-y-auto border hr">
          {hits.map((h) => (
            <li key={h.code}><button className="flex w-full justify-between px-2 py-1 text-left text-sm hover:underline" onClick={() => add(h)}>
              <span>{h.term}</span><span className="mono muted">{h.code}</span></button></li>
          ))}
        </ul>
      )}
      <ul className="space-y-1 text-sm">
        {diagnoses.length === 0 && <li className="muted">No diagnosis coded yet.</li>}
        {diagnoses.map((d) => (
          <li key={d.id} className="flex flex-wrap items-center gap-2">
            <span className={badge(d.code_system)}>{d.code_system}</span><span className="mono">{d.code}</span><span>{d.display_term}</span>
            {d.is_primary && <span className="badge">primary</span>}
          </li>
        ))}
      </ul>
      <p className="text-xs muted">Selecting a NAMASTE term records NAMASTE + ICD-11 TM2 + ICD-11 Biomedicine codes together.</p>
      {err && <p className="text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
    </section>
  );
}

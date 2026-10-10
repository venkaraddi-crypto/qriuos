"use client";
import { useEffect, useState } from "react";
import { get, post } from "@/lib/api";

interface Ref {
  grades: { key: string; label: string; score: number }[];
  parameters: { key: string; label: string; description: string; scored: boolean }[];
  ahara_vihara: { key: string; label: string; type: string; options: string[] }[];
}
interface Result { bala_score: number; bala_label: string; parameters_scored: number; parameters_total: number; advice: string[] }

interface Props {
  encId: number;
  initial?: Record<string, unknown> | null;
  aharaInitial?: Record<string, string> | null;
  prakriti?: string | null;
  vikriti?: string | null;
}

export default function DashavidhaPanel({ encId, initial, aharaInitial, prakriti, vikriti }: Props) {
  const [ref, setRef] = useState<Ref | null>(null);
  const [params, setParams] = useState<Record<string, string>>((initial?.parameters as Record<string, string>) || {});
  const [ahara, setAhara] = useState<Record<string, string>>(aharaInitial || {});
  const [result, setResult] = useState<Result | null>(initial && typeof initial.bala_score === "number" ? (initial as unknown as Result) : null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => { get<Ref>("/ayush/dashavidha/reference").then(setRef).catch((e) => setErr(e.message)); }, []);

  const save = async () => {
    setErr(null);
    try { setResult(await post<Result>("/ayush/dashavidha", { encounter_id: encId, parameters: params, ahara_vihara: ahara })); }
    catch (e) { setErr((e as Error).message); }
  };

  if (!ref) return <p className="text-sm muted">Loading Dashavidha reference…</p>;
  return (
    <div className="space-y-3">
      <h4 className="serif">Dashavidha Pariksha</h4>
      <div className="grid gap-2 md:grid-cols-2">
        {ref.parameters.map((p) => (
          <label key={p.key} className="text-sm">
            <span className="label" title={p.description}>{p.label}</span>
            {p.scored ? (
              <select className="input" value={params[p.key] || ""} onChange={(e) => setParams({ ...params, [p.key]: e.target.value })}>
                <option value="">—</option>
                {ref.grades.map((g) => <option key={g.key} value={g.key}>{g.label}</option>)}
              </select>
            ) : (
              <input className="input" readOnly value={p.key === "prakriti" ? (prakriti || "see Prakriti above") : (vikriti || "see Vikriti above")} />
            )}
          </label>
        ))}
      </div>
      <h4 className="serif">Ahara–Vihara</h4>
      <div className="grid gap-2 md:grid-cols-2">
        {ref.ahara_vihara.map((f) => (
          <label key={f.key} className="text-sm">
            <span className="label">{f.label}</span>
            {f.type === "choice" ? (
              <select className="input" value={ahara[f.key] || ""} onChange={(e) => setAhara({ ...ahara, [f.key]: e.target.value })}>
                <option value="">—</option>{f.options.map((o) => <option key={o}>{o}</option>)}
              </select>
            ) : <input className="input" value={ahara[f.key] || ""} onChange={(e) => setAhara({ ...ahara, [f.key]: e.target.value })} />}
          </label>
        ))}
      </div>
      <div className="flex items-center gap-3">
        <button className="btn-primary" onClick={save}>Assess Bala</button>
        {result && <span className="text-sm">Bala <span className="mono">{result.bala_score}</span> — <strong>{result.bala_label}</strong> ({result.parameters_scored}/{result.parameters_total})</span>}
      </div>
      {result && result.advice.length > 0 && <ul className="list-disc pl-5 text-sm">{result.advice.map((a) => <li key={a}>{a}</li>)}</ul>}
      {err && <p className="text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
    </div>
  );
}

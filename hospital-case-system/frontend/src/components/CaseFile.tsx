"use client";
import { useEffect, useState } from "react";
import { get } from "@/lib/api";

interface Event { type: string; date: string | null; [k: string]: unknown }
interface File { patient: { name: string; uhid: string; gender: string | null; age: number | null; abha_id: string | null }; events: Event[] }
const TYPES = ["APPOINTMENT", "ENCOUNTER", "VITALS", "PRESCRIPTION", "LAB", "BILL", "DISCHARGE", "REFERRAL", "THERAPY"];
type Med = { name: string; dose?: string; frequency?: string; duration_days?: number };
type Dx = { code_system: string; code: string; term: string };

function Body({ e }: { e: Event }) {
  const s = (k: string) => (e[k] == null ? "" : String(e[k]));
  switch (e.type) {
    case "APPOINTMENT": return <p><span className="badge">{s("status")}</span> token <span className="mono">{s("token")}</span> · {s("system")} · {s("chief_complaint") || "—"}</p>;
    case "VITALS": return <p className="mono">{s("bp")} · {s("pulse")} bpm · {s("temp")}°F · {s("weight")} kg</p>;
    case "ENCOUNTER": return (
      <div><p>{s("summary") || "—"}</p>
        <p className="mt-1 flex flex-wrap gap-1">{((e.diagnoses as Dx[]) || []).map((d) => <span key={d.code} className={`badge ${d.code_system === "NAMASTE" ? "badge-amber" : ""}`}>{d.code} {d.term}</span>)}</p></div>);
    case "PRESCRIPTION": return (
      <table className="text-xs"><tbody>{((e.medications as Med[]) || []).map((m, i) => <tr key={i}><td className="pr-3">{m.name}</td><td className="pr-3">{m.dose}</td><td className="pr-3">{m.frequency}</td><td className="mono">{m.duration_days} d</td></tr>)}</tbody></table>);
    case "LAB": return (
      <p>{s("test_name")} <span className="badge">{s("status")}</span> {Boolean(e.flagged_abnormal) && <span className="badge badge-red">ABNORMAL</span>}
        {e.result_values ? <span className="mono ml-2 text-xs">{Object.entries(e.result_values as Record<string, unknown>).map(([k, v]) => `${k}=${String(v)}`).join(" · ")}</span> : null}</p>);
    case "BILL": return <p><span className="mono">₹{Number(e.total_amount).toFixed(2)}</span> <span className={`badge ${s("payment_status") === "PAID" ? "badge-green" : "badge-amber"}`}>{s("payment_status")}</span></p>;
    case "DISCHARGE": return <p>{s("instructions") || "—"} {e.follow_up_date ? <span className="muted">· follow-up {s("follow_up_date")}</span> : null}</p>;
    case "REFERRAL": return <p><span className="badge">{s("kind")}</span> {s("status")} {s("note")}</p>;
    case "THERAPY": return <p>{s("therapy_name")} <span className="badge">{s("status")}</span></p>;
    default: return null;
  }
}

export default function CaseFile({ patientId }: { patientId: number }) {
  const [f, setF] = useState<File | null>(null);
  const [filter, setFilter] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { get<File>(`/case-file/${patientId}`).then(setF).catch((e) => setErr(e.message)); }, [patientId]);

  if (err) return <p className="text-sm" style={{ color: "#A03A2A" }}>{err}</p>;
  if (!f) return <p className="muted">Loading case file…</p>;
  const events = f.events.filter((e) => !filter || e.type === filter);
  return (
    <div className="space-y-3">
      <section className="card">
        <h2 className="serif text-2xl">{f.patient.name}</h2>
        <p className="text-sm muted"><span className="mono">{f.patient.uhid}</span> · {f.patient.gender || "—"} · {f.patient.age ?? "—"} y{f.patient.abha_id && <> · ABHA <span className="mono">{f.patient.abha_id}</span></>}</p>
      </section>
      <div className="flex flex-wrap gap-1 text-xs">
        <button className={`badge ${filter === null ? "badge-amber" : ""}`} onClick={() => setFilter(null)}>All ({f.events.length})</button>
        {TYPES.map((t) => { const n = f.events.filter((e) => e.type === t).length; return n ? <button key={t} className={`badge ${filter === t ? "badge-amber" : ""}`} onClick={() => setFilter(t)}>{t} ({n})</button> : null; })}
      </div>
      <ol className="space-y-2 border-l pl-4 hr">
        {events.map((e, i) => (
          <li key={i} className="card text-sm">
            <p className="mb-1 flex items-center gap-2"><span className="mono text-xs muted">{(e.date || "").slice(0, 10)}</span><span className="badge">{e.type}</span></p>
            <Body e={e} />
          </li>
        ))}
      </ol>
    </div>
  );
}

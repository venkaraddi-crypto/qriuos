"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { get, put } from "@/lib/api";
import { IconLock } from "@/components/icons";

interface Audit { id: number; actor: string | null; role: string | null; action: string; target_record: string | null; timestamp: string }
interface Policy { raw_audio_retention_days: number; updated_at: string | null }

export default function SecurityPage() {
  const [log, setLog] = useState<Audit[]>([]);
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [days, setDays] = useState(30);
  const [filter, setFilter] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    get<Audit[]>("/audit-log?limit=200").then(setLog).catch((e) => setErr(e.message));
    get<Policy>("/admin/retention-policy").then((p) => { setPolicy(p); setDays(p.raw_audio_retention_days); }).catch(() => {});
  }, []);

  const savePolicy = async () => {
    setErr(null);
    try { const p = await put<Policy>("/admin/retention-policy", { raw_audio_retention_days: days }); setPolicy(p); setMsg("Retention policy updated"); } catch (e) { setErr((e as Error).message); }
  };

  const shown = log.filter((a) => !filter || a.action.toLowerCase().includes(filter.toLowerCase()) || (a.actor || "").toLowerCase().includes(filter.toLowerCase()));

  return (
    <Shell portal="staff" title="Security & audit">
      {err && <p className="mb-2 text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
      <div className="grid gap-4 md:grid-cols-[1fr_2fr]">
        <section className="card space-y-3">
          <h3 className="serif flex items-center gap-2"><IconLock size={18} /> Data retention</h3>
          <p className="text-sm muted">Raw consultation audio is purged on startup once older than this; transcripts are kept.</p>
          <label className="block text-sm"><span className="label">Raw audio retention (days)</span>
            <input className="input w-32" type="number" min={1} max={365} value={days} onChange={(e) => setDays(Number(e.target.value))} /></label>
          <button className="btn-primary" onClick={savePolicy}>Save</button>
          {policy?.updated_at && <p className="text-xs muted">Last updated {policy.updated_at.slice(0, 16).replace("T", " ")}</p>}
          {msg && <p className="text-xs muted">{msg}</p>}
          <ul className="mt-2 space-y-1 text-xs muted">
            <li>JWT access tokens (12 h) + rotating HTTP-only refresh cookie</li>
            <li>Aadhaar encrypted at rest, masked in every API response</li>
            <li>Medical Drive blobs Fernet-encrypted; downloads audited</li>
            <li>Role gates on every endpoint; patients only see their own records</li>
          </ul>
        </section>
        <section className="card">
          <div className="flex items-center justify-between gap-2">
            <h3 className="serif">Audit log</h3>
            <input className="input w-48" placeholder="Filter action / actor" value={filter} onChange={(e) => setFilter(e.target.value)} />
          </div>
          <div className="mt-2 max-h-[70vh] overflow-auto">
            <table className="w-full text-xs">
              <thead><tr className="border-b hr text-left"><th className="py-1">When</th><th>Actor</th><th>Action</th><th>Target</th></tr></thead>
              <tbody>
                {shown.map((a) => (
                  <tr key={a.id} className="border-b hr">
                    <td className="mono py-1">{a.timestamp.slice(0, 19).replace("T", " ")}</td>
                    <td>{a.actor || "—"} <span className="muted">{a.role || ""}</span></td>
                    <td><span className="badge">{a.action}</span></td>
                    <td className="mono muted">{a.target_record || ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </Shell>
  );
}

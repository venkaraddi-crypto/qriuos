"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import CameraScanner from "@/components/CameraScanner";
import { get, post } from "@/lib/api";
import TherapyPanel from "./TherapyPanel";

interface Appt { id: number; patient_name: string; uhid: string; token_number: string; doctor_name: string; status: string; vitals_missing?: boolean; vitals?: { bp: string | null; pulse: number | null; temp: number | null; weight: number | null } | null }
const EMPTY = { bp: "", pulse: "", temp: "", weight: "" };

export default function NurseVitals() {
  const [board, setBoard] = useState<Appt[]>([]);
  const [target, setTarget] = useState<Appt | null>(null);
  const [v, setV] = useState(EMPTY);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = () => get<Appt[]>("/nurse/today").then(setBoard).catch((e) => setErr(e.message));
  useEffect(() => { void load(); }, []);

  const scan = async (code: string) => { try { setTarget(await post<Appt>("/qr/lookup", { code })); setErr(null); } catch (e) { setErr((e as Error).message); } };
  const save = async (e: React.FormEvent) => {
    e.preventDefault(); if (!target) return; setErr(null);
    try {
      await post(`/nurse/vitals/${target.id}`, { bp: v.bp || null, pulse: v.pulse ? Number(v.pulse) : null, temp: v.temp ? Number(v.temp) : null, weight: v.weight ? Number(v.weight) : null });
      setMsg(`Vitals saved for ${target.patient_name}`); setV(EMPTY); setTarget(null); void load();
    } catch (ex) { setErr((ex as Error).message); }
  };

  return (
    <Shell portal="staff" title="Vitals & therapy">
      {err && <p className="mb-2 text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
      {msg && <p className="mb-2 text-xs muted">{msg}</p>}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-4">
          <CameraScanner onScan={scan} label="Scan patient QR" />
          {target && (
            <form onSubmit={save} className="card space-y-2">
              <h3 className="serif">{target.patient_name} <span className="mono text-sm muted">{target.uhid}</span> · Token <span className="mono">{target.token_number}</span></h3>
              <div className="grid grid-cols-2 gap-2">
                <input className="input mono" placeholder="BP (120/80)" value={v.bp} onChange={(e) => setV({ ...v, bp: e.target.value })} />
                <input className="input mono" type="number" placeholder="Pulse /min" value={v.pulse} onChange={(e) => setV({ ...v, pulse: e.target.value })} />
                <input className="input mono" type="number" step="0.1" placeholder="Temp °F" value={v.temp} onChange={(e) => setV({ ...v, temp: e.target.value })} />
                <input className="input mono" type="number" step="0.1" placeholder="Weight kg" value={v.weight} onChange={(e) => setV({ ...v, weight: e.target.value })} />
              </div>
              <div className="flex gap-2"><button className="btn-primary">Save vitals</button><button type="button" className="btn-ghost" onClick={() => setTarget(null)}>Cancel</button></div>
            </form>
          )}
          <section className="card">
            <h3 className="serif">Today&apos;s board</h3>
            {board.length === 0 && <p className="text-sm muted">No checked-in patients.</p>}
            <ul className="text-sm">
              {board.map((a) => (
                <li key={a.id} className="flex items-center justify-between border-b py-1 hr">
                  <button className="text-left hover:underline" onClick={() => setTarget(a)}><span className="mono">{a.token_number}</span> {a.patient_name} <span className="muted">{a.uhid}</span></button>
                  {a.vitals_missing ? <span className="badge badge-red">VITALS MISSING</span> : <span className="mono text-xs">{a.vitals?.bp} · {a.vitals?.pulse} bpm</span>}
                </li>
              ))}
            </ul>
          </section>
        </div>
        <TherapyPanel onMessage={setMsg} />
      </div>
    </Shell>
  );
}

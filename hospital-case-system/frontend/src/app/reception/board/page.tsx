"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { get, post } from "@/lib/api";

interface Appt { id: number; patient_name: string; uhid: string; token_number: string; doctor_name: string; slot_time: string; date: string; status: string; red_flag: boolean }
interface Board { checked_in: Appt[]; upcoming: Appt[]; date: string }

function Row({ a, actions }: { a: Appt; actions?: React.ReactNode }) {
  return (
    <li className="flex flex-wrap items-center justify-between gap-2 border-b py-1.5 text-sm hr">
      <span className="flex items-center gap-2">
        <span className={`mono text-lg ${a.token_number === "E" ? "badge-red badge" : ""}`}>{a.token_number}</span>
        <span>{a.patient_name} <span className="muted">{a.uhid}</span></span>
        {a.red_flag && <span className="badge badge-red">RED FLAG</span>}
      </span>
      <span className="flex items-center gap-2">
        <span className="muted">{a.doctor_name}</span><span className="mono">{a.date.slice(5)} {a.slot_time}</span><span className="badge">{a.status}</span>{actions}
      </span>
    </li>
  );
}

export default function BoardPage() {
  const [b, setB] = useState<Board | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const load = () => get<Board>("/reception/board").then(setB).catch((e) => setErr(e.message));
  useEffect(() => { load(); const id = setInterval(load, 10000); return () => clearInterval(id); }, []);
  const act = async (id: number, action: "NO_SHOW" | "CANCEL") => { try { await post("/reception/process", { appointment_id: id, action }); load(); } catch (e) { setErr((e as Error).message); } };

  return (
    <Shell portal="staff" title="Reception board">
      {err && <p className="mb-2 text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
      <p className="mb-2 text-xs muted">Auto-refreshes every 10 s · {b?.date}</p>
      <div className="grid gap-4 md:grid-cols-2">
        <section className="card"><h3 className="serif">Checked in ({b?.checked_in.length ?? 0})</h3>
          <ul>{b?.checked_in.map((a) => <Row key={a.id} a={a} />)}</ul></section>
        <section className="card"><h3 className="serif">Upcoming ({b?.upcoming.length ?? 0})</h3>
          <ul>{b?.upcoming.map((a) => <Row key={a.id} a={a} actions={<><button className="btn-ghost px-2 py-0.5 text-xs" onClick={() => act(a.id, "NO_SHOW")}>No-show</button><button className="btn-ghost px-2 py-0.5 text-xs" onClick={() => act(a.id, "CANCEL")}>Cancel</button></>} />)}</ul></section>
      </div>
    </Shell>
  );
}

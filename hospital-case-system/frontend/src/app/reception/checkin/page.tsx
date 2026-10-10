"use client";
import { useState } from "react";
import Shell from "@/components/Shell";
import CameraScanner from "@/components/CameraScanner";
import { post } from "@/lib/api";
import { IconCheck } from "@/components/icons";

interface Appt { id: number; patient_name: string; uhid: string; token_number: string; doctor_name: string; department: string; status: string; red_flag: boolean; slot_time: string }
type Result = { kind: "ok"; appt: Appt } | { kind: "warn" | "err"; text: string };

export default function Checkin() {
  const [result, setResult] = useState<Result | null>(null);
  const [recent, setRecent] = useState<Appt[]>([]);

  const scan = async (code: string) => {
    try {
      const a = await post<Appt>("/reception/scan", { code });
      setResult({ kind: "ok", appt: a });
      setRecent((r) => [a, ...r].slice(0, 5));
    } catch (e) {
      const m = (e as Error).message;
      setResult({ kind: /already/i.test(m) ? "warn" : "err", text: m });
    }
  };

  return (
    <Shell portal="staff" title="Scan check-in">
      <div className="grid gap-4 md:grid-cols-2">
        <CameraScanner onScan={scan} label="Scan appointment QR" />
        <div className="space-y-3">
          {result?.kind === "ok" && (
            <div className="card" style={{ borderColor: "#4A6B3A", background: "#EDF3E6" }}>
              <p className="flex items-center gap-2 text-sm" style={{ color: "#4A6B3A" }}><IconCheck size={18} /> Checked in</p>
              <h2 className="serif text-2xl">{result.appt.patient_name}</h2>
              <p className="mono text-sm">{result.appt.uhid}</p>
              <p className="text-sm">{result.appt.doctor_name} — {result.appt.department} · {result.appt.slot_time}</p>
              <p className="mt-1">Token <span className="mono text-3xl">{result.appt.token_number}</span> {result.appt.red_flag && <span className="badge badge-red ml-2">RED FLAG</span>}</p>
            </div>
          )}
          {result?.kind === "warn" && <div className="card"><span className="badge badge-amber">Already checked in</span> <span className="text-sm muted">{result.text}</span></div>}
          {result?.kind === "err" && <div className="card"><span className="badge badge-red">Rejected</span> <span className="text-sm">{result.text}</span></div>}
          {recent.length > 0 && (
            <section className="card">
              <h3 className="serif">Recent check-ins</h3>
              <ul className="text-sm">{recent.map((a, i) => <li key={`${a.id}-${i}`} className="flex justify-between border-b py-1 hr"><span>{a.patient_name} <span className="muted">{a.uhid}</span></span><span className="mono">#{a.token_number}</span></li>)}</ul>
            </section>
          )}
          <p className="text-xs muted">Scanning is the only check-in path; forged or unknown codes are rejected.</p>
        </div>
      </div>
    </Shell>
  );
}

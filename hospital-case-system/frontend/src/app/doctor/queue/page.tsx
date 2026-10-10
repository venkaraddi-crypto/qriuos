"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import CameraScanner from "@/components/CameraScanner";
import { get, patch, post } from "@/lib/api";

interface Appt { id: number; patient_name: string; uhid: string; token_number: string; chief_complaint: string | null; slot_time: string; status: string; red_flag: boolean; system: string; encounter_id: number | null }

export default function QueuePage() {
  const router = useRouter();
  const [q, setQ] = useState<Appt[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const load = () => get<Appt[]>("/queue").then(setQ).catch((e) => setErr(e.message));
  useEffect(() => { load(); const id = setInterval(load, 10000); return () => clearInterval(id); }, []);

  const callIn = async (id: number) => {
    try { const r = await patch<{ encounter_id: number }>(`/queue/${id}/call-next`); router.push(`/doctor/consultation/${r.encounter_id}`); } catch (e) { setErr((e as Error).message); }
  };
  const act = async (id: number, what: "skip" | "no-show") => { try { await patch(`/queue/${id}/${what}`); load(); } catch (e) { setErr((e as Error).message); } };
  const scan = async (code: string) => {
    try {
      const a = await post<Appt>("/qr/lookup", { code });
      if (q.some((x) => x.id === a.id) || a.status === "CHECKED_IN" || a.status === "IN_CONSULTATION") await callIn(a.id);
      else setErr(`Patient ${a.patient_name} is ${a.status}, not in your queue.`);
    } catch (e) { setErr((e as Error).message); }
  };
  const tint = q[0]?.system === "AYURVEDA" ? "ayu" : "allo";

  return (
    <Shell portal="staff" title="Today's queue" tint={tint}>
      {err && <p className="mb-2 text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
      <div className="grid gap-4 md:grid-cols-[2fr_1fr]">
        <section className="card">
          <h3 className="serif">Waiting ({q.length})</h3>
          {q.length === 0 && <p className="text-sm muted">No checked-in patients.</p>}
          <ul>
            {q.map((a, i) => (
              <li key={a.id} className="flex flex-wrap items-center justify-between gap-2 border-b py-2 hr">
                <span className="flex items-center gap-3">
                  <span className={`mono text-2xl ${a.token_number === "E" ? "badge badge-red" : ""}`}>{a.token_number}</span>
                  <span>
                    <span className="font-medium">{a.patient_name}</span> <span className="mono text-xs muted">{a.uhid}</span>
                    {a.red_flag && <span className="badge badge-red ml-2">RED FLAG</span>}
                    {a.status === "IN_CONSULTATION" && <span className="badge badge-amber ml-2">in consultation</span>}
                    <br /><span className="text-sm muted">{a.chief_complaint || "—"}</span>
                  </span>
                </span>
                <span className="flex gap-1">
                  <button className={i === 0 ? "btn-primary" : "btn-ghost"} onClick={() => callIn(a.id)}>{a.encounter_id ? "Resume" : "Call in"}</button>
                  <button className="btn-ghost" onClick={() => act(a.id, "skip")}>Skip</button>
                  <button className="btn-ghost" onClick={() => act(a.id, "no-show")}>No-show</button>
                </span>
              </li>
            ))}
          </ul>
        </section>
        <CameraScanner onScan={scan} label="Scan to consult" />
      </div>
    </Shell>
  );
}

"use client";
import { useEffect, useState } from "react";
import { get, post } from "@/lib/api";
import type { Department, Dispatch } from "./types";

interface Props { encounterId: number; refreshKey: number; onReferred: () => void }

export default function DispatchCard({ encounterId, refreshKey, onReferred }: Props) {
  const [d, setD] = useState<Dispatch | null>(null);
  const [depts, setDepts] = useState<Department[]>([]);
  const [therapy, setTherapy] = useState("Abhyanga + Swedana");
  const [when, setWhen] = useState("");
  const [deptId, setDeptId] = useState<number | "">("");
  const [note, setNote] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const load = () => get<Dispatch>(`/encounters/${encounterId}/dispatch`).then(setD).catch((e) => setErr(e.message));
  useEffect(() => { void load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [encounterId, refreshKey]);
  useEffect(() => { get<Department[]>("/departments").then(setDepts).catch(() => {}); }, []);

  const refer = async (body: Record<string, unknown>) => {
    setErr(null);
    try { await post(`/encounters/${encounterId}/refer`, body); await load(); onReferred(); } catch (e) { setErr((e as Error).message); }
  };

  return (
    <section className="card space-y-3">
      <h3 className="serif text-lg">Dispatch</h3>
      <ol className="space-y-3 text-sm">
        <li className="flex items-center gap-2">
          <span className="badge">1</span> Medicines to pharmacy
          {d?.medicine_to_pharmacy ? <span className="badge badge-green">sent · {d.pharmacy_pending_items} pending</span> : <span className="badge">after prescription</span>}
        </li>
        <li>
          <div className="flex items-center gap-2"><span className="badge">2</span> Treatment to therapy</div>
          <div className="mt-1 flex flex-wrap gap-1">
            <input className="input w-auto" value={therapy} onChange={(e) => setTherapy(e.target.value)} aria-label="Therapy" />
            <input className="input w-auto" type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)} aria-label="When" />
            <button className="btn-ghost" onClick={() => refer({ kind: "THERAPY", therapy_name: therapy, scheduled_at: when ? new Date(when).toISOString() : null })}>Refer</button>
          </div>
          {d?.treatment_to_therapy.map((t) => <p key={t.id} className="muted">{t.therapy?.name} · {t.therapy?.scheduled_at?.slice(0, 16).replace("T", " ")} · {t.therapy?.status}</p>)}
        </li>
        <li>
          <div className="flex items-center gap-2"><span className="badge">3</span> File to department</div>
          <div className="mt-1 flex flex-wrap gap-1">
            <select className="input w-auto" value={deptId} onChange={(e) => setDeptId(e.target.value ? Number(e.target.value) : "")} aria-label="Department">
              <option value="">Department…</option>{depts.map((x) => <option key={x.id} value={x.id}>{x.name} ({x.system})</option>)}
            </select>
            <input className="input w-auto" placeholder="Note" value={note} onChange={(e) => setNote(e.target.value)} />
            <button className="btn-ghost" disabled={deptId === ""} onClick={() => refer({ kind: "DEPARTMENT", department_id: deptId, note })}>Refer</button>
          </div>
          {d?.file_to_departments.map((f) => <p key={f.id} className="muted">{f.department} · <span className="badge">{f.status}</span>{f.new_appointment_id ? ` · appt #${f.new_appointment_id}` : ""}</p>)}
        </li>
      </ol>
      {err && <p className="text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
    </section>
  );
}

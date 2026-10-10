"use client";
import Link from "next/link";
import QRCode from "qrcode";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { get, patch } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

interface Appt { id: number; doctor_id: number; date: string; slot_time: string; doctor_name: string; department: string; token_number: string; status: string; red_flag: boolean; qr_code: string; system: string; type: string }
interface Slot { id: number; start_time: string; available: number }

function days(n: number) { return Array.from({ length: n }, (_, i) => { const d = new Date(); d.setDate(d.getDate() + i); return d.toISOString().slice(0, 10); }); }

export default function MyAppointments() {
  const { t } = useI18n();
  const [rows, setRows] = useState<Appt[]>([]);
  const [qrs, setQrs] = useState<Record<number, string>>({});
  const [resched, setResched] = useState<Appt | null>(null);
  const [day, setDay] = useState(days(1)[0]);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [err, setErr] = useState<string | null>(null);

  const load = () => get<Appt[]>("/appointments/me").then(async (a) => { setRows(a); const m: Record<number, string> = {}; for (const x of a) m[x.id] = await QRCode.toDataURL(x.qr_code, { margin: 0, width: 120 }); setQrs(m); }).catch((e) => setErr(e.message));
  useEffect(() => { void load(); }, []);
  useEffect(() => { if (resched) get<Slot[]>(`/doctors/${resched.doctor_id}/slots?date=${day}`).then(setSlots).catch(() => setSlots([])); }, [resched, day]);

  const cancel = async (id: number) => { if (!confirm("Cancel this appointment?")) return; try { await patch(`/appointments/${id}/cancel`); void load(); } catch (e) { setErr((e as Error).message); } };
  const doResched = async (slotId: number) => { if (!resched) return; try { await patch(`/appointments/${resched.id}/reschedule`, { slot_id: slotId }); setResched(null); void load(); } catch (e) { setErr((e as Error).message); } };

  return (
    <Shell portal="patient" title={t("my_appointments")}>
      {err && <p className="mb-2 text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
      {resched && (
        <div className="card mb-4 space-y-2" role="dialog" aria-label="Reschedule">
          <h3 className="serif">Reschedule — {resched.doctor_name}</h3>
          <div className="flex flex-wrap gap-1">{days(7).map((d) => <button key={d} className={`badge ${day === d ? "badge-amber" : ""}`} onClick={() => setDay(d)}>{d.slice(5)}</button>)}</div>
          <div className="flex flex-wrap gap-1">{slots.length === 0 ? <span className="text-sm muted">No slots</span> : slots.map((s) => <button key={s.id} disabled={s.available <= 0} className="btn-ghost mono" onClick={() => doResched(s.id)}>{s.start_time} ({s.available})</button>)}</div>
          <button className="btn-ghost" onClick={() => setResched(null)}>{t("cancel")}</button>
        </div>
      )}
      <div className="grid gap-3 md:grid-cols-2">
        {rows.length === 0 && <p className="muted">No appointments yet.</p>}
        {rows.map((a) => (
          <div key={a.id} className={`card flex gap-3 ${a.system === "AYURVEDA" ? "tint-ayu" : "tint-allo"}`}>
            {qrs[a.id] && <img src={qrs[a.id]} alt="QR" width={96} height={96} className="shrink-0 self-start" />}
            <div className="flex-1 text-sm">
              <p className="mono">{a.date} · {a.slot_time}</p>
              <p className="font-medium">{a.doctor_name}</p>
              <p className="muted">{a.department} · {a.type}</p>
              <p className="mt-1">{t("token")} <span className="mono text-xl">{a.token_number}</span> <span className="badge ml-2">{a.status}</span> {a.red_flag && <span className="badge badge-red ml-1">RED FLAG</span>}</p>
              <div className="mt-2 flex flex-wrap gap-1">
                <Link className="btn-ghost px-2 py-0.5 text-xs" href={`/patient/slip/${a.id}`}>Print slip</Link>
                {(a.status === "BOOKED" || a.status === "CHECKED_IN") && <Link className="btn-ghost px-2 py-0.5 text-xs" href={`/intake/${a.id}`}>Pre-consult intake</Link>}
                {a.status === "BOOKED" && <><button className="btn-ghost px-2 py-0.5 text-xs" onClick={() => setResched(a)}>Reschedule</button><button className="btn-ghost px-2 py-0.5 text-xs" onClick={() => cancel(a.id)}>{t("cancel")}</button></>}
              </div>
            </div>
          </div>
        ))}
      </div>
    </Shell>
  );
}

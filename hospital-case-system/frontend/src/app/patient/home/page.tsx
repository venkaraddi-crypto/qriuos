"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { get } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { IconAlert, IconBell, IconCalendar, IconFile } from "@/components/icons";

interface Summary {
  patient: { name: string; uhid: string; abha_id: string | null };
  next_appointment: { id: number; date: string; slot_time: string; token_number: string; status: string; doctor_name: string; department: string; system: string } | null;
  total_visits: number;
  pending_bills: number;
  pending_amount: number;
}
interface Note { id: number; message: string; created_at: string; read: boolean }

export default function PatientHome() {
  const { t } = useI18n();
  const [s, setS] = useState<Summary | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    const load = () => {
      get<Summary>("/patients/me/summary").then(setS).catch((e) => setErr(e.message));
      get<Note[]>("/notifications/me").then(setNotes).catch(() => {});
    };
    load();
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, []);

  const turn = notes.find((n) => !n.read && /your turn/i.test(n.message));

  return (
    <Shell portal="patient" title={t("home")}>
      {err && <p className="text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
      {turn && (
        <div className="card mb-4 flex items-center gap-3" style={{ borderColor: "#4A6B3A", background: "#EDF3E6", color: "#4A6B3A" }}>
          <IconAlert /> <strong>{t("your_turn")}</strong> — {turn.message}
        </div>
      )}
      {s && (
        <div className="grid gap-4 md:grid-cols-2">
          <section className="card">
            <h2 className="serif text-xl">{t("welcome")}, {s.patient.name}</h2>
            <p className="mono text-sm muted">{s.patient.uhid}{s.patient.abha_id ? ` · ABHA ${s.patient.abha_id}` : ""}</p>
            <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
              <dt className="muted">Total visits</dt><dd className="mono">{s.total_visits}</dd>
              <dt className="muted">Pending bills</dt><dd className="mono">{s.pending_bills} (₹{s.pending_amount.toFixed(2)})</dd>
            </dl>
          </section>
          <section className={`card ${s.next_appointment?.system === "AYURVEDA" ? "tint-ayu" : "tint-allo"}`}>
            <h2 className="serif text-lg flex items-center gap-2"><IconCalendar size={18} /> {t("next_appointment")}</h2>
            {s.next_appointment ? (
              <div className="mt-2 space-y-1 text-sm">
                <p>{s.next_appointment.date} · <span className="mono">{s.next_appointment.slot_time}</span></p>
                <p>{s.next_appointment.doctor_name} — {s.next_appointment.department}</p>
                <p>{t("token")} <span className="mono text-xl">{s.next_appointment.token_number}</span> <span className="badge ml-2">{s.next_appointment.status}</span></p>
                <div className="flex gap-2 pt-2">
                  <Link className="btn-ghost" href={`/patient/slip/${s.next_appointment.id}`}>OPD slip & QR</Link>
                  {s.next_appointment.status === "BOOKED" && <Link className="btn-primary" href={`/intake/${s.next_appointment.id}`}>Pre-consult intake</Link>}
                </div>
              </div>
            ) : (
              <p className="mt-2 text-sm muted">No upcoming appointment. <Link className="underline" href="/patient/book-appointment">Book one</Link>.</p>
            )}
          </section>
          <section className="card md:col-span-2">
            <h2 className="serif text-lg">Quick links</h2>
            <div className="mt-2 flex flex-wrap gap-2">
              <Link className="btn-ghost" href="/patient/book-appointment"><IconCalendar size={16} /> {t("book_appointment")}</Link>
              <Link className="btn-ghost" href="/patient/my-records"><IconFile size={16} /> {t("my_records")}</Link>
              <Link className="btn-ghost" href="/patient/notifications"><IconBell size={16} /> {t("notifications")} {notes.filter((n) => !n.read).length > 0 && <span className="badge badge-amber">{notes.filter((n) => !n.read).length}</span>}</Link>
            </div>
          </section>
        </div>
      )}
    </Shell>
  );
}

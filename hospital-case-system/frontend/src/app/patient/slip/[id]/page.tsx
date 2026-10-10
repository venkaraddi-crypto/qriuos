"use client";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import QRCode from "qrcode";
import { useEffect, useState } from "react";
import { get } from "@/lib/api";
import { IconLeaf, IconPrint } from "@/components/icons";

interface Appt { id: number; patient_name: string; uhid: string; date: string; slot_time: string; doctor_name: string; department: string; token_number: string; qr_code: string; status: string; system: string }

export default function Slip() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [a, setA] = useState<Appt | null>(null);
  const [qr, setQr] = useState("");
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!localStorage.getItem("arogya_token")) { router.replace("/login"); return; }
    get<Appt[]>("/appointments/me").then((rows) => {
      const x = rows.find((r) => r.id === Number(id));
      if (!x) { setErr("Appointment not found"); return; }
      setA(x);
      QRCode.toDataURL(x.qr_code, { margin: 1, width: 220 }).then(setQr);
    }).catch((e) => setErr(e.message));
  }, [id, router]);

  if (err) return <main className="p-6 text-sm" style={{ color: "#A03A2A" }}>{err}</main>;
  if (!a) return <main className="p-6 muted">Loading…</main>;
  return (
    <main id="main-content" className="mx-auto max-w-sm p-6 text-center">
      <h1 className="serif flex items-center justify-center gap-2 text-xl"><IconLeaf size={22} /> All India Institute of Ayurveda — OPD</h1>
      <p className="text-xs muted">{a.system} · {a.department}</p>
      <div className="card mt-4 space-y-1">
        <p className="serif text-lg">{a.patient_name}</p>
        <p className="mono text-sm">{a.uhid}</p>
        <p className="text-sm"><span className="mono">{a.date}</span> · <span className="mono">{a.slot_time}</span></p>
        <p className="text-sm">{a.doctor_name}</p>
        <p className="mt-2 text-xs muted">TOKEN</p>
        <p className="mono text-6xl">{a.token_number}</p>
        {qr && <img src={qr} alt="Appointment QR" className="mx-auto mt-2" />}
        <p className="mono text-xs muted">{a.qr_code}</p>
        <p className="text-xs muted">Show this code at reception, nurse station, pharmacy and billing.</p>
      </div>
      <div className="mt-4 flex justify-center gap-2 no-print">
        <button className="btn-primary" onClick={() => window.print()}><IconPrint size={16} /> Print</button>
        <Link className="btn-ghost" href="/patient/my-appointments">Back</Link>
      </div>
    </main>
  );
}

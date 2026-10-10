"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import CameraScanner from "@/components/CameraScanner";
import { get, post } from "@/lib/api";
import StockPanel from "./StockPanel";

interface Dispense { id: number; prescription_id: number; encounter_id: number | null; patient_name: string | null; uhid: string | null; medication_name: string; quantity: number; status: string; in_stock: number | null }
interface DispenseResult extends Dispense { low_stock: boolean; bill_id: number; bill_total: number }
type Tab = "queue" | "scan" | "stock";

export default function Pharmacy() {
  const [tab, setTab] = useState<Tab>("queue");
  const [queue, setQueue] = useState<Dispense[]>([]);
  const [scanned, setScanned] = useState<{ patient_name: string; uhid: string; dispenses: Dispense[] } | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = () => get<Dispense[]>("/pharmacy/queue").then(setQueue).catch((e) => setErr(e.message));
  useEffect(() => { void load(); }, []);

  const dispense = async (id: number) => {
    setErr(null);
    try {
      const r = await post<DispenseResult>(`/pharmacy/dispense/${id}`);
      setMsg(`${r.medication_name} dispensed · Bill #${r.bill_id} raised ₹${r.bill_total.toFixed(2)}${r.low_stock ? " · LOW STOCK" : ""}`);
      void load();
      if (scanned) setScanned({ ...scanned, dispenses: scanned.dispenses.map((d) => (d.id === id ? { ...d, status: "DISPENSED" } : d)) });
    } catch (e) { setErr((e as Error).message); }
  };
  const scan = async (code: string) => {
    setErr(null);
    try {
      const r = await post<{ appointment: { patient_name: string; uhid: string }; dispenses: Dispense[] }>("/pharmacy/scan", { code });
      setScanned({ patient_name: r.appointment.patient_name, uhid: r.appointment.uhid, dispenses: r.dispenses });
    } catch (e) { setErr((e as Error).message); }
  };

  const Row = ({ d }: { d: Dispense }) => (
    <li className="flex flex-wrap items-center justify-between gap-2 border-b py-1.5 text-sm hr">
      <span>{d.medication_name} × <span className="mono">{d.quantity}</span> — {d.patient_name} <span className="mono muted">{d.uhid}</span>
        {d.in_stock != null && d.in_stock < d.quantity && <span className="badge badge-red ml-2">insufficient stock ({d.in_stock})</span>}</span>
      {d.status === "PENDING" ? <button className="btn-primary px-3 py-1" onClick={() => dispense(d.id)}>Dispense</button> : <span className="badge badge-green">DISPENSED</span>}
    </li>
  );

  return (
    <Shell portal="staff" title="Pharmacy">
      <div className="mb-3 flex gap-4 border-b text-sm hr">
        {(["queue", "scan", "stock"] as Tab[]).map((t) => <button key={t} className={`pb-1 capitalize ${tab === t ? "tab-active" : ""}`} onClick={() => setTab(t)}>{t}</button>)}
      </div>
      {err && <p className="mb-2 text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
      {msg && <p className="mb-2 text-xs muted">{msg}</p>}
      {tab === "queue" && (
        <section className="card"><h3 className="serif">Pending dispenses ({queue.length})</h3>
          <ul>{queue.length === 0 ? <li className="text-sm muted">Nothing pending.</li> : queue.map((d) => <Row key={d.id} d={d} />)}</ul></section>
      )}
      {tab === "scan" && (
        <div className="grid gap-4 md:grid-cols-2">
          <CameraScanner onScan={scan} label="Scan patient QR" />
          {scanned && <section className="card"><h3 className="serif">{scanned.patient_name} <span className="mono text-sm muted">{scanned.uhid}</span></h3>
            <ul>{scanned.dispenses.length === 0 ? <li className="text-sm muted">No prescription for this visit yet.</li> : scanned.dispenses.map((d) => <Row key={d.id} d={d} />)}</ul></section>}
        </div>
      )}
      {tab === "stock" && <section className="card"><StockPanel /></section>}
    </Shell>
  );
}

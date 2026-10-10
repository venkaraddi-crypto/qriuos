"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { get } from "@/lib/api";

interface Summary {
  date: string; total_patients: number; appointments_today: number; by_status: Record<string, number>; by_system: Record<string, number>;
  red_flags_today: number; revenue_paid: number; revenue_pending: number; low_stock: { name: string; quantity: number; reorder_level: number }[];
  top_namaste_diagnoses: { term: string; count: number }[];
}

function Stat({ label, value, mono = true }: { label: string; value: string | number; mono?: boolean }) {
  return (
    <div className="card">
      <p className="label">{label}</p>
      <p className={`text-2xl ${mono ? "mono" : "serif"}`}>{value}</p>
    </div>
  );
}

export default function Analytics() {
  const [s, setS] = useState<Summary | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { get<Summary>("/analytics/summary").then(setS).catch((e) => setErr(e.message)); }, []);

  return (
    <Shell portal="staff" title="Analytics">
      {err && <p className="text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
      {s && (
        <div className="space-y-4">
          <p className="text-sm muted">As of <span className="mono">{s.date}</span></p>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat label="Registered patients" value={s.total_patients} />
            <Stat label="Appointments today" value={s.appointments_today} />
            <Stat label="Red flags today" value={s.red_flags_today} />
            <Stat label="Revenue collected" value={`₹${s.revenue_paid.toFixed(0)}`} />
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            <section className="card">
              <h3 className="serif">Today by status</h3>
              <ul className="text-sm">{Object.entries(s.by_status).map(([k, v]) => <li key={k} className="flex justify-between"><span>{k}</span><span className="mono">{v}</span></li>)}</ul>
            </section>
            <section className="card">
              <h3 className="serif">All time by system</h3>
              {Object.entries(s.by_system).map(([k, v]) => {
                const total = Object.values(s.by_system).reduce((a, b) => a + b, 0) || 1;
                return (
                  <div key={k} className="mt-1 text-sm">
                    <div className="flex justify-between"><span>{k}</span><span className="mono">{v}</span></div>
                    <div className="h-2 w-full" style={{ background: "#D8CFC0" }}><div className="h-2" style={{ width: `${(100 * v) / total}%`, background: k === "AYURVEDA" ? "#7A6A21" : "#3E5C76" }} /></div>
                  </div>
                );
              })}
              <p className="mt-2 text-xs muted">Pending revenue ₹{s.revenue_pending.toFixed(0)}</p>
            </section>
            <section className="card">
              <h3 className="serif">Top NAMASTE diagnoses</h3>
              {s.top_namaste_diagnoses.length === 0 && <p className="text-sm muted">None yet</p>}
              <ul className="text-sm">{s.top_namaste_diagnoses.map((d) => <li key={d.term} className="flex justify-between"><span>{d.term}</span><span className="mono">{d.count}</span></li>)}</ul>
              <h3 className="serif mt-3">Low stock</h3>
              <ul className="text-sm">{s.low_stock.map((i) => <li key={i.name}><span className="badge badge-amber">{i.quantity}</span> {i.name} <span className="muted">(reorder at {i.reorder_level})</span></li>)}</ul>
            </section>
          </div>
        </div>
      )}
    </Shell>
  );
}

"use client";
import { useState } from "react";
import { post } from "@/lib/api";
import { LAB_TESTS, type LabOrderRow } from "./types";

interface Props { encounterId: number; orders: LabOrderRow[]; onChanged: (rows: LabOrderRow[]) => void }

export default function LabOrdersCard({ encounterId, orders, onChanged }: Props) {
  const [test, setTest] = useState(LAB_TESTS[0]);
  const [custom, setCustom] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const order = async () => {
    const name = custom.trim() || test;
    setErr(null);
    try {
      const r = await post<LabOrderRow>("/lab/orders", { encounter_id: encounterId, test_name: name });
      onChanged([...orders, r]); setCustom("");
    } catch (e) { setErr((e as Error).message); }
  };

  return (
    <section className="card space-y-2">
      <h3 className="serif text-lg">Lab orders</h3>
      <div className="flex flex-wrap gap-2">
        <select className="input w-auto" value={test} onChange={(e) => setTest(e.target.value)} aria-label="Test">{LAB_TESTS.map((t) => <option key={t}>{t}</option>)}</select>
        <input className="input w-auto" placeholder="or custom test" value={custom} onChange={(e) => setCustom(e.target.value)} />
        <button className="btn-primary" onClick={order}>Order</button>
      </div>
      <ul className="space-y-1 text-sm">
        {orders.length === 0 && <li className="muted">No tests ordered.</li>}
        {orders.map((o) => (
          <li key={o.id} className="flex flex-wrap items-center gap-2">
            <span>{o.test_name}</span>
            <span className={`badge ${o.status === "RESULT_READY" ? "badge-green" : ""}`}>{o.status}</span>
            {o.flagged_abnormal && <span className="badge badge-red">ABNORMAL</span>}
            {o.result_values && <span className="mono text-xs muted">{Object.entries(o.result_values).map(([k, v]) => `${k}=${String(v)}`).join(" · ")}</span>}
          </li>
        ))}
      </ul>
      {err && <p className="text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
    </section>
  );
}

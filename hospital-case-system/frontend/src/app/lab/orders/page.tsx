"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import CameraScanner from "@/components/CameraScanner";
import { get, patch, post } from "@/lib/api";

interface Order { id: number; encounter_id: number; patient_id: number | null; patient_name: string | null; uhid: string | null; test_name: string; status: string; result_values: Record<string, unknown> | null; flagged_abnormal: boolean; flags: Record<string, string> }
type KV = { key: string; value: string };
const DEFAULT_KEYS = ["hemoglobin", "fasting_glucose", "hba1c"];

export default function LabOrders() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [filter, setFilter] = useState("");
  const [patientFilter, setPatientFilter] = useState<number | null>(null);
  const [open, setOpen] = useState<number | null>(null);
  const [kv, setKv] = useState<KV[]>(DEFAULT_KEYS.map((k) => ({ key: k, value: "" })));
  const [err, setErr] = useState<string | null>(null);

  const load = () => get<Order[]>("/lab/orders").then(setOrders).catch((e) => setErr(e.message));
  useEffect(() => { void load(); }, []);

  const scan = async (code: string) => { try { const a = await post<{ patient_id: number; patient_name: string }>("/qr/lookup", { code }); setPatientFilter(a.patient_id); setFilter(""); } catch (e) { setErr((e as Error).message); } };
  const save = async (id: number) => {
    setErr(null);
    const result_values: Record<string, string | number> = {};
    kv.forEach((p) => { if (p.key.trim() && p.value.trim()) result_values[p.key.trim()] = isNaN(Number(p.value)) ? p.value : Number(p.value); });
    try { await patch(`/lab/orders/${id}/result`, { result_values }); setOpen(null); setKv(DEFAULT_KEYS.map((k) => ({ key: k, value: "" }))); void load(); } catch (e) { setErr((e as Error).message); }
  };

  const shown = orders.filter((o) => (patientFilter == null || o.patient_id === patientFilter) && (!filter || `${o.patient_name} ${o.uhid} ${o.test_name}`.toLowerCase().includes(filter.toLowerCase())));

  return (
    <Shell portal="staff" title="Lab orders">
      {err && <p className="mb-2 text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
      <div className="grid gap-4 md:grid-cols-[2fr_1fr]">
        <section className="card">
          <div className="flex items-center gap-2">
            <input className="input" placeholder="Filter by patient / test" value={filter} onChange={(e) => setFilter(e.target.value)} />
            {patientFilter != null && <button className="btn-ghost" onClick={() => setPatientFilter(null)}>Clear scan filter</button>}
          </div>
          <ul className="mt-2">
            {shown.length === 0 && <li className="text-sm muted">No orders.</li>}
            {shown.map((o) => (
              <li key={o.id} className="border-b py-2 text-sm hr">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span><strong>{o.test_name}</strong> — {o.patient_name} <span className="mono muted">{o.uhid}</span></span>
                  <span className="flex items-center gap-2">
                    <span className={`badge ${o.status === "RESULT_READY" ? "badge-green" : ""}`}>{o.status}</span>
                    {o.flagged_abnormal && <span className="badge badge-red">ABNORMAL</span>}
                    {o.status === "ORDERED" && <button className="btn-ghost px-2 py-0.5 text-xs" onClick={() => setOpen(open === o.id ? null : o.id)}>Enter result</button>}
                  </span>
                </div>
                {o.result_values && (
                  <p className="mono mt-1 text-xs">{Object.entries(o.result_values).map(([k, v]) => <span key={k} className="mr-3">{k}={String(v)} {o.flags[k] && <span className={`badge ${o.flags[k] === "HIGH" ? "badge-red" : "badge-amber"}`}>{o.flags[k]}</span>}</span>)}</p>
                )}
                {open === o.id && (
                  <div className="mt-2 space-y-1">
                    {kv.map((p, i) => (
                      <div key={i} className="flex gap-1">
                        <input className="input mono" placeholder="test key" value={p.key} onChange={(e) => setKv(kv.map((x, j) => (j === i ? { ...x, key: e.target.value } : x)))} />
                        <input className="input mono" placeholder="value" value={p.value} onChange={(e) => setKv(kv.map((x, j) => (j === i ? { ...x, value: e.target.value } : x)))} />
                      </div>
                    ))}
                    <div className="flex gap-2"><button className="btn-ghost" onClick={() => setKv([...kv, { key: "", value: "" }])}>Add row</button><button className="btn-primary" onClick={() => save(o.id)}>Save result</button></div>
                    <p className="text-xs muted">Values outside reference ranges are auto-flagged.</p>
                  </div>
                )}
              </li>
            ))}
          </ul>
        </section>
        <CameraScanner onScan={scan} label="Scan to filter" />
      </div>
    </Shell>
  );
}

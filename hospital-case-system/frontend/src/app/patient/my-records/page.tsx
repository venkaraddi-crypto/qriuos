"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { get, post } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

interface Med { name: string; dose?: string; frequency?: string; duration_days?: number }
interface Records {
  medicines: { prescription_id: number; encounter_id: number; date: string; medications: Med[] | null }[];
  reports: { id: number | string; encounter_id: number; date: string; test_name: string; status: string; result_values: Record<string, unknown> | null; flagged_abnormal: boolean }[];
  bills: { id: number; total_amount: number; payment_status: string; date: string | null; line_items: { description: string; amount: number }[] | null }[];
}
type Tab = "medicines" | "reports" | "bills";

export default function MyRecords() {
  const { t } = useI18n();
  const [r, setR] = useState<Records | null>(null);
  const [tab, setTab] = useState<Tab>("medicines");
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const load = () => get<Records>("/patients/me/records").then(setR).catch((e) => setErr(e.message));
  useEffect(() => { void load(); }, []);
  const pay = async (id: number) => { try { const b = await post<{ gateway: { reference: string } }>(`/billing/pay/${id}`); setMsg(`Paid · ${b.gateway.reference} (mock gateway)`); void load(); } catch (e) { setErr((e as Error).message); } };

  return (
    <Shell portal="patient" title={t("my_records")}>
      <div className="mb-3 flex gap-4 border-b text-sm hr">{(["medicines", "reports", "bills"] as Tab[]).map((x) => <button key={x} className={`pb-1 capitalize ${tab === x ? "tab-active" : ""}`} onClick={() => setTab(x)}>{x}</button>)}</div>
      {err && <p className="mb-2 text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
      {msg && <p className="mb-2 text-xs muted">{msg}</p>}
      {r && tab === "medicines" && (
        <div className="grid gap-3 md:grid-cols-2">
          {r.medicines.length === 0 && <p className="muted">No prescriptions yet.</p>}
          {r.medicines.map((m) => (
            <div key={m.prescription_id} className="card text-sm">
              <p className="mono text-xs muted">{m.date.slice(0, 10)}</p>
              <table className="mt-1 w-full"><tbody>{(m.medications || []).map((x, i) => <tr key={i}><td>{x.name}</td><td className="muted">{x.dose}</td><td className="muted">{x.frequency}</td><td className="mono">{x.duration_days} d</td></tr>)}</tbody></table>
              <Link className="mt-2 inline-block text-xs underline" href={`/rx/${m.encounter_id}`}>View ℞</Link>
            </div>
          ))}
        </div>
      )}
      {r && tab === "reports" && (
        <ul className="space-y-1">
          {r.reports.length === 0 && <li className="muted">No reports yet.</li>}
          {r.reports.map((x) => (
            <li key={x.id} className="card text-sm">
              <p><strong>{x.test_name}</strong> <span className="mono text-xs muted">{x.date.slice(0, 10)}</span> <span className="badge ml-1">{x.status}</span> {x.flagged_abnormal && <span className="badge badge-red ml-1">ABNORMAL</span>}</p>
              {x.result_values && <p className="mono mt-1 text-xs">{Object.entries(x.result_values).map(([k, v]) => `${k}: ${String(v)}`).join(" · ")}</p>}
            </li>
          ))}
        </ul>
      )}
      {r && tab === "bills" && (
        <ul className="space-y-1">
          {r.bills.length === 0 && <li className="muted">No bills.</li>}
          {r.bills.map((b) => (
            <li key={b.id} className="card flex items-center justify-between text-sm">
              <span>Bill #{b.id} <span className="mono text-xs muted">{b.date?.slice(0, 10)}</span> · <span className="mono">₹{b.total_amount.toFixed(2)}</span> <span className={`badge ml-1 ${b.payment_status === "PAID" ? "badge-green" : "badge-amber"}`}>{b.payment_status}</span></span>
              {b.payment_status === "PENDING" && <button className="btn-primary px-3 py-1" onClick={() => pay(b.id)}>Pay now</button>}
            </li>
          ))}
        </ul>
      )}
    </Shell>
  );
}

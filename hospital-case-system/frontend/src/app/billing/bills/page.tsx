"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { get, post } from "@/lib/api";
import { IconPrint } from "@/components/icons";

interface Bill { id: number; encounter_id: number; patient_name: string | null; uhid: string | null; line_items: { description: string; amount: number }[] | null; total_amount: number; payment_status: string; date: string | null; gateway?: { mocked: boolean; reference: string } }
interface Worklist { unbilled: { encounter_id: number; patient_name: string; uhid: string; date: string }[]; bills: Bill[] }

export default function Billing() {
  const [w, setW] = useState<Worklist | null>(null);
  const [receipt, setReceipt] = useState<Bill | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const load = () => get<Worklist>("/billing/worklist").then(setW).catch((e) => setErr(e.message));
  useEffect(() => { void load(); }, []);

  const generate = async (encId: number) => { try { const b = await post<Bill>(`/billing/generate/${encId}`); setMsg(`Bill #${b.id} generated ₹${b.total_amount.toFixed(2)}`); void load(); } catch (e) { setErr((e as Error).message); } };
  const pay = async (id: number) => {
    try { const b = await post<Bill>(`/billing/pay/${id}`); setMsg(`Paid · ref ${b.gateway?.reference}`); setReceipt(b); void load(); } catch (e) { setErr((e as Error).message); }
  };

  return (
    <Shell portal="staff" title="Billing">
      {err && <p className="mb-2 text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
      {msg && <p className="mb-2 text-xs muted no-print">{msg}</p>}
      <div className="grid gap-4 md:grid-cols-[1fr_2fr] no-print">
        <section className="card">
          <h3 className="serif">Unbilled encounters</h3>
          <ul className="text-sm">
            {w?.unbilled.length === 0 && <li className="muted">All encounters billed.</li>}
            {w?.unbilled.map((u) => (
              <li key={u.encounter_id} className="flex items-center justify-between border-b py-1 hr">
                <span>{u.patient_name} <span className="mono muted">{u.uhid}</span></span>
                <button className="btn-ghost px-2 py-0.5 text-xs" onClick={() => generate(u.encounter_id)}>Generate bill</button>
              </li>
            ))}
          </ul>
        </section>
        <section className="card">
          <h3 className="serif">Bills</h3>
          <table className="w-full text-sm">
            <thead><tr className="border-b hr text-left"><th className="py-1">#</th><th>Patient</th><th>Total</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {w?.bills.map((b) => (
                <tr key={b.id} className="border-b hr">
                  <td className="mono py-1">{b.id}</td>
                  <td>{b.patient_name} <span className="mono muted">{b.uhid}</span></td>
                  <td className="mono">₹{b.total_amount.toFixed(2)}</td>
                  <td><span className={`badge ${b.payment_status === "PAID" ? "badge-green" : "badge-amber"}`}>{b.payment_status}</span></td>
                  <td className="flex gap-1 py-1">
                    {b.payment_status === "PENDING" && <button className="btn-primary px-2 py-0.5 text-xs" onClick={() => pay(b.id)}>Collect payment</button>}
                    <button className="btn-ghost px-2 py-0.5 text-xs" onClick={() => setReceipt(b)}><IconPrint size={12} /> Receipt</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>
      {receipt && (
        <section className="card mt-4 mx-auto max-w-md">
          <div className="flex items-center justify-between no-print"><h3 className="serif">Receipt #{receipt.id}</h3>
            <span className="flex gap-2">{receipt.gateway?.mocked && <span className="badge badge-amber">MOCK GATEWAY</span>}<button className="btn-ghost px-2 py-0.5 text-xs" onClick={() => window.print()}>Print</button><button className="btn-ghost px-2 py-0.5 text-xs" onClick={() => setReceipt(null)}>Close</button></span></div>
          <p className="text-sm">{receipt.patient_name} · <span className="mono">{receipt.uhid}</span> · {receipt.date?.slice(0, 10)}</p>
          <ul className="mt-2 text-sm">{receipt.line_items?.map((l, i) => <li key={i} className="flex justify-between border-b py-0.5 hr"><span>{l.description}</span><span className="mono">₹{l.amount.toFixed(2)}</span></li>)}</ul>
          <p className="mt-2 flex justify-between font-medium"><span>Total</span><span className="mono">₹{receipt.total_amount.toFixed(2)}</span></p>
          <p className="text-xs muted">{receipt.payment_status}{receipt.gateway ? ` · ${receipt.gateway.reference}` : ""}</p>
        </section>
      )}
    </Shell>
  );
}

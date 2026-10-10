"use client";
import { useEffect, useState } from "react";
import { get, patch, post } from "@/lib/api";

interface Stock { id: number; name: string; quantity: number; reorder_level: number; unit_price: number; low_stock: boolean }

export default function StockPanel() {
  const [rows, setRows] = useState<Stock[]>([]);
  const [form, setForm] = useState({ name: "", quantity: 0, reorder_level: 10, unit_price: 0 });
  const [err, setErr] = useState<string | null>(null);
  const load = () => get<Stock[]>("/pharmacy/stock").then(setRows).catch((e) => setErr(e.message));
  useEffect(() => { void load(); }, []);

  const edit = async (id: number, field: "quantity" | "reorder_level" | "unit_price", value: string) => {
    try { await patch(`/pharmacy/stock/${id}`, { [field]: Number(value) }); void load(); } catch (e) { setErr((e as Error).message); }
  };
  const add = async (e: React.FormEvent) => {
    e.preventDefault(); setErr(null);
    try { await post("/pharmacy/stock", form); setForm({ name: "", quantity: 0, reorder_level: 10, unit_price: 0 }); void load(); } catch (ex) { setErr((ex as Error).message); }
  };

  return (
    <div className="space-y-3">
      {err && <p className="text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
      <table className="w-full text-sm">
        <thead><tr className="border-b hr text-left"><th className="py-1">Item</th><th>Qty</th><th>Reorder at</th><th>Unit ₹</th><th></th></tr></thead>
        <tbody>
          {rows.map((s) => (
            <tr key={s.id} className="border-b hr">
              <td className="py-1">{s.name}</td>
              <td><input className="input mono w-20 py-0.5" type="number" defaultValue={s.quantity} onBlur={(e) => edit(s.id, "quantity", e.target.value)} aria-label="Quantity" /></td>
              <td><input className="input mono w-20 py-0.5" type="number" defaultValue={s.reorder_level} onBlur={(e) => edit(s.id, "reorder_level", e.target.value)} aria-label="Reorder level" /></td>
              <td><input className="input mono w-20 py-0.5" type="number" step="0.5" defaultValue={s.unit_price} onBlur={(e) => edit(s.id, "unit_price", e.target.value)} aria-label="Unit price" /></td>
              <td>{s.low_stock && <span className="badge badge-amber">LOW</span>}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <form onSubmit={add} className="flex flex-wrap gap-2">
        <input className="input w-48" placeholder="New item" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
        <input className="input mono w-24" type="number" placeholder="Qty" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: Number(e.target.value) })} />
        <input className="input mono w-24" type="number" placeholder="Reorder" value={form.reorder_level} onChange={(e) => setForm({ ...form, reorder_level: Number(e.target.value) })} />
        <input className="input mono w-24" type="number" step="0.5" placeholder="₹" value={form.unit_price} onChange={(e) => setForm({ ...form, unit_price: Number(e.target.value) })} />
        <button className="btn-primary">Add</button>
      </form>
    </div>
  );
}

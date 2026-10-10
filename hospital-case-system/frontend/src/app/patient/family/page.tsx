"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { get, post } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

interface Member { id: number; relation: string; name: string; uhid: string; age: number | null; gender: string | null }

export default function Family() {
  const { t } = useI18n();
  const [rows, setRows] = useState<Member[]>([]);
  const [form, setForm] = useState({ name: "", relation: "", dob: "", gender: "", phone: "", uhid: "" });
  const [err, setErr] = useState<string | null>(null);
  const load = () => get<Member[]>("/patients/me/family").then(setRows).catch((e) => setErr(e.message));
  useEffect(() => { void load(); }, []);
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setForm({ ...form, [k]: e.target.value });
  const add = async (e: React.FormEvent) => {
    e.preventDefault(); setErr(null);
    try { await post("/patients/me/family", { ...form, dob: form.dob || null, gender: form.gender || null, phone: form.phone || null, uhid: form.uhid || null }); setForm({ name: "", relation: "", dob: "", gender: "", phone: "", uhid: "" }); void load(); } catch (ex) { setErr((ex as Error).message); }
  };

  return (
    <Shell portal="patient" title={t("family")}>
      {err && <p className="mb-2 text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
      <div className="grid gap-4 md:grid-cols-2">
        <section className="card">
          <h3 className="serif">Family members</h3>
          <ul className="text-sm">
            {rows.length === 0 && <li className="muted">No family members linked.</li>}
            {rows.map((m) => <li key={m.id} className="flex justify-between border-b py-1 hr"><span>{m.name} <span className="muted">({m.relation})</span></span><span className="mono text-xs">{m.uhid}{m.age != null ? ` · ${m.age} y` : ""}</span></li>)}
          </ul>
        </section>
        <form onSubmit={add} className="card space-y-2">
          <h3 className="serif">Add member</h3>
          <input className="input mono" placeholder="Existing UHID (optional)" value={form.uhid} onChange={set("uhid")} />
          <input className="input" placeholder="Name" value={form.name} onChange={set("name")} required />
          <input className="input" placeholder="Relation (Mother, Son…)" value={form.relation} onChange={set("relation")} required />
          <div className="grid grid-cols-2 gap-2">
            <input className="input" type="date" value={form.dob} onChange={set("dob")} aria-label="Date of birth" />
            <select className="input" value={form.gender} onChange={set("gender")} aria-label="Gender"><option value="">Gender…</option><option>Female</option><option>Male</option><option>Other</option></select>
          </div>
          <input className="input" placeholder="Phone (defaults to yours)" value={form.phone} onChange={set("phone")} />
          <button className="btn-primary">Add</button>
        </form>
      </div>
    </Shell>
  );
}

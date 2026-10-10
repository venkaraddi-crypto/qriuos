"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { get, post } from "@/lib/api";

interface Staff { id: number; name: string; email: string; role: string; registration_number: string | null; doctor_profile: { id: number; department_id: number; specialty: string | null; system: string } | null }
interface Dept { id: number; name: string; system: string }
const ROLES = ["RECEPTION", "DOCTOR", "NURSE", "LAB", "PHARMACY", "BILLING", "ADMIN"];

export default function StaffPage() {
  const [rows, setRows] = useState<Staff[]>([]);
  const [depts, setDepts] = useState<Dept[]>([]);
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "DOCTOR", registration_number: "", department_id: "", specialty: "" });
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const load = () => get<Staff[]>("/admin/staff").then(setRows).catch((e) => setErr(e.message));
  useEffect(() => { load(); get<Dept[]>("/departments").then(setDepts).catch(() => {}); }, []);

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null); setMsg(null);
    try {
      await post("/admin/staff", { ...form, department_id: form.department_id ? Number(form.department_id) : null, registration_number: form.registration_number || null, specialty: form.specialty || null });
      setMsg(`Created ${form.name}`); setForm({ ...form, name: "", email: "", password: "", registration_number: "", specialty: "" }); load();
    } catch (ex) { setErr((ex as Error).message); }
  };
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setForm({ ...form, [k]: e.target.value });

  return (
    <Shell portal="staff" title="Staff management">
      <div className="grid gap-4 md:grid-cols-[1fr_2fr]">
        <form onSubmit={create} className="card space-y-2">
          <h3 className="serif">Add staff</h3>
          <input className="input" placeholder="Name" value={form.name} onChange={set("name")} required />
          <input className="input" type="email" placeholder="Email" value={form.email} onChange={set("email")} required />
          <input className="input" type="password" placeholder="Temporary password" value={form.password} onChange={set("password")} required minLength={6} />
          <select className="input" value={form.role} onChange={set("role")}>{ROLES.map((r) => <option key={r}>{r}</option>)}</select>
          <input className="input" placeholder="Registration / badge no." value={form.registration_number} onChange={set("registration_number")} />
          {form.role === "DOCTOR" && (
            <>
              <select className="input" value={form.department_id} onChange={set("department_id")} required>
                <option value="">Department…</option>{depts.map((d) => <option key={d.id} value={d.id}>{d.name} ({d.system})</option>)}
              </select>
              <input className="input" placeholder="Specialty" value={form.specialty} onChange={set("specialty")} />
            </>
          )}
          <button className="btn-primary">Create</button>
          {msg && <p className="text-xs muted">{msg}</p>}
          {err && <p className="text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
        </form>
        <section className="card overflow-x-auto">
          <h3 className="serif">Staff directory</h3>
          <table className="mt-2 w-full text-sm">
            <thead><tr className="border-b hr text-left"><th className="py-1">Name</th><th>Role</th><th>Email</th><th>Badge</th><th>Dept / system</th></tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-b hr">
                  <td className="py-1">{r.name}</td><td><span className="badge">{r.role}</span></td><td className="muted">{r.email}</td>
                  <td className="mono">{r.registration_number || "—"}</td>
                  <td>{r.doctor_profile ? `${depts.find((d) => d.id === r.doctor_profile?.department_id)?.name || r.doctor_profile.department_id} · ${r.doctor_profile.system}` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>
    </Shell>
  );
}

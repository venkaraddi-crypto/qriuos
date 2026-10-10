"use client";
import Link from "next/link";
import { useState } from "react";
import { post } from "@/lib/api";
import { IconLeaf } from "@/components/icons";

export default function Register() {
  const [form, setForm] = useState({ name: "", email: "", password: "", phone: "", dob: "", gender: "" });
  const [result, setResult] = useState<{ uhid: string; name: string } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null);
    try {
      const r = await post<{ uhid: string; name: string }>("/auth/register", {
        ...form, dob: form.dob || null, gender: form.gender || null,
      });
      setResult(r);
    } catch (ex) {
      setErr((ex as Error).message);
    }
  };

  if (result) {
    return (
      <main id="main-content" className="mx-auto flex min-h-screen max-w-md flex-col justify-center p-6">
        <div className="card space-y-3 text-center">
          <h1 className="serif text-2xl">Welcome, {result.name}</h1>
          <p className="muted">Your Unique Hospital ID</p>
          <p className="mono text-2xl">{result.uhid}</p>
          <p className="text-sm muted">Keep this ID; every appointment QR carries it.</p>
          <Link href="/login" className="btn-primary justify-center">Continue to login</Link>
        </div>
      </main>
    );
  }

  return (
    <main id="main-content" className="mx-auto flex min-h-screen max-w-md flex-col justify-center p-6">
      <h1 className="serif mb-1 flex items-center gap-2 text-3xl"><IconLeaf size={28} /> Register</h1>
      <p className="mb-6 muted">Create your patient account to book OPD appointments.</p>
      <form onSubmit={submit} className="card space-y-3">
        <label className="block"><span className="label">Full name</span><input className="input" value={form.name} onChange={set("name")} required /></label>
        <label className="block"><span className="label">Email</span><input className="input" type="email" value={form.email} onChange={set("email")} required /></label>
        <label className="block"><span className="label">Password</span><input className="input" type="password" value={form.password} onChange={set("password")} minLength={6} required /></label>
        <label className="block"><span className="label">Phone</span><input className="input" value={form.phone} onChange={set("phone")} required /></label>
        <div className="grid grid-cols-2 gap-3">
          <label className="block"><span className="label">Date of birth</span><input className="input" type="date" value={form.dob} onChange={set("dob")} /></label>
          <label className="block"><span className="label">Gender</span>
            <select className="input" value={form.gender} onChange={set("gender")}>
              <option value="">—</option><option>Female</option><option>Male</option><option>Other</option>
            </select></label>
        </div>
        {err && <p className="text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
        <button className="btn-primary w-full justify-center">Create account</button>
      </form>
      <Link href="/login" className="mt-4 text-sm underline">Already registered? Login</Link>
    </main>
  );
}

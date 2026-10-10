"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ROLE_HOME, useAuth } from "@/store/auth";
import { IconLeaf } from "@/components/icons";
import StaffIdentifier from "@/components/StaffIdentifier";

const DEMO = [
  ["reception@demo.in", "Reception"], ["doctor-allo@demo.in", "Doctor (Allopathic)"], ["doctor-ayu@demo.in", "Doctor (Ayurveda)"],
  ["nurse@demo.in", "Nurse"], ["lab@demo.in", "Lab"], ["pharmacy@demo.in", "Pharmacy"], ["billing@demo.in", "Billing"], ["admin@demo.in", "Admin"],
];

export default function StaffLogin() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState("doctor-allo@demo.in");
  const [password, setPassword] = useState("password123");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [showScan, setShowScan] = useState(false);

  const submit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      const role = await login(email, password);
      router.replace(ROLE_HOME[role]);
    } catch (ex) {
      setErr((ex as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <main id="main-content" className="mx-auto flex min-h-screen max-w-lg flex-col justify-center p-6">
      <h1 className="serif mb-1 flex items-center gap-2 text-3xl"><IconLeaf size={28} /> ArogyaSetu — Staff</h1>
      <p className="mb-6 muted">Sign in with your hospital credentials or scan your badge.</p>
      <form onSubmit={submit} className="card space-y-4">
        <label className="block"><span className="label">Email</span>
          <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></label>
        <label className="block"><span className="label">Password</span>
          <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required /></label>
        {err && <p className="text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
        <div className="flex gap-2">
          <button className="btn-primary flex-1 justify-center" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
          <button type="button" className="btn-ghost" onClick={() => setShowScan((s) => !s)}>Scan badge</button>
        </div>
      </form>
      {showScan && (
        <div className="mt-4">
          <StaffIdentifier onIdentified={(e) => { setEmail(e); setShowScan(false); }} />
        </div>
      )}
      <div className="card mt-4 text-xs">
        <p className="mb-2 muted">Demo accounts (password <span className="mono">password123</span>):</p>
        <div className="grid grid-cols-2 gap-1">
          {DEMO.map(([e, l]) => (
            <button key={e} type="button" className="text-left underline" onClick={() => setEmail(e)}>{l}</button>
          ))}
        </div>
      </div>
      <Link href="/login" className="mt-4 text-sm underline muted">Patient login</Link>
    </main>
  );
}

"use client";
import { useState } from "react";
import CameraScanner from "@/components/CameraScanner";
import { post } from "@/lib/api";

interface Props {
  onIdentified: (email: string, name: string, role: string) => void;
}

export default function StaffIdentifier({ onIdentified }: Props) {
  const [msg, setMsg] = useState<string | null>(null);
  const identify = async (code: string) => {
    setMsg(null);
    try {
      const r = await post<{ email: string; name: string; role: string }>("/staff/identify", { code });
      setMsg(`Badge recognised: ${r.name} (${r.role})`);
      onIdentified(r.email, r.name, r.role);
    } catch (e) {
      setMsg((e as Error).message);
    }
  };
  return (
    <div className="space-y-2">
      <CameraScanner onScan={(c) => void identify(c)} label="Scan staff badge" />
      {msg && <p className="text-sm muted">{msg}</p>}
    </div>
  );
}

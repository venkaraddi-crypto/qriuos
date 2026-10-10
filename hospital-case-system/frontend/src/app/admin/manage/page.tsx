"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { get, post } from "@/lib/api";

interface Dept { id: number; name: string; system: string }
interface Doc { id: number; name: string; department: string; system: string }
interface Slot { id: number; date: string; start_time: string; end_time: string; capacity: number; available: number }

export default function ManagePage() {
  const [depts, setDepts] = useState<Dept[]>([]);
  const [docs, setDocs] = useState<Doc[]>([]);
  const [dept, setDept] = useState({ name: "", system: "ALLOPATHIC" });
  const today = new Date().toISOString().slice(0, 10);
  const [slot, setSlot] = useState({ doctor_id: "", date: today, start_time: "09:00", end_time: "10:00", capacity: 10 });
  const [slots, setSlots] = useState<Slot[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const load = () => { get<Dept[]>("/departments").then(setDepts).catch((e) => setErr(e.message)); get<Doc[]>("/doctors").then(setDocs).catch(() => {}); };
  useEffect(load, []);
  useEffect(() => { if (slot.doctor_id) get<Slot[]>(`/doctors/${slot.doctor_id}/slots?date=${slot.date}`).then(setSlots).catch(() => setSlots([])); }, [slot.doctor_id, slot.date]);

  const addDept = async (e: React.FormEvent) => {
    e.preventDefault(); setErr(null);
    try { await post("/admin/departments", dept); setMsg(`Department ${dept.name} added`); setDept({ ...dept, name: "" }); load(); } catch (ex) { setErr((ex as Error).message); }
  };
  const addSlot = async (e: React.FormEvent) => {
    e.preventDefault(); setErr(null);
    try {
      await post("/admin/doctor-slots", { ...slot, doctor_id: Number(slot.doctor_id), capacity: Number(slot.capacity) });
      setMsg("Slot added");
      setSlots(await get<Slot[]>(`/doctors/${slot.doctor_id}/slots?date=${slot.date}`));
    } catch (ex) { setErr((ex as Error).message); }
  };

  return (
    <Shell portal="staff" title="Departments & slots">
      {msg && <p className="mb-2 text-xs muted">{msg}</p>}
      {err && <p className="mb-2 text-sm" style={{ color: "#A03A2A" }}>{err}</p>}
      <div className="grid gap-4 md:grid-cols-2">
        <section className="card space-y-3">
          <h3 className="serif">Departments</h3>
          <ul className="text-sm">{depts.map((d) => <li key={d.id} className="flex justify-between border-b py-1 hr"><span>{d.name}</span><span className={`badge ${d.system === "AYURVEDA" ? "badge-amber" : ""}`}>{d.system}</span></li>)}</ul>
          <form onSubmit={addDept} className="flex gap-2">
            <input className="input" placeholder="New department" value={dept.name} onChange={(e) => setDept({ ...dept, name: e.target.value })} required />
            <select className="input w-auto" value={dept.system} onChange={(e) => setDept({ ...dept, system: e.target.value })}><option>ALLOPATHIC</option><option>AYURVEDA</option></select>
            <button className="btn-primary">Add</button>
          </form>
        </section>
        <section className="card space-y-3">
          <h3 className="serif">Doctor slots</h3>
          <form onSubmit={addSlot} className="grid grid-cols-2 gap-2 text-sm">
            <select className="input col-span-2" value={slot.doctor_id} onChange={(e) => setSlot({ ...slot, doctor_id: e.target.value })} required>
              <option value="">Doctor…</option>{docs.map((d) => <option key={d.id} value={d.id}>{d.name} — {d.department}</option>)}
            </select>
            <input className="input" type="date" value={slot.date} onChange={(e) => setSlot({ ...slot, date: e.target.value })} />
            <input className="input" type="number" min={1} value={slot.capacity} onChange={(e) => setSlot({ ...slot, capacity: Number(e.target.value) })} aria-label="Capacity" />
            <input className="input" type="time" value={slot.start_time} onChange={(e) => setSlot({ ...slot, start_time: e.target.value })} />
            <input className="input" type="time" value={slot.end_time} onChange={(e) => setSlot({ ...slot, end_time: e.target.value })} />
            <button className="btn-primary col-span-2">Add slot</button>
          </form>
          {slot.doctor_id && (
            <ul className="text-sm">
              {slots.length === 0 && <li className="muted">No slots on {slot.date}.</li>}
              {slots.map((s) => <li key={s.id} className="flex justify-between border-b py-1 hr"><span className="mono">{s.start_time}–{s.end_time}</span><span className="muted">{s.available}/{s.capacity} free</span></li>)}
            </ul>
          )}
        </section>
      </div>
    </Shell>
  );
}

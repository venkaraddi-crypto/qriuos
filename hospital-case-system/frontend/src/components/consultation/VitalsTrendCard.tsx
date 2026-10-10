"use client";
import type { VitalsRow } from "./types";

export default function VitalsTrendCard({ history }: { history: VitalsRow[] }) {
  const pts = history.filter((h) => h.pulse != null);
  if (history.length === 0) return null;
  const W = 320, H = 80, pad = 6;
  const pulses = pts.map((p) => p.pulse as number);
  const min = Math.min(...pulses, 60), max = Math.max(...pulses, 100);
  const x = (i: number) => pad + (pts.length > 1 ? (i * (W - 2 * pad)) / (pts.length - 1) : (W - 2 * pad) / 2);
  const y = (v: number) => H - pad - ((v - min) / Math.max(1, max - min)) * (H - 2 * pad);
  const path = pts.map((p, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(p.pulse as number).toFixed(1)}`).join(" ");
  const latest = history[history.length - 1];

  return (
    <section className="card">
      <div className="flex items-center justify-between">
        <h3 className="serif text-lg">Vitals trend</h3>
        <p className="text-xs muted">{history.length} reading{history.length === 1 ? "" : "s"}</p>
      </div>
      {pts.length > 0 && (
        <svg viewBox={`0 0 ${W} ${H}`} className="mt-2 w-full" role="img" aria-label="Pulse sparkline">
          <path d={path} fill="none" stroke="#B4552D" strokeWidth={1.5} />
          {pts.map((p, i) => <circle key={i} cx={x(i)} cy={y(p.pulse as number)} r={2.5} fill="#B4552D" />)}
        </svg>
      )}
      <div className="mt-2 flex flex-wrap gap-3 text-sm">
        {history.slice(-4).map((h, i) => (
          <div key={i} className="mono">
            <span className="muted">{h.date.slice(0, 10)}</span> {h.bp || "—"} · {h.pulse ?? "—"} bpm
            {h.temp != null && ` · ${h.temp}°F`}{h.weight != null && ` · ${h.weight} kg`}
          </div>
        ))}
      </div>
      <p className="mt-1 text-xs muted">Latest: {latest.bp || "—"} / {latest.pulse ?? "—"} bpm</p>
    </section>
  );
}

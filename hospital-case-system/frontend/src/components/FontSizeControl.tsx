"use client";
import { useEffect, useState } from "react";

const STEPS = [0.9, 1, 1.15, 1.3];

export default function FontSizeControl() {
  const [idx, setIdx] = useState(1);
  useEffect(() => {
    const saved = parseFloat(localStorage.getItem("arogya_font_scale") || "1");
    const i = STEPS.indexOf(saved);
    if (i >= 0) setIdx(i);
  }, []);
  const apply = (i: number) => {
    const clamped = Math.max(0, Math.min(STEPS.length - 1, i));
    setIdx(clamped);
    document.documentElement.style.setProperty("--font-scale", String(STEPS[clamped]));
    localStorage.setItem("arogya_font_scale", String(STEPS[clamped]));
  };
  return (
    <span className="inline-flex items-center gap-1" role="group" aria-label="Text size">
      <button className="btn-ghost px-2 py-0.5 text-xs" onClick={() => apply(idx - 1)} aria-label="Smaller text">A−</button>
      <button className="btn-ghost px-2 py-0.5 text-xs" onClick={() => apply(idx + 1)} aria-label="Larger text">A+</button>
    </span>
  );
}

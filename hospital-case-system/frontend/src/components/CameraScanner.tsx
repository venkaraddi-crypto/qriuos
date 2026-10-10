"use client";
import jsQR from "jsqr";
import { useEffect, useRef, useState } from "react";
import { IconQr } from "@/components/icons";

interface Props {
  onScan: (code: string) => void;
  label?: string;
  autoStart?: boolean;
}

export default function CameraScanner({ onScan, label = "Scan QR", autoStart = false }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef<number>(0);
  const lastRef = useRef<string>("");
  const [active, setActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [manual, setManual] = useState("");

  const stop = () => {
    cancelAnimationFrame(rafRef.current);
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setActive(false);
  };

  const start = async () => {
    setError(null);
    if (typeof window !== "undefined" && !window.isSecureContext) {
      setError("Camera requires HTTPS or localhost. Use manual entry below.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setActive(true);
      const loop = () => {
        const v = videoRef.current;
        const c = canvasRef.current;
        if (v && c && v.readyState === v.HAVE_ENOUGH_DATA) {
          c.width = v.videoWidth;
          c.height = v.videoHeight;
          const ctx = c.getContext("2d");
          if (ctx) {
            ctx.drawImage(v, 0, 0, c.width, c.height);
            const img = ctx.getImageData(0, 0, c.width, c.height);
            const code = jsQR(img.data, img.width, img.height);
            if (code?.data && code.data !== lastRef.current) {
              lastRef.current = code.data;
              onScan(code.data);
              setTimeout(() => (lastRef.current = ""), 3000);
            }
          }
        }
        rafRef.current = requestAnimationFrame(loop);
      };
      rafRef.current = requestAnimationFrame(loop);
    } catch (e) {
      setError(`Camera unavailable: ${(e as Error).message}`);
    }
  };

  useEffect(() => {
    if (autoStart) void start();
    return stop;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="card space-y-3">
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-2 text-sm font-medium"><IconQr size={18} /> {label}</span>
        {active ? (
          <button className="btn-ghost" onClick={stop}>Stop camera</button>
        ) : (
          <button className="btn-primary" onClick={() => void start()}>Start camera</button>
        )}
      </div>
      <video ref={videoRef} className={`w-full max-w-md rounded-sm border hr ${active ? "" : "hidden"}`} muted playsInline />
      <canvas ref={canvasRef} className="hidden" />
      {error && <p className="text-sm" style={{ color: "#A03A2A" }}>{error}</p>}
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (manual.trim()) {
            onScan(manual.trim());
            setManual("");
          }
        }}
      >
        <input className="input mono" placeholder="or type code: AIIA-CK-…" value={manual} onChange={(e) => setManual(e.target.value)} aria-label="Manual code" />
        <button className="btn-ghost" type="submit">Submit</button>
      </form>
    </div>
  );
}

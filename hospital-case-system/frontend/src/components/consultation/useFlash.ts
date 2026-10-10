"use client";
import { useCallback, useRef, useState } from "react";

/** Auto-clearing status line. */
export function useFlash(defaultMs = 2000) {
  const [message, setMessage] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const flash = useCallback(
    (text: string, ms = defaultMs) => {
      setMessage(text);
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => setMessage(null), ms);
    },
    [defaultMs],
  );
  return { message, flash };
}

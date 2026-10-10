"use client";
import { createContext, useContext, useEffect, useState } from "react";

export type Theme = "light" | "dark" | "system";

const ThemeCtx = createContext<{ theme: Theme; setTheme: (t: Theme) => void }>({ theme: "system", setTheme: () => {} });

function apply(theme: Theme) {
  const dark = theme === "dark" || (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
}

export default function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("system");
  useEffect(() => {
    const saved = (localStorage.getItem("arogya_theme") as Theme | null) || "system";
    setThemeState(saved);
    apply(saved);
    const scale = localStorage.getItem("arogya_font_scale");
    if (scale) document.documentElement.style.setProperty("--font-scale", scale);
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => apply((localStorage.getItem("arogya_theme") as Theme | null) || "system");
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);
  const setTheme = (t: Theme) => {
    setThemeState(t);
    localStorage.setItem("arogya_theme", t);
    apply(t);
  };
  return <ThemeCtx.Provider value={{ theme, setTheme }}>{children}</ThemeCtx.Provider>;
}

export const useTheme = () => useContext(ThemeCtx);

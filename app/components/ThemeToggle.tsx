"use client";

import { useEffect, useState } from "react";

type Theme = "dark" | "light";

function getSystemTheme(): Theme {
  if (typeof window === "undefined") return "dark";
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

function getStoredTheme(): Theme | null {
  if (typeof window === "undefined") return null;
  const stored = localStorage.getItem("aletheia-theme");
  return stored === "light" || stored === "dark" ? stored : null;
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const theme = getStoredTheme() ?? getSystemTheme();
    document.documentElement.setAttribute("data-theme", theme);
    setMounted(true);
  }, []);

  // Prevent flash — children render immediately but theme class is applied in useEffect
  return <>{children}</>;
}

export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("dark");

  useEffect(() => {
    const current = getStoredTheme() ?? getSystemTheme();
    setTheme(current);
  }, []);

  const toggle = () => {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("aletheia-theme", next);
  };

  return (
    <button
      onClick={toggle}
      aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
      title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
      style={{
        background: "none",
        border: "1px solid var(--border-hi)",
        borderRadius: "4px",
        color: "var(--muted)",
        cursor: "pointer",
        fontSize: "1rem",
        padding: "0.3rem 0.5rem",
        lineHeight: 1,
        transition: "color 0.2s, border-color 0.2s",
      }}
    >
      {theme === "dark" ? "☀" : "☾"}
    </button>
  );
}

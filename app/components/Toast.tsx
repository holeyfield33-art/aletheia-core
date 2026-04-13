"use client";

import { createContext, useCallback, useContext, useState, useRef } from "react";

type ToastType = "success" | "error" | "info";

interface ToastItem {
  id: number;
  message: string;
  type: ToastType;
  removing?: boolean;
}

interface ToastContextValue {
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within <ToastProvider>");
  return ctx;
}

const AUTO_DISMISS_MS = 4000;
const REMOVE_ANIMATION_MS = 200;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const counter = useRef(0);

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.map((t) => (t.id === id ? { ...t, removing: true } : t)));
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, REMOVE_ANIMATION_MS);
  }, []);

  const addToast = useCallback(
    (message: string, type: ToastType) => {
      const id = ++counter.current;
      setToasts((prev) => [...prev.slice(-4), { id, message, type }]);
      setTimeout(() => dismiss(id), AUTO_DISMISS_MS);
    },
    [dismiss],
  );

  const value: ToastContextValue = {
    success: useCallback((m: string) => addToast(m, "success"), [addToast]),
    error: useCallback((m: string) => addToast(m, "error"), [addToast]),
    info: useCallback((m: string) => addToast(m, "info"), [addToast]),
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-container" aria-live="polite" role="status">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`toast ${t.type === "success" ? "toast-success" : t.type === "error" ? "toast-error" : ""}`}
            data-removing={t.removing ? "true" : undefined}
          >
            <span>{t.message}</span>
            <button
              className="toast-dismiss"
              onClick={() => dismiss(t.id)}
              aria-label="Dismiss notification"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

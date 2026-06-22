// Change log:
// [#001] 2026-06-22 — Sumeet — File created. Minimal toast provider matching the mockup's
//        bottom-center toast.
import { createContext, useCallback, useContext, useState } from "react"
import type { ReactNode } from "react"

interface ToastValue {
  show: (msg: string, kind?: "ok" | "err") => void
}
const ToastCtx = createContext<ToastValue>({ show: () => {} })
export const useToast = () => useContext(ToastCtx)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [msg, setMsg] = useState("")
  const [kind, setKind] = useState<"ok" | "err">("ok")
  const [open, setOpen] = useState(false)

  const show = useCallback((m: string, k: "ok" | "err" = "ok") => {
    setMsg(m)
    setKind(k)
    setOpen(true)
    window.clearTimeout((show as unknown as { _t?: number })._t)
    ;(show as unknown as { _t?: number })._t = window.setTimeout(() => setOpen(false), 3400)
  }, [])

  return (
    <ToastCtx.Provider value={{ show }}>
      {children}
      <div className={`toast ${open ? "show" : ""} ${kind === "err" ? "err" : ""}`}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M9 12l2 2 4-4m6 2a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
        </svg>
        <span>{msg}</span>
      </div>
    </ToastCtx.Provider>
  )
}

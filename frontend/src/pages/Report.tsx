// Change log:
// [#002] 2026-06-22 — Sumeet — Let users REMOVE an attached recording/screenshot before
//        submitting (× on each preview thumbnail) and re-attach; revoke object URLs on
//        removal/unmount.
// [#001] 2026-06-22 — Sumeet — File created. Client "Report a bug" flow: title, steps, module,
//        plain-language severity picker, screen recording + screenshot upload with previews,
//        and the auto-captured environment note (spec §6 — no raw query text/results).
import { useEffect, useRef, useState } from "react"
import { api, ApiError } from "../api"
import { ScreenRecorder } from "../components/ScreenRecorder"
import { useRouter } from "../router"
import { useToast } from "../toast"
import type { Module, Severity } from "../types"
import { Icon, SEVERITY_META } from "../ui"

const MODULES: { value: Module; label: string }[] = [
  { value: "conversational_query", label: "Conversational query" },
  { value: "charts", label: "Dashboard / charts" },
  { value: "datasource", label: "Datasource connection" },
  { value: "agent_view", label: "Agent reasoning view" },
  { value: "rbac", label: "User & role settings (RBAC)" },
  { value: "audit_log", label: "Audit log" },
  { value: "other", label: "Other" },
]

function detectEnv(module: Module): Record<string, string> {
  const ua = navigator.userAgent
  const browser =
    /Edg\//.test(ua) ? "Edge" : /Chrome\//.test(ua) ? "Chrome" :
    /Safari\//.test(ua) ? "Safari" : /Firefox\//.test(ua) ? "Firefox" : "Unknown"
  const os =
    /Windows/.test(ua) ? "Windows" : /Mac OS X/.test(ua) ? "macOS" :
    /Linux/.test(ua) ? "Linux" : /Android/.test(ua) ? "Android" : "Unknown"
  return {
    browser,
    os,
    screen: `${window.screen.width}x${window.screen.height}`,
    unveilix_module: module,
    datasource_type: "PostgreSQL via Trino",
    agent_run_id: `run_${Math.random().toString(16).slice(2, 8)}`,
    reported_url: window.location.href,
  }
}

export function Report() {
  const { navigate } = useRouter()
  const toast = useToast()
  const fileRef = useRef<HTMLInputElement>(null)

  const [title, setTitle] = useState("")
  const [description, setDescription] = useState("")
  const [module, setModule] = useState<Module>("conversational_query")
  const [severity, setSeverity] = useState<Severity>("blocks_work")
  const [screenshots, setScreenshots] = useState<{ file: File; url: string; id: string }[]>([])
  const [recording, setRecording] = useState<{ blob: Blob; seconds: number } | null>(null)
  const [busy, setBusy] = useState(false)

  function addFiles(files: FileList | null) {
    if (!files) return
    const imgs = Array.from(files)
      .filter((f) => f.type.startsWith("image/"))
      .map((f) => ({
        file: f,
        url: URL.createObjectURL(f),
        id: `${f.name}-${f.size}-${f.lastModified}-${Math.random().toString(16).slice(2, 8)}`,
      }))
    setScreenshots((prev) => [...prev, ...imgs])
  }

  function removeScreenshot(id: string) {
    setScreenshots((prev) => {
      const target = prev.find((s) => s.id === id)
      if (target) URL.revokeObjectURL(target.url)
      return prev.filter((s) => s.id !== id)
    })
  }

  // Revoke any outstanding preview URLs when leaving the page.
  useEffect(() => {
    return () => {
      screenshots.forEach((s) => URL.revokeObjectURL(s.url))
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  async function submit() {
    if (!title.trim()) {
      toast.show("Please describe what happened", "err")
      return
    }
    setBusy(true)
    try {
      const ticket = await api.createTicket({
        title: title.trim(),
        description: description.trim() || null,
        module,
        severity,
        environment: detectEnv(module),
      })
      if (recording) {
        await api.uploadAttachment(ticket.id, recording.blob, "screen-recording.webm")
      }
      for (const s of screenshots) {
        await api.uploadAttachment(ticket.id, s.file, s.file.name)
      }
      toast.show(`Bug reported — ${ticket.reference} created. We auto-tagged it ${ticket.priority}.`)
      setTimeout(() => navigate("/tickets"), 900)
    } catch (e) {
      toast.show(e instanceof ApiError ? e.message : "Could not submit", "err")
      setBusy(false)
    }
  }

  return (
    <div className="view">
      <div className="topbar">
        <div>
          <h1>Report a bug</h1>
          <p>Tell us what went wrong in Unveilix. We'll route it to the right engineer.</p>
        </div>
      </div>
      <div className="report-wrap">
        <div className="report-card">
          <div className="field">
            <label>What happened?</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Chart didn't render after I asked for revenue by region"
            />
          </div>
          <div className="field">
            <label>
              Steps &amp; details <span className="opt">— the more, the faster we fix it</span>
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What you were doing, what you expected, what you saw instead…"
            />
          </div>
          <div className="field">
            <label>Where in Unveilix?</label>
            <select value={module} onChange={(e) => setModule(e.target.value as Module)}>
              {MODULES.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>

          <div className="field">
            <label>How much is this blocking you?</label>
            <div className="sev-grid">
              {SEVERITY_META.map((s) => (
                <button
                  type="button"
                  key={s.value}
                  className={`sev ${severity === s.value ? "sel" : ""}`}
                  onClick={() => setSeverity(s.value)}
                >
                  <b>
                    <span className="pin" style={{ background: s.color }} />
                    {s.title}
                  </b>
                  <small>{s.hint}</small>
                </button>
              ))}
            </div>
          </div>

          <div className="field">
            <label>Show us (optional but powerful)</label>
            <div className="capture">
              <ScreenRecorder
                hasClip={recording !== null}
                onCapture={(blob, seconds) => setRecording({ blob, seconds })}
              />
              <button type="button" className="drop" onClick={() => fileRef.current?.click()}>
                <Icon.Upload size={26} />
                <b>Upload screenshot</b>
                <small>Browse · PNG or JPEG</small>
              </button>
              <input
                ref={fileRef}
                type="file"
                accept="image/png,image/jpeg"
                multiple
                hidden
                onChange={(e) => addFiles(e.target.files)}
              />
            </div>
            <div className="attach-preview">
              {recording && (
                <div className="thumb vid" title="screen recording">
                  ▶ {Math.floor(recording.seconds / 60)}:{String(recording.seconds % 60).padStart(2, "0")}
                  <button
                    type="button"
                    className="rm"
                    title="Remove recording"
                    aria-label="Remove recording"
                    onClick={() => setRecording(null)}
                  >
                    ×
                  </button>
                </div>
              )}
              {screenshots.map((s) => (
                <div className="thumb" key={s.id} title={s.file.name}>
                  <img src={s.url} alt={s.file.name} />
                  <button
                    type="button"
                    className="rm"
                    title="Remove screenshot"
                    aria-label="Remove screenshot"
                    onClick={() => removeScreenshot(s.id)}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          </div>

          <div className="auto-note">
            <Icon.Check size={16} />
            <div>
              We'll automatically attach your diagnostics so you don't have to — <code>browser</code>,{" "}
              <code>OS</code>, the <code>Unveilix module</code>, your <code>datasource type</code>, and the
              last query ID. Raw query text and result values are never captured.
            </div>
          </div>

          <div className="submit-row">
            <button
              className="btn btn-primary"
              style={{ flex: 1, justifyContent: "center" }}
              onClick={submit}
              disabled={busy}
            >
              {busy ? "Submitting…" : "Submit bug report"}
            </button>
            <button className="btn btn-ghost" onClick={() => navigate("/tickets")}>
              My tickets
            </button>
          </div>
        </div>
        <p className="hint">
          Tickets stay private to your organization. Only the Unveilix team and your admins can see them.
        </p>
      </div>
    </div>
  )
}

// Change log:
// [#002] 2026-06-22 — Sumeet — Added date formatting (formatDate) and the "filter by date"
//        presets (DATE_PRESETS + sinceIso) used by the toolbars.
// [#001] 2026-06-22 — Sumeet — File created. Shared display helpers (status/priority/module
//        maps, avatars, age formatting) and small presentational components + icons used
//        across the Unveilix Support screens. Mirrors the mockup's visual language.
import type { Priority, Severity, TicketStatus } from "./types"

export const STATUS_ORDER: TicketStatus[] = [
  "new", "deferred", "in_development", "in_testing", "deployed", "closed",
]
export const STATUS_LABEL: Record<TicketStatus, string> = {
  new: "New", deferred: "Deferred", in_development: "In Development",
  in_testing: "In Testing", deployed: "Deployed", closed: "Closed",
}
export const STATUS_COLOR: Record<TicketStatus, string> = {
  new: "#5B8CFF", deferred: "#5E6B8C", in_development: "#9C7BFF",
  in_testing: "#F4B740", deployed: "#22D3A7", closed: "#4a5578",
}
export const PRI_CLASS: Record<Priority, string> = {
  P1: "pri-p1", P2: "pri-p2", P3: "pri-p3", P4: "pri-p4",
}
export const PRI_LABEL: Record<Priority, string> = {
  P1: "P1 · Critical", P2: "P2 · High", P3: "P3 · Medium", P4: "P4 · Low",
}
export const MODULE_LABEL: Record<string, string> = {
  conversational_query: "Conversational query", charts: "Dashboard / charts",
  datasource: "Datasource connection", agent_view: "Agent reasoning view",
  rbac: "User & role settings (RBAC)", audit_log: "Audit log", other: "Other",
}
export const SEVERITY_META: {
  value: Severity; title: string; hint: string; color: string
}[] = [
  { value: "blocks_work", title: "Blocks my work", hint: "Can't use a core feature", color: "var(--rose)" },
  { value: "major", title: "Major problem", hint: "Workaround exists but painful", color: "var(--amber)" },
  { value: "minor", title: "Minor issue", hint: "Annoying, not urgent", color: "var(--accent)" },
  { value: "suggestion", title: "Suggestion", hint: "Idea or polish", color: "var(--ink-3)" },
]

const AV_COLORS = [
  "linear-gradient(135deg,#5B8CFF,#9C7BFF)",
  "linear-gradient(135deg,#22D3A7,#5B8CFF)",
  "linear-gradient(135deg,#F4B740,#FF6B81)",
  "linear-gradient(135deg,#9C7BFF,#FF6B81)",
]
export function initials(name: string | null | undefined): string {
  if (!name) return "?"
  const parts = name.trim().split(/\s+/)
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase() || "?"
}
export function avatarColor(seed: string | null | undefined): string {
  if (!seed) return "var(--line)"
  let h = 0
  for (const c of seed) h = (h * 31 + c.charCodeAt(0)) >>> 0
  return AV_COLORS[h % AV_COLORS.length]
}
export function formatAge(iso: string): string {
  const then = new Date(iso).getTime()
  const mins = Math.max(0, Math.floor((Date.now() - then) / 60000))
  if (mins < 60) return `${mins}m`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h`
  return `${Math.floor(hrs / 24)}d`
}
export function formatWhen(iso: string): string {
  const age = formatAge(iso)
  return `${age} ago`
}
export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric", month: "short", day: "numeric",
  })
}

// "Filter by date" presets — value is the number of days back ("" = any time).
export const DATE_PRESETS: { value: string; label: string }[] = [
  { value: "", label: "Any time" },
  { value: "1", label: "Last 24 hours" },
  { value: "7", label: "Last 7 days" },
  { value: "30", label: "Last 30 days" },
  { value: "90", label: "Last 90 days" },
]
/** Convert a preset (days back) to an ISO timestamp for the `created_after` filter. */
export function sinceIso(days: string): string | undefined {
  if (!days) return undefined
  const d = new Date()
  d.setDate(d.getDate() - Number(days))
  return d.toISOString()
}

export function Avatar({ name, code }: { name?: string | null; code?: string | null }) {
  const label = code ?? initials(name)
  return (
    <div className="mini-av" style={{ background: avatarColor(name ?? code) }}>
      {label}
    </div>
  )
}

export function DateFilter({
  value, onChange,
}: {
  value: string
  onChange: (v: string) => void
}) {
  return (
    <div className="filter">
      Reported
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {DATE_PRESETS.map((d) => (
          <option key={d.value} value={d.value}>{d.label}</option>
        ))}
      </select>
    </div>
  )
}

export function StatusPill({ status }: { status: TicketStatus }) {
  return (
    <span className="status-pill">
      <span className="dot" style={{ background: STATUS_COLOR[status] }} />
      {STATUS_LABEL[status]}
    </span>
  )
}

export function PriChip({ priority }: { priority: Priority }) {
  return <span className={`chip ${PRI_CLASS[priority]}`}>{priority}</span>
}

export function MediaIcons({ recording, screenshot }: { recording: boolean; screenshot: boolean }) {
  if (!recording && !screenshot) return null
  return (
    <div className="has-media">
      {recording && (
        <span>
          <Icon.Video />
        </span>
      )}
      {screenshot && (
        <span>
          <Icon.Image />
        </span>
      )}
    </div>
  )
}

/* ---------- Icons (lucide-style strokes, matching the mockup) ---------- */
type IP = { size?: number }
const S = (size = 17) => ({
  width: size, height: size, viewBox: "0 0 24 24", fill: "none",
  stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round" as const, strokeLinejoin: "round" as const,
})
export const Icon = {
  Alert: (p: IP) => (<svg {...S(p.size)}><path d="M12 9v4m0 4h.01M10.3 3.3 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.3a2 2 0 0 0-3.4 0Z" /></svg>),
  Clipboard: (p: IP) => (<svg {...S(p.size)}><path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2M9 5a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2M9 5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2" /></svg>),
  Grid: (p: IP) => (<svg {...S(p.size)}><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /></svg>),
  Board: (p: IP) => (<svg {...S(p.size)}><path d="M3 5h6v14H3zM10 5h6v9h-6zM17 5h4v6h-4z" /></svg>),
  List: (p: IP) => (<svg {...S(p.size)}><line x1="8" y1="6" x2="21" y2="6" /><line x1="8" y1="12" x2="21" y2="12" /><line x1="8" y1="18" x2="21" y2="18" /><line x1="3" y1="6" x2="3.01" y2="6" /><line x1="3" y1="12" x2="3.01" y2="12" /><line x1="3" y1="18" x2="3.01" y2="18" /></svg>),
  Users: (p: IP) => (<svg {...S(p.size)}><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" /></svg>),
  Search: (p: IP) => (<svg {...S(p.size)}><circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" /></svg>),
  Video: (p: IP) => (<svg {...S(p.size)}><path d="M15 10l4.55-2.28A1 1 0 0 1 21 8.62v6.76a1 1 0 0 1-1.45.9L15 14M5 6h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2Z" /></svg>),
  Image: (p: IP) => (<svg {...S(p.size)}><rect x="3" y="3" width="18" height="18" rx="2" /><circle cx="9" cy="9" r="2" /><path d="m21 15-3.1-3.1a2 2 0 0 0-2.8 0L6 21" /></svg>),
  Upload: (p: IP) => (<svg {...S(p.size)}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" /></svg>),
  Check: (p: IP) => (<svg {...S(p.size)}><path d="M9 12l2 2 4-4m6 2a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>),
  Logout: (p: IP) => (<svg {...S(p.size)}><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" /></svg>),
  Play: (p: IP) => (<svg width={p.size ?? 16} height={p.size ?? 16} viewBox="0 0 24 24" fill="#fff"><path d="M8 5v14l11-7z" /></svg>),
}

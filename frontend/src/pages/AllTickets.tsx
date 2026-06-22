// Change log:
// [#002] 2026-06-22 — Sumeet — Added a Reporter column, a Reported date column, and a
//        "filter by date" dropdown.
// [#001] 2026-06-22 — Sumeet — File created. Team "All tickets" table with client / status /
//        priority filters + search. (For clients this same route renders their org-scoped
//        list via MyTickets; this page is team-only.)
import { useQuery } from "@tanstack/react-query"
import { useState } from "react"
import { api } from "../api"
import { useRouter } from "../router"
import { Avatar, DateFilter, formatDate, Icon, PriChip, sinceIso, StatusPill } from "../ui"

export function AllTickets() {
  const { navigate } = useRouter()
  const [org, setOrg] = useState("")
  const [status, setStatus] = useState("")
  const [priority, setPriority] = useState("")
  const [since, setSince] = useState("")
  const [q, setQ] = useState("")

  const orgs = useQuery({ queryKey: ["organizations"], queryFn: () => api.organizations() })
  const tickets = useQuery({
    queryKey: ["tickets", org, status, priority, since, q],
    queryFn: () =>
      api.listTickets({
        organization_id: org || undefined,
        status: status || undefined,
        priority: priority || undefined,
        created_after: sinceIso(since),
        q: q || undefined,
      }),
  })

  return (
    <div className="view">
      <div className="topbar">
        <div>
          <h1>All tickets</h1>
          <p>Sortable, filterable record of every reported bug.</p>
        </div>
        <div className="search">
          <Icon.Search size={15} />
          <input placeholder="Search title or ID…" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
      </div>

      <div className="toolbar">
        <div className="filter">
          <Icon.Users size={14} />
          Client
          <select value={org} onChange={(e) => setOrg(e.target.value)}>
            <option value="">All clients</option>
            {(orgs.data?.data ?? []).map((o) => (
              <option key={o.id} value={o.id}>{o.name}</option>
            ))}
          </select>
        </div>
        <div className="filter">
          Status
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All</option>
            <option value="new">New</option>
            <option value="deferred">Deferred</option>
            <option value="in_development">In Development</option>
            <option value="in_testing">In Testing</option>
            <option value="deployed">Deployed</option>
            <option value="closed">Closed</option>
          </select>
        </div>
        <div className="filter">
          Priority
          <select value={priority} onChange={(e) => setPriority(e.target.value)}>
            <option value="">All</option>
            <option value="P1">P1</option>
            <option value="P2">P2</option>
            <option value="P3">P3</option>
            <option value="P4">P4</option>
          </select>
        </div>
        <DateFilter value={since} onChange={setSince} />
        <div className="seg">
          <button onClick={() => navigate("/board")}>Board</button>
          <button className="on">List</button>
        </div>
      </div>

      <div className="tablewrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Summary</th>
              <th>Client</th>
              <th>Raised by</th>
              <th>Priority</th>
              <th>Status</th>
              <th>Assignee</th>
              <th>Reported</th>
            </tr>
          </thead>
          <tbody>
            {(tickets.data?.data ?? []).map((t) => (
              <tr key={t.id} onClick={() => navigate(`/tickets/${t.id}`)}>
                <td style={{ fontFamily: "var(--mono)", fontSize: 11.5, color: "var(--ink-3)" }}>
                  {t.reference}
                </td>
                <td style={{ fontWeight: 600, maxWidth: 320 }}>{t.title}</td>
                <td>
                  <span className="client-tag">{t.organization_name}</span>
                </td>
                <td style={{ fontSize: 12.5 }}>{t.reporter_name ?? "—"}</td>
                <td>
                  <PriChip priority={t.priority} />
                </td>
                <td>
                  <StatusPill status={t.status} />
                </td>
                <td>
                  {t.assignee_name ? (
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <Avatar name={t.assignee_name} />
                      <span style={{ fontSize: 12 }}>{t.assignee_name.split(" ")[0]}</span>
                    </div>
                  ) : (
                    <span className="muted">—</span>
                  )}
                </td>
                <td className="muted" style={{ whiteSpace: "nowrap" }}>{formatDate(t.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {(tickets.data?.data.length ?? 0) === 0 && !tickets.isLoading && (
          <div className="empty">No tickets match these filters.</div>
        )}
      </div>
    </div>
  )
}

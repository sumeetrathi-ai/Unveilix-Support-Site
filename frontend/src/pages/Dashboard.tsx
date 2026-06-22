// Change log:
// [#001] 2026-06-22 — Sumeet — File created. Team triage dashboard: KPI cards (open, breaching
//        SLA, deployed 7d, median resolution) + the six-column Kanban with client/assignee
//        filters.
import { useQuery } from "@tanstack/react-query"
import { useState } from "react"
import { api } from "../api"
import { Kanban } from "../components/Kanban"
import { useRouter } from "../router"
import { DateFilter, Icon, sinceIso } from "../ui"

export function Dashboard() {
  const { navigate } = useRouter()
  const [org, setOrg] = useState("")
  const [assignee, setAssignee] = useState("")
  const [since, setSince] = useState("")

  const stats = useQuery({ queryKey: ["dashboard"], queryFn: () => api.dashboard() })
  const orgs = useQuery({ queryKey: ["organizations"], queryFn: () => api.organizations() })
  const team = useQuery({ queryKey: ["teamMembers"], queryFn: () => api.teamMembers() })
  const board = useQuery({
    queryKey: ["board", org, assignee, since],
    queryFn: () =>
      api.board({
        organization_id: org || undefined,
        assignee_id: assignee || undefined,
        created_after: sinceIso(since),
      }),
  })

  const k = stats.data
  const median = k?.median_resolution_days != null ? `${k.median_resolution_days}d` : "—"

  return (
    <div className="view">
      <div className="topbar">
        <div>
          <h1>Triage dashboard</h1>
          <p>Everything across all client instances, at a glance.</p>
        </div>
      </div>

      <div className="kpis">
        <div className="kpi">
          <label>Open tickets</label>
          <div className="big">{k?.open_count ?? "—"}</div>
          <div className="delta">across all clients</div>
        </div>
        <div className="kpi amber">
          <label>Breaching SLA</label>
          <div className="big">{k?.breaching_sla_count ?? "—"}</div>
          <div className="delta down">needs attention</div>
        </div>
        <div className="kpi teal">
          <label>Deployed (7d)</label>
          <div className="big">{k?.deployed_last_7d ?? "—"}</div>
          <div className="delta">shipped this week</div>
        </div>
        <div className="kpi violet">
          <label>Median resolution</label>
          <div className="big">{median}</div>
          <div className="delta">closed tickets</div>
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
          Assignee
          <select value={assignee} onChange={(e) => setAssignee(e.target.value)}>
            <option value="">Anyone</option>
            {(team.data?.data ?? []).map((m) => (
              <option key={m.id} value={m.id}>{m.full_name}</option>
            ))}
          </select>
        </div>
        <DateFilter value={since} onChange={setSince} />
        <div className="seg">
          <button className="on">Board</button>
          <button onClick={() => navigate("/tickets")}>List</button>
        </div>
      </div>

      {board.isLoading || !board.data ? (
        <div className="center-state">
          <div className="spinner" />
        </div>
      ) : (
        <Kanban board={board.data} onOpen={(id) => navigate(`/tickets/${id}`)} />
      )}
    </div>
  )
}

// Change log:
// [#001] 2026-06-22 — Sumeet — File created. Team Board: full-lifecycle six-column Kanban with
//        client / priority / assignee / module filters.
import { useQuery } from "@tanstack/react-query"
import { useState } from "react"
import { api } from "../api"
import { Kanban } from "../components/Kanban"
import { useRouter } from "../router"
import { DateFilter, Icon, sinceIso } from "../ui"

export function Board() {
  const { navigate } = useRouter()
  const [org, setOrg] = useState("")
  const [priority, setPriority] = useState("")
  const [assignee, setAssignee] = useState("")
  const [module, setModule] = useState("")
  const [since, setSince] = useState("")

  const orgs = useQuery({ queryKey: ["organizations"], queryFn: () => api.organizations() })
  const team = useQuery({ queryKey: ["teamMembers"], queryFn: () => api.teamMembers() })
  const board = useQuery({
    queryKey: ["board", org, priority, assignee, module, since],
    queryFn: () =>
      api.board({
        organization_id: org || undefined,
        priority: priority || undefined,
        assignee_id: assignee || undefined,
        module: module || undefined,
        created_after: sinceIso(since),
      }),
  })

  return (
    <div className="view">
      <div className="topbar">
        <div>
          <h1>Board</h1>
          <p>Triage across the full lifecycle. Click any card for detail.</p>
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
          Priority
          <select value={priority} onChange={(e) => setPriority(e.target.value)}>
            <option value="">All</option>
            <option value="P1">P1 — Critical</option>
            <option value="P2">P2 — High</option>
            <option value="P3">P3 — Medium</option>
            <option value="P4">P4 — Low</option>
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
        <div className="filter">
          Module
          <select value={module} onChange={(e) => setModule(e.target.value)}>
            <option value="">All modules</option>
            <option value="conversational_query">Conversational query</option>
            <option value="charts">Charts</option>
            <option value="datasource">Datasource</option>
            <option value="agent_view">Agent view</option>
            <option value="rbac">RBAC</option>
            <option value="audit_log">Audit log</option>
            <option value="other">Other</option>
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

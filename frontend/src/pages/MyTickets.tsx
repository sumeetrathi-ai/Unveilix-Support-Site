// Change log:
// [#002] 2026-06-22 — Sumeet — Show who raised each ticket + the reported date, and a
//        "filter by date" dropdown.
// [#001] 2026-06-22 — Sumeet — File created. Client "My tickets": every ticket the user's org
//        has reported (tenant-scoped by the backend), with status. Cannot see other orgs.
import { useQuery } from "@tanstack/react-query"
import { useState } from "react"
import { api } from "../api"
import { useAuth } from "../auth"
import { useRouter } from "../router"
import { DateFilter, formatDate, sinceIso, StatusPill } from "../ui"

export function MyTickets() {
  const { navigate } = useRouter()
  const { user } = useAuth()
  const [since, setSince] = useState("")
  const { data, isLoading } = useQuery({
    queryKey: ["tickets", since],
    queryFn: () => api.listTickets({ created_after: sinceIso(since) }),
  })

  return (
    <div className="view">
      <div className="topbar">
        <div>
          <h1>My tickets</h1>
          <p>
            Everything your organization has reported, and where it stands. You can't see other
            companies' tickets.
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => navigate("/report")}>
          + New bug
        </button>
      </div>

      <div className="toolbar">
        <DateFilter value={since} onChange={setSince} />
      </div>

      {isLoading ? (
        <div className="center-state">
          <div className="spinner" />
        </div>
      ) : (data?.data.length ?? 0) === 0 ? (
        <div className="empty">No tickets yet. Report your first bug.</div>
      ) : (
        <div className="my-list">
          {data!.data.map((t) => (
            <div className="row" key={t.id} onClick={() => navigate(`/tickets/${t.id}`)}>
              <div>
                <div className="id">{t.reference}</div>
                <h4>{t.title}</h4>
                <div className="row-sub">
                  Raised by {t.reporter_name ?? "—"} · {formatDate(t.created_at)}
                </div>
              </div>
              <div className="progress">
                <StatusPill status={t.status} />
              </div>
            </div>
          ))}
        </div>
      )}
      <p className="hint" style={{ marginTop: 18 }}>
        Signed in as {user?.email}
      </p>
    </div>
  )
}

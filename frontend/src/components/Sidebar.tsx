// Change log:
// [#001] 2026-06-22 — Sumeet — File created. Role-aware sidebar (client vs Unveilix team nav),
//        brand, signed-in user footer + logout. Mirrors the mockup sidebar.
import { useQuery } from "@tanstack/react-query"
import { api } from "../api"
import { useAuth } from "../auth"
import { Link, useRouter } from "../router"
import { Icon, initials } from "../ui"

function NavItem({
  to, icon, label, count, active,
}: {
  to: string; icon: React.ReactNode; label: string; count?: number; active: boolean
}) {
  return (
    <Link to={to} className={`nav-item ${active ? "active" : ""}`}>
      {icon}
      {label}
      {count !== undefined && <span className="count">{count}</span>}
    </Link>
  )
}

export function Sidebar() {
  const { user, logout } = useAuth()
  const { path } = useRouter()
  const isTeam = user?.family === "unveilix"

  const countQuery = useQuery({
    queryKey: ["ticketCount", isTeam],
    queryFn: () => api.listTickets(),
    enabled: !!user,
  })
  const total = countQuery.data?.count

  const is = (p: string) => path === p || (p !== "/" && path.startsWith(p + "/"))

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="logo">
          <i />
        </div>
        <div>
          <b>Unveilix</b>
          <span>Support</span>
        </div>
      </div>

      {!isTeam ? (
        <div>
          <div className="nav-label">Support</div>
          <NavItem to="/report" icon={<Icon.Alert />} label="Report a bug" active={is("/report")} />
          <NavItem to="/tickets" icon={<Icon.Clipboard />} label="My tickets" count={total} active={is("/tickets")} />
        </div>
      ) : (
        <div>
          <div className="nav-label">Triage</div>
          <NavItem to="/dashboard" icon={<Icon.Grid />} label="Dashboard" active={is("/dashboard")} />
          <NavItem to="/board" icon={<Icon.Board />} label="Board" count={total} active={is("/board")} />
          <NavItem to="/tickets" icon={<Icon.List />} label="All tickets" active={is("/tickets")} />
          <div className="nav-label">Manage</div>
          <NavItem to="/clients" icon={<Icon.Users />} label="Clients" active={is("/clients")} />
        </div>
      )}

      <div className="side-foot">
        <div className="who">
          <div className="av">{initials(user?.full_name)}</div>
          <div>
            <b>{user?.full_name}</b>
            <small>
              {isTeam ? "Unveilix · Product team" : `${user?.role === "admin" ? "Admin" : "Reporter"}`}
            </small>
          </div>
        </div>
        <button className="logout-btn" onClick={logout}>
          <Icon.Logout size={13} /> Sign out
        </button>
      </div>
    </aside>
  )
}

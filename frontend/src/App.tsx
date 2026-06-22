// Change log:
// [#001] 2026-06-22 — Sumeet — File created. App shell: auth gate, redirect-by-family routing
//        (client → /report, unveilix → /dashboard), and the shared ticket detail drawer
//        rendered from the /tickets/:id URL.
import { useEffect } from "react"
import type { ReactNode } from "react"
import { useAuth } from "./auth"
import { Sidebar } from "./components/Sidebar"
import { TicketDrawer } from "./components/TicketDrawer"
import { AllTickets } from "./pages/AllTickets"
import { Board } from "./pages/Board"
import { Clients } from "./pages/Clients"
import { Dashboard } from "./pages/Dashboard"
import { Login } from "./pages/Login"
import { MyTickets } from "./pages/MyTickets"
import { Report } from "./pages/Report"
import { matchPath, useRouter } from "./router"

export default function App() {
  const { user, loading } = useAuth()
  const { path, navigate } = useRouter()

  const isTeam = user?.family === "unveilix"
  const onDetail = matchPath("/tickets/:id", path)

  const clientAllowed = (p: string) =>
    p === "/report" || p === "/tickets" || !!matchPath("/tickets/:id", p)
  const teamAllowed = (p: string) =>
    p === "/dashboard" || p === "/board" || p === "/tickets" || p === "/clients" ||
    !!matchPath("/tickets/:id", p)

  // Redirect by family for empty/invalid routes.
  useEffect(() => {
    if (loading || !user) return
    if (isTeam && !teamAllowed(path)) navigate("/dashboard")
    if (!isTeam && !clientAllowed(path)) navigate("/report")
  }, [loading, user, isTeam, path]) // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) {
    return (
      <div className="center-state">
        <div className="spinner" />
      </div>
    )
  }
  if (!user) return <Login />

  let page: ReactNode
  if (isTeam) {
    if (path === "/board") page = <Board />
    else if (path === "/clients") page = <Clients />
    else if (path === "/tickets" || onDetail) page = <AllTickets />
    else page = <Dashboard />
  } else {
    if (path === "/tickets" || onDetail) page = <MyTickets />
    else page = <Report />
  }

  return (
    <div className="shell">
      <Sidebar />
      <main className="main">{page}</main>
      <TicketDrawer ticketId={onDetail ? onDetail.id : null} onClose={() => navigate("/tickets")} />
    </div>
  )
}

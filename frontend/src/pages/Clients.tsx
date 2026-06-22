// Change log:
// [#001] 2026-06-22 — Sumeet — File created. Team "Clients": organizations with open/deployed
//        counts and primary contact (team only).
import { useQuery } from "@tanstack/react-query"
import { api } from "../api"

export function Clients() {
  const { data, isLoading } = useQuery({
    queryKey: ["organizations"],
    queryFn: () => api.organizations(),
  })

  return (
    <div className="view">
      <div className="topbar">
        <div>
          <h1>Clients</h1>
          <p>Organizations and their bug load.</p>
        </div>
      </div>

      {isLoading ? (
        <div className="center-state">
          <div className="spinner" />
        </div>
      ) : (
        <div className="tablewrap">
          <table>
            <thead>
              <tr>
                <th>Organization</th>
                <th>Plan</th>
                <th>Open</th>
                <th>Deployed</th>
                <th>Primary contact</th>
              </tr>
            </thead>
            <tbody>
              {(data?.data ?? []).map((o) => (
                <tr key={o.id} style={{ cursor: "default" }}>
                  <td style={{ fontWeight: 700 }}>{o.name}</td>
                  <td>
                    <span className="client-tag" style={{ textTransform: "capitalize" }}>{o.plan}</span>
                  </td>
                  <td style={{ fontWeight: 600 }}>{o.open_count}</td>
                  <td style={{ color: "var(--accent-2)", fontWeight: 600 }}>{o.deployed_count}</td>
                  <td style={{ fontFamily: "var(--mono)", fontSize: 11.5, color: "var(--ink-2)" }}>
                    {o.primary_contact ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

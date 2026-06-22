// Change log:
// [#002] 2026-06-22 — Sumeet — Replaced the hard-coded demo-credential hint (stale + a secret
//        leak for a public repo) with a generic account-domain hint.
// [#001] 2026-06-22 — Sumeet — File created. Login screen (replaces the mockup's demo role
//        chooser with real auth). Redirects by user family after sign-in.
import { useState } from "react"
import { ApiError } from "../api"
import { useAuth } from "../auth"
import { useRouter } from "../router"

export function Login() {
  const { login } = useAuth()
  const { navigate } = useRouter()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError("")
    setBusy(true)
    try {
      const user = await login(email, password)
      navigate(user.family === "unveilix" ? "/dashboard" : "/report")
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login failed")
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-wrap">
      <form className="login-card" onSubmit={submit}>
        <div className="logo">
          <i />
        </div>
        <h1>Unveilix Support</h1>
        <p className="sub">Sign in to report and track bugs.</p>

        {error && <div className="login-err">{error}</div>}

        <div className="field">
          <label>Email</label>
          <input
            type="email"
            autoFocus
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@company.com"
          />
        </div>
        <div className="field">
          <label>Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
          />
        </div>
        <button className="btn btn-primary" style={{ width: "100%", justifyContent: "center" }} disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>

        <div className="login-hint">
          Use your Carnera (<code>@getcarnera.com</code>) or Unveilix (<code>@unveilix.ai</code>)
          account to sign in.
        </div>
      </form>
    </div>
  )
}

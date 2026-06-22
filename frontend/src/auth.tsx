// Change log:
// [#001] 2026-06-22 — Sumeet — File created. Auth context: loads the current user from a
//        stored JWT, exposes login/logout, and drives the redirect-by-family behavior.
import { createContext, useContext, useEffect, useState } from "react"
import type { ReactNode } from "react"
import { api, clearToken, getToken, setToken } from "./api"
import type { User } from "./types"

interface AuthValue {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<User>
  logout: () => void
}
const AuthCtx = createContext<AuthValue>({
  user: null, loading: true, login: async () => ({}) as User, logout: () => {},
})
export const useAuth = () => useContext(AuthCtx)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!getToken()) {
      setLoading(false)
      return
    }
    api
      .me()
      .then(setUser)
      .catch(() => clearToken())
      .finally(() => setLoading(false))
  }, [])

  const login = async (email: string, password: string) => {
    const res = await api.login(email, password)
    setToken(res.access_token)
    setUser(res.user)
    return res.user
  }

  const logout = () => {
    clearToken()
    setUser(null)
    window.location.href = "/login"
  }

  return (
    <AuthCtx.Provider value={{ user, loading, login, logout }}>{children}</AuthCtx.Provider>
  )
}

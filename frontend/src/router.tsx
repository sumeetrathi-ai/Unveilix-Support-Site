// Change log:
// [#001] 2026-06-22 — Sumeet — File created. Tiny dependency-free router (history API) so the
//        app can satisfy the spec's routes without adding a routing library to the Bun build.
import {
  createContext, useCallback, useContext, useEffect, useState,
} from "react"
import type { ReactNode } from "react"

interface RouterValue {
  path: string
  navigate: (to: string) => void
}
const RouterCtx = createContext<RouterValue>({ path: "/", navigate: () => {} })

export function RouterProvider({ children }: { children: ReactNode }) {
  const [path, setPath] = useState(window.location.pathname || "/")
  useEffect(() => {
    const onPop = () => setPath(window.location.pathname)
    window.addEventListener("popstate", onPop)
    return () => window.removeEventListener("popstate", onPop)
  }, [])
  const navigate = useCallback((to: string) => {
    if (to !== window.location.pathname) {
      window.history.pushState({}, "", to)
      setPath(to)
    }
  }, [])
  return <RouterCtx.Provider value={{ path, navigate }}>{children}</RouterCtx.Provider>
}

export const useRouter = () => useContext(RouterCtx)

export function Link({
  to, className, children, onClick,
}: {
  to: string
  className?: string
  children: ReactNode
  onClick?: () => void
}) {
  const { navigate } = useRouter()
  return (
    <a
      href={to}
      className={className}
      onClick={(e) => {
        e.preventDefault()
        onClick?.()
        navigate(to)
      }}
    >
      {children}
    </a>
  )
}

/** Match a `/tickets/:id` style pattern; returns the param map or null. */
export function matchPath(pattern: string, path: string): Record<string, string> | null {
  const pp = pattern.split("/").filter(Boolean)
  const xp = path.split("/").filter(Boolean)
  if (pp.length !== xp.length) return null
  const params: Record<string, string> = {}
  for (let i = 0; i < pp.length; i++) {
    if (pp[i].startsWith(":")) params[pp[i].slice(1)] = decodeURIComponent(xp[i])
    else if (pp[i] !== xp[i]) return null
  }
  return params
}

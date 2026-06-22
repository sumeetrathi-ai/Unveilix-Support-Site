// Change log:
// [#001] 2026-06-22 — Sumeet — File created. Thin typed fetch client for the Unveilix API.
//        Adds the bearer token, handles JSON + multipart, and exposes typed endpoint calls.
import type {
  DashboardStats, LoginResponse, OrganizationsPublic, TicketBoard, TicketCreate,
  TicketDetail, TicketsPublic, TicketUpdate, User, UsersPublic,
} from "./types"

const RAW = (import.meta.env.VITE_API_URL as string | undefined) || ""
export const API = RAW.replace(/\/$/, "") + "/api"

const TOKEN_KEY = "access_token"
export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (t: string) => localStorage.setItem(TOKEN_KEY, t)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const headers = new Headers(opts.headers)
  const token = getToken()
  if (token) headers.set("Authorization", `Bearer ${token}`)
  const res = await fetch(`${API}${path}`, { ...opts, headers })
  if (res.status === 401) {
    clearToken()
    if (!path.startsWith("/auth/login")) window.location.href = "/login"
  }
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail)
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

function qs(params: Record<string, string | undefined | null>): string {
  const p = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v) p.set(k, v)
  const s = p.toString()
  return s ? `?${s}` : ""
}

export const api = {
  // auth
  login: (email: string, password: string) =>
    request<LoginResponse>("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<User>("/auth/me"),

  // tickets
  listTickets: (filters: Record<string, string | undefined | null> = {}) =>
    request<TicketsPublic>(`/tickets${qs(filters)}`),
  board: (filters: Record<string, string | undefined | null> = {}) =>
    request<TicketBoard>(`/tickets/board${qs(filters)}`),
  getTicket: (id: string) => request<TicketDetail>(`/tickets/${id}`),
  createTicket: (payload: TicketCreate) =>
    request<TicketDetail>("/tickets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  updateTicket: (id: string, payload: TicketUpdate) =>
    request<TicketDetail>(`/tickets/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  addComment: (id: string, body: string, is_internal: boolean) =>
    request(`/tickets/${id}/comments`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ body, is_internal }),
    }),
  uploadAttachment: (id: string, file: File | Blob, filename: string) => {
    const fd = new FormData()
    fd.append("file", file, filename)
    return request(`/tickets/${id}/attachments`, { method: "POST", body: fd })
  },

  // org / dashboard / team
  organizations: () => request<OrganizationsPublic>("/organizations"),
  dashboard: () => request<DashboardStats>("/dashboard/stats"),
  teamMembers: () => request<UsersPublic>("/users/team"),

  // media: fetch attachment bytes (with auth) and return an object URL
  attachmentObjectUrl: async (id: string): Promise<string> => {
    const res = await fetch(`${API}/attachments/${id}`, {
      headers: getToken() ? { Authorization: `Bearer ${getToken()}` } : {},
    })
    if (!res.ok) throw new ApiError(res.status, "attachment fetch failed")
    return URL.createObjectURL(await res.blob())
  },
}

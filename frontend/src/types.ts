// Change log:
// [#001] 2026-06-22 — Sumeet — File created. TypeScript types mirroring the FastAPI schemas.

export type Family = "client" | "unveilix"
export type Role = "client_user" | "agent" | "admin"
export type Module =
  | "conversational_query" | "charts" | "datasource" | "agent_view"
  | "rbac" | "audit_log" | "other"
export type Severity = "blocks_work" | "major" | "minor" | "suggestion"
export type Priority = "P1" | "P2" | "P3" | "P4"
export type TicketStatus =
  | "new" | "deferred" | "in_development" | "in_testing" | "deployed" | "closed"

export interface User {
  id: string
  email: string
  full_name: string | null
  family: Family
  role: Role
  organization_id: string | null
  is_active: boolean
}

export interface TicketSummary {
  id: string
  reference: string
  organization_id: string
  organization_name: string
  title: string
  module: Module
  severity: Severity
  priority: Priority
  status: TicketStatus
  reporter_id: string
  reporter_name: string | null
  assignee_id: string | null
  assignee_name: string | null
  attachment_count: number
  comment_count: number
  created_at: string
  updated_at: string | null
  closed_at: string | null
}

export interface AttachmentPublic {
  id: string
  ticket_id: string
  kind: "screenshot" | "recording"
  filename: string
  content_type: string
  size_bytes: number | null
  created_at: string
}

export interface CommentPublic {
  id: string
  ticket_id: string
  author_id: string
  author_name: string | null
  body: string
  is_internal: boolean
  created_at: string
}

export interface ActivityPublic {
  id: string
  ticket_id: string
  actor_id: string
  actor_name: string | null
  action: string
  detail: Record<string, unknown> | null
  created_at: string
}

export interface TicketDetail extends TicketSummary {
  description: string | null
  environment: Record<string, unknown> | null
  rca: string | null
  attachments: AttachmentPublic[]
  comments: CommentPublic[]
  activity: ActivityPublic[]
}

export interface TicketsPublic {
  data: TicketSummary[]
  count: number
}

export interface TicketBoard {
  columns: Record<TicketStatus, TicketSummary[]>
}

export interface OrganizationWithCounts {
  id: string
  name: string
  plan: "growth" | "enterprise"
  is_active: boolean
  created_at: string
  open_count: number
  deployed_count: number
  primary_contact: string | null
}

export interface OrganizationsPublic {
  data: OrganizationWithCounts[]
  count: number
}

export interface DashboardStats {
  open_count: number
  breaching_sla_count: number
  deployed_last_7d: number
  median_resolution_days: number | null
}

export interface UsersPublic {
  data: User[]
  count: number
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

export interface TicketCreate {
  title: string
  description?: string | null
  module: Module
  severity: Severity
  environment?: Record<string, unknown> | null
  organization_id?: string | null
}

export interface TicketUpdate {
  status?: TicketStatus
  priority?: Priority
  assignee_id?: string | null
  rca?: string | null
}

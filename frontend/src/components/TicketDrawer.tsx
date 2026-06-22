// Change log:
// [#002] 2026-06-22 — Sumeet — Closing a ticket now requires a root-cause analysis: selecting
//        "Closed" reveals a required RCA box. The RCA is INTERNAL — shown/editable only for
//        the Unveilix team; clients never see it (backend also strips it from their responses).
// [#001] 2026-06-22 — Sumeet — File created. The shared ticket detail drawer. Team users can
//        edit status/priority/assignee and post internal notes; clients see read-only status
//        and public comments only (the backend already strips internal comments for clients).
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useEffect, useState } from "react"
import { api, ApiError } from "../api"
import { useAuth } from "../auth"
import { useToast } from "../toast"
import type { Priority, TicketStatus } from "../types"
import {
  Avatar, Icon, MODULE_LABEL, PRI_LABEL, PriChip, STATUS_LABEL, STATUS_ORDER,
  formatWhen,
} from "../ui"

const ACTION_VERB: Record<string, string> = {
  created: "reported the bug",
  status_changed: "changed status",
  assigned: "updated the assignee",
  priority_changed: "changed priority",
  commented: "commented",
  attachment_added: "added an attachment",
}

export function TicketDrawer({ ticketId, onClose }: { ticketId: string | null; onClose: () => void }) {
  const { user } = useAuth()
  const isTeam = user?.family === "unveilix"
  const qc = useQueryClient()
  const toast = useToast()

  const { data: ticket, isLoading } = useQuery({
    queryKey: ["ticket", ticketId],
    queryFn: () => api.getTicket(ticketId!),
    enabled: !!ticketId,
  })

  const teamQuery = useQuery({
    queryKey: ["teamMembers"],
    queryFn: () => api.teamMembers(),
    enabled: !!ticketId && isTeam,
  })

  const [media, setMedia] = useState<Record<string, string>>({})
  useEffect(() => {
    if (!ticket) return
    let revoked: string[] = []
    Promise.all(
      ticket.attachments.map(async (a) => {
        try {
          const url = await api.attachmentObjectUrl(a.id)
          revoked.push(url)
          return [a.id, url] as const
        } catch {
          return [a.id, ""] as const
        }
      }),
    ).then((pairs) => setMedia(Object.fromEntries(pairs)))
    return () => {
      revoked.forEach((u) => u && URL.revokeObjectURL(u))
      setMedia({})
    }
  }, [ticket?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  const update = useMutation({
    mutationFn: (payload: Parameters<typeof api.updateTicket>[1]) =>
      api.updateTicket(ticketId!, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ticket", ticketId] })
      qc.invalidateQueries({ queryKey: ["tickets"] })
      qc.invalidateQueries({ queryKey: ["board"] })
      qc.invalidateQueries({ queryKey: ["dashboard"] })
      toast.show("Ticket updated")
    },
    onError: (e) => toast.show((e as ApiError).message || "Update failed", "err"),
  })

  // RCA-on-close: a bug can only be closed with a root-cause analysis.
  const [pendingClose, setPendingClose] = useState(false)
  const [rcaDraft, setRcaDraft] = useState("")
  const [rcaEdit, setRcaEdit] = useState("")
  useEffect(() => {
    setPendingClose(false)
    setRcaDraft("")
    setRcaEdit(ticket?.rca ?? "")
  }, [ticket?.id, ticket?.rca])

  function changeStatus(value: string) {
    if (value === "closed" && !(ticket?.rca && ticket.rca.trim())) {
      setPendingClose(true) // require an RCA before closing
      return
    }
    setPendingClose(false)
    update.mutate({ status: value as TicketStatus })
  }

  const [commentBody, setCommentBody] = useState("")
  const [internal, setInternal] = useState(false)
  const comment = useMutation({
    mutationFn: () => api.addComment(ticketId!, commentBody, internal && !!isTeam),
    onSuccess: () => {
      setCommentBody("")
      setInternal(false)
      qc.invalidateQueries({ queryKey: ["ticket", ticketId] })
      qc.invalidateQueries({ queryKey: ["tickets"] })
      toast.show("Comment added")
    },
    onError: (e) => toast.show((e as ApiError).message || "Could not comment", "err"),
  })

  const open = !!ticketId
  return (
    <>
      <div className={`drawer-bg ${open ? "open" : ""}`} onClick={onClose} />
      <aside className={`drawer ${open ? "open" : ""}`}>
        {isLoading || !ticket ? (
          <div className="center-state" style={{ minHeight: "100vh" }}>
            <div className="spinner" />
          </div>
        ) : (
          <>
            <div className="drawer-head">
              <button className="close-x" onClick={onClose}>
                ✕
              </button>
              <div className="id">{ticket.reference}</div>
              <h3>{ticket.title}</h3>
              <div className="card-meta">
                <PriChip priority={ticket.priority} />
                <span className="client-tag">{ticket.organization_name}</span>
              </div>
            </div>

            <div className="drawer-body">
              <div className="d-grid">
                <div className="d-field">
                  <label>Status</label>
                  {isTeam ? (
                    <select
                      value={pendingClose ? "closed" : ticket.status}
                      onChange={(e) => changeStatus(e.target.value)}
                    >
                      {STATUS_ORDER.map((s) => (
                        <option key={s} value={s}>{STATUS_LABEL[s]}</option>
                      ))}
                    </select>
                  ) : (
                    <div className="static">{STATUS_LABEL[ticket.status]}</div>
                  )}
                </div>

                <div className="d-field">
                  <label>Assigned to</label>
                  {isTeam ? (
                    <select
                      value={ticket.assignee_id ?? ""}
                      onChange={(e) =>
                        update.mutate({ assignee_id: e.target.value || null })
                      }
                    >
                      <option value="">Unassigned</option>
                      {(teamQuery.data?.data ?? []).map((m) => (
                        <option key={m.id} value={m.id}>{m.full_name}</option>
                      ))}
                    </select>
                  ) : (
                    <div className="static">{ticket.assignee_name ?? "Unassigned"}</div>
                  )}
                </div>

                <div className="d-field">
                  <label>Priority</label>
                  {isTeam ? (
                    <select
                      value={ticket.priority}
                      onChange={(e) => update.mutate({ priority: e.target.value as Priority })}
                    >
                      {(["P1", "P2", "P3", "P4"] as Priority[]).map((p) => (
                        <option key={p} value={p}>{PRI_LABEL[p]}</option>
                      ))}
                    </select>
                  ) : (
                    <div className="static">{PRI_LABEL[ticket.priority]}</div>
                  )}
                </div>

                <div className="d-field">
                  <label>Module</label>
                  <div className="static">{MODULE_LABEL[ticket.module]}</div>
                </div>
              </div>

              {pendingClose && (
                <div className="rca-required">
                  <div className="d-sec-title" style={{ marginTop: 0 }}>
                    Root cause analysis — required to close
                  </div>
                  <textarea
                    autoFocus
                    placeholder="What was the root cause, and how was it fixed?"
                    value={rcaDraft}
                    onChange={(e) => setRcaDraft(e.target.value)}
                  />
                  <div className="comment-actions">
                    <button
                      className="btn btn-ghost"
                      onClick={() => {
                        setPendingClose(false)
                        setRcaDraft("")
                      }}
                    >
                      Cancel
                    </button>
                    <button
                      className="btn btn-primary"
                      disabled={!rcaDraft.trim() || update.isPending}
                      onClick={() =>
                        update.mutate(
                          { status: "closed", rca: rcaDraft },
                          { onSuccess: () => { setPendingClose(false); setRcaDraft("") } },
                        )
                      }
                    >
                      {update.isPending ? "Closing…" : "Close ticket"}
                    </button>
                  </div>
                </div>
              )}

              {/* RCA is internal — only rendered for the Unveilix team (the backend also
                  strips it from client responses). */}
              {!pendingClose && isTeam && (ticket.rca || ticket.status === "closed") && (
                <>
                  <div className="d-sec-title">
                    Root cause analysis
                    <span className="tag-internal" style={{ marginLeft: 8 }}>Internal</span>
                  </div>
                  <div className="comment-box" style={{ marginTop: 0, marginBottom: 22 }}>
                    <textarea
                      placeholder="Document the root cause… (clients don't see this)"
                      value={rcaEdit}
                      onChange={(e) => setRcaEdit(e.target.value)}
                    />
                    <div className="comment-actions">
                      <button
                        className="btn btn-primary"
                        disabled={
                          update.isPending ||
                          rcaEdit.trim() === (ticket.rca ?? "").trim()
                        }
                        onClick={() => update.mutate({ rca: rcaEdit })}
                      >
                        Save RCA
                      </button>
                    </div>
                  </div>
                </>
              )}

              {ticket.description && (
                <>
                  <div className="d-sec-title">Description</div>
                  <p style={{ fontSize: 13, color: "var(--ink-2)", marginBottom: 22 }}>
                    {ticket.description}
                  </p>
                </>
              )}

              {ticket.attachments.length > 0 && (
                <>
                  <div className="d-sec-title">Attached by reporter</div>
                  <div className="media-row">
                    {ticket.attachments.map((a) => (
                      <div className="media" key={a.id}>
                        {a.kind === "recording" ? (
                          media[a.id] ? (
                            <video src={media[a.id]} controls />
                          ) : (
                            <div style={{ height: 130, display: "grid", placeItems: "center", color: "var(--ink-3)" }}>
                              <Icon.Play size={28} />
                            </div>
                          )
                        ) : media[a.id] ? (
                          <img src={media[a.id]} alt={a.filename} />
                        ) : (
                          <div style={{ height: 130, display: "grid", placeItems: "center", color: "var(--ink-3)" }}>
                            <Icon.Image size={26} />
                          </div>
                        )}
                        <small>{a.filename}</small>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {ticket.environment && Object.keys(ticket.environment).length > 0 && (
                <>
                  <div className="d-sec-title">Auto-captured diagnostics</div>
                  <div className="env-box">
                    {Object.entries(ticket.environment).map(([k, v]) => (
                      <div className="env-row" key={k}>
                        <span>{k.replace(/_/g, " ")}</span>
                        <b>{String(v)}</b>
                      </div>
                    ))}
                    <div className="env-row">
                      <span>reported by</span>
                      <b>{ticket.reporter_name}</b>
                    </div>
                  </div>
                </>
              )}

              <div className="d-sec-title">Activity</div>
              <div className="timeline">
                {ticket.activity.map((a) => (
                  <div className="tl" key={a.id}>
                    <b>{a.actor_name ?? "Someone"}</b> {ACTION_VERB[a.action] ?? a.action}
                    <span>
                      {formatWhen(a.created_at)}
                      {a.detail?.to ? ` · → ${String(a.detail.to)}` : ""}
                    </span>
                  </div>
                ))}
              </div>

              <div className="d-sec-title" style={{ marginTop: 22 }}>
                Comments
              </div>
              {ticket.comments.length === 0 && (
                <p className="muted" style={{ fontSize: 12.5, marginBottom: 10 }}>
                  No comments yet.
                </p>
              )}
              {ticket.comments.map((c) => (
                <div className={`comment ${c.is_internal ? "internal" : ""}`} key={c.id}>
                  <div className="meta">
                    <Avatar name={c.author_name} />
                    <b style={{ color: "var(--ink)" }}>{c.author_name}</b>
                    <span>· {formatWhen(c.created_at)}</span>
                    {c.is_internal && <span className="tag-internal">Internal</span>}
                  </div>
                  {c.body}
                </div>
              ))}

              <div className="comment-box">
                <textarea
                  placeholder={
                    isTeam
                      ? internal
                        ? "Add an internal note… (clients don't see this)"
                        : "Reply to the client…"
                      : "Add a comment…"
                  }
                  value={commentBody}
                  onChange={(e) => setCommentBody(e.target.value)}
                />
                <div className="comment-actions">
                  {isTeam && (
                    <label className="toggle">
                      <input
                        type="checkbox"
                        checked={internal}
                        onChange={(e) => setInternal(e.target.checked)}
                      />
                      Internal note
                    </label>
                  )}
                  <button
                    className="btn btn-primary"
                    disabled={!commentBody.trim() || comment.isPending}
                    onClick={() => comment.mutate()}
                  >
                    {comment.isPending ? "Sending…" : "Send"}
                  </button>
                </div>
              </div>
            </div>
          </>
        )}
      </aside>
    </>
  )
}

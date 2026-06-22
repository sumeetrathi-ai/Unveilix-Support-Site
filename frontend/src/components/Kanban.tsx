// Change log:
// [#002] 2026-06-22 — Sumeet — Show who raised the bug (reporter) and the reported date on
//        each card.
// [#001] 2026-06-22 — Sumeet — File created. Six-column Kanban (the spec's exact statuses) +
//        ticket cards, used by the team Dashboard and Board.
import type { TicketBoard, TicketSummary } from "../types"
import {
  Avatar, formatDate, MediaIcons, PriChip, STATUS_COLOR, STATUS_LABEL, STATUS_ORDER,
} from "../ui"

export function TicketCard({ t, onOpen }: { t: TicketSummary; onOpen: (id: string) => void }) {
  return (
    <div className="card" onClick={() => onOpen(t.id)}>
      <div className="id">{t.reference}</div>
      <h4>{t.title}</h4>
      <div className="card-meta">
        <PriChip priority={t.priority} />
        <span className="client-tag">{t.organization_name}</span>
      </div>
      <div className="card-sub">
        Raised by {t.reporter_name ?? "—"} · {formatDate(t.created_at)}
      </div>
      <div className="card-foot">
        <Avatar name={t.assignee_name} />
        <MediaIcons recording={t.attachment_count > 0} screenshot={false} />
      </div>
    </div>
  )
}

export function Kanban({ board, onOpen }: { board: TicketBoard; onOpen: (id: string) => void }) {
  return (
    <div className="board">
      {STATUS_ORDER.map((s) => {
        const items = board.columns[s] ?? []
        return (
          <div className="col" key={s}>
            <div className="col-head">
              <span className="dot" style={{ background: STATUS_COLOR[s] }} />
              {STATUS_LABEL[s]}
              <span className="num">{items.length}</span>
            </div>
            {items.map((t) => (
              <TicketCard key={t.id} t={t} onOpen={onOpen} />
            ))}
          </div>
        )
      })}
    </div>
  )
}

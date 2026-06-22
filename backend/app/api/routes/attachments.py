"""
Change log:
[#003] 2026-06-22 — Sumeet — Route uploads/downloads through the pluggable storage backend
        (app.core.storage; local or s3/Backblaze B2). Download now PROXIES the bytes through
        this authenticated, tenant-scoped endpoint via StreamingResponse (the access check
        runs BEFORE any storage read), instead of FileResponse off local disk. Type/size
        limits and tenant scoping are unchanged.
[#002] 2026-06-22 — Sumeet — Strip media-type parameters before validating the upload type,
        so MediaRecorder's `video/webm;codecs=vp9` (and `;codecs=vp8`, etc.) is accepted. The
        base type (e.g. `video/webm`) is what we validate, map to kind, and store.
[#001] 2026-06-22 — Sumeet — File created. Attachment upload + streaming (spec §4).
        Upload is tenant-scoped (a client can only attach to their own org's ticket —
        test #10) and enforces allowed content types + a max size. Files are saved under
        the uploads Docker volume; only metadata is stored in the DB. Streaming is scoped
        the same way (404 if the attachment's ticket is out of tenant).
"""

import os
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app import crud
from app.api.deps import CurrentUser, SessionDep, scoped_ticket_or_404
from app.core.config import settings
from app.core.storage import get_storage
from app.models import (
    ActivityAction,
    Attachment,
    AttachmentKind,
    AttachmentPublic,
)

router = APIRouter(tags=["attachments"])

# Map the allowed content types to their attachment kind (spec §3/§4).
_KIND_BY_TYPE = {
    "image/png": AttachmentKind.screenshot,
    "image/jpeg": AttachmentKind.screenshot,
    "video/webm": AttachmentKind.recording,
    "video/mp4": AttachmentKind.recording,
}


@router.post(
    "/tickets/{ticket_id}/attachments",
    response_model=AttachmentPublic,
    status_code=201,
)
async def upload_attachment(
    session: SessionDep,
    current_user: CurrentUser,
    ticket_id: uuid.UUID,
    file: UploadFile = File(...),
) -> AttachmentPublic:
    """Upload a screenshot or screen recording to a ticket (tenant-scoped)."""
    # Scope first: a client uploading to another org's ticket gets 404 (test #10).
    ticket = scoped_ticket_or_404(
        session=session, current_user=current_user, ticket_id=ticket_id
    )

    # Strip media-type parameters (e.g. "video/webm;codecs=vp9") -> base type.
    raw_type = (file.content_type or "").lower()
    base_type = raw_type.split(";")[0].strip()
    if base_type not in settings.ALLOWED_UPLOAD_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type '{raw_type}'. Allowed: "
            + ", ".join(settings.ALLOWED_UPLOAD_TYPES),
        )

    data = await file.read()
    if len(data) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=422,
            detail=f"File too large (max {settings.MAX_UPLOAD_BYTES // (1024 * 1024)} MB)",
        )

    kind = _KIND_BY_TYPE[base_type]
    safe_name = os.path.basename(file.filename or "upload")
    # Storage key: <ticket_id>/<uuid>_<original-name> — same layout for local + S3.
    key = f"{ticket.id}/{uuid.uuid4().hex}_{safe_name}"
    get_storage().save(key=key, data=data, content_type=base_type)

    attachment = Attachment(
        ticket_id=ticket.id,
        kind=kind.value,
        filename=safe_name,
        content_type=base_type,
        size_bytes=len(data),
        storage_path=key,
    )
    session.add(attachment)
    session.flush()
    crud.record_activity(
        session=session,
        ticket_id=ticket.id,
        actor_id=current_user.id,
        action=ActivityAction.attachment_added,
        detail={"kind": kind.value, "filename": safe_name},
        commit=False,
    )
    session.commit()
    session.refresh(attachment)
    return AttachmentPublic.model_validate(attachment, from_attributes=True)


@router.get("/attachments/{attachment_id}")
def stream_attachment(
    session: SessionDep, current_user: CurrentUser, attachment_id: uuid.UUID
) -> StreamingResponse:
    """Stream an attachment's bytes, scoped to the caller's tenant.

    The access check (scoped_ticket_or_404) runs BEFORE any storage read, so a client can
    never fetch another org's file regardless of the storage backend. Bytes are proxied
    through this authenticated endpoint (we deliberately do NOT hand out presigned URLs —
    see PROGRESS.md for the rationale)."""
    attachment = session.get(Attachment, attachment_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    # Enforce tenant scope via the parent ticket (404 if out of tenant) — BEFORE reading bytes.
    scoped_ticket_or_404(
        session=session, current_user=current_user, ticket_id=attachment.ticket_id
    )
    storage = get_storage()
    if not storage.exists(attachment.storage_path):
        raise HTTPException(status_code=404, detail="File missing from storage")
    return StreamingResponse(
        storage.open_stream(attachment.storage_path),
        media_type=attachment.content_type,
        headers={"Content-Disposition": f'inline; filename="{attachment.filename}"'},
    )

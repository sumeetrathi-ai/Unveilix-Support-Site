"""
Change log:
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
from fastapi.responses import FileResponse

from app import crud
from app.api.deps import CurrentUser, SessionDep, scoped_ticket_or_404
from app.core.config import settings
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

    # [#002] --by Sumeet (2026-06-22)
    # Before: content_type = file.content_type; exact-matched against ALLOWED_UPLOAD_TYPES.
    # After: strip media-type parameters (everything after ';') first, so a MediaRecorder
    #        clip reported as "video/webm;codecs=vp9" validates as its base "video/webm".
    # Why: the screen-recording upload was 422'ing because the browser includes the codec in
    #      the Blob's MIME type; the allowed list only holds base types.
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
    # Store under <uploads>/<ticket_id>/<uuid>_<original-name>; persist a RELATIVE path.
    safe_name = os.path.basename(file.filename or "upload")
    rel_dir = str(ticket.id)
    rel_path = os.path.join(rel_dir, f"{uuid.uuid4().hex}_{safe_name}")
    abs_dir = os.path.join(settings.UPLOADS_DIR, rel_dir)
    os.makedirs(abs_dir, exist_ok=True)
    with open(os.path.join(settings.UPLOADS_DIR, rel_path), "wb") as fh:
        fh.write(data)

    attachment = Attachment(
        ticket_id=ticket.id,
        kind=kind.value,
        filename=safe_name,
        content_type=base_type,
        size_bytes=len(data),
        storage_path=rel_path,
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
) -> FileResponse:
    """Stream an attachment's bytes, scoped to the caller's tenant."""
    attachment = session.get(Attachment, attachment_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    # Enforce tenant scope via the parent ticket (404 if out of tenant).
    scoped_ticket_or_404(
        session=session, current_user=current_user, ticket_id=attachment.ticket_id
    )
    abs_path = os.path.join(settings.UPLOADS_DIR, attachment.storage_path)
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="File missing from storage")
    return FileResponse(
        abs_path,
        media_type=attachment.content_type,
        filename=attachment.filename,
    )

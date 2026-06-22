"""
Change log:
[#001] 2026-06-22 — Sumeet — File created. The acceptance-gate suite: the 10 tenant-
        isolation cases from spec §5, auth tests (login / me / wrong-role 403), and a
        happy-path ticket lifecycle (create -> assign -> status walk -> close) asserting
        the activity timeline. Every isolation case maps to a spec §5 item (noted inline).
"""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import Family, Organization, Role, UserCreate
from tests.utils.fake_s3 import FakeS3Client
from tests.utils.utils import random_email, random_lower_string

API = settings.API_V1_STR
PW = "tenantpass123"


def _login(client: TestClient, email: str, password: str) -> dict[str, str]:
    r = client.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def tenant(client: TestClient, db: Session) -> SimpleNamespace:
    """Two orgs, a client user in each, a team agent, and one ticket per org."""
    org_a = Organization(name=f"OrgA-{random_lower_string()[:10]}", plan="enterprise")
    org_b = Organization(name=f"OrgB-{random_lower_string()[:10]}", plan="growth")
    db.add(org_a)
    db.add(org_b)
    db.commit()
    db.refresh(org_a)
    db.refresh(org_b)

    client_a = crud.create_user(
        session=db,
        user_create=UserCreate(
            email=random_email(), password=PW, full_name="Client A",
            family=Family.client, role=Role.client_user, organization_id=org_a.id,
        ),
    )
    client_b = crud.create_user(
        session=db,
        user_create=UserCreate(
            email=random_email(), password=PW, full_name="Client B",
            family=Family.client, role=Role.client_user, organization_id=org_b.id,
        ),
    )
    agent = crud.create_user(
        session=db,
        user_create=UserCreate(
            email=random_email(), password=PW, full_name="Team Agent",
            family=Family.unveilix, role=Role.agent,
        ),
    )

    h_a = _login(client, client_a.email, PW)
    h_b = _login(client, client_b.email, PW)
    h_agent = _login(client, agent.email, PW)

    ticket_a = client.post(
        f"{API}/tickets", headers=h_a,
        json={"title": "Chart fails to render", "module": "charts",
              "severity": "blocks_work", "environment": {"browser": "Chrome"}},
    )
    assert ticket_a.status_code == 201, ticket_a.text
    ticket_b = client.post(
        f"{API}/tickets", headers=h_b,
        json={"title": "Agent panel freezes", "module": "agent_view", "severity": "major"},
    )
    assert ticket_b.status_code == 201, ticket_b.text

    return SimpleNamespace(
        org_a=org_a, org_b=org_b, client_a=client_a, client_b=client_b, agent=agent,
        h_a=h_a, h_b=h_b, h_agent=h_agent,
        ta=ticket_a.json(), tb=ticket_b.json(),
    )


# ===========================================================================
# Tenant isolation — the 10 acceptance cases (spec §5)
# ===========================================================================
def test_iso_01_client_list_only_own_org(client: TestClient, tenant: SimpleNamespace) -> None:
    """#1 Client A GET /tickets -> only Org A tickets, zero Org B."""
    r = client.get(f"{API}/tickets", headers=tenant.h_a)
    assert r.status_code == 200
    data = r.json()["data"]
    assert all(t["organization_id"] == str(tenant.org_a.id) for t in data)
    assert all(t["id"] != tenant.tb["id"] for t in data)
    assert any(t["id"] == tenant.ta["id"] for t in data)


def test_iso_02_client_get_other_org_ticket_404(client: TestClient, tenant: SimpleNamespace) -> None:
    """#2 Client A GET Org B's ticket -> 404 (not 403, to avoid leaking existence)."""
    r = client.get(f"{API}/tickets/{tenant.tb['id']}", headers=tenant.h_a)
    assert r.status_code == 404


def test_iso_03_client_internal_comment_rejected(client: TestClient, tenant: SimpleNamespace) -> None:
    """#3 Client POST comment with is_internal=true -> rejected (403).

    Spec §5 allows "forced to false or 422"; we reject with 403 (the §4 contract's
    "wrong role for the action"), the stricter, clearer choice.
    """
    r = client.post(
        f"{API}/tickets/{tenant.ta['id']}/comments", headers=tenant.h_a,
        json={"body": "secret", "is_internal": True},
    )
    assert r.status_code == 403
    # And a public comment from the client is accepted, never marked internal.
    ok = client.post(
        f"{API}/tickets/{tenant.ta['id']}/comments", headers=tenant.h_a,
        json={"body": "public note", "is_internal": False},
    )
    assert ok.status_code == 201
    assert ok.json()["is_internal"] is False


def test_iso_04_client_patch_forbidden(client: TestClient, tenant: SimpleNamespace) -> None:
    """#4 Client PATCH /tickets/{id} (status change) -> 403."""
    r = client.patch(
        f"{API}/tickets/{tenant.ta['id']}", headers=tenant.h_a,
        json={"status": "in_development"},
    )
    assert r.status_code == 403


def test_iso_05_internal_comments_hidden_from_client(client: TestClient, tenant: SimpleNamespace) -> None:
    """#5 Client GET own ticket -> internal comments absent; team sees them."""
    # Team adds one internal and one public comment.
    assert client.post(
        f"{API}/tickets/{tenant.ta['id']}/comments", headers=tenant.h_agent,
        json={"body": "internal triage", "is_internal": True},
    ).status_code == 201
    assert client.post(
        f"{API}/tickets/{tenant.ta['id']}/comments", headers=tenant.h_agent,
        json={"body": "public reply", "is_internal": False},
    ).status_code == 201

    detail_client = client.get(f"{API}/tickets/{tenant.ta['id']}", headers=tenant.h_a).json()
    bodies = [c["body"] for c in detail_client["comments"]]
    assert "internal triage" not in bodies
    assert "public reply" in bodies
    assert all(c["is_internal"] is False for c in detail_client["comments"])

    detail_team = client.get(f"{API}/tickets/{tenant.ta['id']}", headers=tenant.h_agent).json()
    team_bodies = [c["body"] for c in detail_team["comments"]]
    assert "internal triage" in team_bodies


def test_iso_06_team_sees_all_orgs(client: TestClient, tenant: SimpleNamespace) -> None:
    """#6 Unveilix agent GET /tickets -> sees Org A + Org B."""
    data = client.get(f"{API}/tickets", headers=tenant.h_agent).json()["data"]
    ids = {t["id"] for t in data}
    assert tenant.ta["id"] in ids
    assert tenant.tb["id"] in ids


def test_iso_07_team_org_filter(client: TestClient, tenant: SimpleNamespace) -> None:
    """#7 Unveilix agent GET /tickets?organization_id=A -> only Org A."""
    data = client.get(
        f"{API}/tickets?organization_id={tenant.org_a.id}", headers=tenant.h_agent
    ).json()["data"]
    assert len(data) >= 1
    assert all(t["organization_id"] == str(tenant.org_a.id) for t in data)


def test_iso_08_priority_from_blocks_work(client: TestClient, tenant: SimpleNamespace) -> None:
    """#8 Ticket created from blocks_work severity -> priority defaults to P1."""
    assert tenant.ta["severity"] == "blocks_work"
    assert tenant.ta["priority"] == "P1"
    # And major -> P2 (sanity on the mapping).
    assert tenant.tb["priority"] == "P2"


def test_iso_09_unique_reference(client: TestClient, tenant: SimpleNamespace) -> None:
    """#9 New ticket auto-generates a unique UVX-#### reference."""
    import re

    assert re.fullmatch(r"UVX-\d+", tenant.ta["reference"])
    assert re.fullmatch(r"UVX-\d+", tenant.tb["reference"])
    assert tenant.ta["reference"] != tenant.tb["reference"]


def test_iso_10_client_attachment_to_other_org_404(client: TestClient, tenant: SimpleNamespace) -> None:
    """#10 Client A uploads an attachment to Org B's ticket -> 404."""
    files = {"file": ("shot.png", b"\x89PNG fake bytes", "image/png")}
    r = client.post(
        f"{API}/tickets/{tenant.tb['id']}/attachments", headers=tenant.h_a, files=files
    )
    assert r.status_code == 404
    # Positive control: client A can attach to their OWN ticket.
    ok = client.post(
        f"{API}/tickets/{tenant.ta['id']}/attachments", headers=tenant.h_a, files=files
    )
    assert ok.status_code == 201
    assert ok.json()["kind"] == "screenshot"


# ===========================================================================
# Auth tests
# ===========================================================================
def test_auth_login_returns_token_and_user(client: TestClient, tenant: SimpleNamespace) -> None:
    r = client.post(
        f"{API}/auth/login",
        json={"email": tenant.client_a.email, "password": PW},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == tenant.client_a.email
    assert body["user"]["family"] == "client"
    assert body["user"]["organization_id"] == str(tenant.org_a.id)


def test_auth_login_bad_password(client: TestClient, tenant: SimpleNamespace) -> None:
    r = client.post(
        f"{API}/auth/login", json={"email": tenant.client_a.email, "password": "wrong-password"}
    )
    assert r.status_code == 400


def test_auth_me(client: TestClient, tenant: SimpleNamespace) -> None:
    r = client.get(f"{API}/auth/me", headers=tenant.h_agent)
    assert r.status_code == 200
    assert r.json()["email"] == tenant.agent.email
    assert r.json()["family"] == "unveilix"


def test_auth_unauthenticated_401(client: TestClient) -> None:
    assert client.get(f"{API}/tickets").status_code == 401
    assert client.get(f"{API}/auth/me").status_code == 401


def test_wrong_role_team_only_endpoints_403(client: TestClient, tenant: SimpleNamespace) -> None:
    """Client family hitting team-only endpoints -> 403."""
    assert client.get(f"{API}/dashboard/stats", headers=tenant.h_a).status_code == 403
    assert client.get(f"{API}/tickets/board", headers=tenant.h_a).status_code == 403
    assert client.get(f"{API}/organizations", headers=tenant.h_a).status_code == 403


def test_admin_only_create_org_forbidden_for_agent(client: TestClient, tenant: SimpleNamespace) -> None:
    """An agent (not admin) cannot onboard an org."""
    r = client.post(
        f"{API}/organizations", headers=tenant.h_agent,
        json={"name": f"Nope-{random_lower_string()[:6]}", "plan": "growth"},
    )
    assert r.status_code == 403


# ===========================================================================
# Happy-path ticket lifecycle (team)
# ===========================================================================
def test_ticket_lifecycle(client: TestClient, tenant: SimpleNamespace, superuser_token_headers: dict[str, str]) -> None:
    """Create -> assign -> walk statuses -> close, asserting the activity timeline."""
    tid = tenant.tb["id"]

    # Assign to the agent.
    r = client.patch(
        f"{API}/tickets/{tid}", headers=tenant.h_agent,
        json={"assignee_id": str(tenant.agent.id)},
    )
    assert r.status_code == 200
    assert r.json()["assignee_id"] == str(tenant.agent.id)

    # Walk through the lifecycle statuses (closing requires an RCA).
    for status in ["in_development", "in_testing", "deployed", "closed"]:
        payload: dict = {"status": status}
        if status == "closed":
            payload["rca"] = "Trino timed out on >50k rows; added result pagination."
        rr = client.patch(f"{API}/tickets/{tid}", headers=tenant.h_agent, json=payload)
        assert rr.status_code == 200
        assert rr.json()["status"] == status

    final = client.get(f"{API}/tickets/{tid}", headers=tenant.h_agent).json()
    assert final["status"] == "closed"
    assert final["closed_at"] is not None
    assert final["rca"] == "Trino timed out on >50k rows; added result pagination."

    # Activity timeline: created + assigned + 4 status changes = 6 entries.
    actions = [a["action"] for a in final["activity"]]
    assert actions.count("created") == 1
    assert actions.count("assigned") == 1
    assert actions.count("status_changed") == 4
    assert len(final["activity"]) == 6

    # Priority override is logged too.
    pr = client.patch(f"{API}/tickets/{tid}", headers=tenant.h_agent, json={"priority": "P1"})
    assert pr.status_code == 200
    assert pr.json()["priority"] == "P1"
    actions2 = [a["action"] for a in pr.json()["activity"]]
    assert "priority_changed" in actions2


def test_attachment_accepts_codec_mime(client: TestClient, tenant: SimpleNamespace) -> None:
    """Regression: MediaRecorder reports clips as 'video/webm;codecs=vp9' — the base type
    must be accepted (the parameter suffix used to cause a spurious 422)."""
    files = {"file": ("clip.webm", b"\x1aE\xdf\xa3fake-webm", "video/webm;codecs=vp9")}
    r = client.post(
        f"{API}/tickets/{tenant.ta['id']}/attachments", headers=tenant.h_a, files=files
    )
    assert r.status_code == 201, r.text
    assert r.json()["kind"] == "recording"
    assert r.json()["content_type"] == "video/webm"  # stored as the base type
    # Genuinely unsupported types are still rejected.
    bad = {"file": ("x.pdf", b"%PDF-1.4", "application/pdf")}
    r2 = client.post(
        f"{API}/tickets/{tenant.ta['id']}/attachments", headers=tenant.h_a, files=bad
    )
    assert r2.status_code == 422


def test_close_requires_rca(client: TestClient, tenant: SimpleNamespace) -> None:
    """A bug can only be closed with a documented root-cause analysis."""
    tid = tenant.tb["id"]
    # Closing without an RCA is rejected.
    r = client.patch(f"{API}/tickets/{tid}", headers=tenant.h_agent, json={"status": "closed"})
    assert r.status_code == 422
    # Closing WITH an RCA works; the RCA is stored and returned in detail.
    r2 = client.patch(
        f"{API}/tickets/{tid}", headers=tenant.h_agent,
        json={"status": "closed", "rca": "Off-by-one in the paginator; fixed + test added."},
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "closed"
    assert r2.json()["closed_at"] is not None
    assert r2.json()["rca"] == "Off-by-one in the paginator; fixed + test added."
    # RCA is INTERNAL: the client who owns the ticket never sees it.
    client_detail = client.get(f"{API}/tickets/{tid}", headers=tenant.h_b).json()
    assert client_detail["status"] == "closed"
    assert client_detail["rca"] is None
    # Re-opening then re-closing needs no new RCA (one already exists).
    client.patch(f"{API}/tickets/{tid}", headers=tenant.h_agent, json={"status": "in_testing"})
    r3 = client.patch(f"{API}/tickets/{tid}", headers=tenant.h_agent, json={"status": "closed"})
    assert r3.status_code == 200


def test_attachment_via_s3_backend(
    client: TestClient, tenant: SimpleNamespace, monkeypatch
) -> None:
    """Attachments work through the S3 (Backblaze B2) backend with a MOCKED client, and tenant
    isolation still holds — the owning client streams the bytes back, another org's client gets
    404. Proves the access check runs before any storage read regardless of backend."""
    from app.core import storage as storage_mod

    fake = FakeS3Client()
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "s3")
    monkeypatch.setattr(settings, "S3_BUCKET", "test-bucket")
    monkeypatch.setattr(storage_mod, "_get_s3_client", lambda: fake)

    payload = b"\x1aE\xdf\xa3-fake-webm-bytes"
    files = {"file": ("clip.webm", payload, "video/webm;codecs=vp9")}
    up = client.post(
        f"{API}/tickets/{tenant.ta['id']}/attachments", headers=tenant.h_a, files=files
    )
    assert up.status_code == 201, up.text
    att_id = up.json()["id"]
    # the object went to the (fake) S3 bucket, not local disk
    assert any(bucket == "test-bucket" for (bucket, _key) in fake.store)

    # owner streams it back through the API -> 200 + exact bytes
    r = client.get(f"{API}/attachments/{att_id}", headers=tenant.h_a)
    assert r.status_code == 200
    assert r.content == payload

    # another org's client cannot fetch it -> 404 (isolation holds with the S3 backend)
    r2 = client.get(f"{API}/attachments/{att_id}", headers=tenant.h_b)
    assert r2.status_code == 404


def test_team_create_ticket_requires_org(client: TestClient, tenant: SimpleNamespace) -> None:
    """A team user must name the org when creating a ticket."""
    r = client.post(
        f"{API}/tickets", headers=tenant.h_agent,
        json={"title": "no org", "module": "other", "severity": "minor"},
    )
    assert r.status_code == 422
    # With an org it succeeds.
    ok = client.post(
        f"{API}/tickets", headers=tenant.h_agent,
        json={"title": "with org", "module": "other", "severity": "minor",
              "organization_id": str(tenant.org_a.id)},
    )
    assert ok.status_code == 201
    assert ok.json()["organization_id"] == str(tenant.org_a.id)

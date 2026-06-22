"""
Change log:
[#001] 2026-06-22 — Sumeet — File created. Unit tests for the pluggable storage layer:
        LocalStorage (filesystem) and S3Storage (mocked boto3 client — no real B2 needed),
        plus get_storage() backend selection.
"""

from app.core import storage as storage_mod
from app.core.config import settings
from app.core.storage import LocalStorage, S3Storage, get_storage
from tests.utils.fake_s3 import FakeS3Client


def test_local_storage_roundtrip(tmp_path) -> None:
    s = LocalStorage(base_dir=str(tmp_path))
    key = "ticket-1/abc_shot.png"
    returned = s.save(key=key, data=b"hello-bytes", content_type="image/png")
    assert returned == key
    assert s.exists(key) is True
    assert b"".join(s.open_stream(key)) == b"hello-bytes"
    s.delete(key)
    assert s.exists(key) is False


def test_s3_storage_roundtrip() -> None:
    fake = FakeS3Client()
    s = S3Storage(client=fake, bucket="bkt")
    key = "ticket-1/abc_clip.webm"
    s.save(key=key, data=b"\x00\x01\x02binary", content_type="video/webm")
    # object landed in the (fake) bucket
    assert ("bkt", key) in fake.store
    assert fake.store[("bkt", key)][1] == "video/webm"  # content type recorded
    assert s.exists(key) is True
    assert s.exists("does/not/exist") is False
    assert b"".join(s.open_stream(key)) == b"\x00\x01\x02binary"
    s.delete(key)
    assert s.exists(key) is False


def test_get_storage_selects_backend(monkeypatch) -> None:
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")
    assert isinstance(get_storage(), LocalStorage)

    monkeypatch.setattr(settings, "STORAGE_BACKEND", "s3")
    monkeypatch.setattr(settings, "S3_BUCKET", "bkt")
    monkeypatch.setattr(storage_mod, "_get_s3_client", lambda: FakeS3Client())
    backend = get_storage()
    assert isinstance(backend, S3Storage)
    assert backend.bucket == "bkt"

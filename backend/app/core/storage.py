"""
Change log:
[#001] 2026-06-22 — Sumeet — File created. Pluggable attachment storage selected by
        settings.STORAGE_BACKEND: LocalStorage (filesystem, the dev default — no credentials
        needed) and S3Storage (S3-compatible object storage / Backblaze B2 via boto3). The
        upload endpoint saves bytes to the configured backend; the auth- + tenant-scoped
        download endpoint streams them back (the access check runs first, so isolation holds).
        boto3 is imported lazily so the local backend has no hard dependency on it, and the
        S3 client factory is isolated so tests can mock it (no real B2 credentials required).
"""

import os
from abc import ABC, abstractmethod
from collections.abc import Iterator

from app.core.config import settings

_CHUNK = 1024 * 256  # 256 KiB streaming chunks


class StorageBackend(ABC):
    """Minimal storage interface used by the attachment endpoints."""

    @abstractmethod
    def save(self, *, key: str, data: bytes, content_type: str) -> str:
        """Store `data` under `key`; return the key (persisted on the attachment row)."""

    @abstractmethod
    def open_stream(self, key: str) -> Iterator[bytes]:
        """Yield the object's bytes in chunks (proxied through the API)."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Whether an object exists at `key`."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove the object at `key` (best-effort)."""


class LocalStorage(StorageBackend):
    """Filesystem storage under a base directory (dev default). `key` is a relative path —
    identical layout to the original local-disk behavior."""

    def __init__(self, base_dir: str) -> None:
        self.base_dir = base_dir

    def _abs(self, key: str) -> str:
        return os.path.join(self.base_dir, key)

    def save(self, *, key: str, data: bytes, content_type: str) -> str:
        path = self._abs(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(data)
        return key

    def open_stream(self, key: str) -> Iterator[bytes]:
        with open(self._abs(key), "rb") as fh:
            while True:
                chunk = fh.read(_CHUNK)
                if not chunk:
                    break
                yield chunk

    def exists(self, key: str) -> bool:
        return os.path.exists(self._abs(key))

    def delete(self, key: str) -> None:
        path = self._abs(key)
        if os.path.exists(path):
            os.remove(path)


def make_s3_client():
    """Build a boto3 S3 client from settings (Backblaze B2 is S3-compatible). Isolated in its
    own function so the test suite can monkeypatch it — tests never need real credentials.
    boto3 is imported here (lazily) so the local backend doesn't require it at import time."""
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        region_name=settings.S3_REGION,
        aws_access_key_id=settings.S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
    )


class S3Storage(StorageBackend):
    """S3-compatible object storage (Backblaze B2 in production)."""

    def __init__(self, *, client, bucket: str) -> None:
        self.client = client
        self.bucket = bucket

    def save(self, *, key: str, data: bytes, content_type: str) -> str:
        self.client.put_object(
            Bucket=self.bucket, Key=key, Body=data, ContentType=content_type
        )
        return key

    def open_stream(self, key: str) -> Iterator[bytes]:
        body = self.client.get_object(Bucket=self.bucket, Key=key)["Body"]
        yield from body.iter_chunks(chunk_size=_CHUNK)

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)


_s3_client = None  # cached boto3 client (built once per process)


def _get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = make_s3_client()
    return _s3_client


def get_storage() -> StorageBackend:
    """Return the storage backend selected by settings.STORAGE_BACKEND."""
    if settings.STORAGE_BACKEND == "s3":
        return S3Storage(client=_get_s3_client(), bucket=settings.S3_BUCKET or "")
    return LocalStorage(base_dir=settings.UPLOADS_DIR)

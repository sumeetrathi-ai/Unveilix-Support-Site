"""
Change log:
[#001] 2026-06-22 — Sumeet — File created. In-memory fake of the boto3 S3 client (only the
        methods S3Storage uses) so the storage suite runs without real Backblaze B2 / AWS
        credentials or network.
"""


class _FakeBody:
    """Mimics a boto3 StreamingBody for get_object()["Body"]."""

    def __init__(self, data: bytes) -> None:
        self._data = data

    def iter_chunks(self, chunk_size: int = 8192):
        for i in range(0, len(self._data), chunk_size):
            yield self._data[i : i + chunk_size]

    def read(self) -> bytes:
        return self._data


class FakeS3Client:
    """Minimal in-memory stand-in for boto3's S3 client."""

    def __init__(self) -> None:
        self.store: dict[tuple[str, str], tuple[bytes, str | None]] = {}

    def put_object(self, Bucket, Key, Body, ContentType=None):  # noqa: N803
        self.store[(Bucket, Key)] = (Body, ContentType)
        return {}

    def get_object(self, Bucket, Key):  # noqa: N803
        body, content_type = self.store[(Bucket, Key)]
        return {"Body": _FakeBody(body), "ContentType": content_type}

    def head_object(self, Bucket, Key):  # noqa: N803
        if (Bucket, Key) not in self.store:
            from botocore.exceptions import ClientError

            raise ClientError(
                {"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject"
            )
        return {}

    def delete_object(self, Bucket, Key):  # noqa: N803
        self.store.pop((Bucket, Key), None)
        return {}

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from poelis_sdk import PoelisClient
from poelis_sdk.exceptions import ClientError, UploadError
from poelis_sdk.files import MAX_UPLOAD_BYTES, prepare_upload


class _RecordingTransport(httpx.BaseTransport):
    def __init__(self, responses: list[httpx.Response]) -> None:
        self._responses = responses
        self.requests: list[httpx.Request] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        request.read()
        self.requests.append(request)
        return self._responses.pop(0)


def _client(transport: httpx.BaseTransport) -> PoelisClient:
    from poelis_sdk.client import Transport as SdkTransport

    def _init(self, base_url: str, api_key: str, timeout_seconds: float) -> None:
        self._client = httpx.Client(base_url=base_url, transport=transport, timeout=timeout_seconds)
        self._api_key = api_key
        self._timeout = timeout_seconds

    original = SdkTransport.__init__
    SdkTransport.__init__ = _init  # type: ignore[method-assign]
    try:
        return PoelisClient(base_url="http://example.com", api_key="poelis_live_test")
    finally:
        SdkTransport.__init__ = original  # type: ignore[method-assign]


def test_prepare_upload_rejects_empty_file(tmp_path: Path) -> None:
    target = tmp_path / "empty.txt"
    target.write_bytes(b"")
    with pytest.raises(UploadError, match="empty"):
        prepare_upload(target)


def test_prepare_upload_rejects_file_over_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("poelis_sdk.files.MAX_UPLOAD_BYTES", 4)
    target = tmp_path / "notes.txt"
    target.write_bytes(b"12345")
    with pytest.raises(UploadError, match="too large"):
        prepare_upload(target)


def test_prepare_upload_uses_the_file_name_only(tmp_path: Path) -> None:
    nested = tmp_path / "dir"
    nested.mkdir()
    target = nested / "spec.pdf"
    target.write_bytes(b"pdf")
    prepared = prepare_upload(target)
    assert prepared.filename == "spec.pdf"
    assert prepared.size_bytes == 3
    assert prepared.content_type == "application/pdf"


def test_upload_sends_signed_put_then_bytes_then_complete(tmp_path: Path) -> None:
    target = tmp_path / "subdir" / "spec.pdf"
    target.parent.mkdir()
    target.write_bytes(b"pdf-bytes")
    transport = _RecordingTransport(
        [
            httpx.Response(
                200,
                json={
                    "upload_url": "https://storage.example/object",
                    "object_path": "org/ws/uploads/abc__spec.pdf",
                    "required_headers": {
                        "Content-Type": "application/pdf",
                        "Authorization": "Bearer storage-should-not-see-this",
                    },
                    "upload_mode": "put",
                },
            ),
            httpx.Response(200),
            httpx.Response(
                200,
                json={
                    "file_id": "file-1",
                    "document_id": "file-1",
                    "object_path": "org/ws/uploads/abc__spec.pdf",
                    "size_bytes": 9,
                    "content_type": "application/pdf",
                },
            ),
        ]
    )
    client = _client(transport)
    uploaded = client.files.upload(target, item_id="item-1")

    assert uploaded.file_id == "file-1"
    assert uploaded.size_bytes == 9
    assert len(transport.requests) == 3

    initiate, put, complete = transport.requests
    assert initiate.method == "POST"
    assert initiate.url.path == "/v1/storage/uploads/signed-put"
    initiate_body = json.loads(initiate.content)
    assert initiate_body["filename"] == "spec.pdf"
    assert initiate_body["item_id"] == "item-1"
    assert initiate_body["size_bytes"] == 9
    assert initiate_body["content_type"] == "application/pdf"
    assert initiate.headers["Authorization"] == "Bearer poelis_live_test"

    assert put.method == "PUT"
    assert str(put.url) == "https://storage.example/object"
    assert put.headers["Content-Type"] == "application/pdf"
    assert "authorization" not in {name.lower() for name in put.headers}
    assert put.content == b"pdf-bytes"

    complete_body = json.loads(complete.content)
    assert complete.url.path == "/v1/storage/uploads/complete"
    assert complete_body["object_path"] == "org/ws/uploads/abc__spec.pdf"
    assert complete_body["expected_size_bytes"] == 9
    assert complete_body["expected_content_type"] == "application/pdf"
    assert complete_body["item_id"] == "item-1"


def test_upload_does_not_call_the_api_when_the_file_is_over_the_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("poelis_sdk.files.MAX_UPLOAD_BYTES", 4)
    target = tmp_path / "big.bin"
    target.write_bytes(b"12345")
    transport = _RecordingTransport([])
    client = _client(transport)
    with pytest.raises(UploadError, match="too large"):
        client.files.upload(target, item_id="item-1")
    assert transport.requests == []


def test_upload_requires_one_target(tmp_path: Path) -> None:
    target = tmp_path / "a.txt"
    target.write_bytes(b"a")
    client = _client(_RecordingTransport([]))
    with pytest.raises(UploadError, match="item_id"):
        client.files.upload(target)
    with pytest.raises(UploadError, match="item_id"):
        client.files.upload(target, item_id="item-1", property_id="prop-1", property_type="text")


def test_upload_surfaces_api_rejection(tmp_path: Path) -> None:
    target = tmp_path / "a.txt"
    target.write_bytes(b"a")
    transport = _RecordingTransport(
        [
            httpx.Response(
                400,
                json={
                    "error": "file_too_large",
                    "message": "File too large: 1 bytes exceeds limit 0 MB",
                },
            )
        ]
    )
    client = _client(transport)
    with pytest.raises(ClientError, match="File too large") as caught:
        client.files.upload(target, property_id="prop-1", property_type="text")
    assert caught.value.status_code == 400
    assert len(transport.requests) == 1
    body = json.loads(transport.requests[0].content)
    assert body["property_id"] == "prop-1"
    assert body["property_type"] == "text"


def test_cap_matches_five_gibibytes() -> None:
    assert MAX_UPLOAD_BYTES == 5 * 1024 * 1024 * 1024

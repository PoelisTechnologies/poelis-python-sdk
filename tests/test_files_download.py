from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import httpx
import pytest

from poelis_sdk.exceptions import ClientError, FileNotDownloadableError, NotFoundError
from tests.conftest import client_with_transport

_SIGNED_URL = "https://storage.example/bucket/object?X-Goog-Signature=abc"


class _RoutingTransport(httpx.BaseTransport):
    """Answers each request with the first route whose predicate matches."""

    def __init__(self, routes: list[tuple[Callable[[httpx.Request], bool], httpx.Response]]) -> None:
        self._routes = routes
        self.requests: list[httpx.Request] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        request.read()
        self.requests.append(request)
        for matches, response in self._routes:
            if matches(request):
                return response
        raise AssertionError(f"unexpected request {request.method} {request.url}")


def _is_download_url(request: httpx.Request) -> bool:
    return request.url.path == "/v1/storage/objects/file-1/download-url"


def _is_storage(request: httpx.Request) -> bool:
    return request.url.host == "storage.example"


def _is_graphql(request: httpx.Request) -> bool:
    return request.url.path == "/v1/graphql"


def _signed_url_then_bytes(body: bytes = b"pdf-bytes") -> _RoutingTransport:
    return _RoutingTransport(
        [
            (_is_download_url, httpx.Response(200, json={"url": _SIGNED_URL})),
            (_is_storage, httpx.Response(200, content=body)),
            (
                _is_graphql,
                httpx.Response(
                    200, json={"data": {"product": {"id": "prod-1", "baselineVersionNumber": 4}}}
                ),
            ),
        ]
    )


def test_download_writes_the_bytes_and_never_sends_the_key_to_storage(tmp_path: Path) -> None:
    transport = _signed_url_then_bytes()
    client = client_with_transport(transport)
    dest = tmp_path / "spec.pdf"

    written = client.files.download("file-1", dest)

    assert written == dest
    assert dest.read_bytes() == b"pdf-bytes"
    assert list(tmp_path.iterdir()) == [dest]
    signed, storage = transport.requests
    assert signed.method == "POST"
    assert json.loads(signed.content) == {}
    assert signed.headers["Authorization"] == "Bearer k"
    assert storage.method == "GET"
    assert str(storage.url) == _SIGNED_URL
    assert "authorization" not in {name.lower() for name in storage.headers}


def test_download_at_a_version_number_sends_product_and_version(tmp_path: Path) -> None:
    transport = _signed_url_then_bytes()
    client = client_with_transport(transport)

    client.files.download("file-1", tmp_path / "spec.pdf", product_id="prod-1", version=3)

    assert json.loads(transport.requests[0].content) == {"product_id": "prod-1", "version_number": 3}


def test_download_at_baseline_resolves_the_version_number_first(tmp_path: Path) -> None:
    transport = _signed_url_then_bytes()
    client = client_with_transport(transport)

    client.files.download("file-1", tmp_path / "spec.pdf", product_id="prod-1", version="baseline")

    lookup, signed, _storage = transport.requests
    assert json.loads(lookup.content)["variables"] == {"id": "prod-1"}
    assert json.loads(signed.content) == {"product_id": "prod-1", "version_number": 4}


def test_download_at_baseline_without_a_baseline_raises_not_found(tmp_path: Path) -> None:
    transport = _RoutingTransport(
        [
            (
                _is_graphql,
                httpx.Response(
                    200, json={"data": {"product": {"id": "prod-1", "baselineVersionNumber": None}}}
                ),
            )
        ]
    )
    client = client_with_transport(transport)

    with pytest.raises(NotFoundError, match="no baseline"):
        client.files.download("file-1", tmp_path / "x", product_id="prod-1", version="baseline")
    assert len(transport.requests) == 1


def test_document_without_bytes_raises_a_clear_error(tmp_path: Path) -> None:
    transport = _RoutingTransport(
        [
            (
                _is_download_url,
                httpx.Response(
                    400,
                    json={
                        "error": "no_blob",
                        "message": "No storage object for this document (e.g. authored SFDT-only).",
                    },
                ),
            )
        ]
    )
    client = client_with_transport(transport)

    with pytest.raises(FileNotDownloadableError, match="cannot be downloaded") as caught:
        client.files.download("file-1", tmp_path / "doc.docx")
    assert isinstance(caught.value, ClientError)
    assert caught.value.error_code == "no_blob"
    assert list(tmp_path.iterdir()) == []


def test_other_client_errors_keep_their_type(tmp_path: Path) -> None:
    transport = _RoutingTransport(
        [
            (
                _is_download_url,
                httpx.Response(
                    400, json={"error": "invalid_version_params", "message": "Provide both"}
                ),
            )
        ]
    )
    client = client_with_transport(transport)

    with pytest.raises(ClientError) as caught:
        client.files.download("file-1", tmp_path / "x")
    assert not isinstance(caught.value, FileNotDownloadableError)
    assert caught.value.error_code == "invalid_version_params"


def test_failed_storage_read_leaves_no_file_behind(tmp_path: Path) -> None:
    transport = _RoutingTransport(
        [
            (_is_download_url, httpx.Response(200, json={"url": _SIGNED_URL})),
            (_is_storage, httpx.Response(403, text="<Error>SignatureDoesNotMatch</Error>")),
        ]
    )
    client = client_with_transport(transport)
    dest = tmp_path / "spec.pdf"
    dest.write_bytes(b"previous")

    with pytest.raises(ClientError) as caught:
        client.files.download("file-1", dest)
    assert caught.value.status_code == 403
    assert dest.read_bytes() == b"previous"
    assert list(tmp_path.iterdir()) == [dest]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"version": 3}, "product_id is required"),
        ({"product_id": "prod-1", "version": "latest"}, "version"),
    ],
)
def test_download_rejects_bad_arguments_before_any_request(
    tmp_path: Path, kwargs: dict, message: str
) -> None:
    transport = _RoutingTransport([])
    client = client_with_transport(transport)
    with pytest.raises(ValueError, match=message):
        client.files.download("file-1", tmp_path / "x", **kwargs)
    with pytest.raises(ValueError, match="directory"):
        client.files.download("file-1", tmp_path)
    assert transport.requests == []


def test_versioned_download_without_bytes_says_the_file_may_not_be_in_that_version(
    tmp_path: Path,
) -> None:
    transport = _RoutingTransport(
        [(_is_download_url, httpx.Response(400, json={"error": "no_blob", "message": "No storage object"}))]
    )
    client = client_with_transport(transport)

    with pytest.raises(FileNotDownloadableError, match="not in that version"):
        client.files.download("file-1", tmp_path / "x", product_id="prod-1", version=2)

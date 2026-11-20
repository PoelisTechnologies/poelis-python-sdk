from __future__ import annotations

import json
from datetime import datetime, timezone

import httpx
import pytest

from poelis_sdk.exceptions import UnauthorizedError
from tests.conftest import client_with_transport


class _GraphQLTransport(httpx.BaseTransport):
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.bodies: list[dict] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/graphql"
        self.bodies.append(json.loads(request.read()))
        return httpx.Response(200, json=self._payload)


_FILE_ROW = {
    "id": "file-1",
    "originalFileName": "spec.pdf",
    "userTitle": "Spec",
    "revision": "Rev B",
    "code": "SPEC-0042",
    "contentType": "application/pdf",
    "description": None,
    "sizeBytes": 1234,
    "uploadedAt": "2026-11-17T09:30:00Z",
    "uploadedBy": {"id": "auth0|u1", "userName": "Ada", "imageUrl": None},
    "deleted": False,
    "itemId": "item-1",
    "propertyId": "prop-1",
}


def _files_payload(*rows: dict) -> dict:
    return {"data": {"files": {"files": list(rows)}}}


@pytest.mark.parametrize(
    ("version", "sent"),
    [(None, None), (3, 3), ("baseline", "baseline"), (" Baseline ", "baseline")],
)
def test_list_property_files_sends_the_version_and_parses_rows(version, sent) -> None:
    transport = _GraphQLTransport(_files_payload(_FILE_ROW))
    client = client_with_transport(transport)

    files = client.files.list(property_id="prop-1", version=version)

    assert transport.bodies[0]["variables"] == {
        "itemId": None,
        "propertyId": "prop-1",
        "version": sent,
    }
    [file] = files
    assert file.id == "file-1"
    assert file.name == file.original_file_name == "spec.pdf"
    assert file.size_bytes == 1234
    assert file.uploaded_at == datetime(2026, 11, 17, 9, 30, tzinfo=timezone.utc)
    assert file.uploaded_by is not None and file.uploaded_by.user_name == "Ada"
    assert file.property_id == "prop-1"


def test_list_item_files_can_include_property_files() -> None:
    older = _FILE_ROW
    newer = {**_FILE_ROW, "id": "file-2", "propertyId": None, "uploadedAt": "2026-11-17T12:00:00Z"}
    transport = _GraphQLTransport(_files_payload(older, newer))
    client = client_with_transport(transport)

    files = client.files.list(item_id="item-1", include_property_files=True)

    assert [f.id for f in files] == ["file-2", "file-1"]
    assert transport.bodies[0]["variables"] == {
        "itemId": "item-1",
        "propertyId": None,
        "version": None,
        "includePropertyFiles": True,
    }


def test_list_returns_empty_when_the_api_has_no_files() -> None:
    client = client_with_transport(_GraphQLTransport({"data": {"files": {"files": []}}}))
    assert client.files.list(item_id="item-1", version="baseline") == []


def test_list_raises_access_denied_on_a_forbidden_error() -> None:
    client = client_with_transport(_GraphQLTransport({"errors": [{"message": "forbidden"}]}))
    with pytest.raises(UnauthorizedError, match="Access denied") as caught:
        client.files.list(property_id="prop-1")
    assert caught.value.error_code == "forbidden"


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({}, "exactly one"),
        ({"item_id": "i", "property_id": "p"}, "exactly one"),
        ({"property_id": "p", "include_property_files": True}, "include_property_files"),
        ({"item_id": "i", "version": "latest"}, "version"),
        ({"item_id": "i", "version": True}, "version"),
        ({"item_id": "i", "version": -1}, "negative"),
    ],
)
def test_list_rejects_bad_arguments_before_any_request(kwargs, message) -> None:
    transport = _GraphQLTransport(_files_payload())
    client = client_with_transport(transport)
    with pytest.raises(ValueError, match=message):
        client.files.list(**kwargs)
    assert transport.bodies == []

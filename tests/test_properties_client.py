"""Tests for PropertiesClient GraphQL update mutations."""

from __future__ import annotations

import json

import httpx

from tests.conftest import client_with_transport


class _Transport(httpx.BaseTransport):
    def __init__(self) -> None:
        self.queries: list[str] = []
        self.variables: list[dict] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:  # type: ignore[override]
        payload = json.loads(request.content.decode("utf-8"))
        query = payload.get("query", "")
        variables = payload.get("variables", {})
        self.queries.append(query)
        self.variables.append(variables)

        if "updateNumericProperty" in query:
            key = "updateNumericProperty"
        elif "updateMatrixProperty" in query:
            key = "updateMatrixProperty"
        elif "updateTextProperty" in query:
            key = "updateTextProperty"
        elif "updateDateProperty" in query:
            key = "updateDateProperty"
        elif "updateStatusProperty" in query:
            key = "updateStatusProperty"
        else:
            return httpx.Response(200, json={"data": {}}, request=request)

        return httpx.Response(
            200,
            json={"data": {key: {"id": variables["id"], "value": variables.get("value")}}},
            request=request,
        )


def test_update_numeric_property_sends_changed_via() -> None:
    t = _Transport()
    c = client_with_transport(t)
    result = c.properties.update_numeric_property(id="pn1", value="1.5", changed_via="PYTHON_SDK")
    assert result["id"] == "pn1"
    assert "updateNumericProperty" in t.queries[0]
    assert t.variables[0]["id"] == "pn1"
    assert t.variables[0]["value"] == "1.5"
    assert t.variables[0]["changedVia"] == "PYTHON_SDK"


def test_update_matrix_property_mutation_name() -> None:
    t = _Transport()
    c = client_with_transport(t)
    c.properties.update_matrix_property(id="pm1", value="[[1,2],[3,4]]")
    assert "updateMatrixProperty" in t.queries[0]


def test_update_text_date_status_mutations() -> None:
    t = _Transport()
    c = client_with_transport(t)
    c.properties.update_text_property(id="pt1", value="hi")
    c.properties.update_date_property(id="pd1", value="2026-07-20")
    c.properties.update_status_property(id="ps1", value="DONE")
    joined = "\n".join(t.queries)
    assert "updateTextProperty" in joined
    assert "updateDateProperty" in joined
    assert "updateStatusProperty" in joined


def test_update_status_property_requests_parsed_value() -> None:
    t = _Transport()
    c = client_with_transport(t)
    c.properties.update_status_property(id="ps1", value="DONE")
    assert len(t.queries) == 1
    assert "updateStatusProperty" in t.queries[0]
    assert "parsedValue" in t.queries[0]

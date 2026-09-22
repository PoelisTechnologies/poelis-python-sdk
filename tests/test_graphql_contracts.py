from __future__ import annotations

from pathlib import Path

import pytest

from poelis_sdk._contract_audit import (
    _RecordingTransport,
    backend_repo_root,
    collect_sdk_graphql_documents,
    validate_sdk_contracts,
)
from poelis_sdk.models import FormulaProperty
from poelis_sdk.properties import PropertiesClient

_REMOVED_STRIPE_FIELDS = (
    "hasChanges",
    "hasPropertyChanges",
    "hasDocumentChanges",
    "hasDescendantChanges",
)


def test_contract_audit_collects_expected_documents() -> None:
    """Ensure the audit exercises the split property mutations and browser reads."""
    documents = collect_sdk_graphql_documents()
    queries = [document.query for document in documents]

    assert any("updateMatrixProperty" in query for query in queries)
    assert any("updateNumericProperty" in query for query in queries)
    assert any("sdkProperties" in query for query in queries)
    assert any("searchProperties" in query for query in queries)


def test_sdk_graphql_documents_validate_against_backend_schema() -> None:
    """All SDK-emitted GraphQL documents should remain valid against the backend schema."""
    backend_root = backend_repo_root()
    if not (backend_root / "src").exists():
        pytest.skip(f"Backend repo not found at {backend_root}")

    errors = validate_sdk_contracts()
    assert not errors, "\n".join(f"{error.label}: {error.message}" for error in errors)


def test_sdk_graphql_documents_omit_removed_change_stripe_fields() -> None:
    """Property/item/file GraphQL must not select GraphQL stripe fields removed from the schema."""
    documents = collect_sdk_graphql_documents()
    assert documents
    for document in documents:
        for field in _REMOVED_STRIPE_FIELDS:
            assert field not in document.query, f"{document.label} still selects {field}"


def test_sdk_graphql_documents_still_select_formula_dependency_changes() -> None:
    """Formula reads still select hasFormulaDependencyChanges; that field is not a stripe flag."""
    documents = collect_sdk_graphql_documents()
    assert any("hasFormulaDependencyChanges" in document.query for document in documents)


def test_formula_property_model_keeps_dependency_change_flag() -> None:
    """Pydantic models never exposed hasChanges; formula dependency changes stay."""
    assert "has_changes" not in FormulaProperty.model_fields
    assert "hasChanges" not in FormulaProperty.model_fields
    field = FormulaProperty.model_fields["has_formula_dependency_changes"]
    assert field.alias == "hasFormulaDependencyChanges"


def test_contract_audit_property_update_fixtures_omit_has_changes() -> None:
    """Mock mutation payloads must not pretend the backend still returns hasChanges."""
    transport = _RecordingTransport()
    client = PropertiesClient(transport)
    payloads = [
        client.update_numeric_property(id="pn1", value="1"),
        client.update_matrix_property(id="pm1", value="[[1, 2], [3, 4]]"),
        client.update_text_property(id="pt1", value="Updated text"),
        client.update_date_property(id="pd1", value="2026-02-01"),
        client.update_status_property(id="ps1", value="DONE"),
    ]
    assert payloads
    for payload in payloads:
        assert "hasChanges" not in payload


def test_sdk_does_not_call_live_tokens_endpoint() -> None:
    """The SDK stays a GraphQL/REST client; it must not mint Electric live tokens."""
    sdk_root = Path(__file__).resolve().parents[1] / "src" / "poelis_sdk"
    offenders = [
        path
        for path in sdk_root.rglob("*.py")
        if "/v1/live/tokens" in path.read_text(encoding="utf-8")
    ]
    assert not offenders

from __future__ import annotations

import pytest

from poelis_sdk._contract_audit import (
    backend_repo_root,
    collect_sdk_graphql_documents,
    validate_sdk_contracts,
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

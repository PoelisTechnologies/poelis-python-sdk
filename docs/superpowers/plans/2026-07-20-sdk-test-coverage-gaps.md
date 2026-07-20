# SDK Test Coverage Gaps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close unit-test gaps for the existing GraphQL SDK surface, unify the split `tests/` vs `src/tests/` layout, and make CI actually fail on regressions — without expanding the SDK into public REST CRUD.

**Architecture:** The SDK talks GraphQL only (`POST /v1/graphql`). Coverage today is strong on Browser/MATLAB/`change_property`, weaker on thin resource clients (`workspaces.get`, `list_product_versions`, `versions.iter_items`, direct `PropertiesClient`). Tests use a duplicated `httpx.BaseTransport` monkeypatch; consolidate that into `tests/conftest.py`, then add focused client/model tests that assert query variables and parsed models.

**Tech Stack:** Python 3.11+, pytest, httpx mock transports, pydantic models, GraphQL contract audit vs sibling `poelis-be-py`.

## Global Constraints

- Do **not** add a public REST (`/v1/public`) client in this plan — that is a separate product decision (see Out of Scope).
- Do **not** add product/item/property create/delete SDK methods here; public REST already has them, GraphQL SDK today is read + property update + set baseline.
- Keep unit tests offline (mock GraphQL). Integration tests stay behind `@pytest.mark.integration` and `POELIS_API_KEY`.
- Mirror existing mock style from `src/tests/test_items_client.py` (`httpx.BaseTransport` + temporary `Transport.__init__` patch).
- Python >= 3.11; run with `uv run pytest`.
- Prefer extending existing test files over inventing parallel frameworks.
- Contract audit (`tests/test_graphql_contracts.py`) already exercises every GraphQL document — new unit tests focus on **behavior/parsing**, not re-validating schema.

## Audit Snapshot (2026-07-20)

**Collected:** 126 tests across 16 files (`src/tests` + `tests`).

| Area | Status |
|------|--------|
| Browser navigation / versions / get_property | Strong (`tests/test_browser_navigation.py`) |
| `_PropWrapper.change_property` all types | Strong (`tests/test_property_writes.py`) |
| MATLAB facade | Strong (`tests/test_matlab_facade.py`) |
| Change tracker | Strong (`src/tests/test_change_detection.py`) |
| Items client | Covered (`src/tests/test_items_client.py`) |
| Errors / 401 / 404 / 429 / GraphQL 5xx | Covered (`src/tests/test_errors_and_backoff.py`) |
| Access-control models + `get_user_accessible_resources` | Covered |
| GraphQL contract vs backend schema | Covered (skips if backend missing) |
| Live integration | Only `workspaces.list` |
| `workspaces.get` | **Missing unit test** |
| `products.list_product_versions` | **Missing direct test** |
| `versions.iter_items` | **Missing direct test** |
| Direct `PropertiesClient.update_*` | **Indirect only** (via wrapper) |
| `FormulaProperty` / `MatrixProperty` models | **Missing** |
| `get_changed_properties()` client API | **Missing dedicated assert** |
| Deletion warning helpers on tracker | **Partial** |
| Logging helpers | **Missing** |
| `ClientError` (4xx non-401/404) | **Missing** |
| Search hit shapes / filter variables | Smoke only |
| CI | `\|\| true` — failures do not block |

### Backend relevancy (do not treat as SDK bugs)

Public REST under `/v1/public` (23 endpoints) includes workspace/product/item/property CRUD, files, org users. The Python SDK does **not** call it. Gaps below are **product scope**, not missing tests:

| Backend public REST | SDK today |
|---------------------|-----------|
| Product/item/property create, patch, delete | Not exposed |
| Files list/upload/download | Not exposed |
| Org users list | Not exposed |
| Search | GraphQL `SearchClient` only |
| Versioned item/property reads | GraphQL `VersionsClient` + browser |
| Property value updates | GraphQL `PropertiesClient` + browser/MATLAB |

A future “REST SDK / CRUD” plan should be separate.

---

## File Structure

| Path | Responsibility |
|------|----------------|
| `tests/conftest.py` | Shared `_client_with_transport` helper + optional mock factories |
| `tests/test_workspaces_client.py` | `WorkspacesClient.list` / `.get` unit tests |
| `tests/test_products_client.py` | `list_by_workspace`, `list_product_versions`, pagination vars |
| `tests/test_versions_client.py` | Extend: `iter_items` pagination |
| `tests/test_properties_client.py` | Direct `PropertiesClient.update_*` GraphQL wiring |
| `tests/test_typed_properties.py` | Add Formula/Matrix model cases |
| `tests/test_logging.py` | `configure_logging` / convenience helpers |
| `tests/test_errors_and_backoff.py` | Move from `src/tests/`; add `ClientError` |
| `tests/test_client_basic.py` | Move from `src/tests/` |
| `tests/test_transport_and_products.py` | Move from `src/tests/` |
| `tests/test_items_client.py` | Move from `src/tests/` |
| `tests/test_search_client.py` | Move from `src/tests/`; add variable assertions |
| `tests/test_change_detection.py` | Move from `src/tests/`; add `get_changed_properties` + deletion warns |
| `pyproject.toml` | `testpaths = ["tests"]` only (after migrate) |
| `.github/workflows/ci.yml` | Drop `\|\| true`; run `uv run pytest` |
| `AGENTS.md` | Point at single `tests/` tree |

No production SDK code changes expected unless a test reveals a real bug (fix in the same task).

---

### Task 1: Unify test layout under `tests/`

**Files:**
- Move: `src/tests/test_*.py` → `tests/`
- Delete: empty `src/tests/` (or leave `__init__` only if needed — prefer delete)
- Modify: `pyproject.toml` (`testpaths` stays `["tests"]`)
- Modify: `.github/workflows/ci.yml` (pytest invocation)
- Modify: `AGENTS.md` (test command)

**Interfaces:**
- Consumes: existing tests unchanged in content
- Produces: single discoverable suite via `uv run pytest`

- [ ] **Step 1: Move files**

```bash
cd /Users/ramin/Documents/Projekte/_POELIS/poelis-python-sdk
git mv src/tests/test_client_basic.py tests/test_client_basic.py
git mv src/tests/test_transport_and_products.py tests/test_transport_and_products.py
git mv src/tests/test_items_client.py tests/test_items_client.py
git mv src/tests/test_search_client.py tests/test_search_client.py
git mv src/tests/test_errors_and_backoff.py tests/test_errors_and_backoff.py
git mv src/tests/test_change_detection.py tests/test_change_detection.py
rmdir src/tests 2>/dev/null || rm -rf src/tests
```

- [ ] **Step 2: Fix CI pytest command**

In `.github/workflows/ci.yml`, replace the test step with:

```yaml
    - name: Run tests with pytest
      run: |
        uv run pytest --maxfail=1 --disable-warnings --cov=src/poelis_sdk --cov-report=xml --cov-report=term
```

Keep `cov-fail-under` unset for now (Task 8 may add a floor). Do **not** use `|| true`.

- [ ] **Step 3: Verify collection**

Run: `uv run pytest --collect-only -q`
Expected: same ~126 tests, all under `tests/`, zero under `src/tests`.

- [ ] **Step 4: Commit**

```bash
git add -A tests/ src/tests pyproject.toml .github/workflows/ci.yml AGENTS.md
git commit -m "$(cat <<'EOF'
test: consolidate suite under tests/ and fail CI on regressions

EOF
)"
```

---

### Task 2: Shared mock client helper in `conftest.py`

**Files:**
- Create: `tests/conftest.py`
- Modify (optional follow-ups in later tasks): call sites can import from conftest

**Interfaces:**
- Consumes: `poelis_sdk.client.Transport`, `PoelisClient`
- Produces: `client_with_transport(transport: httpx.BaseTransport) -> PoelisClient`

- [ ] **Step 1: Write conftest helper**

```python
"""Shared pytest helpers for GraphQL transport mocking."""

from __future__ import annotations

import httpx

from poelis_sdk import PoelisClient
from poelis_sdk.client import Transport


def client_with_transport(transport: httpx.BaseTransport) -> PoelisClient:
    """Build a PoelisClient whose Transport uses the given httpx transport."""

    def _init(self: Transport, base_url: str, api_key: str, timeout_seconds: float) -> None:
        self._client = httpx.Client(base_url=base_url, transport=transport, timeout=timeout_seconds)
        self._api_key = api_key
        self._timeout = timeout_seconds

    original = Transport.__init__
    Transport.__init__ = _init  # type: ignore[method-assign]
    try:
        return PoelisClient(base_url="http://example.com", api_key="k", enable_change_detection=False)
    finally:
        Transport.__init__ = original  # type: ignore[method-assign]
```

- [ ] **Step 2: Smoke-import**

Run: `uv run python -c "from tests.conftest import client_with_transport; print(client_with_transport)"`
Expected: prints function (or use a tiny test that imports it).

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "$(cat <<'EOF'
test: add shared GraphQL mock client helper

EOF
)"
```

---

### Task 3: `WorkspacesClient.get` (+ list) unit tests

**Files:**
- Create: `tests/test_workspaces_client.py`
- Test: `tests/test_workspaces_client.py`

**Interfaces:**
- Consumes: `client.workspaces.list`, `client.workspaces.get`
- Produces: coverage for GraphQL `workspace(id:)` and `workspaces(limit/offset)`

- [ ] **Step 1: Write the failing tests**

```python
"""Unit tests for WorkspacesClient."""

from __future__ import annotations

import json

import httpx

from tests.conftest import client_with_transport


class _Transport(httpx.BaseTransport):
    def __init__(self) -> None:
        self.calls: list[httpx.Request] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:  # type: ignore[override]
        self.calls.append(request)
        payload = json.loads(request.content.decode("utf-8"))
        query = payload.get("query", "")
        variables = payload.get("variables", {})

        if "workspaces(" in query:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "workspaces": [
                            {"id": "w1", "orgId": "o1", "name": "Main", "readableId": "main"},
                        ]
                    }
                },
                request=request,
            )

        if "workspace(id:" in query:
            if variables.get("id") == "w1":
                return httpx.Response(
                    200,
                    json={
                        "data": {
                            "workspace": {
                                "id": "w1",
                                "orgId": "o1",
                                "name": "Main",
                                "readableId": "main",
                            }
                        }
                    },
                    request=request,
                )
            return httpx.Response(200, json={"data": {"workspace": None}}, request=request)

        return httpx.Response(200, json={"data": {}}, request=request)


def test_workspaces_list_passes_limit_offset() -> None:
    t = _Transport()
    c = client_with_transport(t)
    rows = c.workspaces.list(limit=10, offset=5)
    assert rows[0]["id"] == "w1"
    variables = json.loads(t.calls[0].content.decode("utf-8"))["variables"]
    assert variables == {"limit": 10, "offset": 5}


def test_workspaces_get_returns_workspace() -> None:
    t = _Transport()
    c = client_with_transport(t)
    ws = c.workspaces.get(workspace_id="w1")
    assert ws is not None
    assert ws["readableId"] == "main"
    variables = json.loads(t.calls[0].content.decode("utf-8"))["variables"]
    assert variables == {"id": "w1"}


def test_workspaces_get_returns_none_when_missing() -> None:
    t = _Transport()
    c = client_with_transport(t)
    assert c.workspaces.get(workspace_id="missing") is None
```

- [ ] **Step 2: Run tests**

Run: `uv run pytest tests/test_workspaces_client.py -v`
Expected: PASS (no production changes if `WorkspacesClient` already correct).

- [ ] **Step 3: Commit**

```bash
git add tests/test_workspaces_client.py
git commit -m "$(cat <<'EOF'
test: cover WorkspacesClient list and get

EOF
)"
```

---

### Task 4: `ProductsClient.list_product_versions` (+ list vars)

**Files:**
- Create: `tests/test_products_client.py`

**Interfaces:**
- Consumes: `ProductsClient.list_by_workspace`, `list_product_versions`
- Produces: asserts on `PaginatedProductVersions` / `ProductVersion` parsing

- [ ] **Step 1: Write the failing tests**

```python
"""Unit tests for ProductsClient GraphQL reads."""

from __future__ import annotations

import json

import httpx

from tests.conftest import client_with_transport


class _Transport(httpx.BaseTransport):
    def __init__(self) -> None:
        self.calls: list[httpx.Request] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:  # type: ignore[override]
        self.calls.append(request)
        payload = json.loads(request.content.decode("utf-8"))
        query = payload.get("query", "")

        if "productVersions(" in query:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "productVersions": [
                            {
                                "productId": "p1",
                                "versionNumber": 2,
                                "title": "v2",
                                "description": "Ship",
                                "createdAt": "2026-01-01T00:00:00Z",
                            }
                        ]
                    }
                },
                request=request,
            )

        if "products(" in query:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "products": [
                            {
                                "id": "p1",
                                "name": "Widget",
                                "description": None,
                                "readableId": "widget",
                                "workspaceId": "w1",
                                "baselineVersionNumber": 2,
                                "reviewers": [],
                            }
                        ]
                    }
                },
                request=request,
            )

        return httpx.Response(200, json={"data": {}}, request=request)


def test_list_by_workspace_parses_products() -> None:
    t = _Transport()
    c = client_with_transport(t)
    page = c.products.list_by_workspace(workspace_id="w1", q="wid", limit=5, offset=0)
    assert page.data[0].id == "p1"
    assert page.data[0].baseline_version_number == 2
    variables = json.loads(t.calls[0].content.decode("utf-8"))["variables"]
    assert variables["ws"] == "w1"
    assert variables["filter"] == {"q": "wid"}
    assert variables["limit"] == 5


def test_list_product_versions_parses_versions() -> None:
    t = _Transport()
    c = client_with_transport(t)
    page = c.products.list_product_versions(product_id="p1", limit=50, offset=0)
    assert len(page.data) == 1
    assert page.data[0].version_number == 2
    assert page.data[0].title == "v2"
    variables = json.loads(t.calls[0].content.decode("utf-8"))["variables"]
    assert variables == {"pid": "p1"}
```

- [ ] **Step 2: Run tests**

Run: `uv run pytest tests/test_products_client.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_products_client.py
git commit -m "$(cat <<'EOF'
test: cover ProductsClient list and list_product_versions

EOF
)"
```

---

### Task 5: `VersionsClient.iter_items` pagination

**Files:**
- Modify: `tests/test_versions_client.py`

**Interfaces:**
- Consumes: `VersionsClient.list_items`, `VersionsClient.iter_items`
- Produces: pagination across offsets (same pattern as `items.iter_all_by_product`)

- [ ] **Step 1: Add failing test to existing file**

Append (reuse/adapt local transport — respond to `sdkItems` with offset pages):

```python
def test_versions_iter_items_paginates() -> None:
    """iter_items should walk offset pages until empty."""

    class _PagingTransport(httpx.BaseTransport):
        def __init__(self) -> None:
            self.offsets: list[int] = []

        def handle_request(self, request: httpx.Request) -> httpx.Response:  # type: ignore[override]
            payload = json.loads(request.content.decode("utf-8"))
            variables = payload.get("variables", {})
            offset = int(variables.get("offset", 0))
            self.offsets.append(offset)
            if offset == 0:
                data = [
                    {
                        "id": "vi1",
                        "name": "A",
                        "readableId": "a",
                        "productId": "p1",
                        "parentId": None,
                        "draftItemId": "i1",
                        "position": 1,
                        "deleted": False,
                    },
                    {
                        "id": "vi2",
                        "name": "B",
                        "readableId": "b",
                        "productId": "p1",
                        "parentId": None,
                        "draftItemId": "i2",
                        "position": 2,
                        "deleted": False,
                    },
                ]
            elif offset == 2:
                data = [
                    {
                        "id": "vi3",
                        "name": "C",
                        "readableId": "c",
                        "productId": "p1",
                        "parentId": None,
                        "draftItemId": "i3",
                        "position": 3,
                        "deleted": True,
                    },
                ]
            else:
                data = []
            return httpx.Response(200, json={"data": {"sdkItems": data}}, request=request)

    # Use the same client_with_transport helper as other files
    from tests.conftest import client_with_transport

    t = _PagingTransport()
    c = client_with_transport(t)
    ids = [
        row["id"]
        for row in c.versions.iter_items(product_id="p1", version_number=2, page_size=2)
    ]
    assert ids == ["vi1", "vi2", "vi3"]
    assert t.offsets == [0, 2, 4]
```

Add `import json` / `httpx` at top if missing.

- [ ] **Step 2: Run test**

Run: `uv run pytest tests/test_versions_client.py::test_versions_iter_items_paginates -v`
Expected: PASS (if `iter_items` already stops on empty page). If FAIL because stop condition differs, fix `versions.py` minimally to match `ItemsClient.iter_all_by_product`.

- [ ] **Step 3: Commit**

```bash
git add tests/test_versions_client.py src/poelis_sdk/versions.py
git commit -m "$(cat <<'EOF'
test: cover VersionsClient.iter_items pagination

EOF
)"
```

---

### Task 6: Direct `PropertiesClient` update wiring

**Files:**
- Create: `tests/test_properties_client.py`

**Interfaces:**
- Consumes: `PropertiesClient.update_numeric_property`, `update_text_property`, `update_matrix_property`, `update_date_property`, `update_status_property`
- Produces: asserts mutation operation names + variables (`id`, `value`, `changedVia`)

Note: Browser wrapper tests already cover validation/routing. This task only proves the thin client sends the right GraphQL.

- [ ] **Step 1: Write tests (one transport, branch on mutation name)**

```python
"""Direct PropertiesClient GraphQL wiring tests."""

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
```

- [ ] **Step 2: Run**

Run: `uv run pytest tests/test_properties_client.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_properties_client.py
git commit -m "$(cat <<'EOF'
test: cover PropertiesClient update mutations directly

EOF
)"
```

---

### Task 7: Formula / Matrix model coverage

**Files:**
- Modify: `tests/test_typed_properties.py`

**Interfaces:**
- Consumes: `FormulaProperty`, `MatrixProperty` in `src/poelis_sdk/models.py`
- Produces: `typed_value` / alias parsing parity with Numeric/Text

- [ ] **Step 1: Add tests inside `TestTypedPropertyModels`**

```python
def test_formula_property_with_parsed_value(self) -> None:
    from poelis_sdk.models import FormulaProperty

    prop = FormulaProperty.model_validate(
        {
            "id": "f1",
            "name": "Mass total",
            "value": "10 kg",
            "parsedValue": 10.0,
            "formulaExpression": "a + b",
            "category": None,
            "displayUnit": None,
        }
    )
    assert prop.typed_value == 10.0
    assert prop.formula_expression == "a + b"
    assert prop.category is None


def test_formula_property_invalid_falls_back(self) -> None:
    from poelis_sdk.models import FormulaProperty

    prop = FormulaProperty.model_validate(
        {"id": "f2", "name": "Broken", "value": None, "parsedValue": None}
    )
    assert prop.typed_value is None


def test_matrix_property_with_parsed_value(self) -> None:
    from poelis_sdk.models import MatrixProperty

    prop = MatrixProperty.model_validate(
        {
            "id": "m1",
            "name": "Grid",
            "value": "[[1, 2], [3, 4]]",
            "parsedValue": [[1, 2], [3, 4]],
            "category": "LENGTH",
            "displayUnit": "mm",
        }
    )
    assert prop.typed_value == [[1, 2], [3, 4]]
    assert prop.display_unit == "mm"
```

- [ ] **Step 2: Run**

Run: `uv run pytest tests/test_typed_properties.py::TestTypedPropertyModels -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_typed_properties.py
git commit -m "$(cat <<'EOF'
test: cover FormulaProperty and MatrixProperty models

EOF
)"
```

---

### Task 8: Change-detection client API + deletion warnings

**Files:**
- Modify: `tests/test_change_detection.py`

**Interfaces:**
- Consumes: `PoelisClient.get_changed_properties`, `PropertyChangeTracker.warn_if_deleted`, `check_item_deleted`, `check_property_deleted`
- Produces: assertions that client delegates to tracker; deletion warning emitted once

- [ ] **Step 1: Add tests**

```python
def test_client_get_changed_properties_delegates(tmp_path, monkeypatch) -> None:
    from poelis_sdk import PoelisClient

    client = PoelisClient(
        api_key="k",
        base_url="http://example.com",
        enable_change_detection=True,
        baseline_file=str(tmp_path / "baselines.json"),
        log_file=str(tmp_path / "changes.log"),
    )
    tracker = client._change_tracker  # noqa: SLF001 — test seam
    tracker.record_baseline("ws.p.i.mass", 1.0, property_id="pn1")
    tracker.check_changed("ws.p.i.mass", 2.0, property_id="pn1")
    changed = client.get_changed_properties()
    assert "ws.p.i.mass" in changed
    assert changed["ws.p.i.mass"]["old_value"] == 1.0
    assert changed["ws.p.i.mass"]["new_value"] == 2.0


def test_warn_if_deleted_emits_item_warning(tmp_path) -> None:
    import warnings

    from poelis_sdk.change_tracker import ItemOrPropertyDeletedWarning, PropertyChangeTracker

    tracker = PropertyChangeTracker(
        enabled=True,
        baseline_file=str(tmp_path / "baselines.json"),
        log_file=str(tmp_path / "changes.log"),
    )
    tracker.record_accessed_item("ws.p.item", "Item", item_id="i1")
    # Simulate disappearance: clear live presence by checking deleted path
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        # Force deletion path: mark accessed then call check with missing current set
        info = tracker.check_item_deleted("ws.p.item")
        # If implementation requires an explicit "still exists" registry, call the
        # public warn_if_deleted API the way browser does after a failed lookup.
        tracker.warn_if_deleted(item_path="ws.p.item")
        assert any(issubclass(w.category, ItemOrPropertyDeletedWarning) for w in caught) or info is not None
```

**Important:** Before finalizing Step 1, read `change_tracker.py` `check_item_deleted` / `warn_if_deleted` and align the test with the actual control flow (accessed set vs existence probe). Do not invent a second API — assert the real one.

- [ ] **Step 2: Run**

Run: `uv run pytest tests/test_change_detection.py -k "get_changed or deleted" -v`
Expected: PASS (adjust asserts to match real tracker semantics).

- [ ] **Step 3: Commit**

```bash
git add tests/test_change_detection.py
git commit -m "$(cat <<'EOF'
test: cover get_changed_properties and deletion warnings

EOF
)"
```

---

### Task 9: Logging helpers + `ClientError`

**Files:**
- Create: `tests/test_logging.py`
- Modify: `tests/test_errors_and_backoff.py`

**Interfaces:**
- Consumes: `configure_logging`, `quiet_logging`, `verbose_logging`, `debug_logging`, `get_logger`; transport error mapping for non-401/404 4xx → `ClientError`
- Produces: logger level assertions; one `ClientError` case

- [ ] **Step 1: Logging tests**

```python
"""Tests for public logging helpers."""

from __future__ import annotations

import logging

from poelis_sdk.logging import (
    configure_logging,
    debug_logging,
    get_logger,
    quiet_logging,
    verbose_logging,
)


def test_get_logger_namespaced() -> None:
    logger = get_logger("demo")
    assert logger.name == "poelis_sdk.demo"


def test_quiet_logging_sets_warning() -> None:
    quiet_logging()
    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("poelis_sdk").level == logging.WARNING


def test_verbose_and_debug_enable_sdk_logs() -> None:
    verbose_logging()
    assert logging.getLogger("poelis_sdk").level == logging.DEBUG
    debug_logging()
    assert logging.getLogger("poelis_sdk").level == logging.DEBUG
    configure_logging(level="ERROR", enable_sdk_logs=False)
    assert logging.getLogger("poelis_sdk").level == logging.WARNING
```

- [ ] **Step 2: Add ClientError case in errors file**

Extend the existing mock transport pattern so a GraphQL HTTP 400 (or 422) raises `ClientError`:

```python
def test_400_raises_client_error() -> None:
    # Same structure as test_401_raises_unauthorized, but status_code=400
    # assert isinstance(exc, ClientError)
    ...
```

Read `src/poelis_sdk/_transport.py` to confirm which status codes map to `ClientError` before writing the assert.

- [ ] **Step 3: Run**

Run: `uv run pytest tests/test_logging.py tests/test_errors_and_backoff.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_logging.py tests/test_errors_and_backoff.py
git commit -m "$(cat <<'EOF'
test: cover logging helpers and ClientError mapping

EOF
)"
```

---

### Task 10: Search client variable / hit-shape assertions

**Files:**
- Modify: `tests/test_search_client.py`

**Interfaces:**
- Consumes: `SearchClient.products`, `.items`, `.properties`
- Produces: assert GraphQL variables (`workspace_id`/`product_id`/`property_type`/`sort`) and a non-empty hit parse path

- [ ] **Step 1: Strengthen existing test**

Replace empty-hits-only coverage with:

```python
def test_search_properties_passes_filters_and_parses_hits() -> None:
    # Mock returns one hit with camelCase fields matching PropertySearchResult
    # Call:
    #   c.search.properties(
    #       q="mass",
    #       workspace_id="w1",
    #       product_id="p1",
    #       item_id="i1",
    #       property_type="numeric",
    #       category="MASS",
    #       limit=5,
    #       offset=0,
    #       sort="updated_at",
    #   )
    # Assert variables match and hits[0] id/name present
    ...
```

Keep `test_search_endpoints` or merge into one file with clear names.

- [ ] **Step 2: Run**

Run: `uv run pytest tests/test_search_client.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_search_client.py
git commit -m "$(cat <<'EOF'
test: assert SearchClient filters and hit parsing

EOF
)"
```

---

### Task 11: Expand integration smoke (optional, credential-gated)

**Files:**
- Modify: `tests/test_integration_smoke.py`

**Interfaces:**
- Consumes: live API via `POELIS_API_KEY` (same as `check_sdk.py`)
- Produces: read-only chain: list workspaces → get workspace → list products → list versions → list items → search

- [ ] **Step 1: Add one chained integration test**

```python
@pytest.mark.integration
def test_smoke_read_chain() -> None:
    api_key = os.environ.get("POELIS_API_KEY")
    if not api_key:
        pytest.skip("POELIS_API_KEY not set")

    client = PoelisClient(api_key=api_key, enable_change_detection=False)
    workspaces = client.workspaces.list(limit=1)
    assert workspaces
    ws_id = workspaces[0]["id"]
    assert client.workspaces.get(workspace_id=ws_id) is not None
    products = client.products.list_by_workspace(workspace_id=ws_id, limit=1)
    if not products.data:
        pytest.skip("no products in workspace")
    product = products.data[0]
    versions = client.products.list_product_versions(product_id=product.id, limit=1)
    items = client.items.list_by_product(product_id=product.id, limit=1)
    assert isinstance(items, list)
    _ = client.search.products(q="*", workspace_id=ws_id, limit=1)
    if versions.data:
        _ = client.versions.list_items(
            product_id=product.id,
            version_number=versions.data[0].version_number,
            limit=1,
        )
```

Do **not** call write mutations in integration smoke.

- [ ] **Step 2: Run unit suite (skip integration)**

Run: `uv run pytest -q -m "not integration"`
Expected: all unit tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_integration_smoke.py
git commit -m "$(cat <<'EOF'
test: expand read-only integration smoke chain

EOF
)"
```

---

### Task 12: Final suite gate

**Files:**
- Modify: none unless failures

- [ ] **Step 1: Full local unit run**

Run: `uv run pytest -q -m "not integration"`
Expected: PASS, count ≥ previous 126 + new tests from Tasks 3–10.

- [ ] **Step 2: Contract test (if backend sibling present)**

Run: `uv run pytest tests/test_graphql_contracts.py -v`
Expected: PASS or skip if `poelis-be-py` not adjacent.

- [ ] **Step 3: Confirm CI config has no `|| true`**

```bash
rg "\|\| true" .github/workflows/ci.yml
```

Expected: no matches on the pytest step.

- [ ] **Step 4: Commit only if CI/docs tweaks remain**

```bash
git add .github/workflows/ci.yml AGENTS.md
git commit -m "$(cat <<'EOF'
chore: finalize test suite CI gate

EOF
)"
```

---

## Out of Scope (separate plans if desired)

1. **Public REST SDK** — wrap `/v1/public` for product/item/property CRUD, files, org users.
2. **SDK create/delete GraphQL mutations** — if product wants mutate without REST.
3. **Coverage % floor** — set `--cov-fail-under` only after Tasks 1–10 land and baseline is known.
4. **Refactor all existing tests onto `client_with_transport`** — optional cleanup; new tests must use it, old ones can migrate opportunistically.
5. **`enable_dynamic_completion` / `org_validation`** — low user impact; skip unless bugs appear.

---

## Self-Review

1. **Spec coverage:** Audit gaps mapped to tasks — layout/CI (1,12), shared helper (2), workspaces.get (3), list_product_versions (4), iter_items (5), PropertiesClient direct (6), Formula/Matrix models (7), get_changed_properties + deletion (8), logging + ClientError (9), search shapes (10), integration breadth (11). REST feature gaps explicitly out of scope.
2. **Placeholder scan:** Task 8/9/10 include `...` only where implementation must read current tracker/transport semantics first; those steps require filling concrete asserts from the live code before commit — not deferred to a later task.
3. **Type consistency:** Method names match SDK (`list_product_versions`, `iter_items`, `update_*_property`, `get_changed_properties`, `workspaces.get`).

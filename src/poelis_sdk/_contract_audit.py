from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .browser import Browser
from .client import PoelisClient
from .items import ItemsClient
from .matlab_facade import PoelisMatlab
from .products import ProductsClient
from .properties import PropertiesClient
from .search import SearchClient
from .versions import VersionsClient
from .workspaces import WorkspacesClient


@dataclass(frozen=True)
class GraphQLDocument:
    label: str
    query: str


@dataclass(frozen=True)
class ContractValidationError:
    label: str
    message: str


class _MockResponse:
    def __init__(self, payload: Dict[str, Any]) -> None:
        self._payload = payload
        self.status_code = 200

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Dict[str, Any]:
        return self._payload


class _RecordingTransport:
    def __init__(self) -> None:
        self.documents: list[GraphQLDocument] = []

    def graphql(self, query: str, variables: Optional[Dict[str, Any]] = None) -> _MockResponse:
        variables = variables or {}
        self.documents.append(GraphQLDocument(label=self._label_for(query), query=query))
        return _MockResponse(self._payload_for(query, variables))

    def _label_for(self, query: str) -> str:
        for marker, label in (
            ("userAccessibleResources(", "workspaces.get_user_accessible_resources"),
            ("workspace(", "workspaces.get"),
            ("workspaces(", "workspaces.list"),
            ("setProductBaselineVersion(", "products.set_product_baseline_version"),
            ("productVersions(", "products.list_product_versions"),
            ("products(", "products.list_by_workspace"),
            ("sdkItems(", "versions.list_items"),
            ("items(productId:", "items.list_by_product"),
            ("item(id:", "items.get"),
            ("searchProperties(", "search.properties"),
            ("sdkProperties(", "browser.sdk_properties"),
            ("properties(itemId:", "browser.properties"),
            ("updateMatrixProperty(", "properties.update_matrix_property"),
            ("updateNumericProperty(", "properties.update_numeric_property"),
            ("updateTextProperty(", "properties.update_text_property"),
            ("updateDateProperty(", "properties.update_date_property"),
            ("updateStatusProperty(", "properties.update_status_property"),
        ):
            if marker in query:
                return label
        return "unknown"

    def _payload_for(self, query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        if "userAccessibleResources(" in query:
            return {
                "data": {
                    "userAccessibleResources": [
                        {
                            "id": "w1",
                            "name": "Workspace Main",
                            "readableId": "workspace_main",
                            "role": "EDITOR",
                            "products": [
                                {
                                    "id": "p1",
                                    "name": "Widget Product",
                                    "readableId": "widget_product",
                                    "role": "EDITOR",
                                }
                            ],
                        }
                    ]
                }
            }

        if "workspaces(" in query:
            return {
                "data": {
                    "workspaces": [
                        {
                            "id": "w1",
                            "orgId": "org-1",
                            "name": "Workspace Main",
                            "readableId": "workspace_main",
                        }
                    ]
                }
            }

        if "workspace(" in query:
            return {
                "data": {
                    "workspace": {
                        "id": "w1",
                        "orgId": "org-1",
                        "name": "Workspace Main",
                        "readableId": "workspace_main",
                    }
                }
            }

        if "setProductBaselineVersion(" in query:
            version_number = variables.get("versionNumber", 2)
            return {
                "data": {
                    "setProductBaselineVersion": {
                        "id": "p1",
                        "name": "Widget Product",
                        "readableId": "widget_product",
                        "workspaceId": "w1",
                        "baselineVersionNumber": version_number,
                        "reviewers": [],
                    }
                }
            }

        if "productVersions(" in query:
            return {
                "data": {
                    "productVersions": [
                        {
                            "productId": "p1",
                            "versionNumber": 2,
                            "title": "Version 2",
                            "description": "Current baseline",
                            "createdAt": "2026-01-01T00:00:00Z",
                        }
                    ]
                }
            }

        if "products(" in query:
            offset = int(variables.get("offset", 0))
            limit = int(variables.get("limit", 100))
            products = [
                {
                    "id": "p1",
                    "name": "Widget Product",
                    "readableId": "widget_product",
                    "workspaceId": "w1",
                    "baselineVersionNumber": 2,
                    "reviewers": [],
                }
            ]
            return {
                "data": {
                    "products": products[offset:offset + limit]
                }
            }

        if "sdkItems(" in query:
            offset = int(variables.get("offset", 0))
            limit = int(variables.get("limit", 100))
            items = [
                {
                    "id": "i1",
                    "name": "Widget Alpha",
                    "readableId": "widget_alpha",
                    "productId": "p1",
                    "parentId": None,
                    "position": 1,
                    "deleted": False,
                }
            ]
            return {
                "data": {
                    "sdkItems": items[offset:offset + limit]
                }
            }

        if "item(id:" in query:
            return {
                "data": {
                    "item": {
                        "id": "i1",
                        "name": "Widget Alpha",
                        "readableId": "widget_alpha",
                        "productId": "p1",
                        "parentId": None,
                        "position": 1,
                    }
                }
            }

        if "items(productId:" in query:
            offset = int(variables.get("offset", 0))
            limit = int(variables.get("limit", 100))
            parent_item_id = (variables.get("filter") or {}).get("parentItemId")
            items: list[dict[str, Any]]
            if parent_item_id:
                items = []
            else:
                items = [
                    {
                        "id": "i1",
                        "name": "Widget Alpha",
                        "readableId": "widget_alpha",
                        "productId": "p1",
                        "parentId": None,
                        "position": 1,
                    }
                ]
            return {"data": {"items": items[offset:offset + limit]}}

        if "searchProperties(" in query:
            return {
                "data": {
                    "searchProperties": {
                        "query": variables.get("q", "*"),
                        "hits": [
                            {
                                "id": "pn1",
                                "workspaceId": "w1",
                                "productId": "p1",
                                "itemId": "i1",
                                "propertyType": "numeric",
                                "name": "Mass",
                                "category": "MASS",
                                "value": "12.5",
                            }
                        ],
                        "total": 1,
                        "limit": variables.get("limit", 20),
                        "offset": variables.get("offset", 0),
                        "processingTimeMs": 1,
                    }
                }
            }

        if "sdkProperties(" in query or "properties(itemId:" in query:
            base_props = [
                {
                    "__typename": "NumericProperty",
                    "id": "pn1",
                    "name": "Mass",
                    "readableId": "mass",
                    "itemId": "i1",
                    "value": "12.5",
                    "parsedValue": 12.5,
                    "category": "MASS",
                    "displayUnit": "kg",
                    "deleted": False,
                    "draftPropertyId": None,
                    "updatedAt": "2026-01-01T00:00:00Z",
                    "updatedBy": "sdk@poelis.test",
                },
                {
                    "__typename": "MatrixProperty",
                    "id": "pm1",
                    "name": "Mass Matrix",
                    "readableId": "mass_matrix",
                    "itemId": "i1",
                    "value": "[[1, 2], [3, 4]]",
                    "parsedValue": [[1, 2], [3, 4]],
                    "category": "MASS",
                    "displayUnit": "kg",
                    "deleted": False,
                    "draftPropertyId": None,
                    "updatedAt": "2026-01-01T00:00:00Z",
                    "updatedBy": "sdk@poelis.test",
                },
                {
                    "__typename": "TextProperty",
                    "id": "pt1",
                    "name": "Description",
                    "readableId": "description",
                    "itemId": "i1",
                    "value": "Widget",
                    "parsedValue": "Widget",
                    "deleted": False,
                    "draftPropertyId": None,
                    "updatedAt": "2026-01-01T00:00:00Z",
                    "updatedBy": "sdk@poelis.test",
                },
                {
                    "__typename": "DateProperty",
                    "id": "pd1",
                    "name": "Release Date",
                    "readableId": "release_date",
                    "itemId": "i1",
                    "value": "2026-01-02",
                    "deleted": False,
                    "draftPropertyId": None,
                    "updatedAt": "2026-01-01T00:00:00Z",
                    "updatedBy": "sdk@poelis.test",
                },
                {
                    "__typename": "StatusProperty",
                    "id": "ps1",
                    "name": "Status",
                    "readableId": "status",
                    "itemId": "i1",
                    "value": "DRAFT",
                    "deleted": False,
                    "draftPropertyId": None,
                    "updatedAt": "2026-01-01T00:00:00Z",
                    "updatedBy": "sdk@poelis.test",
                },
                {
                    "__typename": "FormulaProperty",
                    "id": "pf1",
                    "name": "Computed Mass",
                    "readableId": "computed_mass",
                    "itemId": "i1",
                    "numericValue": "42",
                    "parsedValue": 42,
                    "formulaExpression": "@{pn1}",
                    "formulaDependencies": [
                        {
                            "id": "pn1",
                            "name": "Mass",
                            "value": "12.5",
                            "displayUnit": "kg",
                            "itemId": "i1",
                            "productId": "p1",
                            "hierarchyContext": [{"id": "i1", "name": "Widget Alpha"}],
                        }
                    ],
                    "hasFormulaDependencyChanges": False,
                    "deleted": False,
                    "draftPropertyId": None,
                    "updatedAt": "2026-01-01T00:00:00Z",
                    "updatedBy": "sdk@poelis.test",
                },
            ]
            field_name = "sdkProperties" if "sdkProperties(" in query else "properties"
            return {"data": {field_name: base_props}}

        if "updateNumericProperty(" in query:
            return {
                "data": {
                    "updateNumericProperty": {
                        "id": variables["id"],
                        "readableId": "mass",
                        "itemId": "i1",
                        "name": "Mass",
                        "position": 1,
                        "value": variables.get("value"),
                        "draftPropertyId": None,
                        "deleted": False,
                        "hasChanges": True,
                        "parsedValue": json.loads(variables.get("value", "0")),
                        "category": "MASS",
                        "displayUnit": "kg",
                    }
                }
            }

        if "updateMatrixProperty(" in query:
            return {
                "data": {
                    "updateMatrixProperty": {
                        "id": variables["id"],
                        "readableId": "mass_matrix",
                        "itemId": "i1",
                        "name": "Mass Matrix",
                        "position": 2,
                        "value": variables.get("value"),
                        "draftPropertyId": None,
                        "deleted": False,
                        "hasChanges": True,
                        "parsedValue": json.loads(variables.get("value", "[]")),
                        "category": "MASS",
                        "displayUnit": "kg",
                    }
                }
            }

        if "updateTextProperty(" in query:
            return {
                "data": {
                    "updateTextProperty": {
                        "id": variables["id"],
                        "readableId": "description",
                        "itemId": "i1",
                        "name": "Description",
                        "position": 3,
                        "value": variables.get("value"),
                        "draftPropertyId": None,
                        "deleted": False,
                        "hasChanges": True,
                        "parsedValue": variables.get("value"),
                    }
                }
            }

        if "updateDateProperty(" in query:
            return {
                "data": {
                    "updateDateProperty": {
                        "id": variables["id"],
                        "readableId": "release_date",
                        "itemId": "i1",
                        "name": "Release Date",
                        "position": 4,
                        "value": variables.get("value"),
                        "draftPropertyId": None,
                        "deleted": False,
                        "hasChanges": True,
                    }
                }
            }

        if "updateStatusProperty(" in query:
            return {
                "data": {
                    "updateStatusProperty": {
                        "id": variables["id"],
                        "readableId": "status",
                        "itemId": "i1",
                        "name": "Status",
                        "position": 5,
                        "value": variables.get("value"),
                        "draftPropertyId": None,
                        "deleted": False,
                        "hasChanges": True,
                    }
                }
            }

        return {"data": {}}


def _configure_client(transport: _RecordingTransport, *, enable_sdk_properties: bool = False) -> PoelisClient:
    client = PoelisClient(
        api_key="contract-audit",
        base_url="http://example.com",
        enable_change_detection=False,
    )
    client._transport = transport
    client.workspaces = WorkspacesClient(transport)
    client.products = ProductsClient(transport, client.workspaces)
    client.items = ItemsClient(transport)
    client.versions = VersionsClient(transport)
    client.properties = PropertiesClient(transport)
    client.search = SearchClient(transport)
    client.browser = Browser(client)
    if enable_sdk_properties:
        client._change_tracker.enable()
    return client


def collect_sdk_graphql_documents() -> List[GraphQLDocument]:
    transport = _RecordingTransport()
    client = _configure_client(transport)

    client.workspaces.list(limit=1, offset=0)
    client.workspaces.get(workspace_id="w1")
    client.workspaces.get_user_accessible_resources(user_id="user-1")

    client.products.list_by_workspace(workspace_id="w1", q="widget", limit=1, offset=0)
    client.products.list_product_versions(product_id="p1")
    client.products.set_product_baseline_version(product_id="p1", version_number=2)
    list(client.products.iter_all_by_workspace(workspace_id="w1", q="widget", page_size=1))
    list(client.products.iter_all(q="widget", page_size=1))

    client.items.list_by_product(product_id="p1", q="alpha", limit=1, offset=0)
    client.items.get("i1")
    list(client.items.iter_all_by_product(product_id="p1", q="alpha", page_size=1))

    client.versions.list_items(product_id="p1", version_number=2, q="alpha", limit=1, offset=0)
    list(client.versions.iter_items(product_id="p1", version_number=2, q="alpha", page_size=1))

    client.search.products(q="widget", workspace_id="w1", limit=1, offset=0)
    client.search.items(q="alpha", product_id="p1", parent_item_id="i1", limit=1, offset=0)
    client.search.properties(
        q="*",
        workspace_id="w1",
        product_id="p1",
        item_id="i1",
        property_type="numeric",
        category="mass",
        limit=1,
        offset=0,
        sort="updated_at",
    )

    client.properties.update_numeric_property(id="pn1", value="123.5", changed_via="PYTHON_SDK")
    client.properties.update_matrix_property(id="pm1", value="[[1, 2], [3, 4]]", changed_via="PYTHON_SDK")
    client.properties.update_text_property(id="pt1", value="Updated text", changed_via="PYTHON_SDK")
    client.properties.update_date_property(id="pd1", value="2026-02-01", changed_via="PYTHON_SDK")
    client.properties.update_status_property(id="ps1", value="DONE", changed_via="PYTHON_SDK")

    workspace = client.browser["workspace_main"]
    product = workspace["widget_product"]
    baseline_item = product["widget_alpha"]
    _ = baseline_item.list_properties().names
    _ = baseline_item.mass.value
    _ = product.draft["widget_alpha"].list_items().names

    sdk_transport = _RecordingTransport()
    sdk_client = _configure_client(sdk_transport, enable_sdk_properties=True)
    sdk_workspace = sdk_client.browser["workspace_main"]
    sdk_product = sdk_workspace["widget_product"]
    sdk_item = sdk_product["widget_alpha"]
    _ = sdk_item.list_properties().names
    _ = sdk_item.mass.value

    matlab = PoelisMatlab.__new__(PoelisMatlab)
    matlab.client = client
    matlab.get_value("workspace_main.widget_product.widget_alpha.mass")
    matlab.get_property("workspace_main.widget_product.widget_alpha.description")
    matlab.list_children("workspace_main")
    matlab.list_properties("workspace_main.widget_product.widget_alpha")
    matlab.change_property("workspace_main.widget_product.draft.widget_alpha.description", "Updated text")

    return _dedupe_documents([*transport.documents, *sdk_transport.documents])


def _dedupe_documents(documents: Iterable[GraphQLDocument]) -> List[GraphQLDocument]:
    seen: set[str] = set()
    unique: list[GraphQLDocument] = []
    for document in documents:
        normalized = "\n".join(line.rstrip() for line in document.query.strip().splitlines())
        if normalized in seen:
            continue
        seen.add(normalized)
        unique.append(GraphQLDocument(label=document.label, query=normalized))
    return unique


def backend_repo_root() -> Path:
    return Path(__file__).resolve().parents[3] / "poelis-be-py"


def backend_python() -> Path:
    return backend_repo_root() / ".venv" / "bin" / "python"


def validate_sdk_contracts() -> list[ContractValidationError]:
    python_bin = backend_python()
    if not python_bin.exists():
        raise FileNotFoundError(f"Backend Python not found at {python_bin}")

    script = """
import json
import sys

sys.path.insert(0, "src")

from graphql import parse, validate
from poelis.api.graphql.schema import schema

documents = json.load(sys.stdin)
errors = []
for document in documents:
    for error in validate(schema._schema, parse(document["query"])):
        errors.append({"label": document["label"], "message": str(error)})

json.dump(errors, sys.stdout)
"""

    completed = subprocess.run(
        [str(python_bin), "-c", script],
        input=json.dumps(
            [{"label": document.label, "query": document.query} for document in collect_sdk_graphql_documents()]
        ),
        text=True,
        cwd=backend_repo_root(),
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "Contract validation failed")

    payload = json.loads(completed.stdout or "[]")
    return [ContractValidationError(label=error["label"], message=error["message"]) for error in payload]

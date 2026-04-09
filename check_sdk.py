#!/usr/bin/env python3
"""Check the SDK against live data and/or the local backend schema."""

from __future__ import annotations

import argparse
import os
from typing import Any, Optional

from poelis_sdk import PoelisClient
from poelis_sdk._contract_audit import collect_sdk_graphql_documents, validate_sdk_contracts


def run(name: str, fn, *args, **kwargs) -> Any:
    """Run a call, print result summary, return value or None on error."""
    try:
        result = fn(*args, **kwargs)
        if result is None:
            print(f"  ✓ {name} → None")
        elif isinstance(result, (list, tuple)):
            print(f"  ✓ {name} → {len(result)} items")
        elif hasattr(result, "data"):
            print(f"  ✓ {name} → {len(result.data)} items")
        elif isinstance(result, dict):
            hits = result.get("hits", result)
            n = len(hits) if isinstance(hits, list) else "dict"
            print(f"  ✓ {name} → {n}")
        else:
            print(f"  ✓ {name} → {type(result).__name__}")
        return result
    except Exception as exc:
        print(f"  ✗ {name} → {type(exc).__name__}: {exc}")
        return None


def run_contract_audit() -> bool:
    print("\n=== Contract Audit ===")
    documents = collect_sdk_graphql_documents()
    print(f"  ✓ collected {len(documents)} unique GraphQL documents from the SDK surface")

    errors = validate_sdk_contracts()
    if errors:
        for error in errors:
            print(f"  ✗ {error.label} → {error.message}")
        return False

    print("  ✓ all SDK GraphQL documents validate against the local backend schema")
    return True


def run_live_checks() -> bool:
    api_key = os.environ.get("POELIS_API_KEY")
    if not api_key:
        print("Set POELIS_API_KEY to run live checks")
        return False

    base_url = os.environ.get("POELIS_BASE_URL", "https://poelis-be-py-753618215333.europe-west1.run.app")
    user_id = os.environ.get("POELIS_USER_ID")
    client = PoelisClient(api_key=api_key, base_url=base_url, enable_change_detection=False)
    ws_id: Optional[str] = None
    product_id: Optional[str] = None
    item_id: Optional[str] = None
    version_number: Optional[int] = None
    had_error = False

    print("\n=== 1. get_user_accessible_resources ===")
    if not user_id:
        print("  (skipped: set POELIS_USER_ID to run)")
        resources = None
    else:
        resources = run(
            "get_user_accessible_resources",
            client.workspaces.get_user_accessible_resources,
            user_id=user_id,
        )
    if resources and resources.workspaces:
        ws_id = resources.workspaces[0].id
        if resources.workspaces[0].products:
            product_id = resources.workspaces[0].products[0].id

    print("\n=== 2. workspaces.list ===")
    workspaces = run("workspaces.list", client.workspaces.list, limit=10, offset=0)
    if workspaces and not ws_id:
        ws_id = workspaces[0].get("id")

    print("\n=== 3. workspaces.get ===")
    if ws_id:
        if run("workspaces.get", client.workspaces.get, workspace_id=ws_id) is None:
            had_error = True
    else:
        print("  (skipped: no workspace_id from previous steps)")

    print("\n=== 4. products.list_by_workspace ===")
    products_page = None
    if ws_id:
        products_page = run(
            "products.list_by_workspace",
            client.products.list_by_workspace,
            workspace_id=ws_id,
            limit=10,
            offset=0,
        )
        if products_page and products_page.data and not product_id:
            product_id = products_page.data[0].id
    else:
        print("  (skipped: no workspace_id)")

    print("\n=== 5. products.list_product_versions ===")
    versions_page = None
    if product_id:
        versions_page = run(
            "products.list_product_versions",
            client.products.list_product_versions,
            product_id=product_id,
        )
        if versions_page and versions_page.data:
            version_number = versions_page.data[0].version_number
    else:
        print("  (skipped: no product_id)")

    print("\n=== 6. products.set_product_baseline_version (SKIP - write op) ===")
    print("  (skipped to avoid modifying data)")

    print("\n=== 7. items.list_by_product ===")
    items_list = None
    if product_id:
        items_list = run(
            "items.list_by_product",
            client.items.list_by_product,
            product_id=product_id,
            limit=10,
            offset=0,
        )
        if items_list and len(items_list) > 0 and not item_id:
            item_id = items_list[0].get("id")
    else:
        print("  (skipped: no product_id)")

    print("\n=== 8. items.get ===")
    if item_id:
        if run("items.get", client.items.get, item_id) is None:
            had_error = True
    else:
        print("  (skipped: no item_id)")

    print("\n=== 9. versions.list_items ===")
    if product_id and version_number:
        if run(
            "versions.list_items",
            client.versions.list_items,
            product_id=product_id,
            version_number=version_number,
            limit=10,
            offset=0,
        ) is None:
            had_error = True
    else:
        print("  (skipped: need product_id and version_number)")

    print("\n=== 10. search.products ===")
    if ws_id:
        if run(
            "search.products",
            client.search.products,
            q="*",
            workspace_id=ws_id,
            limit=10,
            offset=0,
        ) is None:
            had_error = True
    else:
        print("  (skipped: no workspace_id)")

    print("\n=== 11. search.items ===")
    if product_id:
        if run(
            "search.items",
            client.search.items,
            q=None,
            product_id=product_id,
            parent_item_id=None,
            limit=10,
            offset=0,
        ) is None:
            had_error = True
    else:
        print("  (skipped: no product_id)")

    print("\n=== 12. search.properties ===")
    if run(
        "search.properties",
        client.search.properties,
        q="*",
        workspace_id=ws_id,
        product_id=product_id,
        item_id=item_id,
        limit=10,
        offset=0,
    ) is None:
        had_error = True

    print("\n=== 13. properties.update_* (SKIP - write ops) ===")
    print("  (skipped to avoid modifying data)")

    print("\n=== 14. browser (navigate workspace → product → item → props) ===")
    ws_name = None
    if workspaces:
        ws_name = workspaces[0].get("readableId") or workspaces[0].get("name") or workspaces[0].get("id")
    elif resources and resources.workspaces:
        ws_name = resources.workspaces[0].name
    if ws_name:
        try:
            ws_node = client.browser[ws_name]
            prod_node = ws_node[ws_node.list_products().names[0]]
            item_node = prod_node[prod_node.list_items().names[0]]
            props = item_node.list_properties().names
            print(f"  ✓ browser traversal → {len(props)} properties")
        except Exception as exc:
            print(f"  ✗ browser → {exc}")
            had_error = True
    else:
        print("  (skipped: no workspace data)")

    print("\n=== 15. Client properties ===")
    print(f"  base_url: {client.base_url}")
    print(f"  org_id: {client.org_id}")
    print(f"  enable_change_detection: {client.enable_change_detection}")

    print("\n=== 16. PoelisClient.from_env ===")
    try:
        env_client = PoelisClient.from_env()
        print(f"  ✓ from_env → client (base_url={env_client.base_url})")
    except Exception as exc:
        print(f"  ✗ from_env → {exc}")
        had_error = True

    print("\n=== Done ===")
    return not had_error


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--validate-contracts",
        action="store_true",
        help="Validate the SDK's GraphQL documents against the sibling backend schema.",
    )
    parser.add_argument(
        "--contracts-only",
        action="store_true",
        help="Run only the local contract audit and skip live API checks.",
    )
    args = parser.parse_args(argv)

    success = True

    if args.validate_contracts or args.contracts_only:
        success = run_contract_audit() and success

    if not args.contracts_only:
        live_success = run_live_checks()
        if os.environ.get("POELIS_API_KEY"):
            success = live_success and success

    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())

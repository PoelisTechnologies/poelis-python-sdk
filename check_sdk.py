#!/usr/bin/env python3
"""Check every SDK method, chaining results from previous calls."""

from __future__ import annotations

import os
import sys
from typing import Any, Optional

from poelis_sdk import PoelisClient


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
    except Exception as e:
        print(f"  ✗ {name} → {type(e).__name__}: {e}")
        return None


def main() -> None:
    api_key = os.environ.get("POELIS_API_KEY")
    if not api_key:
        print("Set POELIS_API_KEY")
        sys.exit(1)

    base_url = os.environ.get("POELIS_BASE_URL", "https://poelis-be-py-753618215333.europe-west1.run.app")
    user_id = os.environ.get("POELIS_USER_ID")
    client = PoelisClient(api_key=api_key, base_url=base_url, enable_change_detection=False)
    ws_id: Optional[str] = None
    product_id: Optional[str] = None
    item_id: Optional[str] = None
    version_number: Optional[int] = None

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
        n_products = 0
        for ws in resources.workspaces:
            for p in ws.products:
                _ = (p.id, p.name, p.role)
                n_products += 1
        if n_products > 0:
            print(f"  ✓ ProductAccess validated ({n_products} products)")

    print("\n=== 2. workspaces.list ===")
    workspaces = run("workspaces.list", client.workspaces.list, limit=10, offset=0)
    if workspaces and not ws_id:
        ws_id = workspaces[0].get("id")

    print("\n=== 3. workspaces.get ===")
    if ws_id:
        run("workspaces.get", client.workspaces.get, workspace_id=ws_id)
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

    print("\n=== 6b. products.iter_all_by_workspace (first 3) ===")
    if not ws_id:
        print("  (skipped: no workspace_id)")
    elif ws_id:
        try:
            count = 0
            for _ in client.products.iter_all_by_workspace(workspace_id=ws_id, page_size=5):
                count += 1
                if count >= 3:
                    break
            print(f"  ✓ products.iter_all_by_workspace → yielded {count} products")
        except Exception as e:
            print(f"  ✗ products.iter_all_by_workspace → {e}")

    print("\n=== 7. items.list_by_product ===")
    items_list = None
    if not product_id:
        print("  (skipped: no product_id)")
    elif product_id:
        items_list = run(
            "items.list_by_product",
            client.items.list_by_product,
            product_id=product_id,
            limit=10,
            offset=0,
        )
        if items_list and len(items_list) > 0 and not item_id:
            item_id = items_list[0].get("id")

    print("\n=== 7b. items.iter_all_by_product (first 3) ===")
    if not product_id:
        print("  (skipped: no product_id)")
    elif product_id:
        try:
            count = 0
            for _ in client.items.iter_all_by_product(product_id=product_id, page_size=5):
                count += 1
                if count >= 3:
                    break
            print(f"  ✓ items.iter_all_by_product → yielded {count} items")
        except Exception as e:
            print(f"  ✗ items.iter_all_by_product → {e}")

    print("\n=== 7c. items.list_by_product (filter q) ===")
    if not product_id:
        print("  (skipped: no product_id)")
    elif product_id:
        run(
            "items.list_by_product(q='a')",
            client.items.list_by_product,
            product_id=product_id,
            q="a",
            limit=10,
            offset=0,
        )

    print("\n=== 8. items.get ===")
    if item_id:
        run("items.get", client.items.get, item_id)
    else:
        print("  (skipped: no item_id)")

    print("\n=== 9. versions.list_items ===")
    if not (product_id and version_number):
        print("  (skipped: need product_id and version_number)")
    elif product_id and version_number:
        run(
            "versions.list_items",
            client.versions.list_items,
            product_id=product_id,
            version_number=version_number,
            limit=10,
            offset=0,
        )

    print("\n=== 9b. versions.iter_items (first 3) ===")
    if not (product_id and version_number):
        print("  (skipped: need product_id and version_number)")
    elif product_id and version_number:
        try:
            count = 0
            for _ in client.versions.iter_items(product_id=product_id, version_number=version_number, page_size=5):
                count += 1
                if count >= 3:
                    break
            print(f"  ✓ versions.iter_items → yielded {count} items")
        except Exception as e:
            print(f"  ✗ versions.iter_items → {e}")

    print("\n=== 9c. versions.list_items (filter q) ===")
    if not (product_id and version_number):
        print("  (skipped: need product_id and version_number)")
    elif product_id and version_number:
        run(
            "versions.list_items(q='a')",
            client.versions.list_items,
            product_id=product_id,
            version_number=version_number,
            q="a",
            limit=10,
            offset=0,
        )

    print("\n=== 10. search.products ===")
    if not ws_id:
        print("  (skipped: no workspace_id)")
    elif ws_id:
        run(
            "search.products",
            client.search.products,
            q="*",
            workspace_id=ws_id,
            limit=10,
            offset=0,
        )

    print("\n=== 11. search.items ===")
    if not product_id:
        print("  (skipped: no product_id)")
    elif product_id:
        run(
            "search.items",
            client.search.items,
            q=None,
            product_id=product_id,
            parent_item_id=None,
            limit=10,
            offset=0,
        )

    print("\n=== 11b. search.items (filter q, parent_item_id) ===")
    if not product_id:
        print("  (skipped: no product_id)")
    elif product_id:
        run(
            "search.items(q='a', parent_item_id=item_id)",
            client.search.items,
            q="a",
            product_id=product_id,
            parent_item_id=item_id,
            limit=10,
            offset=0,
        )

    print("\n=== 12. search.properties ===")
    run(
        "search.properties",
        client.search.properties,
        q="*",
        workspace_id=ws_id,
        product_id=product_id,
        item_id=item_id,
        limit=10,
        offset=0,
    )

    print("\n=== 13. properties.update_* (SKIP - write ops) ===")
    print("  (skipped to avoid modifying data)")

    print("\n=== 14. browser (navigate workspace → product → item → props) ===")
    ws_name = None
    has_ws_data = (workspaces and len(workspaces) > 0) or (resources and resources.workspaces)
    if not has_ws_data:
        print("  (skipped: no workspace data)")
    elif workspaces:
        ws_name = workspaces[0].get("readableId") or workspaces[0].get("name") or workspaces[0].get("id")
    elif resources and resources.workspaces:
        ws_name = resources.workspaces[0].name
    if ws_name:
        try:
            ws_node = client.browser[ws_name]
            print(f"  ✓ browser[{ws_name!r}] → workspace node")
            prod_names = list(ws_node._children_cache.keys()) if ws_node._children_cache else []
            if not prod_names and hasattr(ws_node, "_load_children"):
                ws_node._load_children()
                prod_names = list(ws_node._children_cache.keys())
            if prod_names:
                prod_node = ws_node[prod_names[0]]
                print("  ✓ browser → product node")
                baseline = getattr(prod_node, "baseline", None)
                if baseline:
                    baseline._load_children()
                    item_keys = list(baseline._children_cache.keys()) if baseline._children_cache else []
                    if item_keys:
                        item_node = baseline[item_keys[0]]
                        props = item_node._properties() if hasattr(item_node, "_properties") else []
                        print(f"  ✓ browser → item → {len(props)} props")
                    else:
                        print("  ✓ browser → product (no items)")
                else:
                    print("  ✓ browser → product (no baseline)")
        except Exception as e:
            print(f"  ✗ browser → {e}")

    print("\n=== 15. browser.list_workspaces ===")
    run("browser.list_workspaces", client.browser.list_workspaces)

    print("\n=== 16. Client properties ===")
    print(f"  base_url: {client.base_url}")
    print(f"  org_id: {client.org_id}")
    print(f"  enable_change_detection: {client.enable_change_detection}")

    print("\n=== 17. PoelisClient.from_env ===")
    try:
        env_client = PoelisClient.from_env()
        print(f"  ✓ from_env → client (base_url={env_client.base_url})")
    except Exception as e:
        print(f"  ✗ from_env → {e}")

    print("\n=== Done ===")


if __name__ == "__main__":
    main()

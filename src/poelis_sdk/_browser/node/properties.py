"""Property loading/search logic for Browser `_Node` (internal)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .._graphql_errors import _handle_graphql_read_errors
from ..props import _PropWrapper
from ..utils import _safe_key

if TYPE_CHECKING:  # pragma: no cover
    from ..nodes import _Node


def properties(node: "_Node") -> List[Dict[str, Any]]:
    """Return cached properties for an item node (behavior preserved)."""
    if not node._is_props_cache_stale():
        return node._props_cache or []
    if node._level != "item":
        node._props_cache = []
        node._props_loaded_at = time.time()
        return node._props_cache

    version_number = getattr(node, "_version_number", None)
    anc = node
    pid: Optional[str] = None
    while anc is not None:
        if anc._level == "product":
            pid = anc._id
            break
        anc = anc._parent  # type: ignore[assignment]

    use_sdk_properties = False
    try:
        change_tracker = getattr(node._client, "_change_tracker", None)
        if change_tracker is not None and change_tracker.is_enabled():
            use_sdk_properties = True
    except Exception:
        pass

    query_name = "sdkProperties" if use_sdk_properties else "properties"
    property_type_prefix = "Sdk" if use_sdk_properties else ""

    formula_on_numeric = " formulaExpression formulaDependencies { id name value displayUnit hierarchyContext { id name } itemId productId }" if use_sdk_properties else " formulaExpression formulaDependencies { id name value displayUnit itemId productId }"
    updated_fields = " updatedAt updatedBy" if use_sdk_properties else ""
    formula_fragment = f"    ... on {property_type_prefix}FormulaProperty {{ id name readableId category displayUnit numericValue: value parsedValue{formula_on_numeric} hasFormulaDependencyChanges{updated_fields} }}\n"
    matrix_fragment = f"    ... on {property_type_prefix}MatrixProperty {{ id name readableId category displayUnit value parsedValue{updated_fields} }}\n"
    if version_number is not None and pid is not None:
        q_parsed = (
            f"query($iid: ID!, $version: VersionInput!) {{\n"
            f"  {query_name}(itemId: $iid, version: $version) {{\n"
            f"    __typename\n"
            f"    ... on {property_type_prefix}NumericProperty {{ id name readableId category displayUnit numericValue: value parsedValue{updated_fields} }}\n"
            f"{formula_fragment}"
            f"{matrix_fragment}"
            f"    ... on {property_type_prefix}TextProperty {{ id name readableId value parsedValue{updated_fields} }}\n"
            f"    ... on {property_type_prefix}DateProperty {{ id name readableId value{updated_fields} }}\n"
            f"  }}\n"
            f"}}"
        )
        variables = {"iid": node._id, "version": {"productId": pid, "versionNumber": version_number}}
    else:
        q_parsed = (
            f"query($iid: ID!) {{\n"
            f"  {query_name}(itemId: $iid) {{\n"
            f"    __typename\n"
            f"    ... on {property_type_prefix}NumericProperty {{ id name readableId category displayUnit numericValue: value parsedValue{updated_fields} }}\n"
            f"{formula_fragment}"
            f"{matrix_fragment}"
            f"    ... on {property_type_prefix}TextProperty {{ id name readableId value parsedValue{updated_fields} }}\n"
            f"    ... on {property_type_prefix}DateProperty {{ id name readableId value{updated_fields} }}\n"
            f"  }}\n"
            f"}}"
        )
        variables = {"iid": node._id}

    try:
        r = node._client._transport.graphql(q_parsed, variables)
        r.raise_for_status()
        data = r.json()
        if "errors" in data:
            if use_sdk_properties:
                pass
            else:
                errors = data["errors"]
                if version_number is not None:
                    error_msg = str(errors)
                    if "version" in error_msg.lower() and ("unknown" in error_msg.lower() or "cannot" in error_msg.lower()):
                        pass
                    else:
                        raise RuntimeError(data["errors"])
                else:
                    raise RuntimeError(data["errors"])
        else:
            props_data = data.get("data", {}).get(query_name, []) or []
            node._props_cache = props_data
            node._props_loaded_at = time.time()
            return node._props_cache
    except RuntimeError:
        if not use_sdk_properties:
            raise
    except Exception:
        if not use_sdk_properties:
            raise

    if use_sdk_properties:
        try:
            if version_number is not None and pid is not None:
                q_value_only = (
                    "query($iid: ID!, $version: VersionInput!) {\n"
                    "  properties(itemId: $iid, version: $version) {\n"
                    "    __typename\n"
                    "    ... on NumericProperty { id name readableId category displayUnit numericValue: value parsedValue }\n"
                    "    ... on FormulaProperty { id name readableId category displayUnit numericValue: value parsedValue formulaExpression formulaDependencies { id name value displayUnit itemId productId } hasFormulaDependencyChanges }\n"
                    "    ... on MatrixProperty { id name readableId category displayUnit value parsedValue }\n"
                    "    ... on TextProperty { id name readableId value }\n"
                    "    ... on DateProperty { id name readableId value }\n"
                    "  }\n"
                    "}"
                )
                variables = {"iid": node._id, "version": {"productId": pid, "versionNumber": version_number}}
            else:
                q_value_only = (
                    "query($iid: ID!) {\n"
                    "  properties(itemId: $iid) {\n"
                    "    __typename\n"
                    "    ... on NumericProperty { id name readableId category displayUnit numericValue: value parsedValue }\n"
                    "    ... on FormulaProperty { id name readableId category displayUnit numericValue: value parsedValue formulaExpression formulaDependencies { id name value displayUnit itemId productId } hasFormulaDependencyChanges }\n"
                    "    ... on MatrixProperty { id name readableId category displayUnit value parsedValue }\n"
                    "    ... on TextProperty { id name readableId value }\n"
                    "    ... on DateProperty { id name readableId value }\n"
                    "  }\n"
                    "}"
                )
                variables = {"iid": node._id}
            try:
                r = node._client._transport.graphql(q_value_only, variables)
                r.raise_for_status()
                data = r.json()
                if "errors" in data:
                    errors = data["errors"]
                    if version_number is not None:
                        error_msg = str(errors)
                        if "version" in error_msg.lower() and ("unknown" in error_msg.lower() or "cannot" in error_msg.lower()):
                            pass
                        else:
                            _handle_graphql_read_errors(errors)
                    else:
                        _handle_graphql_read_errors(errors)
                node._props_cache = data.get("data", {}).get("properties", []) or []
                node._props_loaded_at = time.time()
                return node._props_cache
            except RuntimeError:
                raise
            except Exception:
                pass
        except Exception:
            pass

    try:
        q2_parsed = (
            "query($iid: ID!, $limit: Int!, $offset: Int!) {\n"
            "  searchProperties(q: \"*\", itemId: $iid, limit: $limit, offset: $offset) {\n"
            "    hits { id workspaceId productId itemId propertyType name readableId category displayUnit value parsedValue }\n"
            "  }\n"
            "}"
        )
        try:
            r2 = node._client._transport.graphql(q2_parsed, {"iid": node._id, "limit": 100, "offset": 0})
            r2.raise_for_status()
            data2 = r2.json()
            if "errors" in data2:
                _handle_graphql_read_errors(data2["errors"])
            node._props_cache = data2.get("data", {}).get("searchProperties", {}).get("hits", []) or []
            node._props_loaded_at = time.time()
        except Exception:
            q2_min = (
                "query($iid: ID!, $limit: Int!, $offset: Int!) {\n"
                "  searchProperties(q: \"*\", itemId: $iid, limit: $limit, offset: $offset) {\n"
                "    hits { id workspaceId productId itemId propertyType name readableId category displayUnit value }\n"
                "  }\n"
                "}"
            )
            r3 = node._client._transport.graphql(q2_min, {"iid": node._id, "limit": 100, "offset": 0})
            r3.raise_for_status()
            data3 = r3.json()
            if "errors" in data3:
                _handle_graphql_read_errors(data3["errors"])
            node._props_cache = data3.get("data", {}).get("searchProperties", {}).get("hits", []) or []
            node._props_loaded_at = time.time()
    except Exception:
        node._props_cache = []
        node._props_loaded_at = time.time()
    return node._props_cache


def props_key_map(node: "_Node") -> Dict[str, Dict[str, Any]]:
    """Map safe keys to property wrappers for item-level attribute access."""
    out: Dict[str, Dict[str, Any]] = {}
    if node._level != "item":
        return out
    props = node._properties()
    used_names: Dict[str, int] = {}
    for i, pr in enumerate(props):
        display = pr.get("readableId") or pr.get("name") or pr.get("id") or pr.get("category") or f"property_{i}"
        safe = _safe_key(str(display))
        if safe in used_names:
            used_names[safe] += 1
            safe = f"{safe}_{used_names[safe]}"
        else:
            used_names[safe] = 0
        out[safe] = _PropWrapper(pr, client=node._client)
    return out


def get_property(node: "_Node", readable_id: str) -> "_PropWrapper":
    """Get a property by its readableId from an item context.

    Implementation moved from `src/poelis_sdk/_browser/node_properties.py` (legacy)
    to fully consolidate node property logic under `src/poelis_sdk/_browser/node/`.
    
    Note: get_property() is only available on item nodes. For product or version nodes,
    navigate to an item first, e.g., product.baseline.<item>.get_property() or
    version.<item>.get_property().
    """
    if node._level == "product":
        raise AttributeError(
            "get_property() is not available on product nodes. "
            "Use product.baseline.<item>.get_property() or product.draft.<item>.get_property() instead."
        )

    if node._level == "version":
        raise AttributeError(
            "get_property() is not available on version nodes. "
            "Use version.<item>.get_property() instead to access properties from items in this version."
        )

    # Only item nodes are allowed
    return get_property_from_item_tree(node, readable_id)


def get_property_from_item_tree(node: "_Node", readable_id: str) -> "_PropWrapper":
    """Search for a property recursively starting from an item node."""
    anc = node
    pid: Optional[str] = None
    version_number: Optional[int] = None

    while anc is not None:
        if anc._level == "product":
            pid = anc._id
        elif anc._level == "version":
            if anc._id is not None:
                try:
                    version_number = int(anc._id)
                except (TypeError, ValueError):
                    version_number = None
            else:
                version_number = None
        elif anc._level == "item":
            item_version = getattr(anc, "_version_number", None)
            if item_version is not None:
                version_number = item_version
        anc = anc._parent  # type: ignore[assignment]

    if not pid:
        raise RuntimeError("Cannot determine product ID for item node")

    return search_property_in_item_and_children(node, node._id, readable_id, pid, version_number)


def search_property_in_item_and_children(
    node: "_Node",
    item_id: Optional[str],
    readable_id: str,
    product_id: str,
    version_number: Optional[int],
) -> "_PropWrapper":
    """Recursively search for a property in an item and all its children."""
    if not item_id:
        raise RuntimeError(f"Property with readableId '{readable_id}' not found")

    use_sdk_properties = False
    try:
        change_tracker = getattr(node._client, "_change_tracker", None)
        if change_tracker is not None and change_tracker.is_enabled():
            use_sdk_properties = True
    except Exception:
        use_sdk_properties = False

    query_name = "sdkProperties" if use_sdk_properties else "properties"
    property_type_prefix = "Sdk" if use_sdk_properties else ""
    updated_fields = " updatedAt updatedBy" if use_sdk_properties else ""
    formula_on_numeric = " formulaExpression formulaDependencies { id name value displayUnit hierarchyContext { id name } itemId productId }" if use_sdk_properties else " formulaExpression formulaDependencies { id name value displayUnit itemId productId }"
    formula_fragment = f"    ... on {property_type_prefix}FormulaProperty {{ id name readableId category displayUnit numericValue: value parsedValue{formula_on_numeric} hasFormulaDependencyChanges{updated_fields} }}\n"
    matrix_fragment = f"    ... on {property_type_prefix}MatrixProperty {{ id name readableId category displayUnit value parsedValue{updated_fields} }}\n"
    if version_number is not None:
        prop_query = (
            f"query($iid: ID!, $version: VersionInput!) {{\n"
            f"  {query_name}(itemId: $iid, version: $version) {{\n"
            f"    __typename\n"
            f"    ... on {property_type_prefix}NumericProperty {{ id name readableId category displayUnit numericValue: value parsedValue{updated_fields} }}\n"
            f"{formula_fragment}"
            f"{matrix_fragment}"
            f"    ... on {property_type_prefix}TextProperty {{ id name readableId value parsedValue{updated_fields} }}\n"
            f"    ... on {property_type_prefix}DateProperty {{ id name readableId value{updated_fields} }}\n"
            f"  }}\n"
            f"}}"
        )
        prop_variables = {"iid": item_id, "version": {"productId": product_id, "versionNumber": version_number}}
    else:
        prop_query = (
            f"query($iid: ID!) {{\n"
            f"  {query_name}(itemId: $iid) {{\n"
            f"    __typename\n"
            f"    ... on {property_type_prefix}NumericProperty {{ id name readableId category displayUnit numericValue: value parsedValue{updated_fields} }}\n"
            f"{formula_fragment}"
            f"{matrix_fragment}"
            f"    ... on {property_type_prefix}TextProperty {{ id name readableId value parsedValue{updated_fields} }}\n"
            f"    ... on {property_type_prefix}DateProperty {{ id name readableId value{updated_fields} }}\n"
            f"  }}\n"
            f"}}"
        )
        prop_variables = {"iid": item_id}

    try:
        r = node._client._transport.graphql(prop_query, prop_variables)
        r.raise_for_status()
        data = r.json()
        if "errors" in data:
            if use_sdk_properties:
                if version_number is not None:
                    fallback_query = (
                        "query($iid: ID!, $version: VersionInput!) {\n"
                        "  properties(itemId: $iid, version: $version) {\n"
                        "    __typename\n"
                        "    ... on NumericProperty { id name readableId category displayUnit numericValue: value parsedValue }\n"
                        "    ... on FormulaProperty { id name readableId category displayUnit numericValue: value parsedValue formulaExpression formulaDependencies { id name value displayUnit itemId productId } hasFormulaDependencyChanges }\n"
                        "    ... on MatrixProperty { id name readableId category displayUnit value parsedValue }\n"
                        "    ... on TextProperty { id name readableId value parsedValue }\n"
                        "    ... on DateProperty { id name readableId value }\n"
                        "  }\n"
                        "}"
                    )
                    fallback_vars = {"iid": item_id, "version": {"productId": product_id, "versionNumber": version_number}}
                else:
                    fallback_query = (
                        "query($iid: ID!) {\n"
                        "  properties(itemId: $iid) {\n"
                        "    __typename\n"
                        "    ... on NumericProperty { id name readableId category displayUnit numericValue: value parsedValue }\n"
                        "    ... on FormulaProperty { id name readableId category displayUnit numericValue: value parsedValue formulaExpression formulaDependencies { id name value displayUnit itemId productId } hasFormulaDependencyChanges }\n"
                        "    ... on MatrixProperty { id name readableId category displayUnit value parsedValue }\n"
                        "    ... on TextProperty { id name readableId value parsedValue }\n"
                        "    ... on DateProperty { id name readableId value }\n"
                        "  }\n"
                        "}"
                    )
                    fallback_vars = {"iid": item_id}

                try:
                    r_fb = node._client._transport.graphql(fallback_query, fallback_vars)
                    r_fb.raise_for_status()
                    data = r_fb.json()
                    if "errors" in data:
                        raise RuntimeError(data["errors"])
                except Exception:
                    data = {"data": {}}
            else:
                raise RuntimeError(data["errors"])

        props = data.get("data", {}).get(query_name, []) or []
        if not props:
            props = data.get("data", {}).get("properties", []) or []

        for prop in props:
            if prop.get("readableId") == readable_id:
                wrapper = _PropWrapper(prop, client=node._client)
                if node._client is not None:
                    try:
                        change_tracker2 = getattr(node._client, "_change_tracker", None)
                        if change_tracker2 is not None and change_tracker2.is_enabled():
                            property_path = node._build_path(readable_id)
                            if property_path:
                                prop_name = prop.get("readableId") or prop.get("name") or readable_id
                                prop_id = prop.get("id")
                                change_tracker2.record_accessed_property(property_path, prop_name, prop_id)
                    except Exception:
                        pass
                return wrapper
    except Exception:
        pass

    if version_number is not None:
        all_items = node._client.versions.list_items(
            product_id=product_id,
            version_number=version_number,
            limit=1000,
            offset=0,
        )
        child_items = [it for it in all_items if it.get("parentId") == item_id]
    else:
        child_query = (
            "query($pid: ID!, $parent: ID!, $limit: Int!, $offset: Int!) {\n"
            "  items(productId: $pid, parentItemId: $parent, limit: $limit, offset: $offset) { id name readableId productId parentId position }\n"
            "}"
        )
        try:
            r = node._client._transport.graphql(
                child_query, {"pid": product_id, "parent": item_id, "limit": 1000, "offset": 0}
            )
            r.raise_for_status()
            data = r.json()
            if "errors" in data:
                raise RuntimeError(f"Property with readableId '{readable_id}' not found")
            child_items = data.get("data", {}).get("items", []) or []
        except Exception:
            raise RuntimeError(f"Property with readableId '{readable_id}' not found")

    for child_item in child_items:
        child_id = child_item.get("id")
        if child_id:
            try:
                return search_property_in_item_and_children(node, child_id, readable_id, product_id, version_number)
            except RuntimeError:
                continue

    raise RuntimeError(f"Property with readableId '{readable_id}' not found in item tree")



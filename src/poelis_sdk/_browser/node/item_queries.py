"""Item query helpers for the Browser layer (internal)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from poelis_sdk._item_filter import item_draft_id

from ..utils import _is_visible_version_item

if TYPE_CHECKING:  # pragma: no cover
    from ..nodes import _Node


def _list_draft_items(
    node: "_Node",
    *,
    product_id: str,
    root_only: bool | None = None,
    parent_item_id: str | None = None,
) -> list[dict[str, Any]]:
    return list(
        node._client.items.iter_all_by_product(
            product_id=product_id,
            root_only=root_only,
            parent_item_id=parent_item_id,
        )
    )


def _list_versioned_items(
    node: "_Node",
    *,
    product_id: str,
    version_number: int,
    root_only: bool | None = None,
    parent_item_id: str | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in node._client.versions.iter_items(
        product_id=product_id,
        version_number=version_number,
        root_only=root_only,
        parent_item_id=parent_item_id,
    ):
        if _is_visible_version_item(item):
            rows.append(item)
    return rows


def _direct_child_rows(
    rows: list[dict[str, Any]],
    *,
    parent_node_id: str,
) -> list[dict[str, Any]]:
    """Keep only direct children; parentItemId filter also returns the parent row."""
    children: list[dict[str, Any]] = []
    for row in rows:
        if str(row.get("id")) == parent_node_id:
            continue
        parent_id = row.get("parentId")
        if parent_id is not None and str(parent_id) == parent_node_id:
            children.append(row)
    return children


def _node_draft_item_id(node: "_Node") -> str:
    draft_id = getattr(node, "_draft_item_id", None)
    if draft_id is not None:
        return str(draft_id)
    return str(node._id)


def _child_node_draft_id(item_row: dict[str, Any]) -> str:
    return item_draft_id(item_row)

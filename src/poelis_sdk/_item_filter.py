from __future__ import annotations

from typing import Any


def build_item_filter(
    *,
    q: str | None = None,
    root_only: bool | None = None,
    parent_item_id: str | None = None,
    include_deleted: bool | None = None,
) -> dict[str, Any] | None:
    """Build a GraphQL ItemFilter object, omitting unset fields."""
    filt: dict[str, Any] = {}
    if q is not None:
        filt["q"] = q
    if root_only is not None:
        filt["rootOnly"] = root_only
    if parent_item_id is not None:
        filt["parentItemId"] = parent_item_id
    if include_deleted is not None:
        filt["includeDeleted"] = include_deleted
    return filt or None


def item_draft_id(item: dict[str, Any]) -> str:
    """Return the draft-scoped id used for ItemFilter.parentItemId."""
    draft_id = item.get("draftItemId")
    if draft_id is not None:
        return str(draft_id)
    return str(item["id"])

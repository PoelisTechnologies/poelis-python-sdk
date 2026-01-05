"""Public Browser entrypoint (internal implementation)."""

from __future__ import annotations

from typing import Any, List

from ..org_validation import get_organization_context_message
from .completion import enable_dynamic_completion
from .nodes import _Node
from .props import _NodeList


# Internal guard to avoid repeated completer installation
_AUTO_COMPLETER_INSTALLED: bool = False


class Browser:
    """Public browser entrypoint."""

    def __init__(self, client: Any, cache_ttl: float = 30.0) -> None:
        """Initialize browser with optional cache TTL.

        Args:
            client: PoelisClient instance
            cache_ttl: Cache time-to-live in seconds (default: 30)
        """
        self._root = _Node(client, "root", None, None, None)
        # Set cache TTL for all nodes
        self._root._cache_ttl = cache_ttl
        # Best-effort: auto-enable curated completion in interactive shells
        global _AUTO_COMPLETER_INSTALLED
        if not _AUTO_COMPLETER_INSTALLED:
            try:
                if enable_dynamic_completion():
                    _AUTO_COMPLETER_INSTALLED = True
            except Exception:
                # Non-interactive or IPython not available; ignore silently
                pass

    def __getattr__(self, attr: str) -> Any:  # pragma: no cover - notebook UX
        return getattr(self._root, attr)

    def __repr__(self) -> str:  # pragma: no cover - notebook UX
        org_context = get_organization_context_message(None)
        return f"<browser root> ({org_context})"

    def __getitem__(self, key: str) -> Any:  # pragma: no cover - notebook UX
        """Delegate index-based access to the root node so names work: browser["Workspace Name"]."""
        return self._root[key]

    def __dir__(self) -> list[str]:  # pragma: no cover - notebook UX
        # Performance optimization: only load children if cache is stale or empty
        if self._root._is_children_cache_stale():
            self._root._load_children()
        keys = [*self._root._children_cache.keys(), "list_workspaces"]
        return sorted(keys)

    def _names(self) -> List[str]:
        """Return display names of root-level children (workspaces)."""
        return self._root._names()

    # keep suggest internal so it doesn't appear in help/dir
    def _suggest(self) -> List[str]:
        sugg = list(self._root._suggest())
        sugg.append("list_workspaces")
        return sorted(set(sugg))

    # suggest() removed from public API; dynamic completion still uses internal _suggest

    def list_workspaces(self) -> "_NodeList":
        """Return workspaces as a list-like object with `.names`."""
        return self._root._list_workspaces()



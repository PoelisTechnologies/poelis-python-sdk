"""Compatibility shim for `_Node` (internal).

For max internal consistency, the `_Node` implementation lives in
`poelis_sdk._browser.node.core`. This module re-exports `_Node` so other
internal modules can continue importing from `poelis_sdk._browser.nodes`.
"""

from __future__ import annotations

from .node.core import _Node as _Node

__all__ = ["_Node"]





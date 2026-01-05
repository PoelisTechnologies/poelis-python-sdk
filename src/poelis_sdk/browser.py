"""GraphQL-backed dot-path browser for Poelis SDK.

This module is the **public** import location for the Browser DSL:

    - ``from poelis_sdk.browser import Browser``

Internally, the implementation is split across multiple files under
``poelis_sdk._browser``. This file intentionally re-exports the public surface
to keep backwards compatibility while allowing a maintainable structure.

Important:
    The refactor is **structural only**: runtime behavior should remain the
    same. If you find a behavioral difference, treat it as a bug.
"""

from __future__ import annotations

# Public entrypoint
from ._browser.public import Browser as Browser

# Completion helper (kept importable for compatibility, even if typically used
# indirectly via Browser auto-installation).
from ._browser.completion import enable_dynamic_completion as enable_dynamic_completion

# Internal types historically imported by tests / advanced users.
from ._browser.nodes import _Node as _Node
from ._browser.props import _NodeList as _NodeList
from ._browser.props import _PropsNode as _PropsNode
from ._browser.props import _PropWrapper as _PropWrapper

# Internal helpers kept for compatibility with previous module-level symbols.
from ._browser._graphql_errors import _handle_graphql_read_errors as _handle_graphql_read_errors
from ._browser.utils import _safe_key as _safe_key

__all__ = [
    "Browser",
    "enable_dynamic_completion",
    "_Node",
    "_NodeList",
    "_PropsNode",
    "_PropWrapper",
    "_handle_graphql_read_errors",
    "_safe_key",
]




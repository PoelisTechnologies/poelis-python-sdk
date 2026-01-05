"""Dynamic completion integration for IPython/Jupyter (internal)."""

from __future__ import annotations

from types import MethodType
from typing import Any, List


def enable_dynamic_completion() -> bool:
    """Enable dynamic attribute completion in IPython/Jupyter environments.

    This helper attempts to configure IPython to use runtime-based completion
    (disabling Jedi) so that our dynamic `__dir__` and `suggest()` methods are
    respected by TAB completion. Returns True if an interactive shell was found
    and configured, False otherwise.
    """

    try:
        # Deferred import to avoid hard dependency
        from IPython import get_ipython  # type: ignore
    except Exception:
        return False

    ip = None
    try:
        ip = get_ipython()  # type: ignore[assignment]
    except Exception:
        ip = None
    if ip is None:
        return False

    enabled = False
    # Best-effort configuration: rely on IPython's fallback (non-Jedi) completer
    try:
        if hasattr(ip, "Completer") and hasattr(ip.Completer, "use_jedi"):
            # Disable Jedi to let IPython consult __dir__ dynamically
            ip.Completer.use_jedi = False  # type: ignore[assignment]
            # Greedy completion improves attribute completion depth
            if hasattr(ip.Completer, "greedy"):
                ip.Completer.greedy = True  # type: ignore[assignment]
            enabled = True
    except Exception:
        pass

    # Additionally, install a lightweight attribute completer that uses suggest()
    try:
        comp = getattr(ip, "Completer", None)
        if comp is not None and hasattr(comp, "attr_matches"):
            orig_attr_matches = comp.attr_matches  # type: ignore[attr-defined]

            def _poelis_attr_matches(self: Any, text: str) -> List[str]:  # pragma: no cover - interactive behavior
                try:
                    # text is like "client.browser.uh2.pr" → split at last dot
                    obj_expr, _, prefix = text.rpartition(".")
                    if not obj_expr:
                        return orig_attr_matches(text)  # type: ignore[operator]
                    # Evaluate the object in the user namespace
                    ns = getattr(self, "namespace", {})
                    obj_val = eval(obj_expr, ns, ns)

                    # Lazy import to avoid circular imports during module init
                    from .nodes import _Node
                    from .props import _PropsNode, _PropWrapper
                    from .public import Browser

                    # For Poelis browser objects, show ONLY our curated suggestions
                    from_types = (Browser, _Node, _PropsNode, _PropWrapper)
                    if isinstance(obj_val, from_types):
                        # Build suggestion list
                        if isinstance(obj_val, _PropWrapper):
                            sugg: List[str] = ["value", "category", "unit"]
                        elif hasattr(obj_val, "_suggest"):
                            sugg = list(getattr(obj_val, "_suggest")())  # type: ignore[no-untyped-call]
                        else:
                            sugg = list(dir(obj_val))
                        # Filter by prefix and format matches as full attribute paths
                        out: List[str] = []
                        for s in sugg:
                            if not prefix or str(s).startswith(prefix):
                                out.append(f"{obj_expr}.{s}")
                        return out

                    # Otherwise, fall back to default behavior
                    return orig_attr_matches(text)  # type: ignore[operator]
                except Exception:
                    # fall back to original on any error
                    return orig_attr_matches(text)  # type: ignore[operator]

            comp.attr_matches = MethodType(_poelis_attr_matches, comp)  # type: ignore[assignment]
            enabled = True
    except Exception:
        pass

    # Also register as a high-priority matcher in IPCompleter.matchers
    try:
        comp = getattr(ip, "Completer", None)
        if comp is not None and hasattr(comp, "matchers") and not getattr(comp, "_poelis_matcher_installed", False):
            orig_attr_matches = comp.attr_matches  # type: ignore[attr-defined]

            def _poelis_matcher(self: Any, text: str) -> List[str]:  # pragma: no cover - interactive behavior
                # Delegate to our attribute logic for dotted expressions; otherwise empty
                if "." in text:
                    try:
                        return self.attr_matches(text)  # type: ignore[operator]
                    except Exception:
                        return orig_attr_matches(text)  # type: ignore[operator]
                return []

            # Prepend our matcher so it's consulted early
            comp.matchers.insert(0, MethodType(_poelis_matcher, comp))  # type: ignore[arg-type]
            setattr(comp, "_poelis_matcher_installed", True)
            enabled = True
    except Exception:
        pass

    return bool(enabled)



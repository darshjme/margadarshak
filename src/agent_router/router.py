"""Core routing primitives for multi-agent request routing."""

from __future__ import annotations

import re
from typing import Any, Callable


class NoRouteError(Exception):
    """Raised when no route matches a request and no fallback is set."""

    def __init__(self, request: str) -> None:
        self.request = request
        super().__init__(f"No route matched request: {request!r}")


class Route:
    """A routing rule that matches a request string against a pattern."""

    def __init__(
        self,
        pattern: str,
        handler: Callable,
        priority: int = 0,
        method: str = "any",
    ) -> None:
        self._pattern = pattern
        self.handler = handler
        self.priority = priority
        self.method = method

    @property
    def pattern(self) -> str:
        return self._pattern

    def matches(self, request: str) -> bool:
        """Return True if the pattern appears as a substring of the request."""
        return self._pattern in request

    def __call__(self, request: str) -> Any:
        return self.handler(request)


class RegexRoute(Route):
    """A route that matches using a regular expression.

    Named groups extracted from the match are passed as keyword arguments
    to the handler in addition to the positional request string.
    """

    def __init__(
        self,
        pattern: str,
        handler: Callable,
        priority: int = 0,
        method: str = "any",
    ) -> None:
        super().__init__(pattern, handler, priority, method)
        self._compiled = re.compile(pattern)

    def matches(self, request: str) -> bool:
        return bool(self._compiled.search(request))

    def __call__(self, request: str) -> Any:
        m = self._compiled.search(request)
        kwargs = m.groupdict() if m else {}
        return self.handler(request, **kwargs)


class KeywordRoute(Route):
    """A route that matches if ANY of the given keywords is present in the request."""

    def __init__(
        self,
        keywords: list[str],
        handler: Callable,
        case_sensitive: bool = False,
        priority: int = 0,
        method: str = "any",
    ) -> None:
        # Use a joined representation as the "pattern" for display purposes
        pattern = "|".join(keywords)
        super().__init__(pattern, handler, priority, method)
        self.keywords = keywords
        self.case_sensitive = case_sensitive

    def matches(self, request: str) -> bool:
        haystack = request if self.case_sensitive else request.lower()
        needles = self.keywords if self.case_sensitive else [k.lower() for k in self.keywords]
        return any(needle in haystack for needle in needles)

    def __call__(self, request: str) -> Any:
        return self.handler(request)


class Router:
    """Routes requests to registered handlers."""

    def __init__(self) -> None:
        self._routes: list[Route] = []
        self._fallback: Callable | None = None

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def add_route(self, route: Route) -> "Router":
        """Add a Route instance. Returns self for fluent chaining."""
        self._routes.append(route)
        return self

    def route(self, pattern: str, priority: int = 0):
        """Decorator factory: register a function as a handler for *pattern*."""

        def decorator(fn: Callable) -> Callable:
            self.add_route(Route(pattern, fn, priority=priority))
            return fn

        return decorator

    def set_fallback(self, handler: Callable) -> None:
        """Set a handler to call when no route matches."""
        self._fallback = handler

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def _sorted_matches(self, request: str) -> list[Route]:
        """Return matching routes sorted by priority (descending)."""
        matched = [r for r in self._routes if r.matches(request)]
        return sorted(matched, key=lambda r: r.priority, reverse=True)

    def dispatch(self, request: str) -> Any:
        """Call the highest-priority matching handler.

        Raises NoRouteError if no route matches and no fallback is set.
        """
        matches = self._sorted_matches(request)
        if matches:
            return matches[0](request)
        if self._fallback is not None:
            return self._fallback(request)
        raise NoRouteError(request)

    def dispatch_all(self, request: str) -> list[Any]:
        """Call ALL matching handlers (sorted by priority) and return results."""
        matches = self._sorted_matches(request)
        return [r(request) for r in matches]

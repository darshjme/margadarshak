"""agent-router: Production request routing for multi-agent systems."""

from .router import Router, Route, RegexRoute, KeywordRoute, NoRouteError

__all__ = ["Router", "Route", "RegexRoute", "KeywordRoute", "NoRouteError"]
__version__ = "1.0.0"

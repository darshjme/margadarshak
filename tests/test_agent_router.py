"""Comprehensive test suite for agent-router (22+ tests, zero external deps)."""

import pytest
from agent_router import Router, Route, RegexRoute, KeywordRoute, NoRouteError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_handler(name: str):
    def handler(request, **kwargs):
        return {"handler": name, "request": request, **kwargs}
    return handler


# ===========================================================================
# Route tests
# ===========================================================================

class TestRoute:
    def test_pattern_property(self):
        r = Route("hello", make_handler("h"))
        assert r.pattern == "hello"

    def test_matches_substring(self):
        r = Route("schedule", make_handler("cal"))
        assert r.matches("please schedule a meeting")

    def test_not_matches_absent(self):
        r = Route("schedule", make_handler("cal"))
        assert not r.matches("write some code")

    def test_default_priority_zero(self):
        r = Route("x", make_handler("h"))
        assert r.priority == 0

    def test_custom_priority(self):
        r = Route("x", make_handler("h"), priority=5)
        assert r.priority == 5

    def test_default_method_any(self):
        r = Route("x", make_handler("h"))
        assert r.method == "any"

    def test_call_invokes_handler(self):
        r = Route("code", make_handler("coder"))
        result = r("write code please")
        assert result["handler"] == "coder"
        assert result["request"] == "write code please"

    def test_exact_match_only_in_string(self):
        r = Route("cat", make_handler("h"))
        assert r.matches("category")   # substring present
        assert not r.matches("dog")


# ===========================================================================
# RegexRoute tests
# ===========================================================================

class TestRegexRoute:
    def test_basic_regex(self):
        r = RegexRoute(r"\bschedule\b", make_handler("cal"))
        assert r.matches("please schedule a meeting")
        assert not r.matches("rescheduled")

    def test_named_groups_passed_as_kwargs(self):
        def handler(request, action=None, target=None):
            return {"action": action, "target": target}

        r = RegexRoute(r"(?P<action>write|read) (?P<target>\w+)", handler)
        result = r("write report")
        assert result["action"] == "write"
        assert result["target"] == "report"

    def test_no_match_returns_false(self):
        r = RegexRoute(r"^\d{3}-\d{4}$", make_handler("h"))
        assert not r.matches("hello world")

    def test_pattern_property(self):
        r = RegexRoute(r"\bfoo\b", make_handler("h"))
        assert r.pattern == r"\bfoo\b"

    def test_inherits_route(self):
        r = RegexRoute(r"x", make_handler("h"))
        assert isinstance(r, Route)

    def test_named_group_missing_not_passed(self):
        """Groups that don't participate in the match are still passed as None."""
        def handler(request, a=None, b=None):
            return (a, b)

        r = RegexRoute(r"(?P<a>foo)|(?P<b>bar)", handler)
        result = r("foo")
        assert result == ("foo", None)


# ===========================================================================
# KeywordRoute tests
# ===========================================================================

class TestKeywordRoute:
    def test_matches_any_keyword(self):
        r = KeywordRoute(["schedule", "meeting", "calendar"], make_handler("cal"))
        assert r.matches("I need to schedule a call")
        assert r.matches("book a meeting")
        assert r.matches("open calendar please")

    def test_no_match(self):
        r = KeywordRoute(["schedule", "meeting"], make_handler("cal"))
        assert not r.matches("write some code for me")

    def test_case_insensitive_default(self):
        r = KeywordRoute(["Schedule"], make_handler("cal"))
        assert r.matches("SCHEDULE a meeting")

    def test_case_sensitive(self):
        r = KeywordRoute(["Schedule"], make_handler("cal"), case_sensitive=True)
        assert not r.matches("schedule a meeting")
        assert r.matches("Schedule a meeting")

    def test_pattern_is_joined_keywords(self):
        r = KeywordRoute(["a", "b", "c"], make_handler("h"))
        assert r.pattern == "a|b|c"

    def test_call_invokes_handler(self):
        r = KeywordRoute(["code", "write"], make_handler("coder"))
        result = r("write some code")
        assert result["handler"] == "coder"


# ===========================================================================
# Router tests
# ===========================================================================

class TestRouter:
    def test_add_route_returns_self(self):
        router = Router()
        r = Route("x", make_handler("h"))
        assert router.add_route(r) is router

    def test_fluent_chaining(self):
        router = Router()
        result = (
            router
            .add_route(Route("a", make_handler("h1")))
            .add_route(Route("b", make_handler("h2")))
        )
        assert result is router

    def test_dispatch_basic(self):
        router = Router()
        router.add_route(Route("schedule", make_handler("cal")))
        result = router.dispatch("please schedule a meeting")
        assert result["handler"] == "cal"

    def test_dispatch_no_match_raises(self):
        router = Router()
        router.add_route(Route("schedule", make_handler("cal")))
        with pytest.raises(NoRouteError) as exc_info:
            router.dispatch("write code please")
        assert "write code please" in str(exc_info.value)

    def test_dispatch_uses_fallback(self):
        router = Router()
        router.set_fallback(make_handler("fallback"))
        result = router.dispatch("unknown request")
        assert result["handler"] == "fallback"

    def test_dispatch_priority_ordering(self):
        router = Router()
        router.add_route(Route("code", make_handler("low"), priority=0))
        router.add_route(Route("code", make_handler("high"), priority=10))
        result = router.dispatch("write code please")
        assert result["handler"] == "high"

    def test_dispatch_all_calls_all_matches(self):
        router = Router()
        router.add_route(Route("code", make_handler("h1")))
        router.add_route(Route("code", make_handler("h2")))
        router.add_route(Route("schedule", make_handler("h3")))
        results = router.dispatch_all("code")
        handlers = {r["handler"] for r in results}
        assert handlers == {"h1", "h2"}

    def test_dispatch_all_empty_when_no_match(self):
        router = Router()
        router.add_route(Route("code", make_handler("h1")))
        results = router.dispatch_all("schedule a meeting")
        assert results == []

    def test_route_decorator(self):
        router = Router()

        @router.route("search")
        def search_handler(request):
            return "searched"

        result = router.dispatch("search the web")
        assert result == "searched"

    def test_route_decorator_priority(self):
        router = Router()

        @router.route("code", priority=5)
        def high(request):
            return "high"

        @router.route("code", priority=1)
        def low(request):
            return "low"

        assert router.dispatch("write code") == "high"

    def test_no_route_error_attributes(self):
        err = NoRouteError("test request")
        assert err.request == "test request"

    def test_dispatch_all_priority_order(self):
        router = Router()
        router.add_route(Route("x", make_handler("p0"), priority=0))
        router.add_route(Route("x", make_handler("p5"), priority=5))
        results = router.dispatch_all("x")
        assert results[0]["handler"] == "p5"
        assert results[1]["handler"] == "p0"

    def test_regex_route_in_router(self):
        router = Router()
        def handler(request, action=None):
            return action
        router.add_route(RegexRoute(r"(?P<action>schedule|cancel) meeting", handler))
        assert router.dispatch("please schedule meeting") == "schedule"

    def test_keyword_route_in_router(self):
        router = Router()
        router.add_route(KeywordRoute(["deploy", "release", "ship"], make_handler("devops")))
        result = router.dispatch("ship the product now")
        assert result["handler"] == "devops"

    def test_mixed_routes(self):
        router = Router()
        router.add_route(Route("schedule", make_handler("cal"), priority=1))
        router.add_route(KeywordRoute(["meeting", "calendar"], make_handler("cal2"), priority=2))
        # "schedule a meeting" matches both; keyword has higher priority
        result = router.dispatch("schedule a meeting")
        assert result["handler"] == "cal2"

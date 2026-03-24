# Changelog

All notable changes to **agent-router** will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-03-24

### Added
- `Route` — substring pattern matching with priority and method fields
- `RegexRoute` — regex-based routing with named-group extraction as handler kwargs
- `KeywordRoute` — keyword-list routing (any match, configurable case sensitivity)
- `Router` — fluent route registration, `dispatch`, `dispatch_all`, fallback support
- `NoRouteError` exception with `.request` attribute
- Zero external dependencies (stdlib `re` only)
- Full pytest test suite (22+ tests)

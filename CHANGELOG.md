# Changelog

All notable changes to the `mangrove-kb` package will be documented in this file.

This project uses [Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-03-12

### Breaking Changes
- `IndicatorInterface.inputs` and `IndicatorInterface.outputs` are now classmethods (call with `()`)

### Added
- 40 pattern signals (Doji variants, Hammer, Engulfing, Stars, Three White Soldiers, etc.)
- 27 pattern indicators with candlestick geometry detection
- Automated PyPI release workflow via GitHub Actions (`workflow_dispatch`)
- `CHANGELOG.md`

### Fixed
- Standardized all signal parameters to `window` (from `lookback`, `period`, `length`)
- Pattern signal names in quick reference now match `RuleRegistry`
- KB documentation signal counts updated to reflect actual 136 signals
- Pydantic V2 compatibility (migrated from deprecated `class Config` pattern)
- Removed dead code (`indicator_utils.py`)

### Improved
- KB server concurrency: sync routes, WAL mode, N+1 query fix, 2 workers
- Developer docs portal (Mintlify) with Docker build support

## [0.1.1] - 2025-12-15

### Fixed
- Publish script now bumps `__version__` in `__init__.py`
- Renamed old package references to `mangrove_kb`

## [0.1.0] - 2025-12-01

### Added
- Initial release
- 96 trading signals (Momentum, Trend, Volume, Volatility)
- 43 technical indicators
- RuleRegistry with decorator-based signal registration
- Docstring parser for signal metadata extraction
- KB server with REST + MCP dual protocol
- SQLite FTS5 full-text search
- 11 trading education documents
- x402 payment gating

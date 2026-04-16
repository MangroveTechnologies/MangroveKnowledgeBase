# Changelog

All notable changes to the `mangrove-kb` package will be documented in this file.

This project uses [Semantic Versioning](https://semver.org/).

## [0.4.0] - 2026-04-16

### Fixed
- **PSAR `psar_down_indicator` copy-paste bug**: Convenience output `psar_down_indicator` was computed from `psar_up` instead of `psar_down`. Core PSAR outputs (psar, psar_up, psar_down) were unaffected. Bug existed in upstream reference (Bukosabino ta) as well.
- **PSAR indexing inconsistency**: Changed `psar[i]` to `psar.iloc[i]` for index-safety in the PSAR computation loop.
- **TRIX, KST, DPO, Vortex fill_value lookahead**: Removed `fill_value=series.mean()` from shift operations in TRIX, KST (4 shifts), DPO, and Vortex indicators. The mean of the entire series introduced subtle lookahead bias into early warmup bars. Shifted positions now produce NaN (standard behavior). Post-warmup values are unchanged.

### Added
- **PiercingLine `require_gap` parameter**: New boolean parameter (default `True`). When `False`, relaxes the gap requirement from "open below previous low" to "open below previous close", making the pattern detectable in 24/7 crypto/forex markets where price gaps are rare.
- **DarkCloudCover `require_gap` parameter**: Same as PiercingLine. When `False`, relaxes from "open above previous high" to "open above previous close".
- **TwoBarReversal `close_proximity` parameter**: New float parameter (default `0.25`, range `0.1-0.5`). Controls how close the close must be to the high/low for reversal detection. Previously hardcoded at `0.25`.
- **Indicator audit framework** at `scripts/audit/` -- reproducible accuracy verification for all 70 indicators and 136 signals against Bukosabino `ta` reference library.
- **Audit reports** at `audit_results/` -- indicator, signal, pattern, and gap analysis reports.

### Documentation
- Updated KB document 07-chart-patterns.md with notes on `require_gap` and `close_proximity` parameters
- Updated signals quick reference with new parameter documentation

## [0.3.0] - 2026-04-01

### Fixed
- Capped all window-type signal parameters at max 200 to prevent excessive computation
- Docker build with setuptools-scm (pass version via build arg)

### Added
- CODEOWNERS file
- CodeQL security scanning
- Dependabot configuration

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

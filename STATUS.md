# Project Status Report

**Date:** 2026-02-22
**Version:** 0.1.0
**Status:** Initial extraction complete, ready for publishing

## What Was Done

### Signal Metadata Consolidation

The original MangroveAI platform had signal metadata spread across three redundant sources:
1. `signals_metadata.json` — 127 entries, ground truth for runtime validation
2. `06-indicators.md` (Knowledge Base) — 122 entries, loaded at Flask startup via regex parsing
3. Function docstrings — implementation docs, not used for metadata

**Problem:** The KB parser hardcoded `requires: ["Close"]` for all signals, which was wrong for ~50 signals that need `High`, `Low`, `Volume`, or combinations thereof. The three sources had additional discrepancies in parameter ranges (CCI, CMF) and missing parameters (Keltner Channel).

**Solution:** Enriched all signal docstrings to be self-describing with structured metadata tags (`Type:`, `Requires:`, param `Range:`/`Default:`), then built a docstring parser that extracts this metadata at runtime. The JSON file and KB regex parser are no longer needed.

### What Was Extracted

From MangroveAI into this standalone package:

| Component | Count | Source |
|-----------|-------|--------|
| Momentum signals | 26 | `domains/signals/momentum/signals.py` |
| Trend signals | 38 | `domains/signals/trend/signals.py` |
| Volume signals | 22 | `domains/signals/volume/signals.py` |
| Volatility signals | 10 | `domains/signals/volatility/signals.py` |
| Indicator classes | 40+ | `domains/indicators/*.py` |
| Signal registry | 1 | `domains/signals/registry.py` |
| **Total signals** | **96** | |

**Not extracted** (stays private in MangroveAI):
- 5 social/X signals (disabled, `x_user_post_trigger`, etc.)
- AI copilot, backtesting, strategy engine, Flask routes
- All authentication, database, and cloud integrations

### MangroveAI Integration

MangroveAI now imports signals and indicators from this package via re-export wrappers:
- `MangroveAI.domains.signals.registry` re-exports `mangrove_signals.registry`
- `MangroveAI.domains.indicators` re-exports `mangrove_signals.indicators`
- Signal category modules re-export from `mangrove_signals.signals.*`
- Social signals remain in MangroveAI and register into the shared `RuleRegistry`
- `signals_metadata.json` has been deleted
- `kb_signal_parser.py` now uses the docstring parser instead of KB markdown regex

### Bugs Fixed During Extraction

1. **`requires` field hardcoded to `["Close"]`** — ~50 signals now have correct required columns
2. **CCI `constant` range** — KB had 0.0-100.0, fixed to 0.001-0.1
3. **CMF `threshold` range** — KB had 0.0-100.0, fixed to -1.0-1.0
4. **Keltner Channel missing params** — KB was missing `multiplier` and `original_version`
5. **VPT param name** — KB had `window`, code uses `lookback`

### Validation

- 27 pytest tests validate docstring parser output matches the original JSON schema
- Field-by-field comparison: type, requires, param names, types, ranges, defaults
- All 96 signals verified in both standalone and Docker-deployed MangroveAI

## Current Architecture

```
mangrove-signals (this repo, public)
    |
    +-- mangrove_signals/
    |       +-- registry.py          # RuleRegistry singleton
    |       +-- docstring_parser.py  # Metadata extraction from docstrings
    |       +-- signals/             # 96 signal functions (4 categories)
    |       +-- indicators/          # 40+ indicator classes (5 categories)
    |
    +-- tests/
    |       +-- test_docstring_parser.py  # 27 tests
    |
    +-- findings/
            +-- signal-source-diff.md    # Original analysis document

MangroveAI (private, consumes this package)
    |
    +-- domains/signals/
    |       +-- registry.py          # Re-exports from mangrove_signals
    |       +-- kb_signal_parser.py  # Uses docstring parser
    |       +-- services.py          # Signal metadata service
    |       +-- momentum/signals.py  # Re-exports from mangrove_signals
    |       +-- trend/signals.py     # Re-exports from mangrove_signals
    |       +-- volume/signals.py    # Re-exports from mangrove_signals
    |       +-- volatility/signals.py # Re-exports from mangrove_signals
    |       +-- social/signals.py    # Private, registers into shared registry
    |
    +-- domains/indicators/
            +-- __init__.py          # Re-exports from mangrove_signals
```

## Next Steps

### Short-term

- [ ] Publish to GitHub (`MangroveTechnologies/mangrove-signals`)
- [ ] Set up GitHub Actions CI (lint + test on push)
- [ ] Add a LICENSE file
- [ ] Consider publishing to PyPI for easier installation
- [ ] Pin mangrove-signals version in MangroveAI requirements.txt (e.g., `@v0.1.0` tag)

### Medium-term

- [ ] Add unit tests for individual signal functions (not just the parser)
- [ ] Add unit tests for indicator `compute()` methods
- [ ] Extract Knowledge Base content (06-indicators.md) into this repo
- [ ] Add type stubs / py.typed marker for type checker support
- [ ] Set up pre-commit hooks (black, flake8)

### Long-term

- [ ] Remove dead signal/indicator code from MangroveAI (currently kept as re-export wrappers)
- [ ] Add new signal categories (pattern recognition, on-chain, sentiment)
- [ ] Publish to PyPI with semantic versioning
- [ ] Add signal backtesting utilities
- [ ] Consider splitting indicators and signals into separate packages if the library grows large

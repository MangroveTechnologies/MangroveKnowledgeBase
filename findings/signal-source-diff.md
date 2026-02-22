# Signal Source Cross-Reference Report

Generated: 2026-02-21
Purpose: Identify all discrepancies between the three current sources of signal metadata before
removing signals_metadata.json and making docstrings the single source of truth.

## Sources Compared

| ID | Source | Location | Role |
|----|--------|----------|------|
| JSON | signals_metadata.json | `domains/signals/signals_metadata.json` | Primary fallback, ground truth for runtime validation |
| KB | 06-indicators.md | `MangroveKnowledgeBase/knowledge-base/06-indicators.md` | Primary load source at Flask startup |
| DS | Function docstrings | `domains/signals/[category]/signals.py` | Implementation docs, currently NOT used for metadata |

## Signal Count Summary

| Source | Signal Count |
|--------|-------------|
| signals_metadata.json | 127 (122 enabled + 5 disabled social) |
| 06-indicators.md (KB) | 122 (social signals not present) |
| Function docstrings | 127 (all categories including social) |

The discrepancy in KB count (122 vs 127) is expected: the 5 social/X signals are not documented
in the KB markdown. They are defined in code and JSON only.

---

## Section 1: Fields Present in JSON But Missing From Docstrings

These are the fields that MUST be added to docstrings before JSON can be retired.
The docstring schema must encode all of these.

### 1A. Signal Type (TRIGGER vs FILTER)

**Status: MISSING from all docstrings.**

The JSON has an explicit `"type"` field for every signal. Docstrings mention the type only
informally in prose (e.g., "state-based" or "event-based" in a few cases, not all).

Required addition to docstring schema:
```
Type: TRIGGER  (or FILTER)
```

This is used at runtime by `validate_strategy_signals()` to enforce the "1 TRIGGER + 1 FILTER"
rule per strategy entry block.

### 1B. Required Data Columns (`requires`)

**Status: MISSING as structured data. Present as prose in some docstrings.**

The JSON has a structured `requires` array per signal, e.g.:
- `["Close"]`
- `["High", "Low", "Close"]`
- `["High", "Low", "Close", "Volume"]`
- `["Close", "Volume"]`
- `["High", "Low"]`
- `["High", "Low", "Volume"]`

The KB parser hardcodes `["Close"]` as the default for ALL signals, which is WRONG for many.
The docstrings mention required columns in Args prose but not as structured data.

The `requires` field is used at runtime by `evaluate_signal()` to validate DataFrame columns
before calling the signal function. If wrong, signals crash at runtime.

Required addition to docstring schema:
```
Requires: Close, Volume  (comma-separated, exact column names)
```

The ground truth for this field is the JSON (not the KB). See Section 3 for per-signal values.

### 1C. Parameter Min/Max Ranges

**Status: MISSING from all docstrings. Present only in JSON and KB.**

Every parameter in the JSON has explicit `min` and `max` fields. Neither the function
signatures nor the docstring Args sections include these ranges.

Required addition to docstring schema (per parameter in Args):
```
Args:
    window: RSI calculation window. Range: 2-100. Default: 14.
    threshold: Overbought threshold. Range: 50.0-100.0. Default: 70.0.
```

Or structured as a tag:
```
    window (int): RSI calculation window. [range: 2-100, default: 14]
```

### 1D. Disabled Flag and Reason

**Status: MISSING from all docstrings. Present only in JSON.**

The 5 social signals have `"disabled": true` and `"disabled_reason": "..."` in the JSON.
The docstrings have no such marker. This means without the JSON, disabled signals would be
exposed in the API and available for strategy creation, causing runtime failures.

Required addition to docstring schema (for disabled signals only):
```
Disabled: True
Disabled-Reason: Social signals integration not yet available
```

---

## Section 2: Discrepancies Between JSON and KB

Where the two existing sources disagree. JSON is ground truth.

### 2A. `requires` Field: KB Is Systematically Wrong

The KB parser (`kb_signal_parser.py` line 186) hardcodes `requires: ["Close"]` for every
signal. This is correct for close-only signals but wrong for a large set.

Signals where KB `requires` is WRONG (hardcoded `["Close"]` but JSON says otherwise):

| Signal | JSON requires | KB requires (wrong) |
|--------|--------------|---------------------|
| stoch_overbought | High, Low, Close | Close |
| stoch_oversold | High, Low, Close | Close |
| williams_r_overbought | High, Low, Close | Close |
| williams_r_oversold | High, Low, Close | Close |
| uo_overbought | High, Low, Close | Close |
| uo_oversold | High, Low, Close | Close |
| adx_strong_trend | High, Low, Close | Close |
| adx_bullish_di | High, Low, Close | Close |
| aroon_up_trend | High, Low | Close |
| aroon_down_trend | High, Low | Close |
| aroon_crossover | High, Low | Close |
| mass_reversal_signal | High, Low | Close |
| ichimoku_bullish | High, Low | Close |
| ichimoku_bearish | High, Low | Close |
| ichimoku_tk_cross | High, Low | Close |
| vortex_bullish | High, Low, Close | Close |
| vortex_bearish | High, Low, Close | Close |
| vortex_crossover | High, Low, Close | Close |
| psar_bullish | High, Low, Close | Close |
| psar_bearish | High, Low, Close | Close |
| psar_reversal | High, Low, Close | Close |
| cci_overbought | High, Low, Close | Close |
| cci_oversold | High, Low, Close | Close |
| atr_high_volatility | High, Low, Close | Close |
| kc_upper_breakout | High, Low, Close | Close |
| kc_lower_breakout | High, Low, Close | Close |
| dc_upper_breakout | High, Low, Close | Close |
| dc_lower_breakout | High, Low, Close | Close |
| ao_bullish | High, Low | Close |
| ao_bearish | High, Low | Close |
| ao_zero_cross | High, Low | Close |
| adi_bullish | High, Low, Close, Volume | Close |
| adi_bearish | High, Low, Close, Volume | Close |
| cmf_bullish | High, Low, Close, Volume | Close |
| cmf_bearish | High, Low, Close, Volume | Close |
| mfi_overbought | High, Low, Close, Volume | Close |
| mfi_oversold | High, Low, Close, Volume | Close |
| vwap_above | High, Low, Close, Volume | Close |
| vwap_below | High, Low, Close, Volume | Close |
| obv_bullish | Close, Volume | Close |
| obv_bearish | Close, Volume | Close |
| force_bullish | Close, Volume | Close |
| force_bearish | Close, Volume | Close |
| vpt_bullish | Close, Volume | Close |
| vpt_bearish | Close, Volume | Close |
| nvi_bullish | Close, Volume | Close |
| nvi_bearish | Close, Volume | Close |
| pvo_bullish_cross | Volume | Close |
| pvo_bearish_cross | Volume | Close |
| eom_bullish | High, Low, Volume | Close |
| eom_bearish | High, Low, Volume | Close |

**Conclusion:** The KB `requires` field is unreliable for ~50 signals. The JSON is the only
correct source for this field. Docstrings (via the `df` Args description) also correctly describe
the required columns and are confirmed to match the JSON.

### 2B. Keltner Channel: KB Missing `multiplier` and `original_version` Params

**Signal:** `kc_upper_breakout`, `kc_lower_breakout`

| Param | JSON | KB | Docstring |
|-------|------|----|-----------|
| window | int, 10-50, default=20 | int, 10-50, default=20 | int, default=20 |
| window_atr | int, 5-30, default=10 | int, 5-30, default=10 | int, default=10 |
| multiplier | float, 0.5-5.0, default=2.0 | **MISSING** | float, default=2.0 |
| original_version | bool, default=False | **MISSING** | bool, default=False |

The KB `<details>` block for these signals only documents 2 of the 4 parameters. JSON and
docstring agree on all 4. This is a KB documentation gap.

### 2C. CCI `constant` Parameter: Range Discrepancy

**Signal:** `cci_overbought`, `cci_oversold`

| Param | JSON | KB |
|-------|------|----|
| constant | float, min=0.001, max=0.1 | float, min=0.0, max=100.0 |

The KB has a nonsensical range (0.0-100.0) for the CCI constant, which in practice is always
0.015 (the standard Lambert constant). The JSON range (0.001-0.1) is correct. Docstring
shows `constant: float = 0.015` in signature, no range specified.

### 2D. CMF `threshold` Parameter: Range Discrepancy

**Signal:** `cmf_bullish`, `cmf_bearish`

| Param | JSON | KB |
|-------|------|----|
| threshold | float, min=-1.0, max=1.0 | float, min=0.0, max=100.0 |

CMF ranges from -1 to +1 by definition. JSON is correct. KB range is wrong.

### 2E. Social Signals: Present in JSON and Docstrings, Absent From KB

The 5 social/X signals are fully defined in both JSON (with `disabled: true`) and in
`social/signals.py` docstrings, but are not present in `06-indicators.md` at all.

This is intentional: social signals are private. The open-source KB should not document them.
The new docstring schema needs the `disabled` flag to handle this at runtime without the KB.

### 2F. Description Text Differences (Minor)

Several signals have slightly different description wording between JSON and KB. These are
cosmetic and do not affect runtime behavior. Examples:

| Signal | JSON description | KB description |
|--------|-----------------|----------------|
| rsi_cross_up | "Check if RSI crosses above a threshold level" | Same + "In crypto markets, consider higher thresholds..." |
| ema_crossover | "Detect EMA crossover signal with configurable direction..." | Same + "Common periods: 9/21 (short), 50/200 (long)..." |
| is_above_sma | "Check if current price is above Simple Moving Average Common periods..." | Same (KB has more context) |

The KB descriptions are generally richer. The new docstrings should incorporate the richer KB
descriptions where they add value.

---

## Section 3: Complete `requires` Field Ground Truth

This is the authoritative mapping from JSON (verified against docstrings). Use this when
writing the new structured docstrings.

### Close only
rsi_overbought, rsi_oversold, rsi_cross_up, rsi_cross_down, macd_bullish_cross,
macd_bearish_cross, macd_positive, is_above_sma, sma_crossover, sma_cross_up, sma_cross_down,
ema_cross_up, ema_cross_down, ema_crossover, price_above_ema, wma_cross_up, wma_cross_down,
kama_cross_up, kama_cross_down, tsi_bullish, tsi_bearish, roc_positive, roc_negative,
roc_momentum_shift, ppo_bullish_cross, ppo_bearish_cross, trix_bullish, trix_bearish,
kst_bullish_cross, kst_bearish_cross, dpo_positive, dpo_negative, stochrsi_overbought,
stochrsi_oversold, stc_overbought, stc_oversold, bb_upper_breakout, bb_lower_breakout,
bb_squeeze, ulcer_high_risk, ulcer_low_risk, daily_return_positive, daily_return_negative,
cumulative_return_positive, cumulative_return_target

### High, Low only
aroon_up_trend, aroon_down_trend, aroon_crossover, mass_reversal_signal, ichimoku_bullish,
ichimoku_bearish, ichimoku_tk_cross, ao_bullish, ao_bearish, ao_zero_cross

### High, Low, Close
stoch_overbought, stoch_oversold, williams_r_overbought, williams_r_oversold, uo_overbought,
uo_oversold, adx_strong_trend, adx_bullish_di, vortex_bullish, vortex_bearish, vortex_crossover,
psar_bullish, psar_bearish, psar_reversal, cci_overbought, cci_oversold, atr_high_volatility,
kc_upper_breakout, kc_lower_breakout, dc_upper_breakout, dc_lower_breakout

### Close, Volume
obv_bullish, obv_bearish, force_bullish, force_bearish, vpt_bullish, vpt_bearish, nvi_bullish,
nvi_bearish

### High, Low, Volume
eom_bullish, eom_bearish

### High, Low, Close, Volume
adi_bullish, adi_bearish, cmf_bullish, cmf_bearish, mfi_overbought, mfi_oversold, vwap_above,
vwap_below

### Volume only
pvo_bullish_cross, pvo_bearish_cross

### Social (no standard OHLCV - uses XProvider)
x_user_post_trigger, x_topic_mention_trigger, x_social_sentiment_trigger,
x_user_influence_filter, x_topic_sentiment_filter

---

## Section 4: Proposed Docstring Schema

This is the structured format to add to every signal function docstring. It must encode
ALL fields currently in the JSON so the JSON can be retired.

```python
@RuleRegistry.register("rsi_overbought")
def rsi_overbought(df: pd.DataFrame, window: int = 14, threshold: float = 70.0) -> bool:
    """
    Check if RSI is above the overbought threshold.

    RSI values above 70 typically indicate overbought conditions, suggesting
    the asset may be due for a pullback. In crypto markets, consider using
    higher thresholds (e.g. 80) during strong uptrends.

    Type: FILTER
    Requires: Close

    Args:
        window (int): RSI calculation window. Range: 2-100. Default: 14.
        threshold (float): Overbought threshold. Range: 50.0-100.0. Default: 70.0.

    Returns:
        bool: True if RSI > threshold, False otherwise.
    """
```

For disabled signals:

```python
@RuleRegistry.register("x_user_post_trigger")
def x_user_post_trigger(df: pd.DataFrame, username: str, topic: str = None, max_age_hours: int = 1) -> bool:
    """
    Fires when a specific X user posts about a topic.

    Uses XProvider integration to monitor X (Twitter) users in real time.

    Type: TRIGGER
    Requires: None
    Disabled: True
    Disabled-Reason: Social signals integration not yet available

    Args:
        username (str): X username to monitor. Required.
        topic (str): Topic keyword filter. Optional. Default: None.
        max_age_hours (int): Max post age in hours. Range: 1-168. Default: 1.

    Returns:
        bool: True if user posted about topic within the time window.
    """
```

### Schema Rules

1. `Type:` line is required on all signals. Value is `TRIGGER` or `FILTER`.
2. `Requires:` line is required on all signals. Value is comma-separated column names
   (`Close`, `High`, `Low`, `Volume`) or `None` for social signals.
3. `Disabled:` line is only present when `True`.
4. `Disabled-Reason:` line is only present when `Disabled: True`.
5. Args format: `name (type): Description. Range: min-max. Default: value.`
   - `Range:` is omitted for `str`, `bool`, and required params with no meaningful range.
   - `Default:` is omitted for required params (no default in function signature).
6. `Type:` and `Requires:` tags come AFTER the main description, separated by a blank line.
7. `Args:` section follows the tags.

### Parser Requirements

The docstring parser (to be written) must extract:
- `Type:` -> `type` field (TRIGGER/FILTER)
- `Requires:` -> `requires` field (list of column names, or empty list for None)
- `Disabled:` -> `disabled` field (bool)
- `Disabled-Reason:` -> `disabled_reason` field (str)
- `Args:` section -> `params` dict with per-param `type`, `default`, `min`, `max`, `optional`
  - `optional` = True if param has a default value in the function signature
  - `type` = extracted from `(type)` annotation in Args line
  - `default` = extracted from `Default: value` in Args description
  - `min`/`max` = extracted from `Range: min-max` in Args description
- `rule_name` = extracted from `@RuleRegistry.register("name")` decorator
- `description` = first paragraph of docstring (before `Type:` tag)

---

## Section 5: Signals in Code Not In KB

These signals exist in the codebase (JSON + docstrings) but are absent from 06-indicators.md.
All are social signals, which is intentional (private).

| Signal | JSON | Docstring | KB |
|--------|------|-----------|----|
| x_user_post_trigger | Yes (disabled) | Yes | No |
| x_topic_mention_trigger | Yes (disabled) | Yes | No |
| x_social_sentiment_trigger | Yes (disabled) | Yes | No |
| x_user_influence_filter | Yes (disabled) | Yes | No |
| x_topic_sentiment_filter | Yes (disabled) | Yes | No |

These will remain in the private MangroveAI repo only. The open-source `mangrove-signals` repo
will not contain `social/signals.py` source code. The `disabled` flag in docstrings handles
the API surface gracefully.

---

## Section 6: Signals Where JSON and Docstring Agree Fully

The following are confirmed consistent across JSON and docstring (type, params, defaults):

All momentum signals: rsi_*, stoch_*, stochrsi_*, williams_r_*, tsi_*, uo_*, kama_*, roc_*,
ao_*, ppo_*, pvo_*

All trend signals: sma_*, ema_*, wma_*, macd_*, adx_*, aroon_*, vortex_*, psar_*, ichimoku_*,
kst_*, trix_*, dpo_*, cci_*, stc_*, mass_reversal_signal

All volume signals: adi_*, obv_*, cmf_*, force_*, eom_*, vpt_*, nvi_*, mfi_*, vwap_*,
daily_return_*, cumulative_return_*

All volatility signals: bb_*, atr_*, kc_*, dc_*, ulcer_*

The only discrepancies are the KB `requires` field (wrong for ~50 signals) and the two
parameter range issues noted in Section 2C and 2D.

---

## Section 7: Action Checklist Before Retiring JSON

- [ ] Define and document the final docstring schema (Section 4 above is a proposal)
- [ ] Write docstring parser and validate it reconstructs JSON correctly for all 127 signals
- [ ] Enrich all 122 enabled signal docstrings with: Type, Requires, param ranges
- [ ] Enrich all 5 social signal docstrings with: Type, Requires, Disabled, Disabled-Reason
- [ ] Fix KB 06-indicators.md for kc_upper/lower_breakout (add missing params)
- [ ] Fix KB 06-indicators.md for cci constant range (0.001-0.1 not 0.0-100.0)
- [ ] Fix KB 06-indicators.md for cmf threshold range (-1.0-1.0 not 0.0-100.0)
- [ ] Verify parser output matches JSON for all 127 signals (diff test)
- [ ] Update kb_signal_parser.py to use docstring parser instead of KB markdown regex
- [ ] Remove signals_metadata.json from MangroveAI repo

---

## Section 8: Open-Source Split Summary

What goes into `mangrove-signals` (public):
- signals/momentum/signals.py
- signals/trend/signals.py
- signals/volume/signals.py
- signals/volatility/signals.py
- registry.py
- indicators/ (all indicator classes)
- knowledge-base/ (all .md files except 04-strategy-design-modeling.md)
- kb/ (the FastAPI KB service)

What stays in MangroveAI (private):
- signals/social/signals.py (source only - API docs may reference it)
- All AI copilot code and prompts
- Backtest engine
- Execution/trading logic
- All Flask routes, services, domain models

What moves to MangroveAdmin (new repo):
- MangroveAdmin/frontend/ (React UI)
- MangroveKnowledgeBase/ (FastAPI KB service, merged in)

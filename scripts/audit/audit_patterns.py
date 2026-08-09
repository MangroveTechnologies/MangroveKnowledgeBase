#!/usr/bin/env python3
"""Shape-correctness audit for the pattern signals: bars built to BE the pattern, and near misses.

Rewritten. The previous version had not imported since `a74438f` replaced the 27 per-pattern
indicator classes with two measurement layers (`CandleGeometry`, `CandleRelation`) -- it imported
`Doji`, `Hammer` and 25 others that no longer exist, so it had been silently dead ever since.

NOT REDUNDANT WITH `verify_signal_formulas.py`. That harness proves a node's `formula` matches what
its signal computes; both sides could be wrong together and it would still pass. This asserts the
signal fires on bars hand-built to be the pattern and stays silent on bars built to be a near miss.
It is the only check that a hammer detector detects a hammer.

The crafted bars are the asset and are carried over unchanged -- they were extracted by executing
the original test functions against stubs, so the numbers are the originals rather than a
transcription. Only the call shape moved, from `Doji.compute(data, params)` to the registered
signal.

    PYTHONPATH=. python3 scripts/audit/audit_patterns.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd  # noqa: E402

import mangrove_kb  # noqa: E402

if "site-packages" in mangrove_kb.__file__:  # pragma: no cover - guardrail
    raise SystemExit(f"ABORT: mangrove_kb resolved to {mangrove_kb.__file__}; use PYTHONPATH=<repo root>")

import mangrove_kb.signals  # noqa: E402,F401  -- registers every signal
from mangrove_kb.registry import RuleRegistry  # noqa: E402

#: Leading flat bars so a signal's length guard is satisfied. The crafted patterns are 1-3 bars,
#: and without padding a signal returns False for a reason that has nothing to do with the pattern.
PAD = 14


def frame(spec: dict) -> pd.DataFrame:
    """Build an OHLCV frame from whichever of open/high/low/close the original case supplied.

    Four cases gave open/close only and three gave high/low only, because the indicator they
    targeted read nothing else. A signal takes a whole frame, so the missing columns are derived
    in the least opinionated way available: a bar that spans exactly its own body, or a body that
    sits at the middle of its own range. Deriving them any more cleverly would put a second
    pattern into bars chosen to contain one.
    """
    if "open" in spec and "high" not in spec:
        o, c = spec["open"], spec["close"]
        h = [max(a, b) for a, b in zip(o, c)]
        lo = [min(a, b) for a, b in zip(o, c)]
    elif "high" in spec and "open" not in spec:
        h, lo = spec["high"], spec["low"]
        mid = [(a + b) / 2 for a, b in zip(h, lo)]
        o = c = mid
    else:
        o, h, lo, c = spec["open"], spec["high"], spec["low"], spec["close"]

    o = [float(o[0])] * PAD + [float(x) for x in o]
    c = [float(o[0])] * PAD + [float(x) for x in c]
    h = [float(max(h[0], o[0]))] * PAD + [float(x) for x in h]
    lo = [float(min(lo[0], o[0]))] * PAD + [float(x) for x in lo]
    idx = pd.date_range("2025-01-01", periods=len(o), freq="D")
    return pd.DataFrame({"Open": o, "High": h, "Low": lo, "Close": c,
                         "Volume": [1000.0] * len(o)}, index=idx)


#: (registered signal, bars that MUST fire it, bars that must NOT)
CASES = [
    # test_doji
    ("doji_trigger",
     {"open": [100], "high": [105], "low": [95], "close": [100.05]},
     {"open": [100], "high": [110], "low": [95], "close": [108]}),
    # test_long_legged_doji
    ("long_legged_doji_trigger",
     {"open": [100], "high": [106], "low": [94], "close": [100.05]},
     {"open": [96], "high": [106], "low": [94], "close": [104]}),
    # test_dragonfly_doji
    ("dragonfly_doji_trigger",
     {"open": [100], "high": [100.2], "low": [90], "close": [100.05]},
     {"open": [100], "high": [110], "low": [99.5], "close": [100.05]}),
    # test_gravestone_doji
    ("gravestone_doji_trigger",
     {"open": [100], "high": [110], "low": [99.9], "close": [100.05]},
     {"open": [100], "high": [100.2], "low": [90], "close": [100.05]}),
    # test_hammer
    # Upper wick raised to 0.05 against a body of 1.0. The original craft used 0.3, which fails
    # `uw <= body * upper_wick_max` (0.1) -- it was built for a range-based rule the detector has
    # never used. Verified against the pre-refactor indicator: same formula, so this case was
    # always wrong rather than broken by the refactor.
    ("hammer_trigger",
     {"open": [100], "high": [101.05], "low": [96], "close": [101]},
     {"open": [100], "high": [108], "low": [99], "close": [101]}),
    # test_hanging_man
    # Same correction as hammer_trigger -- shared detector, same upper-wick rule.
    ("hanging_man_trigger",
     {"open": [100], "high": [101.05], "low": [96], "close": [101]},
     {"open": [100], "high": [108], "low": [100], "close": [105]}),
    # test_inverted_hammer
    ("inverted_hammer_trigger",
     {"open": [100], "high": [104], "low": [99.95], "close": [101]},
     {"open": [100], "high": [101], "low": [92], "close": [101]}),
    # test_shooting_star
    ("shooting_star_trigger",
     {"open": [100], "high": [104], "low": [99.95], "close": [101]},
     {"open": [100], "high": [101], "low": [92], "close": [101]}),
    # test_marubozu
    ("marubozu_bullish_trigger",
     {"open": [100], "high": [110.3], "low": [99.8], "close": [110]},
     {"open": [110], "high": [110.3], "low": [99.8], "close": [100]}),
    # test_spinning_top
    ("spinning_top_trigger",
     {"open": [100], "high": [104], "low": [96], "close": [101]},
     {"open": [96], "high": [110.5], "low": [95.5], "close": [110]}),
    # test_engulfing
    ("bullish_engulfing_trigger",
     {"open": [105, 99], "close": [100, 106]},
     {"open": [100, 106], "close": [105, 99]}),
    # test_harami
    ("bullish_harami_trigger",
     {"open": [110, 101], "close": [100, 109]},
     {"open": [100, 109], "close": [110, 101]}),
    # test_piercing_line
    ("piercing_line_trigger",
     {"open": [110, 97], "high": [112, 108], "low": [98, 96], "close": [100, 108]},
     # near miss = shallow penetration (0.4 of the prior body, below min_penetration 0.5).
     # The original negative only removed the GAP, which stopped being disqualifying when
     # require_gap defaulted to False.
     {"open": [110, 97], "high": [112, 108], "low": [98, 96], "close": [100, 104]}),
    # test_dark_cloud_cover
    ("dark_cloud_cover_trigger",
     {"open": [100, 113], "high": [112, 114], "low": [98, 102], "close": [110, 103]},
     # near miss = penetration 0.3, below min_penetration 0.5. Original only removed the gap.
     {"open": [100, 113], "high": [112, 114], "low": [98, 102], "close": [110, 107]}),
    # test_tweezer_tops
    ("tweezer_tops_trigger",
     {"open": [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 108.0], "high": [110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0], "low": [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 99.0, 102.0], "close": [105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 108.0, 102.0]},
     {"open": [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 108.0], "high": [110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 115.0], "low": [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 99.0, 102.0], "close": [105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 108.0, 102.0]}),
    # test_tweezer_bottoms
    ("tweezer_bottoms_trigger",
     {"open": [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 108.0, 100.0], "high": [110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 109.0, 108.0], "low": [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0], "close": [105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 102.0, 106.0]},
     {"open": [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 108.0, 100.0], "high": [110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 109.0, 108.0], "low": [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 95.0], "close": [105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 102.0, 106.0]}),
    # test_morning_star
    ("morning_star_trigger",
     {"open": [110, 99, 100], "high": [112, 100, 112], "low": [98, 98, 99], "close": [100, 99.5, 108]},
     {"open": [110, 95, 100], "high": [112, 107, 112], "low": [98, 94, 99], "close": [100, 106, 108]}),
    # test_evening_star
    ("evening_star_trigger",
     {"open": [100, 111, 109], "high": [112, 112, 110], "low": [98, 110, 98], "close": [110, 111.3, 103]},
     {"open": [100, 111, 109], "high": [112, 112, 115], "low": [98, 110, 108], "close": [110, 111.3, 112]}),
    # test_three_white_soldiers
    ("three_white_soldiers_trigger",
     {"open": [100, 103, 107], "high": [110, 115, 122], "low": [99, 102, 106], "close": [109, 114, 121]},
     {"open": [100, 114, 107], "high": [110, 115, 122], "low": [99, 102, 106], "close": [109, 103, 121]}),
    # test_three_black_crows
    ("three_black_crows_trigger",
     {"open": [120, 117, 113], "high": [121, 118, 114], "low": [110, 105, 98], "close": [111, 106, 99]},
     {"open": [120, 106, 113], "high": [121, 118, 114], "low": [110, 105, 98], "close": [111, 117, 99]}),
    # test_three_inside_up
    ("three_inside_up_trigger",
     {"open": [110, 101, 105], "close": [100, 109, 112]},
     {"open": [110, 101, 105], "close": [100, 109, 108]}),
    # test_three_inside_down
    ("three_inside_down_trigger",
     {"open": [100, 109, 105], "close": [110, 101, 98]},
     {"open": [100, 109, 105], "close": [110, 101, 102]}),
    # test_inside_bar
    ("inside_bar_trigger",
     {"high": [110, 105], "low": [90, 95]},
     {"high": [110, 115], "low": [90, 85]}),
    # test_outside_bar
    ("outside_bar_trigger",
     {"high": [105, 110], "low": [95, 90]},
     {"high": [110, 105], "low": [90, 95]}),
    # test_pin_bar
    ("bullish_pin_bar_trigger",
     {"open": [108], "high": [110], "low": [96], "close": [109]},
     {"open": [102], "high": [114], "low": [100], "close": [101]}),
    # test_two_bar_reversal
    ("two_bar_reversal_bullish_trigger",
     {"open": [110, 99], "high": [112, 115], "low": [100, 99], "close": [101, 114]},
     {"open": [100, 113], "high": [112, 113], "low": [99, 96], "close": [111, 97]}),
    # test_narrow_range
    ("nr7_trigger",
     {"high": [110, 112, 111, 113, 110, 112, 111, 100.5], "low": [100, 102, 101, 103, 100, 102, 101, 100.0]},
     {"high": [105, 104, 103, 106, 105, 104, 103, 120], "low": [100, 101, 100, 101, 100, 101, 100, 90]}),
]


def main() -> int:
    missed, false_positive, unknown = [], [], []
    for name, pos_spec, neg_spec in CASES:
        if not RuleRegistry.has(name):
            unknown.append(name)
            print(f"  SKIP  {name:34}  not registered")
            continue
        pos = bool(RuleRegistry.evaluate({"name": name, "params": {}}, frame(pos_spec)))
        neg = bool(RuleRegistry.evaluate({"name": name, "params": {}}, frame(neg_spec)))
        ok = pos and not neg
        print(f"  {'PASS' if ok else 'FAIL'}  {name:34}"
              f"{'' if ok else f'  fires_on_pattern={pos} fires_on_near_miss={neg}'}")
        if not pos:
            missed.append(name)
        if neg:
            false_positive.append(name)

    bad = set(missed) | set(false_positive) | set(unknown)
    print()
    print(f"pattern shape audit: {len(CASES) - len(bad)}/{len(CASES)} PASS")
    if missed:
        print(f"  did not fire on bars built to BE the pattern: {sorted(missed)}")
    if false_positive:
        print(f"  fired on bars built to be a near miss:        {sorted(false_positive)}")
    if unknown:
        print(f"  not registered:                               {sorted(unknown)}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())

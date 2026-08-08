#!/usr/bin/env python3
"""Verify every authored `formula` in the ontology graph against the signal it describes.

    PYTHONPATH=. python3 scripts/audit/verify_signal_formulas.py            # every class
    PYTHONPATH=. python3 scripts/audit/verify_signal_formulas.py volatility # one source module

A signal node's `formula` claims what the signal computes. This transcribes each claim back into
code and replays it against the registered signal bar-for-bar, so a formula that drifts from the
implementation fails here rather than misleading a reader of the graph.

WHY THIS FILE EXISTS. The first three authoring passes each got their own throwaway script, and each
one repeated a fresh mistake -- wrong detector call shapes, parameters the signal does not expose,
warmup offsets, degenerate fixtures. This is the one harness. A new class adds a SPEC entry; it does
not add a script.

TWO RULES IT ENFORCES, both learned the hard way:

  1. The REAL fixture first. `load_btc_daily()` is 1,294 bars of actual BTC daily data, and every
     formula is checked against it. Synthetic series are a supplement for setups the real trace does
     not contain -- never a substitute, and the report always says which was used.
  2. A signal that never fires verifies nothing. If it is False on every bar, so is the formula, and
     they agree for a reason unrelated to correctness. Anything that does not fire on the real
     fixture is re-run against a constructed series built to force it, and reported separately.

A signal that fires on NEITHER is a finding, not a gap in the test. Two causes, opposite responses:
the setup does not occur in this market (fine -- `natr_low_volatility` needs NATR below 1.0 and
BTC's daily range is 1.72-6.67), or the signal CANNOT fire in this market (a defect --
`piercing_line_trigger` defaulted to requiring a gap, and a 24/7 market never gaps).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

import mangrove_kb

if "site-packages" in mangrove_kb.__file__:  # pragma: no cover - guardrail
    raise SystemExit(
        f"ABORT: mangrove_kb resolved to {mangrove_kb.__file__}\n"
        "Run with PYTHONPATH=<repo root>. Python puts the SCRIPT's directory on sys.path[0], not "
        "the working directory, so this imports the installed copy otherwise -- a different, older "
        "API that silently verifies the wrong code."
    )

import mangrove_kb.signals  # noqa: E402,F401  -- registers every signal
import mangrove_kb.signals.pattern as P  # noqa: E402
import mangrove_kb.signals.volatility as VOL  # noqa: E402
from audit import load_btc_daily  # noqa: E402
from mangrove_kb.registry import RuleRegistry  # noqa: E402


# =============================================================================
# Fixtures
# =============================================================================

def real_fixture() -> pd.DataFrame:
    """The 1,294-bar BTC daily trace. The primary evidence for every formula."""
    return load_btc_daily()[["Open", "High", "Low", "Close", "Volume"]].copy()


def synthetic_fixture(n: int = 600, seed: int = 71) -> pd.DataFrame:
    """A constructed series for setups the real trace does not contain.

    Drift alternates four times so oscillators traverse both extremes, volatility contracts so
    band-width thresholds are crossed, and a sustained drawdown lets drawdown-depth measures reach
    their high-risk levels. `open` carries its own noise rather than being the previous close: an
    open exactly equal to the prior close makes every strict `<` comparison against it unfirable.
    """
    idx = pd.date_range("2024-01-01", periods=n, freq="h")
    rs = np.random.RandomState(seed)
    q = n // 4
    drift = np.concatenate([np.full(q, 0.35), np.full(q, -0.9),
                            np.full(q, 0.5), np.full(n - 3 * q, -0.2)])
    vol = np.concatenate([np.full(q, 2.2), np.linspace(2.2, 0.15, q),
                          np.full(q, 0.15), np.full(n - 3 * q, 1.0)])
    c = pd.Series(100 + np.cumsum(rs.normal(0, 1, n) * vol + drift), index=idx)
    o = c.shift(1).bfill() + rs.normal(0, 0.4, n)
    hi = np.maximum(o, c) + np.abs(rs.normal(0, 1, n) * vol)
    lo = np.minimum(o, c) - np.abs(rs.normal(0, 1, n) * vol)
    return pd.DataFrame({"Open": o, "High": hi, "Low": lo, "Close": c,
                         "Volume": pd.Series(rs.randint(1000, 9000, n).astype(float), index=idx)},
                        index=idx)


def gapless_fixture(n: int = 400, seed: int = 17) -> pd.DataFrame:
    """A 24/7 market: the open never escapes the prior bar's range, so no bar ever gaps.

    Near the prior close, not equal to it -- an identical open cannot satisfy a strict inequality
    against it either, which makes the fixture degenerate rather than merely gapless.
    """
    idx = pd.date_range("2024-01-01", periods=n, freq="h")
    rs = np.random.RandomState(seed)
    c = pd.Series(100 + rs.normal(0, 1.5, n).cumsum(), index=idx)
    o = c.shift(1).bfill() + rs.normal(0, 0.25, n)
    hi = np.maximum(o, c) + np.abs(rs.normal(0, 0.6, n))
    lo = np.minimum(o, c) - np.abs(rs.normal(0, 0.6, n))
    df = pd.DataFrame({"Open": o, "High": hi, "Low": lo, "Close": c, "Volume": 1000.0}, index=idx)
    df["Open"] = df["Open"].clip(lower=df["Low"].shift(1), upper=df["High"].shift(1)).fillna(df["Open"])
    return df


# =============================================================================
# Predicate builders -- the shapes that recur across every class
# =============================================================================

def defined(*vals) -> bool:
    return all(not pd.isna(v) for v in vals)


def above(series, thr):
    return lambda t: defined(series.iloc[t]) and series.iloc[t] > thr


def below(series, thr):
    return lambda t: defined(series.iloc[t]) and series.iloc[t] < thr


def at_least(series, thr):
    return lambda t: defined(series.iloc[t]) and series.iloc[t] >= thr


def at_most(series, thr):
    return lambda t: defined(series.iloc[t]) and series.iloc[t] <= thr


def crosses_up(series, thr=0.0):
    return lambda t: (defined(series.iloc[t - 1], series.iloc[t])
                      and series.iloc[t - 1] <= thr < series.iloc[t])


def crosses_down(series, thr=0.0):
    return lambda t: (defined(series.iloc[t - 1], series.iloc[t])
                      and series.iloc[t - 1] >= thr > series.iloc[t])


def crosses_above(series, band):
    """`series` crosses above `band`, both moving. Distinct from a fixed threshold."""
    return lambda t: (defined(series.iloc[t - 1], series.iloc[t], band.iloc[t - 1], band.iloc[t])
                      and series.iloc[t - 1] <= band.iloc[t - 1] and series.iloc[t] > band.iloc[t])


def crosses_below(series, band):
    return lambda t: (defined(series.iloc[t - 1], series.iloc[t], band.iloc[t - 1], band.iloc[t])
                      and series.iloc[t - 1] >= band.iloc[t - 1] and series.iloc[t] < band.iloc[t])


def outside_above(series, band):
    """A STATE: true for every bar `series` sits above `band`, not only the crossing bar."""
    return lambda t: defined(series.iloc[t], band.iloc[t]) and series.iloc[t] > band.iloc[t]


def outside_below(series, band):
    return lambda t: defined(series.iloc[t], band.iloc[t]) and series.iloc[t] < band.iloc[t]


def equals(series, value):
    """A detector emitting -1 / 0 / +1, where the sign carries the direction."""
    return lambda t: bool(series.iloc[t] == value)


def nonzero(series):
    return lambda t: bool(series.iloc[t] != 0)


def fired_within(series_list, window):
    """Any of `series_list` non-zero on any bar in [t-window+1 .. t]."""
    return lambda t: any(bool((s.iloc[max(0, t - window + 1):t + 1] != 0).any())
                         for s in series_list)


def detector(fn, O, H, L, C, **kw):
    """Call a private pattern detector.

    The call shape is NOT uniform: the three-inside detectors take (open, close) only, because they
    are pure body comparisons and never touch high/low.
    """
    if fn in (P._three_inside_up, P._three_inside_down):
        return fn(O, C, **kw)
    return fn(O, H, L, C, **kw)


# =============================================================================
# Result reporting
# =============================================================================

class Result:
    __slots__ = ("name", "module", "real_fires", "real_mismatch",
                 "alt_fires", "alt_mismatch", "alt_kind", "error")

    def __init__(self, name, module):
        self.name, self.module = name, module
        self.real_fires = self.real_mismatch = 0
        self.alt_fires = self.alt_mismatch = None
        self.alt_kind = self.error = None

    @property
    def verified(self):
        if self.error:
            return False
        if self.real_mismatch or (self.alt_mismatch or 0):
            return False
        return self.real_fires > 0 or (self.alt_fires or 0) > 0

    @property
    def status(self):
        if self.error:
            return "ERROR"
        if self.real_mismatch or (self.alt_mismatch or 0):
            return "MISMATCH"
        if self.real_fires:
            return "ok (real)"
        if self.alt_fires:
            return f"ok ({self.alt_kind})"
        return "NEVER FIRES"


def replay(name, params, predicate, df, start):
    """Compare the signal against the predicate over `df`. Returns (fires, mismatches)."""
    fires = mismatches = 0
    for t in range(start, len(df)):
        got = bool(RuleRegistry.evaluate({"name": name, "params": params}, df.iloc[:t + 1]))
        try:
            want = bool(predicate(t))
        except Exception:
            want = False
        fires += got
        mismatches += got != want
    return fires, mismatches


def run(spec_builder, label, start=70):
    """Run one class's spec against the real fixture, falling back for anything that never fires."""
    real = real_fixture()
    spec = spec_builder(real)
    results = []
    for name, (params, predicate) in spec.items():
        r = Result(name, label)
        try:
            r.real_fires, r.real_mismatch = replay(name, params, predicate, real, start)
        except Exception as exc:  # a signal that raises is a defect, not a skip
            r.error = f"{type(exc).__name__}: {exc}"
            results.append(r)
            continue
        if r.real_fires == 0 and not r.real_mismatch:
            for kind, builder in (("synthetic", synthetic_fixture), ("gapless", gapless_fixture)):
                alt = builder()
                alt_spec = spec_builder(alt)
                if name not in alt_spec:
                    continue
                f, m = replay(name, alt_spec[name][0], alt_spec[name][1], alt, min(start, len(alt) // 4))
                if f or m:
                    r.alt_fires, r.alt_mismatch, r.alt_kind = f, m, kind
                    break
        results.append(r)
    return results


def report(results):
    bad = [r for r in results if not r.verified]
    for r in sorted(results, key=lambda x: (x.status != "ok (real)", x.name)):
        detail = f"real={r.real_fires:4d}"
        if r.alt_fires is not None:
            detail += f"  {r.alt_kind}={r.alt_fires}"
        if r.error:
            detail = r.error
        print(f"  {r.status:14} {r.name:34} {detail}")
    n = len(results)
    print(f"\n{n - len(bad)} / {n} verified"
          + (f"   PROBLEMS: {[r.name for r in bad]}" if bad else ""))
    return 1 if bad else 0


# =============================================================================
# SPECS -- one entry per authored signal: name -> (params, predicate)
#
# Each builder takes the fixture and returns the spec, so the same definitions run against the real
# trace and any constructed one. A new class appends a builder here and a line in CLASSES; nothing
# else changes.
# =============================================================================

def spec_volatility(df):
    from mangrove_kb.indicators import (ATR, NATR, BollingerBands, DonchianChannel, KeltnerChannel,
                                        STARCBands, UlcerIndex)
    H, L, C = df["High"], df["Low"], df["Close"]
    atr = ATR.compute({"high": H, "low": L, "close": C}, {"window": 14})["atr"]
    natr = NATR.compute({"high": H, "low": L, "close": C}, {"window": 14})["natr"]
    ui = UlcerIndex.compute({"close": C}, {"window": 14})["ulcer_index"]
    bb = BollingerBands.compute({"close": C}, {"window": 20, "window_dev": 2})
    dc = DonchianChannel.compute({"high": H, "low": L, "close": C},
                                 {"window": 20, "include_current_bar": False})
    kc = KeltnerChannel.compute({"high": H, "low": L, "close": C},
                                {"window": 20, "window_atr": 10, "original_version": False,
                                 "multiplier": 2.0})
    st = STARCBands.compute({"high": H, "low": L, "close": C},
                            {"window": 20, "window_atr": 14, "multiplier": 2.0})
    bbp = {"window": 20, "window_dev": 2}
    kcp = {"window": 20, "window_atr": 10, "multiplier": 2.0}
    stp = {"window": 20, "window_atr": 14, "multiplier": 2.0}
    return {
        "bb_upper_breakout": (bbp, crosses_above(C, bb["hband"])),
        "bb_lower_breakout": (bbp, crosses_below(C, bb["lband"])),
        "bb_above_upper": (bbp, outside_above(C, bb["hband"])),
        "bb_below_lower": (bbp, outside_below(C, bb["lband"])),
        "bb_squeeze": ({**bbp, "threshold": 5.0}, crosses_down(bb["wband"], 5.0)),
        # ATR read as a percent of price, so the threshold is comparable across instruments
        "atr_high_volatility": ({"window": 14, "threshold_pct": 2.0},
                                lambda t: defined(atr.iloc[t]) and C.iloc[t] != 0
                                          and (atr.iloc[t] / C.iloc[t]) * 100 > 2.0),
        "natr_high_volatility": ({"window": 14, "threshold": 3.0}, above(natr, 3.0)),
        "natr_low_volatility": ({"window": 14, "threshold": 1.0}, below(natr, 1.0)),
        "ulcer_high_risk": ({"window": 14, "threshold": 10.0}, above(ui, 10.0)),
        "ulcer_low_risk": ({"window": 14, "threshold": 5.0}, below(ui, 5.0)),
        "dc_upper_breakout": ({"window": 20}, crosses_above(C, dc["hband"])),
        "dc_lower_breakout": ({"window": 20}, crosses_below(C, dc["lband"])),
        "kc_upper_breakout": ({**kcp, "original_version": False}, crosses_above(C, kc["hband"])),
        "kc_lower_breakout": ({**kcp, "original_version": False}, crosses_below(C, kc["lband"])),
        "kc_above_upper": (kcp, outside_above(C, kc["hband"])),
        "kc_below_lower": (kcp, outside_below(C, kc["lband"])),
        # named "breakout" but a STATE -- see the node's formula
        "starc_upper_breakout": (stp, outside_above(C, st["starc_hband"])),
        "starc_lower_breakout": (stp, outside_below(C, st["starc_lband"])),
    }


def spec_momentum(df):
    from mangrove_kb.indicators import (BOP, CMO, KAMA, MACD, MOM, PPO, PVO, ROC, RSI, TSI,
                                        AwesomeOscillator, StochasticOscillator, StochRSI,
                                        UltimateOscillator, WilliamsR)
    O, H, L, C, V = df["Open"], df["High"], df["Low"], df["Close"], df["Volume"]
    ao = AwesomeOscillator.compute({"high": H, "low": L}, {"window1": 5, "window2": 34})["ao"]
    bop = BOP.compute({"open": O, "high": H, "low": L, "close": C}, {})["bop"]
    cmo = CMO.compute({"close": C}, {"window": 14})["cmo"]
    kama = KAMA.compute({"close": C}, {"window": 10, "pow1": 2, "pow2": 30})["kama"]
    macd = MACD.compute({"close": C}, {"window_fast": 12, "window_slow": 26, "window_sign": 9})["macd"]
    mom = MOM.compute({"close": C}, {"window": 10})["mom"]
    ppo = PPO.compute({"close": C}, {"window_slow": 26, "window_fast": 12, "window_sign": 9})
    pvo = PVO.compute({"volume": V}, {"window_slow": 26, "window_fast": 12, "window_sign": 9})
    roc = ROC.compute({"close": C}, {"window": 12})["roc"]
    rsi = RSI.compute({"close": C}, {"window": 14})["rsi"]
    stoch = StochasticOscillator.compute({"high": H, "low": L, "close": C},
                                         {"window": 14, "smooth_window": 3})["stoch_k"]
    srsi = StochRSI.compute({"close": C}, {"window": 14, "smooth1": 3, "smooth2": 3})["stochrsi"]
    tsi = TSI.compute({"close": C}, {"window_slow": 25, "window_fast": 13})["tsi"]
    uo = UltimateOscillator.compute({"high": H, "low": L, "close": C},
                                    {"window1": 7, "window2": 14, "window3": 28,
                                     "weight1": 4.0, "weight2": 2.0, "weight3": 1.0})["ultimate_oscillator"]
    wr = WilliamsR.compute({"high": H, "low": L, "close": C}, {"window": 14})["wr"]
    aop = {"window_fast": 5, "window_slow": 34}
    mp = {"window_fast": 12, "window_slow": 26}
    sp = {"window_slow": 26, "window_fast": 12, "window_sign": 9}
    return {
        "ao_bullish": ({**aop, "threshold": 0.0}, above(ao, 0.0)),
        "ao_bearish": ({**aop, "threshold": 0.0}, below(ao, 0.0)),
        "ao_zero_cross": ({**aop, "direction": "bullish"}, crosses_up(ao)),
        "bop_bullish": ({}, above(bop, 0.0)), "bop_bearish": ({}, below(bop, 0.0)),
        "bop_cross_up": ({}, crosses_up(bop)), "bop_cross_down": ({}, crosses_down(bop)),
        "cmo_overbought": ({"window": 14, "threshold": 50.0}, at_least(cmo, 50.0)),
        "cmo_oversold": ({"window": 14, "threshold": -50.0}, at_most(cmo, -50.0)),
        "cmo_cross_up": ({"window": 14, "threshold": -50.0}, crosses_up(cmo, -50.0)),
        "cmo_cross_down": ({"window": 14, "threshold": 50.0}, crosses_down(cmo, 50.0)),
        "kama_cross_up": ({"window": 10, "pow1": 2, "pow2": 30}, crosses_above(C, kama)),
        "kama_cross_down": ({"window": 10, "pow1": 2, "pow2": 30}, crosses_below(C, kama)),
        "macd_line_positive": (mp, above(macd, 0.0)),
        "macd_line_negative": (mp, below(macd, 0.0)),
        "macd_line_cross_up": (mp, crosses_up(macd)),
        "macd_line_cross_down": (mp, crosses_down(macd)),
        "mom_bullish": ({"window": 10}, above(mom, 0.0)),
        "mom_bearish": ({"window": 10}, below(mom, 0.0)),
        "mom_cross_up": ({"window": 10}, crosses_up(mom)),
        "mom_cross_down": ({"window": 10}, crosses_down(mom)),
        "ppo_bullish_cross": (sp, crosses_above(ppo["ppo"], ppo["ppo_signal"])),
        "ppo_bearish_cross": (sp, crosses_below(ppo["ppo"], ppo["ppo_signal"])),
        # PVO is computed from VOLUME despite sharing PPO's shape exactly
        "pvo_bullish_cross": (sp, crosses_above(pvo["pvo"], pvo["pvo_signal"])),
        "pvo_bearish_cross": (sp, crosses_below(pvo["pvo"], pvo["pvo_signal"])),
        "roc_positive": ({"window": 12, "threshold": 0.0}, above(roc, 0.0)),
        "roc_negative": ({"window": 12, "threshold": 0.0}, below(roc, 0.0)),
        "roc_momentum_shift": ({"window": 12, "direction": "bullish"}, crosses_up(roc)),
        "rsi_overbought": ({"window": 14, "threshold": 70.0}, above(rsi, 70.0)),
        "rsi_oversold": ({"window": 14, "threshold": 30.0}, below(rsi, 30.0)),
        "rsi_cross_up": ({"window": 14, "threshold": 30.0}, crosses_up(rsi, 30.0)),
        "rsi_cross_down": ({"window": 14, "threshold": 70.0}, crosses_down(rsi, 70.0)),
        "stoch_overbought": ({"window": 14, "smooth_window": 3, "threshold": 80.0}, above(stoch, 80.0)),
        "stoch_oversold": ({"window": 14, "smooth_window": 3, "threshold": 20.0}, below(stoch, 20.0)),
        # StochRSI is on the 0..1 scale: the conventional 80/20 levels are 0.80/0.20 here
        "stochrsi_overbought": ({"window": 14, "smooth1": 3, "smooth2": 3, "threshold": 0.8}, above(srsi, 0.8)),
        "stochrsi_oversold": ({"window": 14, "smooth1": 3, "smooth2": 3, "threshold": 0.2}, below(srsi, 0.2)),
        "tsi_bullish": ({"window_slow": 25, "window_fast": 13, "threshold": 0.0}, above(tsi, 0.0)),
        "tsi_bearish": ({"window_slow": 25, "window_fast": 13, "threshold": 0.0}, below(tsi, 0.0)),
        "uo_overbought": ({"window_short": 7, "window_medium": 14, "window_long": 28, "threshold": 70.0}, above(uo, 70.0)),
        "uo_oversold": ({"window_short": 7, "window_medium": 14, "window_long": 28, "threshold": 30.0}, below(uo, 30.0)),
        # Williams %R is NEGATIVE: overbought is the band nearest zero
        "williams_r_overbought": ({"window": 14, "threshold": -20.0}, above(wr, -20.0)),
        "williams_r_oversold": ({"window": 14, "threshold": -80.0}, below(wr, -80.0)),
    }


def spec_patterns(df):
    O, H, L, C = df["Open"], df["High"], df["Low"], df["Close"]

    def d(fn, **kw):
        return detector(fn, O, H, L, C, **kw)

    bull = [d(P._hammer, wick_ratio=2.0, upper_wick_max=0.1),
            d(P._inverted_hammer, wick_ratio=2.0, lower_wick_max=0.1),
            d(P._engulfing).clip(lower=0), d(P._harami).clip(lower=0),
            d(P._piercing_line, min_penetration=0.5, require_gap=False),
            d(P._dragonfly_doji, body_threshold=0.1, upper_wick_max=0.1),
            d(P._tweezer_bottoms, tolerance=0.01),
            d(P._pin_bar, wick_ratio=2.0, body_position=0.33).clip(lower=0),
            d(P._morning_star, body_threshold=0.3),
            d(P._three_white_soldiers, min_body_ratio=0.5), d(P._three_inside_up)]
    bear = [d(P._hanging_man, wick_ratio=2.0, upper_wick_max=0.1),
            d(P._shooting_star, wick_ratio=2.0, lower_wick_max=0.1),
            d(P._engulfing).clip(upper=0).abs(), d(P._harami).clip(upper=0).abs(),
            d(P._dark_cloud_cover, min_penetration=0.5, require_gap=False).abs(),
            d(P._gravestone_doji, body_threshold=0.1, lower_wick_max=0.1),
            d(P._tweezer_tops, tolerance=0.01).abs(),
            d(P._pin_bar, wick_ratio=2.0, body_position=0.33).clip(upper=0).abs(),
            d(P._evening_star, body_threshold=0.3).abs(),
            d(P._three_black_crows, min_body_ratio=0.5).abs(), d(P._three_inside_down).abs()]
    W = 5
    return {
        "doji_trigger": ({"body_threshold": 0.1}, nonzero(d(P._doji, body_threshold=0.1))),
        "dragonfly_doji_trigger": ({"body_threshold": 0.1, "upper_wick_max": 0.1},
                                   nonzero(d(P._dragonfly_doji, body_threshold=0.1, upper_wick_max=0.1))),
        "gravestone_doji_trigger": ({"body_threshold": 0.1, "lower_wick_max": 0.1},
                                    nonzero(d(P._gravestone_doji, body_threshold=0.1, lower_wick_max=0.1))),
        "long_legged_doji_trigger": ({"body_threshold": 0.1, "wick_threshold": 0.25},
                                     nonzero(d(P._long_legged_doji, body_threshold=0.1, wick_threshold=0.25))),
        "spinning_top_trigger": ({"body_max": 0.3, "wick_min": 0.2},
                                 nonzero(d(P._spinning_top, body_max=0.3, wick_min=0.2))),
        "marubozu_bullish_trigger": ({"wick_tolerance": 0.05}, equals(d(P._marubozu, wick_tolerance=0.05), 1)),
        "marubozu_bearish_trigger": ({"wick_tolerance": 0.05}, equals(d(P._marubozu, wick_tolerance=0.05), -1)),
        "hammer_trigger": ({"wick_ratio": 2.0, "upper_wick_max": 0.1},
                           nonzero(d(P._hammer, wick_ratio=2.0, upper_wick_max=0.1))),
        "inverted_hammer_trigger": ({"wick_ratio": 2.0, "lower_wick_max": 0.1},
                                    nonzero(d(P._inverted_hammer, wick_ratio=2.0, lower_wick_max=0.1))),
        # identical arithmetic to hammer / inverted_hammer -- deprecated, kept for external callers
        "hanging_man_trigger": ({"wick_ratio": 2.0, "upper_wick_max": 0.1},
                                nonzero(d(P._hanging_man, wick_ratio=2.0, upper_wick_max=0.1))),
        "shooting_star_trigger": ({"wick_ratio": 2.0, "lower_wick_max": 0.1},
                                  nonzero(d(P._shooting_star, wick_ratio=2.0, lower_wick_max=0.1))),
        "bullish_pin_bar_trigger": ({"wick_ratio": 2.0, "body_position": 0.33},
                                    equals(d(P._pin_bar, wick_ratio=2.0, body_position=0.33), 1)),
        "bearish_pin_bar_trigger": ({"wick_ratio": 2.0, "body_position": 0.33},
                                    equals(d(P._pin_bar, wick_ratio=2.0, body_position=0.33), -1)),
        "bullish_engulfing_trigger": ({}, equals(d(P._engulfing), 1)),
        "bearish_engulfing_trigger": ({}, equals(d(P._engulfing), -1)),
        "bullish_harami_trigger": ({}, equals(d(P._harami), 1)),
        "bearish_harami_trigger": ({}, equals(d(P._harami), -1)),
        "inside_bar_trigger": ({}, nonzero(d(P._inside_bar))),
        "outside_bar_trigger": ({}, nonzero(d(P._outside_bar))),
        "nr7_trigger": ({"window": 7}, nonzero(d(P._narrow_range, window=7))),
        # require_gap defaults to False: a 24/7 market never opens beyond the prior extreme
        "piercing_line_trigger": ({"min_penetration": 0.5, "require_gap": False},
                                  nonzero(d(P._piercing_line, min_penetration=0.5, require_gap=False))),
        "dark_cloud_cover_trigger": ({"min_penetration": 0.5, "require_gap": False},
                                     equals(d(P._dark_cloud_cover, min_penetration=0.5, require_gap=False), -1)),
        "tweezer_bottoms_trigger": ({"tolerance": 0.01}, nonzero(d(P._tweezer_bottoms, tolerance=0.01))),
        "tweezer_tops_trigger": ({"tolerance": 0.01}, equals(d(P._tweezer_tops, tolerance=0.01), -1)),
        "two_bar_reversal_bullish_trigger": ({"close_proximity": 0.25},
                                             equals(d(P._two_bar_reversal, close_proximity=0.25), 1)),
        "two_bar_reversal_bearish_trigger": ({"close_proximity": 0.25},
                                             equals(d(P._two_bar_reversal, close_proximity=0.25), -1)),
        "morning_star_trigger": ({"body_threshold": 0.3}, nonzero(d(P._morning_star, body_threshold=0.3))),
        "evening_star_trigger": ({"body_threshold": 0.3}, equals(d(P._evening_star, body_threshold=0.3), -1)),
        "three_white_soldiers_trigger": ({"min_body_ratio": 0.5},
                                         nonzero(d(P._three_white_soldiers, min_body_ratio=0.5))),
        "three_black_crows_trigger": ({"min_body_ratio": 0.5},
                                      equals(d(P._three_black_crows, min_body_ratio=0.5), -1)),
        "three_inside_up_trigger": ({}, nonzero(d(P._three_inside_up))),
        "three_inside_down_trigger": ({}, equals(d(P._three_inside_down), -1)),
        "bullish_pattern_recent": ({"window": W}, fired_within(bull, W)),
        "bearish_pattern_recent": ({"window": W}, fired_within(bear, W)),
        "reversal_pattern_bullish": ({"window": W}, fired_within([bull[0], bull[1], bull[2], bull[4], bull[5], bull[8]], W)),
        "reversal_pattern_bearish": ({"window": W}, fired_within([bear[0], bear[1], bear[2], bear[4], bear[5], bear[8]], W)),
        "continuation_pattern_bullish": ({"window": W}, fired_within(
            [d(P._three_white_soldiers, min_body_ratio=0.5), d(P._three_inside_up)], W)),
        "continuation_pattern_bearish": ({"window": W}, fired_within(
            [d(P._three_black_crows, min_body_ratio=0.5).abs(), d(P._three_inside_down).abs()], W)),
        "indecision_pattern_recent": ({"window": W}, fired_within(
            [d(P._doji, body_threshold=0.1), d(P._spinning_top, body_max=0.3, wick_min=0.2),
             d(P._inside_bar), d(P._narrow_range, window=7)], W)),
        "strong_body_recent": ({"window": W}, fired_within([d(P._marubozu, wick_tolerance=0.05).abs()], W)),
    }


# Keyed by the signal's source module, which is now the ontology CLASS -- `momentum` here covers
# only the 18 rate-of-change signals; the bounded oscillators moved to `oscillator` and the KAMA
# crossings to `averaging`. spec_momentum still returns all three because they are verified the same
# way; the split that matters is in the files, not here.
CLASSES = {
    "volatility": spec_volatility,
    "momentum": spec_momentum,
    "patterns": spec_patterns,
}


def main(argv):
    wanted = argv[1:] or list(CLASSES)
    unknown = [w for w in wanted if w not in CLASSES]
    if unknown:
        print(f"unknown: {unknown}. known: {sorted(CLASSES)}", file=sys.stderr)
        return 2

    # Everything authored must be covered. A signal with a formula and no spec entry is unverified,
    # which is the state this harness exists to make impossible.
    import json
    graph = json.loads((Path(__file__).resolve().parents[2]
                        / "ontology" / "signal-indicator-ontology.json").read_text())
    authored = {a["title"] for a in graph["atoms"]
                if a["id"].startswith("procedure:signal-") and a["props"].get("formula")}
    covered = set()
    for k in CLASSES:
        covered |= set(CLASSES[k](real_fixture()))
    if wanted == list(CLASSES) and (gap := sorted(authored - covered)):
        print(f"ABORT: {len(gap)} signals have an authored formula but no spec here: {gap}",
              file=sys.stderr)
        return 2

    rc = 0
    for name in wanted:
        print(f"=== {name} ===")
        rc |= report(run(CLASSES[name], name))
        print()
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

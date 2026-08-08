"""Candle geometry indicators.

The numeric measurement layer that candlestick pattern analysis is built on:
the shape of a single bar, and the relationship between a bar and the one
before it.

This module used to hold 27 pattern-detection classes as well. They emitted a
decision (0/1, or -1/0/+1) rather than a measurement, which put a boolean-valued
output in the indicator layer and left the ontology unable to say what they
were. They now live as private detectors in `mangrove_kb.signals.pattern`,
where a boolean answer is the contract, and they compute from the two indicators
here rather than from raw comparisons.

Each pattern signal in `mangrove_kb.signals.pattern` carries a `Reference:` URL in its own
docstring, which the ontology builder lifts. The bracket-key scheme this block used to define was
replaced: it named ten distinct keys across the signal docstrings and defined three of them, so
seven cited a source nothing in the repository identified, and nothing could be lifted.
"""

import numpy as np
import pandas as pd

from mangrove_kb.indicators.indicator_interface import IndicatorInterface


# ===========================================================================
# Candle geometry primitives -- private to this module
# ===========================================================================
#
# CandleGeometry is the single public way to obtain candle shape. Nothing outside
# this module should reach for these directly; consume the indicator instead.

def _candle_body(open_s: pd.Series, close_s: pd.Series) -> pd.Series:
    """Absolute body size: |Close - Open|."""
    return (close_s - open_s).abs()


def _candle_range(high_s: pd.Series, low_s: pd.Series) -> pd.Series:
    """Full candle range: High - Low."""
    return high_s - low_s


def _upper_wick(open_s: pd.Series, high_s: pd.Series, close_s: pd.Series) -> pd.Series:
    """Upper wick length: High - max(Open, Close)."""
    return high_s - pd.concat([open_s, close_s], axis=1).max(axis=1)


def _lower_wick(open_s: pd.Series, low_s: pd.Series, close_s: pd.Series) -> pd.Series:
    """Lower wick length: min(Open, Close) - Low."""
    return pd.concat([open_s, close_s], axis=1).min(axis=1) - low_s


def _is_bullish(open_s: pd.Series, close_s: pd.Series) -> pd.Series:
    """Boolean series: True where Close > Open."""
    return close_s > open_s


def _is_bearish(open_s: pd.Series, close_s: pd.Series) -> pd.Series:
    """Boolean series: True where Close < Open."""
    return close_s < open_s


def _body_ratio(open_s: pd.Series, high_s: pd.Series,
               low_s: pd.Series, close_s: pd.Series) -> pd.Series:
    """Body as fraction of range: body / range.

    Returns 0.0 where range is 0 (flat candles).
    """
    body = _candle_body(open_s, close_s)
    rng = _candle_range(high_s, low_s)
    return body / rng.replace(0, np.nan).fillna(np.inf)


# =============================================================================
# Candle Geometry -- the numeric measurement layer beneath the patterns above
# =============================================================================
#
# Everything else in this module emits a DECISION (0/1, or -1/0/+1). These two
# emit MEASUREMENTS -- numeric series describing the shape of a bar and its
# relationship to the previous one -- which is what the pattern detectors are
# built out of. They are indicators in the sense the ontology means it; the
# detectors above are not, and are tracked for reclassification.

class CandleGeometry(IndicatorInterface):
    """Candle Geometry

    Decomposes each bar into the numeric measurements candlestick analysis is
    built from: how large the body is, how far the bar travelled, how long each
    wick is, and what fraction of the range the body occupies. Direction is
    carried by the sign of the body rather than by a separate flag.

    https://chartschool.stockcharts.com/table-of-contents/chart-analysis/candlestick-charts/introduction-to-candlesticks

    Formula:
        body        = |close - open|
        signed_body = close - open
        range       = high - low
        upper_wick  = high - max(open, close)
        lower_wick  = min(open, close) - low
        body_ratio  = body / range        (0 where range is 0)

    Interpretation:
        - A small body relative to range is indecision; a large one is conviction.
        - Long upper wick means an advance was rejected; long lower wick, a decline.
        - The sign of signed_body gives direction without a separate flag.
        - body_ratio near 0 is a doji, near 1 a marubozu with no wicks.
        - Warmup is zero: every output is defined on the first bar.

    Applications:
        - The measurement layer every candlestick pattern signal is built from.
        - Screening for conviction bars (high body_ratio) or indecision (low).
        - Quantifying rejection at a level from wick length.
        - Comparing bar shape across instruments via body_ratio, which is scale-free.

    UNITS: body, signed_body, range and both wicks are in the instrument's own
    PRICE units, so their magnitudes are not comparable across instruments or
    price regimes. `body_ratio` is the scale-free member and is the one to reach
    for when comparing shape across symbols.

    Args:
        data: {'open': pd.Series, 'high': pd.Series, 'low': pd.Series, 'close': pd.Series}
        params: {}
        open (series): opening price of the bar
        high (series): highest price traded during the bar
        low (series): lowest price traded during the bar
        close (series): closing price

    Returns:
        body (series, price): absolute body size, |close - open|. Non-negative by
            construction, and never larger than range, since open and close both
            lie within the bar's high-low span. Range: 0-inf. Canonical: none.
        signed_body (series, price): close - open, so the SIGN carries direction --
            positive is an up bar, negative a down bar, zero a flat one. Replaces
            the boolean is_bullish/is_bearish pair this indicator supersedes,
            keeping every output numeric. Range: -inf-inf. Canonical: none.
        range (series, price): full travel of the bar, high - low. Non-negative,
            and zero on a bar that did not move at all. Range: 0-inf.
            Canonical: none.
        upper_wick (series, price): high - max(open, close) -- the rejection above
            the body. Non-negative. Range: 0-inf. Canonical: none.
        lower_wick (series, price): min(open, close) - low -- the rejection below
            the body. Non-negative. Range: 0-inf. Canonical: none.
        body_ratio (series, ratio): body as a fraction of range. Hard-bounded 0-1
            because the body can never exceed the range: 0 is a doji, 1 a marubozu
            with no wicks at all. The only scale-free output here, so it is what
            makes shape comparable across instruments. Returns 0 on a zero-range
            bar, which is a convention rather than a measurement -- no source
            prescribes one. Range: 0-1. Canonical: none.
    """

    _data = ["open", "high", "low", "close"]
    _params = []
    _outputs = ["body", "signed_body", "range", "upper_wick", "lower_wick", "body_ratio"]

    @classmethod
    def _compute(cls, data, params):
        open_ = data["open"]
        high = data["high"]
        low = data["low"]
        close = data["close"]

        signed = close - open_
        body = _candle_body(open_, close)
        rng = _candle_range(high, low)
        upper = _upper_wick(open_, high, close)
        lower = _lower_wick(open_, low, close)

        # A zero-range bar has no shape to report a ratio for. Returning 0 keeps
        # the series finite and matches the previous helper's behaviour; note it
        # is a convention, not a measurement -- no source prescribes one.
        ratio = np.divide(
            body.to_numpy(dtype=np.float64),
            rng.to_numpy(dtype=np.float64),
            out=np.zeros(len(body), dtype=np.float64),
            where=rng.to_numpy(dtype=np.float64) != 0.0,
        )

        return {
            "body": pd.Series(body.values, index=close.index, name="body"),
            "signed_body": pd.Series(signed.values, index=close.index, name="signed_body"),
            "range": pd.Series(rng.values, index=close.index, name="range"),
            "upper_wick": pd.Series(upper.values, index=close.index, name="upper_wick"),
            "lower_wick": pd.Series(lower.values, index=close.index, name="lower_wick"),
            "body_ratio": pd.Series(ratio, index=close.index, name="body_ratio"),
        }


class CandleRelation(IndicatorInterface):
    """Candle Relation

    Measures the current bar against the previous one along three independent
    axes, because they answer different questions and none implies the others.

    LEVEL -- where this bar sits. Each `*_delta` is the signed distance between
    an edge of the current bar and the same edge of the previous one, so a pair
    of signs states containment directly:

        low_delta < 0 and high_delta > 0    current span CONTAINS the previous
        low_delta > 0 and high_delta < 0    current span is CONTAINED BY it
        signs agree                         the spans overlap, or are disjoint

    This is what Engulfing, Harami, InsideBar and OutsideBar each reduce to.
    Level is NOT recoverable from size: a bar can be smaller than its
    predecessor while sitting entirely above it, so "smaller" is not "nested".

    SIZE -- how much bigger. The `*_size_ratio` outputs are current span over
    previous span, so 2.0 means twice as large and 0.5 means half. Unbounded
    above, floored at 0, and 0 where the previous span was zero.

    GAP -- whether trading jumped between the bars. `gap` is the opening gap,
    open against the previous close. `range_overlap` is the shared extent of the
    two ranges: positive means they overlap by that much, and NEGATIVE means a
    true gap with no overlap at all, its magnitude being the size of the void.
    One output covers gap-up and gap-down, the direction coming from the sign.

    Formula:
        body_low_delta   = (min(o,c) - prev min(o,c)) / prev_close * 100
        body_high_delta  = (max(o,c) - prev max(o,c)) / prev_close * 100
        range_low_delta  = (low  - prev_low)  / prev_close * 100
        range_high_delta = (high - prev_high) / prev_close * 100
        body_size_ratio  = body  / prev_body
        range_size_ratio = range / prev_range
        gap              = (open - prev_close) / prev_close * 100
        range_overlap    = (min(high,prev_high) - max(low,prev_low)) / prev_close * 100

    Interpretation:
        - Negative low_delta with positive high_delta means this bar CONTAINS the
          previous one; the inverse means it is contained by it.
        - A size ratio above 1 means expansion, below 1 contraction.
        - Negative range_overlap means the bars do not touch -- a true gap.
        - Level and size are independent: a bar can be smaller yet sit outside.
        - Warmup is one bar: every output is NaN on the first, which has no
          predecessor to relate to.

    Applications:
        - The relational layer beneath Engulfing, Harami, InsideBar and OutsideBar.
        - Gap detection and gap sizing, without a price-scale dependency.
        - Volatility expansion or contraction from the size ratios.
        - Comparing two-bar structure across instruments and price regimes.

    UNITS: every distance here -- the four deltas, the gap, and the overlap -- is
    a PERCENT of the previous close, not a price. That makes readings comparable
    across instruments and price regimes: a 2% gap is 2% whether the instrument
    trades at 5 or at 50,000. The two size ratios are already scale-free. So no
    output is in price units, and nothing here needs rescaling to be compared.

    Args:
        data: {'open': pd.Series, 'high': pd.Series, 'low': pd.Series, 'close': pd.Series}
        params: {}
        open (series): opening price of the bar
        high (series): highest price traded during the bar
        low (series): lowest price traded during the bar
        close (series): closing price

    Returns:
        body_low_delta (series, percent): distance from the previous bar's lower
            body edge to this one's, as a percent of the previous close. Negative
            means this body starts below the last one. Range: -inf-inf.
            Canonical: none.
        body_high_delta (series, percent): the same for the upper body edge.
            Paired with body_low_delta the signs state containment: negative low
            with positive high is engulfing, the inverse is harami.
            Range: -inf-inf. Canonical: none.
        range_low_delta (series, percent): distance between the two bars' lows.
            Positive means this bar's low sits above the last one's.
            Range: -inf-inf. Canonical: none.
        range_high_delta (series, percent): distance between the two bars' highs.
            With range_low_delta this is InsideBar and OutsideBar: both edges
            drawn inward is inside, both outward is outside. Range: -inf-inf.
            Canonical: none.
        body_size_ratio (series, ratio): this bar's body over the previous bar's,
            so 2.0 is twice as large and 0.5 is half. Non-negative, no ceiling,
            and 0 where the previous body was zero-width. NaN on the first bar,
            which has no predecessor. Range: 0-inf. Canonical: none.
        range_size_ratio (series, ratio): the same for the full high-low range.
            Answers "how much bigger is this bar" independently of where it sits.
            Range: 0-inf. Canonical: none.
        gap (series, percent): open minus the previous close, as a percent of that
            close. Positive is a gap up, negative a gap down. Floored at -100,
            since the open cannot fall below zero. Range: -100-inf.
            Canonical: none.
        range_overlap (series, percent): shared extent of the two bars' ranges, as
            a percent of the previous close. Positive means they overlap by that
            much; NEGATIVE means no overlap at all -- a true gap -- and the
            magnitude is how far apart they are. This is the output to read for
            "did we gap", with direction taken from the sign of `gap`.
            Range: -inf-inf. Canonical: none.
    """

    _data = ["open", "high", "low", "close"]
    _params = []
    _outputs = ["body_low_delta", "body_high_delta",
                "range_low_delta", "range_high_delta",
                "body_size_ratio", "range_size_ratio",
                "gap", "range_overlap"]

    @classmethod
    def _compute(cls, data, params):
        open_ = data["open"]
        high = data["high"]
        low = data["low"]
        close = data["close"]

        oc = pd.concat([open_, close], axis=1)
        body_low = oc.min(axis=1)
        body_high = oc.max(axis=1)
        body = _candle_body(open_, close)
        rng = _candle_range(high, low)
        prev_close = close.shift(1)

        def _pct(distance):
            """Distance as a percent of the previous close.

            Every distance here is reported price-agnostically so readings are
            comparable across instruments and across price regimes -- a 2% gap
            is 2% whether the instrument trades at 5 or 50,000. Dividing by a
            strictly positive prior close also preserves sign, so the
            containment logic built on these is unaffected.
            """
            d = distance.to_numpy(dtype=np.float64)
            p = prev_close.to_numpy(dtype=np.float64)
            out = np.full(len(d), np.nan, dtype=np.float64)
            ok = np.isfinite(d) & np.isfinite(p) & (p != 0.0)
            np.divide(d, p, out=out, where=ok)
            return out * 100.0

        def _ratio(curr, prev):
            """NaN where there is no previous bar; 0 where its span was zero."""
            c = curr.to_numpy(dtype=np.float64)
            p = prev.to_numpy(dtype=np.float64)
            out = np.zeros(len(c), dtype=np.float64)
            out[~np.isfinite(p) | ~np.isfinite(c)] = np.nan
            ok = np.isfinite(c) & np.isfinite(p) & (p != 0.0)
            np.divide(c, p, out=out, where=ok)
            return out

        # Shared extent of the two ranges. skipna=False matters: without it the
        # first bar's min/max drop the missing previous bar and the row reports
        # the bar's own range instead of NaN.
        overlap = (pd.concat([high, high.shift(1)], axis=1).min(axis=1, skipna=False)
                   - pd.concat([low, low.shift(1)], axis=1).max(axis=1, skipna=False))

        return {
            "body_low_delta": pd.Series(
                _pct(body_low - body_low.shift(1)), index=close.index,
                name="body_low_delta"),
            "body_high_delta": pd.Series(
                _pct(body_high - body_high.shift(1)), index=close.index,
                name="body_high_delta"),
            "range_low_delta": pd.Series(
                _pct(low - low.shift(1)), index=close.index,
                name="range_low_delta"),
            "range_high_delta": pd.Series(
                _pct(high - high.shift(1)), index=close.index,
                name="range_high_delta"),
            "body_size_ratio": pd.Series(
                _ratio(body, body.shift(1)), index=close.index,
                name="body_size_ratio"),
            "range_size_ratio": pd.Series(
                _ratio(rng, rng.shift(1)), index=close.index,
                name="range_size_ratio"),
            "gap": pd.Series(
                _pct(open_ - prev_close), index=close.index, name="gap"),
            "range_overlap": pd.Series(
                _pct(overlap), index=close.index, name="range_overlap"),
        }

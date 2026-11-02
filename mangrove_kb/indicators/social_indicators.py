"""
Social Indicators.

Measurements over a per-bar social reading -- a sentiment score, a bullish share, a post count --
that the caller has aligned to the bars without lookahead. The reading is the `value` input, so the
same computation serves every social source (Deep42 scored sentiment, X post counts); which column
feeds it is the signal's choice, named in that signal's `Requires:`.
"""
import numpy as np
import pandas as pd

from mangrove_kb.indicators.indicator_interface import IndicatorInterface

#: Relative spread at or below which a baseline is flat: ``sd <= FLAT_BASELINE_TOLERANCE * max(1, |mean|)``.
#: Identical readings round to about 1e-16 relative under a two-pass standard deviation; two
#: distinct integer counts below 1e9 differ by more than 1e-12.
FLAT_BASELINE_TOLERANCE = 1e-12


class SocialZScore(IndicatorInterface):
    """Indicator: SocialZScore

    How unusual the latest social reading is: its distance from the mean of the readings before it,
    in standard deviations of those readings. The baseline excludes the current bar, so a single
    extreme reading cannot dampen its own score.

    Abbreviation: none
    Warmup: window

    Formula:
        mean[t] = mean(value[t-window .. t-1])
        sd[t]   = std(value[t-window .. t-1])     (sample, ddof=1)
        zscore  = (value[t] - mean[t]) / sd[t]

        Undefined (NaN) where the baseline is flat: sd <= 1e-12 * max(1, |mean|).

    Inputs:
        value: per-bar social reading (sentiment score, bullish share, post count, ...)

    Params:
        window [default=30, min=5, max=365]: readings forming the baseline, current bar excluded

    Outputs:
        zscore [standard deviations, -inf..inf] "social z-score":
            distance of the latest reading from the mean of the prior window, in units of that
            window's sample standard deviation. Unbounded in both directions. +/-2 is the
            conventional "unusual" line; it assumes a roughly stable baseline, and a reading series
            whose collection volume changes (as X post counts did in early 2026) shifts the mean
            without any change in mood

    Interpretation:
        - **Large positive**: the crowd is far more bullish, or far louder, than it has been
        - **Large negative**: far more bearish, or far quieter, than usual
        - **Near zero**: an ordinary reading for this asset
        - Scale-free, so the same threshold reads the same way across assets and sources

    Applications:
        - **Surge and capitulation triggers**: act when sentiment or attention breaks from its norm
        - **Divergence**: an unusual social reading that price does not follow
        - **Data hygiene**: spotting collection breaks in a social series

    Args:
        data: {'value': pd.Series}
        params: {'window': int}

    Returns:
        {'zscore': pd.Series}
    """
    _data = ["value"]
    _params = ["window"]
    _outputs = ["zscore"]

    @classmethod
    def _compute(cls, data, params):
        value = pd.to_numeric(data['value'], errors='coerce')
        window = params['window']

        prior = value.shift(1).rolling(window, min_periods=window)
        mean = prior.mean()
        sd = prior.std()
        # A baseline whose spread is within the tolerance of zero, relative to its magnitude,
        # is flat; the z-score is undefined there.
        flat = sd <= FLAT_BASELINE_TOLERANCE * mean.abs().clip(lower=1.0)
        z = (value - mean) / sd.where(~flat)
        return {'zscore': pd.Series(z.replace([np.inf, -np.inf], np.nan), name="social_zscore")}


class SocialBaselineShift(IndicatorInterface):
    """Indicator: SocialBaselineShift

    Whether the crowd's recent mood or attention sits above or below its own longer-run norm: the
    mean of the last `window` readings against the mean of the `window_baseline` readings before
    them. The two windows do not overlap, so recent readings never count toward their own baseline.

    Abbreviation: none
    Warmup: window + window_baseline - 1

    Formula:
        recent   = mean(value[t-window+1 .. t])
        baseline = mean(value[t-window-window_baseline+1 .. t-window])
        shift    = recent - baseline
        ratio    = recent / baseline          (NaN where baseline <= 0)

    Inputs:
        value: per-bar social reading (sentiment score, bullish share, post count, ...)

    Params:
        window [default=7, min=1, max=90]: readings in the recent mean
        window_baseline [default=60, min=5, max=365]: readings in the baseline mean, immediately before the recent window

    Outputs:
        recent [input units, -inf..inf] "recent social mean":
            mean of the last `window` readings, in the units of the input
        baseline [input units, -inf..inf] "baseline social mean":
            mean of the `window_baseline` readings before the recent window, in the units of the
            input
        shift [input units, -inf..inf] "shift from baseline":
            recent minus baseline. Positive when the recent crowd is above its norm. Same units as
            the input, so a threshold on it is source-specific (0.05 of bullish share, 0.5 of a 0-10
            sentiment score)
        ratio [ratio, 0..inf] "ratio to baseline":
            recent divided by baseline, 1.0 = unchanged. Meaningful for strictly positive inputs such
            as post counts; NaN where the baseline is zero or negative, so it is not used for signed
            readings like net bullish share

    Interpretation:
        - **Shift above zero / ratio above 1**: a more bullish, or louder, crowd than usual
        - **Shift below zero / ratio below 1**: a more bearish, or quieter, crowd than usual
        - A regime reading rather than an event: it moves slowly and stays on for stretches

    Applications:
        - **Regime filter**: allow entries only while the crowd runs warmer, or cooler, than usual
        - **Divergence**: price falling while the crowd holds at or above its baseline
        - **Attention**: elevated post volume as a ratio to its own norm

    Args:
        data: {'value': pd.Series}
        params: {'window': int, 'window_baseline': int}

    Returns:
        {'recent': pd.Series, 'baseline': pd.Series, 'shift': pd.Series, 'ratio': pd.Series}
    """
    _data = ["value"]
    _params = ["window", "window_baseline"]
    _outputs = ["recent", "baseline", "shift", "ratio"]

    @classmethod
    def _compute(cls, data, params):
        value = pd.to_numeric(data['value'], errors='coerce')
        window = params['window']
        window_baseline = params['window_baseline']

        recent = value.rolling(window, min_periods=window).mean()
        baseline = value.shift(window).rolling(window_baseline, min_periods=window_baseline).mean()
        ratio = recent / baseline.where(baseline > 0)
        return {
            'recent': pd.Series(recent, name="social_recent"),
            'baseline': pd.Series(baseline, name="social_baseline"),
            'shift': pd.Series(recent - baseline, name="social_shift"),
            'ratio': pd.Series(ratio, name="social_ratio"),
        }

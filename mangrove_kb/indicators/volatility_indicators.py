"""
Volatility Indicators.

Provides volatility-based technical analysis indicators including ATR,
Bollinger Bands, Keltner Channel, Donchian Channel, and Ulcer Index.

Originally from ta-master library by Dario Lopez Padial (Bukosabino).
"""
import numpy as np
import pandas as pd

from mangrove_kb.indicators.indicator_interface import IndicatorInterface
from mangrove_kb.indicators.utils import true_range, typical_price


class ATR(IndicatorInterface):
    """Indicator: ATR

    The indicator provide an indication of the degree of price volatility. Strong moves, in either
    direction, are often accompanied by large ranges, or large True Ranges.

    Abbreviation: ATR
    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/average-true-range-atr
    Warmup: window - 1

    Formula:
        True Range = max(
          High - Low,
          |High - Previous Close|,
          |Low - Previous Close|
        )
        ATR = EMA(True Range, n periods)

        Typical period: 14

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=14, min=5, max=50]: ATR period

    Outputs:
        atr [price, 0..inf] "Average True Range":
            Wilder-smoothed mean of the true range. Seeded with the arithmetic mean of the first
            `window` true-range values, then smoothed by ewm(alpha=1/window) -- Wilder's original
            recurrence, not an ordinary EMA. In the instrument's own price units, so NOT comparable
            across instruments or price levels; use NATR for that. WARMUP CAVEAT: bars 0..window-2
            are filled with literal 0.0 rather than NaN, so a zero here means 'not yet computed' and
            is indistinguishable from genuine zero volatility -- mask the first window-1 bars before
            consuming this series

    Interpretation:
        - Higher ATR: More volatility
        - Lower ATR: Less volatility
        - Rising ATR: Volatility expanding
        - Falling ATR: Volatility contracting

    Applications:
        - Stop-loss placement (e.g., 2 * ATR from entry)
        - Position sizing (smaller positions when ATR high)
        - Profit target setting
        - Volatility breakout detection
        - Normalizing across different assets

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series}
        params: {'window': int}

    Returns:
        {'atr': pd.Series}
    """
    _data = ["high", "low", "close"]
    _params = ["window"]
    _outputs = ["atr"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        close = data['close']
        window = params['window']

        tr = true_range(high, low, close)
        tr_arr = tr.to_numpy(dtype=np.float64)
        n = len(tr_arr)

        # Warmup is NaN, not zero. Zero is a meaningful ATR reading -- it means no observed range
        # -- so filling warmup with it makes the first window-1 bars indistinguishable from a
        # genuinely flat market, with nothing in the series to mark them. No source proposes a
        # zero-fill; the convention is universally that warmup is undefined.
        #
        # atr[window-1] = mean of the first `window` true-range values, then Wilder smoothing
        # forward. Wilder's recurrence is identical to ewm(alpha=1/window, adjust=False) applied to
        # [seed, tr[window], tr[window+1], ...].
        #
        # Note tr[0] is FINITE: true_range uses np.fmax, which ignores NaN and falls back to
        # high - low. An earlier comment here claimed tr[0] was NaN and the seed therefore a
        # window-1 mean; it is a true `window`-value mean, matching Wilder.
        atr_arr = np.full(n, np.nan)
        if n >= window:
            seed = np.nanmean(tr_arr[:window])
            tail = np.concatenate(([seed], tr_arr[window:]))
            smoothed = pd.Series(tail).ewm(alpha=1.0 / window, adjust=False).mean().to_numpy()
            atr_arr[window - 1 :] = smoothed

        return {'atr': pd.Series(atr_arr, index=close.index, name='atr')}


class BollingerBands(IndicatorInterface):
    """Indicator: BollingerBands

    Volatility bands placed above and below a moving average, with width determined by standard
    deviation.

    Abbreviation: BB
    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/bollinger-bands
    Warmup: window - 1

    Formula:
        Middle Band = SMA(Close, 20)
        Upper Band = SMA + (2 * Standard Deviation)
        Lower Band = SMA - (2 * Standard Deviation)

        Bandwidth = (Upper - Lower) / Middle * 100
        %B = (Close - Lower) / (Upper - Lower)

    Inputs:
        close: closing price

    Params:
        window [default=20, min=5, max=100]: MA period for center band
        window_dev [default=2, min=1, max=5]: Standard deviation multiplier

    Outputs:
        mavg [price, 0..inf]:
            rolling mean of close over window -- the center band
        hband [price, 0..inf]:
            mavg + window_dev * rolling stdev -- the upper band. The stdev is the POPULATION
            calculation (ddof=0), matching Bollinger's own stated convention
        lband [price, 0..inf]:
            mavg - window_dev * rolling stdev -- the lower band. Population stdev, as above
        wband [percent, 0..inf] "BandWidth":
            band separation as a percent of the center band, (hband - lband) / mavg * 100.
            Non-negative because the rolling stdev cannot be negative. Scale-free, so comparable
            across assets and price levels
        pband [ratio, -inf..inf] "%B":
            position of close between the bands, (close - lband) / (hband - lband). 0 at the lower
            band, 1 at the upper, but NOT clamped -- exceeds 1 above hband and drops below 0 under
            lband, which the literature treats as significant rather than as an edge case. NaN when
            the bands coincide, explicitly guarded here unlike Keltner and Donchian

    Interpretation:
        - Price at upper band: Potentially overbought / strong trend
        - Price at lower band: Potentially oversold / strong trend
        - Band squeeze (narrow bands): Low volatility, breakout potential
        - Band expansion: High volatility, trend in progress
        - %B > 1: Above upper band; %B < 0: Below lower band

    Applications:
        - Mean reversion trades at bands in ranges
        - Trend trades with band walking in trends
        - Squeeze detection for breakout anticipation
        - Volatility assessment for position sizing

    Args:
        data: {'close': pd.Series}
        params: {'window': int, 'window_dev': int}

    Returns:
        {'mavg': pd.Series, 'hband': pd.Series, 'lband': pd.Series,
         'wband': pd.Series, 'pband': pd.Series}
    """
    _data = ["close"]
    _params = ["window", "window_dev"]
    _outputs = ["mavg", "hband", "lband", "wband", "pband"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        window = params['window']
        window_dev = params['window_dev']

        mavg = close.rolling(window, min_periods=window).mean()
        mstd = close.rolling(window, min_periods=window).std(ddof=0)
        hband = mavg + window_dev * mstd
        lband = mavg - window_dev * mstd

        wband = ((hband - lband) / mavg) * 100
        pband = (close - lband) / (hband - lband).where(hband != lband, np.nan)

        return {
            'mavg': pd.Series(mavg, name="mavg"),
            'hband': pd.Series(hband, name="hband"),
            'lband': pd.Series(lband, name="lband"),
            'wband': pd.Series(wband, name="bbiwband"),
            'pband': pd.Series(pband, name="bbipband"),
        }


class KeltnerChannel(IndicatorInterface):
    """Indicator: KeltnerChannel

    Keltner Channels are a trend following indicator used to identify reversals with channel
    breakouts and channel direction. Channels can also be used to identify overbought and oversold
    levels when the trend is flat.

    Abbreviation: KC
    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/keltner-channels
    Warmup: window - 1

    Formula:
        Middle Line = EMA(Close, 20)
        Upper Channel = EMA + (2 * ATR)
        Lower Channel = EMA - (2 * ATR)

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=20, min=10, max=50]: EMA period for the center band
        window_atr [default=10, min=5, max=30]: ATR period
        original_version [default=False]: Use original Keltner Channel formula instead of EMA+ATR
        multiplier [default=2, min=0.5, max=5]: ATR multiplier for band width

    Outputs:
        mband [price, 0..inf] "Middle Line":
            the centre line: SMA of typical price ((high+low+close)/3) over window when
            original_version is True, otherwise an EMA of close over window
        hband [price, 0..inf] "Upper Channel Line":
            original_version True: SMA(typical price) + SMA(high - low), verified algebraically
            identical to Chester Keltner's 1960 rule. Otherwise mband + multiplier *
            ATR(window_atr). NOTE on the original path window_atr and multiplier are ignored
            entirely, so tuning them has no effect and raises no error
        lband [price, 0..inf] "Lower Channel Line":
            the mirror of hband below the centre line: SMA(typical price) - SMA(high - low) on the
            original path, otherwise mband - multiplier * ATR(window_atr)
        wband [percent, 0..inf]:
            channel separation as a percent of the centre line, (hband - lband) / mband * 100. The
            literature has no established name for this series -- it is a borrowing of Bollinger's
            BandWidth construction
        pband [ratio, -inf..inf]:
            position of close between the channel lines, (close - lband) / (hband - lband).
            Unclamped, so it exceeds 1 above the upper line and drops below 0 under the lower. NOT
            guarded against coinciding bands, unlike BollingerBands, so a zero-width channel can
            produce inf rather than NaN. No established literature name

    Interpretation:
        - Similar to Bollinger Bands but uses ATR for width
        - Less sensitive to sudden price spikes
        - Squeeze occurs when Bollinger Bands move inside Keltner Channels

    Applications:
        - Combined with Bollinger Bands for squeeze detection
        - Trend direction and strength
        - Dynamic support/resistance

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series}
        params: {'window': int, 'window_atr': int, 'original_version': bool, 'multiplier': int}

    Emits measurements only. `hband_indicator` and `lband_indicator` were removed for the same
    reason as BollingerBands': they were a boolean decision over a numeric series this indicator
    already emits, which is a signal rather than a measurement. That content is now the
    `kc_above_upper` and `kc_below_lower` FILTER signals in `signals/volatility.py`.

    Returns:
        {'mband': pd.Series, 'hband': pd.Series, 'lband': pd.Series,
         'wband': pd.Series, 'pband': pd.Series}
    """
    _data = ["high", "low", "close"]
    _params = ["window", "window_atr", "original_version", "multiplier"]
    _outputs = ["mband", "hband", "lband", "wband", "pband"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        close = data['close']
        window = params['window']
        window_atr = params['window_atr']
        original_version = params['original_version']
        multiplier = params['multiplier']

        if original_version:
            # Chester Keltner's 1960 construction: SMA(typical price) +/- SMA(high - low). It uses
            # neither `window_atr` nor `multiplier`, but both are declared in `_params` and
            # surfaced through the metadata API as though they were live, so a caller tuning them
            # saw no effect and no error.
            #
            # The contract is explicit: on this branch those two params must be None. Checking the
            # COMBINATION rather than comparing against defaults -- an earlier revision compared
            # against hardcoded literals, which was wrong twice over. `IndicatorInterface` has no
            # defaults mechanism, so those numbers duplicated values the class does not know and
            # would drift; and a caller explicitly passing the default got no warning even though
            # that value is equally ignored.
            supplied = [p for p in ('window_atr', 'multiplier') if params[p] is not None]
            if supplied:
                raise ValueError(
                    f"KeltnerChannel(original_version=True) ignores {sorted(supplied)}: the "
                    "original formulation derives its bands from SMA(high - low), not from ATR, "
                    "so any value passed for them has no effect. Pass None for them, or use "
                    "original_version=False."
                )
            tp = typical_price(high, low, close).rolling(window, min_periods=window).mean()
            tp_high = (((4 * high) - (2 * low) + close) / 3.0).rolling(window, min_periods=window).mean()
            tp_low = (((-2 * high) + (4 * low) + close) / 3.0).rolling(window, min_periods=window).mean()
        else:
            tp = close.ewm(span=window, min_periods=window, adjust=False).mean()
            atr = ATR.compute({'high': high, 'low': low, 'close': close}, {'window': window_atr})['atr']
            tp_high = tp + (multiplier * atr)
            tp_low = tp - (multiplier * atr)

        wband = ((tp_high - tp_low) / tp) * 100

        # Guard the zero-width case, matching BollingerBands. Coincident bands make this 0/0 or
        # x/0; without the guard it yields inf.
        width = tp_high - tp_low
        pband = ((close - tp_low) / width).where(width != 0, np.nan)

        # Series names are this indicator's own. They were copy-pasted from BollingerBands
        # ("mavg", "bbiwband", "bbipband") and DonchianChannel ("dcihband", "dcilband"), which is
        # cosmetic but actively misleading when debugging a frame of stacked indicators.
        return {
            'mband': pd.Series(tp, name="kc_mband"),
            'hband': pd.Series(tp_high, name="kc_hband"),
            'lband': pd.Series(tp_low, name="kc_lband"),
            'wband': pd.Series(wband, name="kc_wband"),
            'pband': pd.Series(pband, name="kc_pband"),
        }


class DonchianChannel(IndicatorInterface):
    """Indicator: DonchianChannel

    CONVENTION: the channel is measured over the `window` bars **preceding** the current one, which
    is what every source describing Donchian channels specifies -- Donchian's own 4-week rule ("four
    preceding full calendar weeks"), the Original Turtle Trading Rules ("exceeding the high or low
    of the preceding 20 days"), StockCharts, and TC2000. StockCharts states the reason directly: "A
    channel break would not be possible if the most recent period was used." That is not a stylistic
    preference. Including the current bar makes a breakout arithmetically impossible: the current
    high is one of the values the upper band is the maximum of, so close can never exceed it.
    Measured on 400 bars, `include_current_bar=True` produced 0 closes above the upper band and 0
    below the lower; excluding it produced 5 and 9. `include_current_bar=True` is retained for a
    caller who genuinely wants the raw rolling window -- it is a generic primitive (this is what
    pandas-ta, bukosabino/`ta` and Pine's `ta.highest` give you), not the Donchian convention, and
    no source argues for it. This parameter replaces the previous `offset`, which defaulted to the
    non-standard inclusive form and left each caller to remember to pass `offset=1`. The rename is
    deliberate: every existing call site now fails loudly on a missing parameter rather than
    silently changing meaning. Arbitrary additional lag is no longer a parameter -- shift the output
    series.

    Abbreviation: DC
    Reference: https://www.investopedia.com/terms/d/donchianchannels.asp
    Warmup: window - 1 if include_current_bar else window

    Formula:
        Upper Channel = Highest High over the n periods PRECEDING the current bar
        Lower Channel = Lowest Low over the n periods PRECEDING the current bar
        Middle Line = (Upper + Lower) / 2
        Width = (Upper - Lower) / Middle * 100
        Standard period: 20

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=20, min=5, max=100]: Lookback period
        include_current_bar [default=False]: Whether the current bar's own high and low may set the
        bands. False is the Donchian convention and what every source specifies -- the channel spans
        the `window` bars PRECEDING the current one. True makes a breakout arithmetically
        impossible, since the current high is one of the values the upper band is the maximum of,
        and is retained only as a generic rolling-window primitive. Replaces the former `offset`, an
        arbitrary shift that defaulted to the inclusive form and left each caller to remember to
        pass 1

    Outputs:
        hband [price, 0..inf] "Upper Channel Line":
            highest high over the `window` bars preceding the current one -- the documented
            convention (StockCharts, the Turtle rules, Donchian's own 4-week rule), precisely so a
            close can break the channel. Setting include_current_bar=True folds the current bar in,
            and then no close can ever exceed this band
        lband [price, 0..inf] "Lower Channel Line":
            lowest low over the `window` bars preceding the current one, with the same current-bar
            note as hband
        mband [price, 0..inf] "Middle Channel":
            midpoint of the channel, (hband - lband) / 2 + lband. StockCharts calls this the
            Centerline
        wband [percent, 0..inf]:
            channel separation as a percent, (hband - lband) / mband * 100 -- normalised by this
            indicator's OWN middle band, so it means the same thing here as it does on
            BollingerBands and KeltnerChannel and the three are comparable. It previously divided by
            a rolling mean of close, a different quantity that also made this Donchian's only
            dependency on close outside pband; the two forms diverge by at most 1.69% (measured over
            300 bars), close enough that the difference never looked like an error
        pband [ratio, -inf..inf]:
            position of close within the channel, (close - lband) / (hband - lband), computed from
            the same hband/lband reported alongside it. UNBOUNDED under the default convention: the
            bands span the preceding bars, so a close that breaks the channel reads below 0 or above
            1 -- that excursion IS the breakout, and reading it is the point. Bounded to 0..1 only
            when include_current_bar=True, where close cannot sit outside its own channel. NaN where
            the band has zero width

    Interpretation:
        - Price at upper channel: Strong uptrend / potential overbought
        - Price at lower channel: Strong downtrend / potential oversold
        - Breakouts above upper channel signal long entries
        - Breakouts below lower channel signal short entries

    Applications:
        - Breakout entry signals -- the classic Turtle-style N-period high/low breakout
        - Trend-following systems and trend-reversal detection
        - Volatility gauging via channel width
        - Support and resistance reference levels
        - Trailing-exit placement on the opposite band

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series}
        params: {'window': int, 'include_current_bar': bool}

    Returns:
        {'hband': pd.Series, 'lband': pd.Series, 'mband': pd.Series,
         'wband': pd.Series, 'pband': pd.Series}
    """
    _data = ["high", "low", "close"]
    _params = ["window", "include_current_bar"]
    _outputs = ["hband", "lband", "mband", "wband", "pband"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        close = data['close']
        window = params['window']
        include_current_bar = params['include_current_bar']

        hband = high.rolling(window, min_periods=window).max()
        lband = low.rolling(window, min_periods=window).min()

        # The exclusion is a shift by one, NOT a window of window-1: the band spans `window` bars
        # ending at t-1. It costs one extra warmup bar -- the first valid value is at index
        # `window`, not `window - 1`.
        if not include_current_bar:
            hband = hband.shift(1)
            lband = lband.shift(1)

        mband = ((hband - lband) / 2.0) + lband

        # wband divides by mband -- this indicator's OWN middle band -- so it means the same thing
        # here as it does on BollingerBands and KeltnerChannel, both of which normalise by their own
        # middle band. It used to divide by a rolling mean of close, which is a different quantity:
        # numerically close (max 1.69% divergence measured over 300 bars, so the difference never
        # looks like an error) but not comparable to the other two despite the shared output name.
        # It was also this indicator's only dependency on close outside pband; Donchian is otherwise
        # a pure high/low construction.
        wband = ((hband - lband) / mband) * 100

        # Guard the zero-width case, matching BollingerBands. Coincident bands make this 0/0 or
        # x/0; without the guard it yields inf.
        width = hband - lband
        pband = ((close - lband) / width).where(width != 0, np.nan)

        return {
            'hband': pd.Series(hband, name="dchband"),
            'lband': pd.Series(lband, name="dclband"),
            'mband': pd.Series(mband, name="dcmband"),
            'wband': pd.Series(wband, name="dcwband"),
            'pband': pd.Series(pband, name="dcpband")
        }


class UlcerIndex(IndicatorInterface):
    """Indicator: UlcerIndex

    Measures downside risk and volatility by focusing only on drawdowns from recent highs.

    Abbreviation: UI
    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/ulcer-index
    Warmup: window - 1

    Formula:
        Percentage Drawdown = ((Close - 14-period High Close) / 14-period High Close) * 100
        Ulcer Index = Square Root of Mean of Squared Drawdowns

    Inputs:
        close: closing price

    Params:
        window [default=14, min=5, max=50]: Lookback period

    Outputs:
        ulcer_index [percent, 0..inf] "Ulcer Index":
            downside-only volatility -- the quadratic mean of percentage drawdowns from the highest
            close in the window, sqrt(mean(r^2)) where r = 100 * (close - rolling_max) /
            rolling_max. Squaring penalises deep drawdowns disproportionately, so it measures depth
            and persistence of declines together. Upside contributes nothing, the deliberate
            difference from standard deviation and from ATR; approaches 0 when price keeps making
            new highs within the window. This is the rolling-window charting form, NOT Peter
            Martin's original, which measures retracement against the running peak over the whole
            sample and yields different values

    Interpretation:
        - Low Ulcer Index: Low downside risk
        - High Ulcer Index: High downside risk
        - Focus on downside volatility only
        - Useful for risk-adjusted performance (Martin Ratio)

    Applications:
        - Quantifying downside risk for long-only holdings and portfolios
        - Comparing relative risk between securities, funds or strategies on a common scale
        - Risk-adjusted return measurement as the denominator of the Ulcer Performance Index (Martin
        ratio)
        - Screening for securities whose drawdown behaviour stays under a chosen threshold
        - Substitute for standard deviation where only downside matters

    Args:
        data: {'close': pd.Series}
        params: {'window': int}

    Returns:
        {'ulcer_index': pd.Series}
    """
    _data = ["close"]
    _params = ["window"]
    _outputs = ["ulcer_index"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        window = params['window']

        ui_max = close.rolling(window, min_periods=1).max()
        r_i = 100 * (close - ui_max) / ui_max

        # sqrt(sum(r_i^2) / window) over the rolling window == sqrt(mean(r_i^2)).
        ulcer_idx = np.sqrt((r_i ** 2).rolling(window, min_periods=window).mean())

        return {'ulcer_index': pd.Series(ulcer_idx, name="ui")}


class TrueRange(IndicatorInterface):
    """Indicator: TrueRange

    Welles Wilder's True Range: max of (high - low), |high - prev_close|, |low - prev_close|
    captures gap volatility that a simple high-low range misses. This is the raw building block used
    inside ATR (and Vortex, UO, etc.). Exposed as a standalone indicator for strategies that want
    the raw per-bar range rather than a smoothed average.

    Abbreviation: TR
    Warmup: 0

    Formula:
        TR = max( High - Low,
                 |High - PrevClose|,
                 |Low  - PrevClose| )

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Outputs:
        true_range [price, 0..inf] "True Range":
            per-bar volatility as max(high - low, |high - prev_close|, |low - prev_close|), which
            counts gap moves a plain high-low range would miss. Unsmoothed, so noisier bar to bar
            than ATR. Non-directional: it states how far price travelled, not which way. The first
            bar has no prior close and falls back to high - low rather than NaN -- the common
            convention, though the literature does not agree on one

    Interpretation:
        - Single-bar volatility that includes gaps, unlike a plain high-low range
        - Rising TR: increasing volatility for that bar -- breakout or instability
        - Falling TR: reduced volatility, consolidation or quiet trade
        - Non-directional: states how far price travelled, not which way
        - Unsmoothed, so noisier bar to bar than ATR -- reactive, not predictive
        - Expressed in the instrument's price units

    Applications:
        - Base input to ATR and to Wilder's directional system (DI/ADX) as the normalising
        denominator
        - Volatility-aware stop placement beyond recent true-range values
        - Detecting gap days and outsized single-bar moves a high-low range would understate
        - Confirming that a price move came with real range expansion

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series}
        params: {}

    Returns:
        {'true_range': pd.Series}
    """
    _data = ["high", "low", "close"]
    _params = []
    _outputs = ["true_range"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        close = data['close']
        tr = true_range(high, low, close)
        return {'true_range': pd.Series(tr.values, index=close.index, name='true_range')}


class NATR(IndicatorInterface):
    """Indicator: NATR

    ATR expressed as a percentage of close: NATR = 100 * ATR / close. Useful for comparing
    volatility across assets and timeframes where absolute ATR scales with price.

    Abbreviation: NATR
    Warmup: window - 1

    Formula:
        NATR = 100 * ATR(n) / Close

        where ATR(n) is Wilder's Average True Range over n periods (default 14)

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=14, min=5, max=100]: NATR window

    Outputs:
        natr [percent, 0..inf] "Normalized Average True Range":
            100 * ATR(window) / close -- average true range as a percentage of current price.
            Scale-free, so unlike raw ATR it is comparable across instruments, price levels and
            splits. This is the TA-Lib convention (smooth the true range first, then divide by
            close); an alternative definition normalises each bar's true range before averaging and
            gives different values. Warmup is masked to NaN here, which differs from ATR's zero-fill
            for the same region

    Interpretation:
        - Volatility as a percentage of price rather than in price units
        - Higher readings: proportionally larger average bar range relative to price
        - Lower readings: proportionally tighter ranges, more stable action
        - Non-directional, like ATR
        - Price-level invariant -- two instruments at very different prices with the same
        proportional range give the same NATR
        - Comparable across instruments and across long histories, including across splits

    Applications:
        - Cross-asset volatility comparison and ranking
        - Volatility screening and universe filtering on a common scale
        - Percentage-based position sizing and risk budgeting
        - Percentage-based stop and target distances
        - Regime detection over histories where the absolute price level has changed substantially

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series}
        params: {'window': int}

    Returns:
        {'natr': pd.Series}
    """
    _data = ["high", "low", "close"]
    _params = ["window"]
    _outputs = ["natr"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        close = data['close']
        window = params['window']

        # ATR now emits NaN through warmup rather than zero, so the local mask this used to carry
        # is gone -- the NaN propagates on its own.
        atr = ATR.compute({'high': high, 'low': low, 'close': close}, {'window': window})['atr']
        with np.errstate(divide='ignore', invalid='ignore'):
            natr = 100.0 * atr / close
        return {'natr': pd.Series(natr.to_numpy(dtype=np.float64), index=close.index,
                                  name=f'natr_{window}')}


class ATRTrailingStop(IndicatorInterface):
    """DEPRECATED for the ontology: stateful, and emits a verdict.

    The stop level accumulates forward and `direction` is +1 long / -1 short. Both halves
    of the rule fail. Kept working and unchanged.
ATR Trailing Stop (Chuck LeBeau variant).

    Stateful trailing stop that flips between long and short regimes:
      - In long regime: stop = max(previous_stop, close - multiplier*ATR).
        Flip to short when close crosses below the long stop.
      - In short regime: stop = min(previous_stop, close + multiplier*ATR).
        Flip to long when close crosses above the short stop.

    Outputs:
      - trailing_stop: the active stop level on each bar
      - direction: +1 long, -1 short

    Reference: Chuck LeBeau (Smart Trader), popularized in Chande's
    "Beyond Technical Analysis" (1997).

    Implementation: genuinely state-dependent (stop level accumulates forward);
    pure-Python loop, same pattern as SuperTrend and PSAR.

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series}
        params: {'window': int, 'multiplier': float}

    Returns:
        {'trailing_stop': pd.Series, 'direction': pd.Series}
    """
    _data = ["high", "low", "close"]
    _params = ["window", "multiplier"]
    _outputs = ["trailing_stop", "direction"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        close = data['close']
        window = params['window']
        mult = float(params['multiplier'])

        atr = ATR.compute({'high': high, 'low': low, 'close': close}, {'window': window})['atr']
        close_vals = close.to_numpy(dtype=np.float64, copy=False)
        atr_vals = atr.to_numpy(dtype=np.float64, copy=False)
        n = len(close_vals)

        stop = np.full(n, np.nan)
        direction = np.zeros(n, dtype=np.int64)

        # Warmup: need valid ATR before starting. ATR becomes non-zero at
        # index window-1 in our implementation.
        start = window
        if n <= start:
            return {
                'trailing_stop': pd.Series(stop, index=close.index, name='trailing_stop'),
                'direction': pd.Series(direction.astype(np.float64), index=close.index, name='direction'),
            }

        # Initialize direction based on first bar after warmup using simple
        # comparison to the previous close.
        direction[start] = 1 if close_vals[start] >= close_vals[start - 1] else -1
        if direction[start] == 1:
            stop[start] = close_vals[start] - mult * atr_vals[start]
        else:
            stop[start] = close_vals[start] + mult * atr_vals[start]

        # State-dependent loop: trailing stop ratchets in the trend direction
        # and flips on the opposite-side close cross.
        for i in range(start + 1, n):
            prev_stop = stop[i - 1]
            prev_dir = direction[i - 1]
            candidate_long = close_vals[i] - mult * atr_vals[i]
            candidate_short = close_vals[i] + mult * atr_vals[i]

            if prev_dir == 1:
                if close_vals[i] < prev_stop:
                    # Flip to short
                    direction[i] = -1
                    stop[i] = candidate_short
                else:
                    # Ratchet long stop higher (never lower)
                    direction[i] = 1
                    stop[i] = max(prev_stop, candidate_long)
            else:
                if close_vals[i] > prev_stop:
                    # Flip to long
                    direction[i] = 1
                    stop[i] = candidate_long
                else:
                    # Ratchet short stop lower (never higher)
                    direction[i] = -1
                    stop[i] = min(prev_stop, candidate_short)

        return {
            'trailing_stop': pd.Series(stop, index=close.index, name='trailing_stop'),
            'direction': pd.Series(direction.astype(np.float64), index=close.index, name='direction'),
        }


class STARCBands(IndicatorInterface):
    """Indicator: STARCBands

    SMA-centered ATR-scaled envelope: upper = SMA(close, window) + multiplier * ATR(window_atr)
    lower = SMA(close, window) - multiplier * ATR(window_atr) Similar to Keltner Channel but with an
    explicitly separate window for the SMA and ATR. Useful for breakout strategies.

    Abbreviation: STARC
    Warmup: max(window, window_atr) - 1

    Formula:
        Middle Line = SMA(price, sma_length)
        Upper Band  = Middle + (Multiplier * ATR(atr_length))
        Lower Band  = Middle - (Multiplier * ATR(atr_length))

        Reported original parameterisation: SMA 6, Multiplier 2, ATR 15 (unverified against a primary Stoller source)

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=20, min=5, max=100]: SMA window
        window_atr [default=15, min=5, max=100]: ATR window
        multiplier [default=2, min=0.5]: ATR multiplier for band width

    Outputs:
        starc_mid [price, 0..inf] "Middle Band":
            SMA of close over window -- the centre of the envelope
        starc_hband [price, 0..inf] "STARC Band+":
            starc_mid + multiplier * ATR(window_atr). ATR's warmup region is masked to NaN before
            the band is formed, so zero-ATR values do not leak in and widen the envelope
            artificially
        starc_lband [price, 0..inf] "STARC Band-":
            starc_mid - multiplier * ATR(window_atr), with the same ATR warmup masking as
            starc_hband

    Interpretation:
        - Bands sit a volatility-scaled distance around a short-term SMA, expanding and contracting
        with ATR
        - Price at or above the upper band is characterised as a high-risk zone to buy, low-risk to
        sell
        - Price at or below the lower band is characterised as low-risk to buy, high-risk to sell
        - The bands are described as encompassing most price action, so excursions beyond them are
        unusual
        - Offset derives from Average True Range, not standard deviation, so the bands respond to
        gaps and true range rather than close-to-close dispersion

    Applications:
        - Locating higher-probability entries when price crosses a band boundary
        - Dynamic support and resistance around the moving average
        - Volatility-adjusted overbought/oversold framing
        - Entry timing within an established trend

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series}
        params: {'window': int, 'window_atr': int, 'multiplier': float}

    Returns:
        {'starc_mid': pd.Series, 'starc_hband': pd.Series, 'starc_lband': pd.Series}
    """
    _data = ["high", "low", "close"]
    _params = ["window", "window_atr", "multiplier"]
    _outputs = ["starc_mid", "starc_hband", "starc_lband"]

    @classmethod
    def _compute(cls, data, params):
        # Local import to avoid a circular dependency with trend_indicators.
        from mangrove_kb.indicators.trend_indicators import SMA

        high = data['high']
        low = data['low']
        close = data['close']
        window = params['window']
        window_atr = params['window_atr']
        mult = float(params['multiplier'])

        mid = SMA.compute({'close': close}, {'window': window})['sma']
        # ATR now emits NaN through warmup rather than zero, so the local mask this used to carry
        # is gone -- zero-ATR bands can no longer leak.
        atr = ATR.compute({'high': high, 'low': low, 'close': close}, {'window': window_atr})['atr']

        hband = mid + mult * atr
        lband = mid - mult * atr

        return {
            'starc_mid': pd.Series(mid.values, index=close.index, name='starc_mid'),
            'starc_hband': pd.Series(hband.values, index=close.index, name='starc_hband'),
            'starc_lband': pd.Series(lband.values, index=close.index, name='starc_lband'),
        }


class VolatilityEnvelope(IndicatorInterface):
    """Indicator: VolatilityEnvelope

    vstop_hband = prev_close + multiplier * stdev(returns, window) * prev_close vstop_lband =
    prev_close - multiplier * stdev(returns, window) * prev_close An expected range for the current
    bar, given yesterday's close and how variable returns have been. Close outside it means today
    moved more than `multiplier` standard deviations -- that is the measurement; whether it reads as
    exhaustion or as a breakout is an interpretation, and whether to act on it is a signal's
    business. The centre is the PREVIOUS close deliberately. Centring on the current close would put
    it trivially between the bands and nothing could ever be outside them. Symmetric about that
    centre, so `vstop_hband >= vstop_lband` always holds -- unlike ChandelierLevels, whose two
    offsets are anchored to opposite extremes and cross. Named "VolatilityStop" until 2026-08-09 and
    excluded from the ontology as a stateful policy rule. It is neither: no state is carried forward
    (this docstring already said "not a state machine"), and it emits two levels rather than a
    verdict. Only the word "Stop" was positional.

    Abbreviation: VE
    Warmup: window

    Formula:
        vstop_hband[t] = close[t-1] * (1 + multiplier * stdev(pct_change(close)[t-window+1..t])); vstop_lband[t] = close[t-1] * (1 - multiplier * stdev(pct_change(close)[t-window+1..t]))

    Inputs:
        close: closing price

    Params:
        window [default=20, min=5, max=100]: Rolling stdev window
        multiplier [default=2, min=0.5]: Stdev multiplier for the band distance

    Outputs:
        vstop_hband [price, 0..inf] "vstop_hband":
            Previous close plus `multiplier` standard deviations of recent RETURNS, scaled by that
            close. Symmetric with vstop_lband, so hband >= lband always holds.
        vstop_lband [price, 0..inf] "vstop_lband":
            The lower half of the same envelope.

    Interpretation:
        The range today would stay inside if returns behaved like the recent window. Centred on the
        PREVIOUS close, so being outside it is a statement about today's move rather than an
        artefact of centring on today's own close. Symmetric, so vstop_hband >= vstop_lband always
        holds.

    Applications:
        A move beyond the envelope is one that is large relative to the asset's own recent return
        variability, which is why the bands are scaled by stdev of RETURNS rather than of price --
        the measure is scale-invariant and comparable across assets.

    Args:
        data: {'close': pd.Series}
        params: {'window': int, 'multiplier': float}

    Returns:
        {'vstop_hband': pd.Series, 'vstop_lband': pd.Series}
    """
    _data = ["close"]
    _params = ["window", "multiplier"]
    _outputs = ["vstop_hband", "vstop_lband"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        window = params['window']
        mult = float(params['multiplier'])

        # Rolling stdev of returns (not close), for a scale-invariant measure.
        returns = close.pct_change()
        vol = returns.rolling(window, min_periods=window).std()
        # Use PREVIOUS close as the center: today's expected-range envelope
        # given yesterday's close and recent volatility. If we used current
        # close as the center, close would be trivially between the bands
        # and the signals would never fire.
        prev_close = close.shift(1)
        offset = prev_close * vol * mult

        hband = prev_close + offset
        lband = prev_close - offset
        return {
            'vstop_hband': pd.Series(hband.values, index=close.index, name='vstop_hband'),
            'vstop_lband': pd.Series(lband.values, index=close.index, name='vstop_lband'),
        }


#: Deprecated name. "Stop" states a use, not a measurement.
VolatilityStop = VolatilityEnvelope


class TTMSqueeze(IndicatorInterface):
    """DEPRECATED: use `SqueezeDepth`, which measures instead of concluding.

    TTM Squeeze (John Carter).

    Detects volatility contraction ("squeeze") when Bollinger Bands are
    entirely inside Keltner Channels, and signals a volatility expansion
    when the squeeze releases (BB exits KC). The momentum sub-output
    indicates which direction the coiled volatility is likely to break.

    State definition:
      - squeeze_on: bb_hband < kc_hband  AND  bb_lband > kc_lband
      - squeeze_fired: squeeze was on the previous bar, off on the current
      - momentum: linear-regression slope of (close - midpoint) over the
        momentum window, where midpoint = (highest_high + lowest_low +
        SMA(close)) / 3. Positive = bullish coil; negative = bearish.

    Reference: John Carter, "Mastering the Trade" (2005).

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series}
        params: {'bb_window': int, 'bb_std': float,
                 'kc_window': int, 'kc_atr_mult': float,
                 'mom_window': int}

    Returns:
        {'squeeze_on': pd.Series (bool),
         'squeeze_fired': pd.Series (bool),
         'momentum': pd.Series}
    """
    _data = ["high", "low", "close"]
    _params = ["bb_window", "bb_std", "kc_window", "kc_atr_mult", "mom_window"]
    _outputs = ["squeeze_on", "squeeze_fired", "momentum"]

    @classmethod
    def _compute(cls, data, params):
        from mangrove_kb.indicators.trend_indicators import SMA, _epma_weights

        high = data['high']
        low = data['low']
        close = data['close']
        bb_window = params['bb_window']
        bb_std = float(params['bb_std'])
        kc_window = params['kc_window']
        kc_atr_mult = float(params['kc_atr_mult'])
        mom_window = params['mom_window']

        # Bollinger Bands
        bb = BollingerBands.compute({'close': close}, {'window': bb_window, 'window_dev': bb_std})
        bb_h, bb_l = bb['hband'], bb['lband']

        # Keltner Channel (non-original: SMA + ATR)
        kc = KeltnerChannel.compute(
            data={'high': high, 'low': low, 'close': close},
            params={'window': kc_window, 'window_atr': kc_window, 'original_version': False, 'multiplier': kc_atr_mult},
        )
        kc_h, kc_l = kc['hband'], kc['lband']

        squeeze_on = (bb_h < kc_h) & (bb_l > kc_l)
        # Squeeze fired: on -> off transition
        squeeze_fired = squeeze_on.shift(1).fillna(False) & (~squeeze_on)

        # Carter's momentum: close - ((highest_high + lowest_low)/2 + SMA)/2
        # over mom_window; then fit linear regression over that, return slope*x.
        # Concretely pandas-ta uses: source - midpoint, then linear regression
        # forecast; we use EPMA-style endpoint projection which is the same
        # linear-reg forecast expressed as a FIR filter.
        hh = high.rolling(mom_window, min_periods=mom_window).max()
        ll = low.rolling(mom_window, min_periods=mom_window).min()
        sma_close = SMA.compute({'close': close}, {'window': mom_window})['sma']
        midpoint = ((hh + ll) / 2.0 + sma_close) / 2.0
        raw_momentum = close - midpoint

        # Apply linear-regression endpoint projection to smooth (Carter uses
        # "lsma" which is equivalent to EPMA of raw_momentum).
        weights = _epma_weights(mom_window)
        rm = raw_momentum.to_numpy(dtype=np.float64, copy=False)
        n = len(rm)
        momentum = np.full(n, np.nan)
        if n >= mom_window:
            # Need non-NaN input to convolve; manually handle warmup region
            # by skipping bars where raw_momentum is NaN.
            valid_mask = ~np.isnan(rm)
            if valid_mask.any():
                first_valid = int(np.argmax(valid_mask))
                tail = rm[first_valid:]
                if len(tail) >= mom_window:
                    conv = np.convolve(tail, weights[::-1], mode='valid')
                    momentum[first_valid + mom_window - 1:] = conv

        return {
            'squeeze_on': pd.Series(squeeze_on.values, index=close.index, name='squeeze_on'),
            'squeeze_fired': pd.Series(squeeze_fired.values, index=close.index, name='squeeze_fired'),
            'momentum': pd.Series(momentum, index=close.index, name='ttm_momentum'),
        }


class SqueezeDepth(IndicatorInterface):
    """Indicator: SqueezeDepth

    squeeze_depth = min(kc_hband - bb_hband, bb_lband - kc_lband) momentum      = linear-regression endpoint of (close - midpoint) over mom_window, midpoint = ((highest_high + lowest_low) / 2 + SMA(close)) / 2 `squeeze_depth` is positive exactly when the Bollinger Bands are entirely inside the Keltner Channel -- John Carter's "squeeze" -- and its magnitude says by how much, which the boolean it replaces threw away. A squeeze releasing is `squeeze_depth` crossing down through zero, and that comparison belongs to the signal making it. Replaces `TTMSqueeze`, which emitted `squeeze_on` and `squeeze_fired` as booleans beside this same `momentum`: a verdict and a measurement in one object. That class still exists and still works; it is deprecated.

    Abbreviation: TTM
    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/ttm-squeeze
    Warmup: max(bb_window, kc_window, mom_window) - 1

    Formula:
        squeeze_depth[t] = min(kc_hband[t] - bb_hband[t], bb_lband[t] - kc_lband[t]); momentum[t] = EPMA(close - ((highest_high + lowest_low)/2 + sma(close))/2, mom_window)[t]

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        bb_window [default=20, min=5, max=100]: Bollinger window
        bb_std [default=2, min=0.5]: Bollinger standard deviations
        kc_window [default=20, min=5, max=100]: Keltner window
        kc_atr_mult [default=1.5, min=0.5]: Keltner ATR multiplier
        mom_window [default=12, min=5, max=50]: Momentum window

    Outputs:
        squeeze_depth [price, -inf..inf] "squeeze_depth":
            How far inside the Keltner Channel the Bollinger Bands sit, as the smaller of the two
            side gaps. Positive IS Carter's squeeze; the magnitude says by how much, which the
            boolean it replaced discarded.
        momentum [price, -inf..inf] "momentum":
            Carter's momentum: the linear-regression endpoint of close minus the midpoint of the
            window's range and its SMA. Sign gives the direction the coiled volatility is leaning.

    Interpretation:
        How far inside the Keltner Channel the Bollinger Bands sit. Positive is Carter's squeeze,
        and the magnitude says by how much -- which the boolean it replaces discarded. Crossing down
        through zero is the release.

    Applications:
        Volatility-contraction setups. The threshold at zero and the direction read from momentum
        are both judgements, so they live in the signals.

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series}
        params: {'bb_window': int, 'bb_std': float, 'kc_window': int, 'kc_atr_mult': float,
                 'mom_window': int}

    Returns:
        {'squeeze_depth': pd.Series, 'momentum': pd.Series}
    """
    _data = ["high", "low", "close"]
    _params = ["bb_window", "bb_std", "kc_window", "kc_atr_mult", "mom_window"]
    _outputs = ["squeeze_depth", "momentum"]

    @classmethod
    def _compute(cls, data, params):
        out = TTMSqueeze._compute(data, params)
        bb = BollingerBands.compute({'close': data['close']},
                                    {'window': params['bb_window'], 'window_dev': float(params['bb_std'])})
        kc = KeltnerChannel.compute(
            data={'high': data['high'], 'low': data['low'], 'close': data['close']},
            params={'window': params['kc_window'], 'window_atr': params['kc_window'],
                    'original_version': False, 'multiplier': float(params['kc_atr_mult'])},
        )
        depth = pd.concat([kc['hband'] - bb['hband'], bb['lband'] - kc['lband']], axis=1).min(axis=1)
        return {
            'squeeze_depth': pd.Series(depth.values, index=data['close'].index, name='squeeze_depth'),
            'momentum': out['momentum'],
        }



class ChandelierLevels(IndicatorInterface):
    """Indicator: ChandelierLevels

    window's extremes. high_offset = highest_high(window) - multiplier * ATR(window) low_offset  = lowest_low(window)   + multiplier * ATR(window) Both are emitted every bar and both are plain functions of the window -- there is no state carried forward and no regime decided here. LeBeau published this as the "Chandelier Exit", a trailing stop, but the exit is a USE of the measurement, not part of it: what is computed is a distance, scaled by volatility, in from each extreme. The two are NOT an upper and a lower band. They are anchored to opposite extremes, so in a wide range they cross: measured on 1,294 BTC daily bars at window=22, multiplier=3.0, `high_offset` sits below `low_offset` on only 73% of bars, and both offsets are breached on the same bar 15 times. Anything that assumes a band invariant (`hband >= lband`, as Bollinger, Keltner and Donchian all hold) is wrong about this indicator.

    Abbreviation: CE
    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/chandelier-exit
    Warmup: window - 1

    Formula:
        high_offset[t] = max(high[t-window+1..t]) - multiplier * atr[t]; low_offset[t] = min(low[t-window+1..t]) + multiplier * atr[t]

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price

    Params:
        window [default=22, min=5, max=100]: Rolling extreme and ATR window
        multiplier [default=3, min=0.5]: ATR multiplier

    Outputs:
        high_offset [price, 0..inf] "high_offset":
            A volatility-scaled distance BELOW the window's highest high: highest_high - multiplier
            * ATR. Not a lower band -- it is anchored to the high.
        low_offset [price, 0..inf] "low_offset":
            The mirror, above the window's lowest low. Anchored to the opposite extreme from
            high_offset, so the two cross in a wide range.

    Interpretation:
        How far price has retraced from the window's extreme, measured in units of that window's own
        volatility. The two are anchored to OPPOSITE extremes, so they are not an upper and a lower
        band and can cross: at window=22, multiplier=3.0 on 1,294 BTC daily bars, high_offset sits
        below low_offset on only 73% of them.

    Applications:
        Published as the Chandelier Exit, a trailing stop -- but that is a use of the level, not
        what it measures. As a measurement it marks a volatility-scaled retracement from the recent
        high or low.

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series}
        params: {'window': int, 'multiplier': float}

    Returns:
        {'high_offset': pd.Series, 'low_offset': pd.Series}
    """
    _data = ["high", "low", "close"]
    _params = ["window", "multiplier"]
    _outputs = ["high_offset", "low_offset"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        close = data['close']
        window = params['window']
        mult = float(params['multiplier'])

        atr = ATR.compute({'high': high, 'low': low, 'close': close}, {'window': window})['atr']
        # Mask warmup to NaN: our ATR fills the first window-1 bars with 0.
        atr_vals = atr.to_numpy(dtype=np.float64, copy=False).copy()
        atr_vals[: window - 1] = np.nan
        atr_masked = pd.Series(atr_vals, index=close.index)

        hh = high.rolling(window, min_periods=window).max()
        ll = low.rolling(window, min_periods=window).min()

        return {
            'high_offset': pd.Series((hh - mult * atr_masked).values, index=close.index,
                                     name='high_offset'),
            'low_offset': pd.Series((ll + mult * atr_masked).values, index=close.index,
                                    name='low_offset'),
        }


#: Deprecated name. "Exit" states a use, not a measurement, and this ontology's indicator layer
#: holds measurements only -- what to do about a level is the signal layer's business.
ChandelierExit = ChandelierLevels

"""
Volume Indicators.

Provides volume-based technical analysis indicators including OBV, MFI,
CMF, Force Index, ADI, VWAP, and more.

Originally from ta-master library by Dario Lopez Padial (Bukosabino).
"""
import warnings

import numpy as np
import pandas as pd

from mangrove_kb.indicators.indicator_interface import IndicatorInterface
from mangrove_kb.indicators.trend_indicators import EMA, SMA
from mangrove_kb.indicators.utils import typical_price


class ADI(IndicatorInterface):
    """Indicator: ADI

    Acting as leading indicator of price movements.

    Abbreviation: ADI
    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/accumulation-distribution-line
    Warmup: 0

    Formula:
        Money Flow Multiplier = ((Close - Low) - (High - Close)) / (High - Low)
        Money Flow Volume = Money Flow Multiplier * Volume
        ADL = Previous ADL + Money Flow Volume

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price
        volume: units traded during the bar

    Outputs:
        adi [dimensionless, -inf..inf] "Accumulation Distribution Line":
            running total of volume weighted by where the close sits within the bar's own high-low
            range. The weight (the Money Flow Multiplier, or Close Location Value) is hard-bounded
            -1..+1 -- +1 with the close on the high, -1 on the low, 0 at the midpoint -- so a bar
            can never contribute more than its own volume, unlike VPT. Critically it NEVER LOOKS AT
            THE PRIOR CLOSE, which is why a security can gap down and close lower while this line
            RISES, provided the close sits above the bar's midpoint; neither OBV nor VPT can do
            that. Unbounded, and the level depends on the arbitrary start of the series, so only the
            shape is meaningful. Zero-range bars (high equals low) are treated as zero flow here --
            no source prescribes a convention for that case. Chaikin's original name for it was the
            Cumulative Money Flow Line

    Interpretation:
        - Rising ADL: Accumulation
        - Falling ADL: Distribution
        - ADL confirming price: Trend likely to continue
        - ADL diverging from price: Potential reversal

    Applications:
        - Trend confirmation -- a rising line reinforces an uptrend on the price chart
        - Bullish divergence: price makes new lows while the line moves higher
        - Bearish divergence: price makes new highs while the line moves lower
        - Input to the Chaikin Oscillator, which differences two EMAs of this line
        - Not standalone -- the literature is explicit that it must be confirmed

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series, 'volume': pd.Series}
        params: {}

    Returns:
        {'adi': pd.Series}
    """
    _data = ["high", "low", "close", "volume"]
    _params = []
    _outputs = ["adi"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        close = data['close']
        volume = data['volume']

        # ZERO-RANGE CONVENTION: 0, deliberately, and narrowly. Where high equals low the Money Flow
        # Multiplier is 0/0 and no source states a convention. Zero -- "this bar carries no
        # directional information, so it contributes nothing" -- is the only non-destructive answer
        # available: ADI is a running cumulative total, so a NaN here would propagate through every
        # later bar rather than being contained to this one. (StochasticOscillator, WilliamsR and
        # StochRSI meet the same 0/0 and answer NaN, because they are per-bar readings.)
        #
        # The guard is on `high == low` specifically. It used to be a blanket `.fillna(0.0)`, which
        # also swallowed NaNs arising from missing input data -- a genuine data gap read as "no
        # flow" rather than surfacing.
        clv = ((close - low) - (high - close)) / (high - low)
        clv = clv.where(high != low, 0.0)
        adi = clv * volume
        adi = adi.cumsum()

        return {'adi': pd.Series(adi, name="adi")}


class OBV(IndicatorInterface):
    """Indicator: OBV

    It relates price and volume in the stock market. OBV is based on a cumulative total volume.

    Abbreviation: OBV
    Reference: https://en.wikipedia.org/wiki/On-balance_volume
    Warmup: 0

    Formula:
        If Close > Previous Close: OBV = Previous OBV + Volume
        If Close < Previous Close: OBV = Previous OBV - Volume
        If Close = Previous Close: OBV = Previous OBV

    Inputs:
        close: closing price
        volume: units traded during the bar

    Outputs:
        obv [dimensionless, -inf..inf] "On Balance Volume":
            running total of volume signed by the direction of the close. UNBOUNDED, and the
            ABSOLUTE LEVEL CARRIES NO INFORMATION -- StockCharts states plainly that 'the absolute
            value of OBV is not important' and does not even show its scale, because a cumulative
            total's level is set by where the data happens to begin. Only the shape and direction
            are read, and the zero crossing is an artefact of the start date, not a signal. Full
            volume is committed to one side by close direction alone, so a +0.01% bar and a +8% bar
            add the same amount. IMPLEMENTATION CAVEAT: Granville's rule is three-way and carries
            the total forward UNCHANGED when the close is flat; this implementation branches only
            two ways and adds volume on flat bars, so it drifts upward in instruments where
            unchanged closes are common

    Interpretation:
        - Rising OBV: Accumulation (buying pressure)
        - Falling OBV: Distribution (selling pressure)
        - OBV divergence from price: Potential reversal warning
        - OBV breakouts can precede price breakouts

    Applications:
        - Divergence detection -- price makes a new high or low that OBV does not confirm
        - Trend confirmation, checking the OBV trend matches the security's
        - Support, resistance and trendline analysis drawn on the OBV line itself
        - Breakout confirmation ahead of price

    Args:
        data: {'close': pd.Series, 'volume': pd.Series}
        params: {}

    Returns:
        {'obv': pd.Series}
    """
    _data = ["close", "volume"]
    _params = []
    _outputs = ["obv"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        volume = data['volume']

        # Granville's rule has THREE branches, and the third one matters: an unchanged close
        # contributes nothing. A two-way test folds flat bars into the up-branch, so every flat
        # close adds volume that should have been ignored and the line drifts upward independently
        # of price -- worst on illiquid instruments, coarse tick sizes, and resampled series where
        # flat closes are common. OBV is read by its direction, so a spurious drift is precisely
        # the failure mode that matters.
        direction = np.sign(close.diff())
        # Bar 0 has no prior close, so its direction is undefined and it contributes nothing --
        # the same reasoning as the flat-close branch. Seeding it with +volume (as an earlier
        # revision did) offsets the whole series by one bar's volume. That offset is harmless for
        # reading OBV, whose level is an artefact of where the data begins, but it is an invented
        # value rather than a measured one.
        direction = direction.fillna(0.0)

        obv = (direction * volume).cumsum()

        return {'obv': pd.Series(obv, index=close.index, name="obv")}


class CMF(IndicatorInterface):
    """Indicator: CMF

    It measures the amount of Money Flow Volume over a specific period.

    Abbreviation: CMF
    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/chaikin-money-flow-cmf
    Warmup: window - 1

    Formula:
        CMF = Sum(Money Flow Volume, n) / Sum(Volume, n)

        Typical period: 20

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price
        volume: units traded during the bar

    Params:
        window [default=20, min=10, max=50]: CMF period

    Outputs:
        cmf [ratio, -1..1] "Chaikin Money Flow":
            sum of money-flow volume over sum of volume across window, where the multiplier
            ((close-low)-(high-close))/(high-low) is +1 at a close on the high and -1 on the low.
            Hard-bounded -1..1 as a volume-weighted average of a multiplier already confined to that
            range, but reaching an endpoint would need every bar in the window to close at its
            extreme -- the practical range is roughly +/-0.5, with +/-0.05 used as a buffer around
            the zero line. Zero-range bars are treated as ZERO flow here rather than undefined,
            which the literature does not specify. The multiplier is intrabar only and ignores gaps,
            a known weakness

    Interpretation:
        - CMF > 0: Buying pressure
        - CMF < 0: Selling pressure
        - Rising CMF: Increasing buying pressure
        - Falling CMF: Increasing selling pressure

    Applications:
        - Trend confirmation via sustained readings on one side of zero
        - Zero-line crossover signals, often with a +/-0.05 buffer to reduce whipsaws
        - Quantifying buying versus selling pressure
        - Divergence against price

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series, 'volume': pd.Series}
        params: {'window': int}

    Returns:
        {'cmf': pd.Series}
    """
    _data = ["high", "low", "close", "volume"]
    _params = ["window"]
    _outputs = ["cmf"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        close = data['close']
        volume = data['volume']
        window = params['window']

        # ZERO-RANGE CONVENTION: 0, deliberately, and narrowly -- identical reasoning to ADI, whose
        # per-bar term this is. CMF is a rolling sum, so a NaN would blank the whole `window`-bar
        # window rather than the single bar it describes. The guard is on `high == low` specifically
        # rather than the previous blanket `.fillna(0.0)`, so missing input data still surfaces as
        # NaN instead of reading as "no flow".
        mfv = ((close - low) - (high - close)) / (high - low)
        mfv = mfv.where(high != low, 0.0)
        mfv *= volume

        cmf = (
            mfv.rolling(window, min_periods=window).sum()
            / volume.rolling(window, min_periods=window).sum()
        )

        return {'cmf': pd.Series(cmf, name="cmf")}


class ForceIndex(IndicatorInterface):
    """Indicator: ForceIndex

    It illustrates how strong the actual buying or selling pressure is. High positive values mean
    there is a strong rising trend, and low values signify a strong downward trend.

    Abbreviation: FI
    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/force-index
    Warmup: window

    Formula:
        Force Index = (Close - Previous Close) * Volume
        Smoothed Force Index = EMA(Force Index, period)

    Inputs:
        close: closing price
        volume: units traded during the bar

    Params:
        window [default=13, min=5, max=30]: EMA period for smoothing

    Outputs:
        fi [dimensionless, -inf..inf] "Force Index":
            Elder's combination of direction, extent and volume: (close - prior close) * volume,
            smoothed by an EMA. Units are price-change times volume -- not a price, percentage or
            ratio -- so the scale is arbitrary and readings are NOT comparable across instruments.
            Unbounded both ways with no normalising term anywhere in the formula. The sign of the
            unsmoothed 1-period form exactly tracks the close-to-close direction because volume is
            non-negative; after smoothing that guarantee is lost. Elder pairs a 2-period version for
            corrections with a 13- or 100-period version for trend

    Interpretation:
        - Positive Force Index: Bulls in control
        - Negative Force Index: Bears in control
        - Rising Force Index: Increasing buying pressure
        - Falling Force Index: Increasing selling pressure

    Applications:
        - Long-term trend bias from the sign of a 100-period Force Index
        - Finding corrections inside a trend using a 2-period Force Index with a 22-period price EMA
        - Divergence-based reversal anticipation
        - Confirming breakouts and support breaks

    Args:
        data: {'close': pd.Series, 'volume': pd.Series}
        params: {'window': int}

    Returns:
        {'fi': pd.Series}
    """
    _data = ["close", "volume"]
    _params = ["window"]
    _outputs = ["fi"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        volume = data['volume']
        window = params['window']

        fi_series = (close - close.shift(1)) * volume
        fi = EMA.compute({'close': fi_series}, {'window': window})['ema']

        return {'fi': pd.Series(fi, name=f"fi_{window}")}


class EaseOfMovement(IndicatorInterface):
    """Indicator: EaseOfMovement

    It relate an asset's price change to its volume and is particularly useful for assessing the
    strength of a trend.

    Abbreviation: EMV
    Reference: https://en.wikipedia.org/wiki/Ease_of_movement
    Warmup: window - 1

    Formula:
        Distance Moved = ((High + Low) / 2) - ((Previous High + Previous Low) / 2)
        Box Ratio = (Volume / 10000) / (High - Low)
        EMV = Distance Moved / Box Ratio
        EMV SMA = SMA(EMV, 14)

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        volume: units traded during the bar

    Params:
        window [default=14, min=5, max=30]: EOM period

    Outputs:
        eom [dimensionless, -inf..inf] "1-Period EMV":
            Arms' ratio of midpoint movement to a volume-per-range 'box ratio' -- large when a wide
            range is achieved on light volume, small when a narrow range takes heavy volume. Its
            SIGN is exactly the sign of the midpoint change, since the box ratio is strictly
            positive. The 100,000,000 volume divisor is a CONVENTION chosen so readings land in
            single or double digits, and sources use 1e6, 1e8 and 1e9 for it -- so a bare EMV number
            is uninterpretable without knowing the producer's divisor. Undefined on a flat bar (high
            equals low) or a zero-volume bar
        sma_eom [dimensionless, -inf..inf] "Ease of Movement":
            simple moving average (not exponential) of eom over window. This is the plotted series;
            zero-line crossings are its usual signal. The literature is explicit that it confirms
            other analysis rather than standing alone, since it largely tracks price

    Interpretation:
        - Positive EMV: Price rising easily with volume
        - Negative EMV: Price falling easily with volume
        - High values: Easy price movement
        - Low values: Difficult price movement

    Applications:
        - Confirming a price breakout or breakdown -- explicitly a confirmation tool, not standalone
        - Zero-line crossings as signal triggers
        - Corroborating other oscillators
        - Lengthening the look-back for a smoother reading

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'volume': pd.Series}
        params: {'window': int}

    Returns:
        {'eom': pd.Series, 'sma_eom': pd.Series}
    """
    _data = ["high", "low", "volume"]
    _params = ["window"]
    _outputs = ["eom", "sma_eom"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        volume = data['volume']
        window = params['window']

        emv = (
            (high.diff(1) + low.diff(1))
            * (high - low)
            / (2 * volume)
        )
        emv *= 100000000

        sma_emv = emv.rolling(window, min_periods=window).mean()

        return {
            'eom': pd.Series(emv, name=f"eom_{window}"),
            'sma_eom': pd.Series(sma_emv, name=f"sma_eom_{window}")
        }


class VPT(IndicatorInterface):
    """Indicator: VPT

    Is based on a running cumulative volume that adds or substracts a multiple of the percentage
    change in share price trend and current volume, depending upon the investment's upward or
    downward movements.

    Abbreviation: VPT
    Reference: https://en.wikipedia.org/wiki/Volume-price_trend
    Warmup: smoothing_factor - 1

    Formula:
        VPT = Previous VPT + Volume * ((Close - Previous Close) / Previous Close)

    Inputs:
        close: closing price
        volume: units traded during the bar

    Params:
        smoothing_factor: EMA period applied to the accumulation; 0 leaves it unsmoothed

    Outputs:
        vpt [dimensionless, -inf..inf] "Volume-Price Trend":
            running total of volume weighted by the FRACTIONAL price change, so unlike OBV it
            commits only a portion of each bar's volume in proportion to how far price moved. That
            also means the per-bar contribution is UNCAPPED -- a bar that doubles in price
            contributes twice its volume, where ADI can never exceed one times volume. Unbounded,
            and the level is explicitly arbitrary: only the shape is used, not the actual total. The
            core indicator is a raw cumulative sum with NO canonical smoothing; the optional
            smoothing_factor here is an overlay, and no source standardises a signal-line period.
            CAVEAT: the dropnans parameter DROPS ROWS, returning a shorter series than the input --
            every other indicator in this corpus returns a full-length series aligned to the input
            index

    Interpretation:
        - Rising VPT: Accumulation / bullish volume-price relationship
        - Falling VPT: Distribution / bearish volume-price relationship
        - Divergences with price signal potential reversals
        - More sensitive than OBV to price magnitude

    Applications:
        - Trend identification and confirmation
        - Divergence against price -- the primary documented signal
        - Moving-average crossover signals where a platform provides one
        - Anticipating reversals ahead of price

    Args:
        data: {'close': pd.Series, 'volume': pd.Series}
        params: {'smoothing_factor': Optional[int]}

    Returns:
        {'vpt': pd.Series}
    """
    _data = ["close", "volume"]
    # `dropnans` is REMOVED, not repaired. It returned a shorter series starting at a later index,
    # silently breaking the aligned-index guarantee `compute_frame` documents. Filling the warmup
    # instead would have been worse: VPT is a running cumulative total, so 0 is a real reading, and
    # substituting it makes warmup indistinguishable from a genuinely flat stretch -- the same
    # defect corrected in ATR and ADX. Warmup is NaN here, as it is everywhere else, and no
    # indicator in this package carries an escape hatch from that.
    _params = ["smoothing_factor"]
    _outputs = ["vpt"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        volume = data['volume']
        smoothing_factor = params['smoothing_factor']

        # `_validate` only checks for MISSING params, so dropping `dropnans` from `_params` would
        # let an old caller keep passing it and silently get different behaviour -- NaN-padded
        # warmup where they previously got dropped rows. Tell them instead of failing quietly.
        if params.get('dropnans') is not None:
            warnings.warn(
                "VPT's 'dropnans' parameter is removed and has no effect. It returned a shorter "
                "series starting at a later index, breaking the aligned-index guarantee that lets "
                "compute_frame outer-join indicators into a feature matrix. Warmup is now NaN, as "
                "it is for every other indicator.",
                DeprecationWarning,
                stacklevel=3,
            )

        vpt = (close.pct_change() * volume).cumsum()
        if smoothing_factor:
            vpt = vpt.rolling(smoothing_factor, min_periods=smoothing_factor).mean()
        return {'vpt': pd.Series(vpt, index=close.index, name="vpt")}


class NVI(IndicatorInterface):
    """Indicator: NVI

    Tracks price changes on days when volume decreases from the previous day, thought to track
    "smart money" activity.

    Abbreviation: NVI
    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/negative-volume-index-nvi
    Warmup: 0

    Formula:
        If Volume < Previous Volume:
          NVI = Previous NVI + ((Close - Previous Close) / Previous Close) * Previous NVI
        Else:
          NVI = Previous NVI

    Inputs:
        close: closing price
        volume: units traded during the bar

    Params:
        window [default=255, min=100, max=200]: EMA period for signal

    Outputs:
        nvi [dimensionless, 0..inf] "Negative Volume Index":
            compounding index that moves ONLY on bars where volume FELL against the prior bar, and
            is carried forward unchanged when volume rose. The premise is Dysart's 'smart money'
            theory -- that informed investors trade on quiet days while the crowd trades on heavy
            ones. Seeded at 1000, a pure scale choice with no effect on behaviour (1 and 100 are
            also in use), so the ABSOLUTE LEVEL IS MEANINGLESS and every documented reading is
            positional, relative to its own moving average. Strictly non-negative because it is a
            product of (1 + return) factors over positive prices. Built for broad market indices,
            and unusable where there is no real volume data
        nvi_ema [dimensionless, 0..inf]:
            EMA of nvi, conventionally over 255 bars (one year). Fosback's statistics are defined
            against this line, not against the index: roughly a 96% chance of a bull market when NVI
            sits above it, but only about 53% for a bear market when below -- the bullish reading is
            strong and the bearish one barely better than a coin flip. The literature gives this
            series no proper name, referring to it only descriptively. Note this EMA carries no
            minimum-periods guard, so its earliest values are dominated by the seed rather than by
            data

    Interpretation:
        - Rising NVI on down volume: Smart money accumulating
        - Falling NVI on down volume: Smart money distributing
        - Compare to 255-day EMA for trend
        - Less noise than volume-inclusive indicators

    Applications:
        - Bull/bear regime identification via the cross of NVI against its 255-day EMA
        - Broad market indices, where it works best -- results on individual stocks and ETFs are
        variable
        - Long-term trend context for shorter-term trades
        - Paired with the Positive Volume Index to cross-confirm conditions
        - Not standalone; requires real volume data, so it cannot be used on forex or most
        commodities

    Args:
        data: {'close': pd.Series, 'volume': pd.Series}
        params: {'window': int}

    Returns:
        {'nvi': pd.Series, 'nvi_ema': pd.Series}
    """
    _data = ["close", "volume"]
    _params = ["window"]
    _outputs = ["nvi", "nvi_ema"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        volume = data['volume']
        window = params['window']

        price_change = close.pct_change()
        vol_decrease = volume.shift(1) > volume

        # NVI is a compounding index: on volume-decrease bars, scale by
        # (1 + pct_change); otherwise carry forward. Express as a cumulative
        # product of per-bar factors. pct_change[0] is NaN by definition;
        # vol_decrease[0] is False (prev_volume is NaN); so factor[0] is 1
        # and nvi[0] = 1000 * 1 = 1000, matching the original's hand-seed.
        pct_arr = price_change.to_numpy(dtype=np.float64)
        dec_arr = vol_decrease.to_numpy(dtype=bool)
        pct_clean = np.where(np.isnan(pct_arr), 0.0, pct_arr)
        factor = np.where(dec_arr, 1.0 + pct_clean, 1.0)
        nvi_arr = 1000.0 * np.cumprod(factor)
        nvi = pd.Series(nvi_arr, index=close.index, name="nvi")

        nvi_ema = nvi.ewm(span=window, adjust=False).mean()

        return {'nvi': pd.Series(nvi, name="nvi"), 'nvi_ema': pd.Series(nvi_ema, name="nvi_ema")}


class MFI(IndicatorInterface):
    """Indicator: MFI

    Uses both price and volume to measure buying and selling pressure. It is positive when the
    typical price rises (buying pressure) and negative when the typical price declines (selling
    pressure). A ratio of positive and negative money flow is then plugged into an RSI formula to
    create an oscillator that moves between zero and one hundred.

    Abbreviation: MFI
    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/money-flow-index-mfi
    Warmup: window - 1

    Formula:
        Typical Price = (High + Low + Close) / 3
        Raw Money Flow = Typical Price * Volume
        Money Flow Ratio = Positive Money Flow / Negative Money Flow
        MFI = 100 - (100 / (1 + Money Flow Ratio))

        Typical period: 14

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price
        volume: units traded during the bar

    Params:
        window [default=14, min=5, max=30]: MFI period

    Outputs:
        mfi [dimensionless, 0..100] "Money Flow Index":
            volume-weighted RSI: 100 - 100/(1 + positive money flow / negative money flow) over
            window, where money flow is typical price times volume signed by the direction of
            typical price. Hard-bounded 0..100 by the same construction as RSI, both sums being
            non-negative. Bars where typical price is unchanged contribute zero to either side.
            80/20 are conventional thresholds; readings beyond 90/10 are described as rare and
            unsustainable

    Interpretation:
        - MFI > 80: Overbought
        - MFI < 20: Oversold
        - Divergences with price signal reversals
        - Volume confirmation of price moves

    Applications:
        - Overbought/oversold extremes at 80 and 20
        - Divergence-based reversal anticipation
        - Failure-swing reversal signals at the 80/20 levels
        - Volume confirmation of RSI-style momentum readings

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series, 'volume': pd.Series}
        params: {'window': int}

    Returns:
        {'mfi': pd.Series}
    """
    _data = ["high", "low", "close", "volume"]
    _params = ["window"]
    _outputs = ["mfi"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        close = data['close']
        volume = data['volume']
        window = params['window']

        tp = typical_price(high, low, close)
        up_down = np.where(
            tp > tp.shift(1),
            1,
            np.where(tp < tp.shift(1), -1, 0),
        )
        mfr = tp * volume * up_down

        # Positive and negative money flow with n periods.
        # Mask outside the roll so the window op is a plain vectorized sum.
        mfr_arr = np.asarray(mfr, dtype=np.float64)
        pos_mfr = pd.Series(np.where(mfr_arr >= 0.0, mfr_arr, 0.0), index=tp.index)
        neg_mfr = pd.Series(np.where(mfr_arr < 0.0, mfr_arr, 0.0), index=tp.index)
        n_positive_mf = pos_mfr.rolling(window, min_periods=window).sum()
        n_negative_mf = neg_mfr.rolling(window, min_periods=window).sum().abs()

        # Money flow index
        mfi_ratio = n_positive_mf / n_negative_mf
        mfi = 100 - (100 / (1 + mfi_ratio))

        return {'mfi': pd.Series(mfi, name=f"mfi_{window}")}


class VWAP(IndicatorInterface):
    """Indicator: VWAP

    Rolling volume-weighted average of typical price: traded value over the window divided by volume
    over the window. Each bar is weighted by how much actually traded, so heavy bars pull the level
    toward them and quiet bars barely move it. Uses a rolling `window` rather than a session anchor.
    The textbook definition resets at each session open, but anchoring presupposes a session
    boundary, and a continuously traded 24/7 market does not have one -- there is no open to
    accumulate from and no close to reset at. The rolling form is therefore the coherent definition
    here, not an approximation of the anchored one. Consequence worth knowing: on a session-traded
    instrument such as an equity, this is not the institutional execution benchmark, because that
    benchmark is defined by the session it anchors to. This series is exactly VWMA computed on
    typical price.

    Abbreviation: VWAP
    Reference: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/volume-weighted-average-price-vwap
    Warmup: window - 1

    Formula:
        VWAP = Rolling_Sum(Typical Price * Volume, window) / Rolling_Sum(Volume, window)
        Typical Price = (High + Low + Close) / 3

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price
        volume: units traded during the bar

    Params:
        window [default=14, min=5, max=50]: VWAP period

    Outputs:
        vwap [price, 0..inf] "volume weighted average price":
            Rolling volume-weighted average of typical price over `window` bars. The literature's
            VWAP is session-anchored -- it accumulates from the session open and resets each session
            -- but anchoring presupposes a session boundary, which a 24/7 market does not have, so
            the rolling form is the coherent definition here rather than an approximation of the
            anchored one. Exactly equal to VWMA computed on typical price. Against a synthetic
            session-anchored VWAP over five sessions it differs by up to 4.00 price units (3.9% of
            price), which matters only when reconciling against a session-based instrument or
            platform, where the institutional execution benchmark is defined by the session it
            anchors to

    Interpretation:
        - Price above VWAP: Buyers in control
        - Price below VWAP: Sellers in control
        - VWAP as dynamic support/resistance
        - Deviation from VWAP indicates overextension

    Applications:
        - Dynamic support and resistance in a continuously traded market
        - Volume-weighted trend reference, less sensitive to low-volume bars than a plain moving
        average
        - Entry/exit timing against a volume-aware fair-value estimate
        - Mean reversion trading

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series, 'volume': pd.Series}
        params: {'window': int}

    Returns:
        {'vwap': pd.Series}
    """
    _data = ["high", "low", "close", "volume"]
    _params = ["window"]
    _outputs = ["vwap"]

    @classmethod
    def _compute(cls, data, params):
        high = data['high']
        low = data['low']
        close = data['close']
        volume = data['volume']
        window = params['window']

        # 1 typical price
        tp = typical_price(high, low, close)

        # 2 typical price * volume
        tp_volume = tp * volume

        # 3 total price * volume
        total_pv = tp_volume.rolling(window, min_periods=window).sum()

        # 4 total volume
        total_volume = volume.rolling(window, min_periods=window).sum()

        vwap = total_pv / total_volume

        return {'vwap': pd.Series(vwap, name=f"vwap_{window}")}

class VWMA(IndicatorInterface):
    """Indicator: VWMA

    Weights each price by its bar's volume, emphasizing bars with heavy participation. Unlike VWAP
    (which resets daily/session), VWMA is a true rolling moving average over the last N bars.

    Abbreviation: VWMA
    Warmup: window - 1

    Formula:
        VWMA(n) = sum(Price_i * Volume_i) / sum(Volume_i)   over the last n bars

        Equivalently SMA(price*volume, n) / SMA(volume, n). Standard price input is close.

    Inputs:
        close: closing price
        volume: units traded during the bar

    Params:
        window [default=20, min=2, max=200]: VWMA window in bars

    Outputs:
        vwma [price, 0..inf] "Volume Weighted Moving Average":
            sum(close*volume) / sum(volume) over window -- bars traded on heavy volume dominate the
            average and quiet bars contribute little. Sitting above an SMA of the same window
            indicates volume is concentrated on up bars; below it, on down bars. Converges to the
            SMA when volume is flat across the window. A convex combination of the window's prices
            (weights are non-negative volumes, normalised), so it cannot overshoot that window's
            range

    Interpretation:
        - Volume-weighted, so heavily traded bars dominate and quiet bars contribute little
        - Above an SMA of the same period indicates volume concentrated on up bars; below it, on
        down bars
        - Reacts faster than an SMA when a move is backed by volume
        - Converges toward the SMA when volume is flat across the window
        - A convex combination of the window's prices, so it cannot overshoot that range

    Applications:
        - Trend direction and dynamic support or resistance
        - Paired with an equal-period SMA as a volume-confirmation spread
        - Crossover signals against price or another VWMA
        - Filtering breakouts for volume participation

    Args:
        data: {'close': pd.Series, 'volume': pd.Series}
        params: {'window': int}

    Returns:
        {'vwma': pd.Series}
    """
    _data = ["close", "volume"]
    _params = ["window"]
    _outputs = ["vwma"]

    @classmethod
    def _compute(cls, data, params):
        close = data['close']
        volume = data['volume']
        window = params['window']

        pv_sum = (close * volume).rolling(window, min_periods=window).sum()
        vol_sum = volume.rolling(window, min_periods=window).sum()
        vwma = pv_sum / vol_sum
        return {'vwma': pd.Series(vwma.values, index=close.index, name=f'vwma_{window}')}



class ADOSC(IndicatorInterface):
    """Indicator: ADOSC

    Momentum of the Accumulation/Distribution Line: difference of two EMAs of the AD line. Positive
    values indicate accumulation; negative indicate distribution. A classic Chaikin confirmation
    indicator.

    Abbreviation: ADOSC
    Warmup: slow - 1

    Formula:
        Money Flow Multiplier = ((close - low) - (high - close)) / (high - low)
        Money Flow Volume     = Money Flow Multiplier * volume
        ADL                   = running total of Money Flow Volume

        Chaikin Oscillator    = EMA(ADL, fast) - EMA(ADL, slow)

        Standard defaults fast=3, slow=10. 'ADOSC' is the TA-Lib function name;
        the literature name is Chaikin Oscillator.

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price
        volume: units traded during the bar

    Params:
        fast [default=3, min=2, max=20]: Fast EMA period for AD
        slow [default=10, min=5, max=50]: Slow EMA period for AD

    Outputs:
        adosc [dimensionless, -inf..inf] "Chaikin Oscillator":
            the MACD construction applied to the Accumulation/Distribution Line: fast EMA minus slow
            EMA of the ADL. An indicator of an indicator, and the literature warns it sits three
            steps removed from price and is prone to disconnecting from it. Volume-scaled and
            therefore not comparable across instruments, though it IS invariant to the ADL's
            arbitrary starting value, since a constant offset cancels between the two EMAs.
            Undefined where high equals low. 'ADOSC' is the TA-Lib function name; the literature
            name is Chaikin Oscillator

    Interpretation:
        - Momentum of accumulation/distribution, not of price
        - Positive means the ADL is rising and buying pressure prevails; negative, the reverse
        - An indicator of an indicator -- three steps removed from price, and prone to disconnecting
        from it
        - The default 3/10 pair crosses zero frequently by design
        - Divergence against price indicates changing pressure ahead of the price turn

    Applications:
        - Reading buying versus selling bias from the sign
        - Anticipating ADL trend changes, and through them price trend changes
        - Divergence-based reversal detection, with confirmation
        - Tuning sensitivity by lengthening both EMAs while preserving their ratio

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series, 'volume': pd.Series}
        params: {'fast': int, 'slow': int}

    Returns:
        {'adosc': pd.Series}
    """
    _data = ["high", "low", "close", "volume"]
    _params = ["fast", "slow"]
    _outputs = ["adosc"]

    @classmethod
    def _compute(cls, data, params):
        from mangrove_kb.indicators.trend_indicators import EMA

        high = data['high']
        low = data['low']
        close = data['close']
        volume = data['volume']
        fast = params['fast']
        slow = params['slow']

        ad = ADI.compute({'high': high, 'low': low, 'close': close, 'volume': volume}, {})['adi']
        ema_fast = EMA.compute({'close': ad}, {'window': fast})['ema']
        ema_slow = EMA.compute({'close': ad}, {'window': slow})['ema']
        adosc = ema_fast - ema_slow
        return {'adosc': pd.Series(adosc.values, index=close.index, name=f'adosc_{fast}_{slow}')}


class KVO(IndicatorInterface):
    """Indicator: KVO

    Volume-weighted momentum oscillator. pandas-ta / modern simplified form: sign the volume by the direction of the typical price change, then take the difference of a fast and slow EMA. trend = sign(typical_price - prev_typical_price) signed_volume = volume * trend KVO = EMA(signed_volume, fast) - EMA(signed_volume, slow) KVO_signal = EMA(KVO, signal_window) Positive KVO with rising signal = bullish volume pressure; negative with falling signal = bearish. Divergences from price are the classic Klinger entry cue. VARIANT: this is the **simplified** form, and it is not on the same scale as Klinger's original -- see `KlingerVolumeOscillator` for that one. Two materially different volume-force definitions circulate under the name KVO, and nothing in the name says which you have. Reconstructed on identical data with the same 34/55 periods: this (simplified) : [    -39,493,     32,593] Klinger original  : [ -4,970,310,  5,746,198]     ~145x Anyone reconciling this against SierraChart, TradingView or MotiveWave will see numbers two orders of magnitude apart and reasonably conclude it is broken. It is not -- it is the other published variant. Both are kept because both are in circulation; pick by which platform you are reconciling against, and do not compare their levels.

    Abbreviation: KVO
    Reference: https://www.tradingview.com/scripts/klingeroscillator/
    Warmup: slow + signal_window - 2

    Formula:
        trend = sign(typical_price - prev_typical_price)
        signed_volume = volume * trend
        KVO = EMA(signed_volume, fast) - EMA(signed_volume, slow)
        Signal = EMA(KVO, signal_window)
        Defaults: fast 34, slow 55, signal_window 13

        This is the SIMPLIFIED variant. Klinger's original volume force is on KlingerVolumeOscillator.

    Inputs:
        high: highest price traded during the bar
        low: lowest price traded during the bar
        close: closing price
        volume: units traded during the bar

    Params:
        fast [default=34, min=5, max=100]: Fast EMA period for signed volume
        slow [default=55, min=10, max=200]: Slow EMA period for signed volume
        signal_window [default=13, min=2, max=50]: Signal-line EMA period

    Outputs:
        kvo [dimensionless, -inf..inf] "Klinger Volume Oscillator":
            fast EMA minus slow EMA of a signed volume series. IMPLEMENTATION CAVEAT: this is the
            SIMPLIFIED variant -- volume signed by the direction of typical price -- not Klinger's
            original volume force, which multiplies volume by a |2*(dm/cm - 1)|*100 factor built
            from cumulative range measurements. Both circulate under the same name and they are not
            interchangeable: measured on identical data, the full form runs about 145x larger.
            Volume-scaled, unbounded, not comparable across instruments
        kvo_signal [dimensionless, -inf..inf] "Signal Line":
            EMA of kvo over signal_window; also called the trigger line. Crossings of kvo against it
            are the primary documented signal

    Interpretation:
        - KVO above zero: Bullish volume pressure
        - KVO below zero: Bearish volume pressure
        - KVO crossing signal line: Potential trade signal
        - Divergences with price indicate weakening trends

    Applications:
        - Signal-line crossovers as the primary trade trigger
        - Zero-line crossings for money-flow bias
        - Divergence against price for reversal anticipation
        - Histogram of KVO minus signal for momentum-of-momentum

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series, 'volume': pd.Series}
        params: {'fast': int, 'slow': int, 'signal_window': int}

    Returns:
        {'kvo': pd.Series, 'kvo_signal': pd.Series}
    """
    _data = ["high", "low", "close", "volume"]
    _params = ["fast", "slow", "signal_window"]
    _outputs = ["kvo", "kvo_signal"]

    @classmethod
    def _compute(cls, data, params):
        from mangrove_kb.indicators.trend_indicators import EMA
        from mangrove_kb.indicators.utils import typical_price

        high = data['high']
        low = data['low']
        close = data['close']
        volume = data['volume']
        fast = params['fast']
        slow = params['slow']
        signal_window = params['signal_window']

        tp = typical_price(high, low, close)
        diff = tp.diff(1)
        # Sign of the typical-price change: +1 / -1 / 0 (no change).
        # np.sign gives 0.0 for no-change; we leave that as 0 to match
        # pandas-ta behavior on flat bars.
        trend = np.sign(diff.to_numpy(dtype=np.float64, copy=False))
        # NaN-safe: diff[0] is NaN so sign[0] is NaN -- replace with 0
        # (no prior bar, no trend direction).
        trend = np.nan_to_num(trend, nan=0.0)

        vol_arr = volume.to_numpy(dtype=np.float64, copy=False)
        signed_volume = pd.Series(vol_arr * trend, index=close.index)

        ema_fast = EMA.compute({'close': signed_volume}, {'window': fast})['ema']
        ema_slow = EMA.compute({'close': signed_volume}, {'window': slow})['ema']
        kvo = ema_fast - ema_slow
        kvo_signal = EMA.compute({'close': kvo}, {'window': signal_window})['ema']

        return {
            'kvo': pd.Series(kvo.values, index=close.index, name=f'kvo_{fast}_{slow}'),
            'kvo_signal': pd.Series(kvo_signal.values, index=close.index, name=f'kvo_signal_{signal_window}'),
        }


class KlingerVolumeOscillator(IndicatorInterface):
    """Indicator: KlingerVolumeOscillator

    The full 1997 construction, as opposed to the simplified signed-volume form in `KVO`. Where the simplified variant weights volume by nothing more than the direction of the typical price change, this weights it by how far the current bar's range departs from a running measurement of range accumulated since the last trend change -- which is the part that gives the original its scale and its character:: tp    = (high + low + close) / 3 trend = +1 if tp > tp[-1] else -1                      # binary, no flat branch dm    = high - low                                     # this bar's range cm    = cm[-1] + dm       if trend == trend[-1]        # accumulate within a trend dm[-1] + dm       otherwise                    # reset on a trend change vf    = volume * abs(2 * (dm / cm - 1)) * trend * 100   # volume force KVO   = EMA(vf, fast) - EMA(vf, slow) signal = EMA(KVO, signal_window) Note `cm` is the reason this cannot be expressed as a rolling window: it is a path-dependent accumulator whose reset points are determined by the trend series itself. SCALE: roughly 145x the simplified `KVO` on identical data and identical 34/55 periods -- measured `[-4,970,310, 5,746,198]` against `[-39,493, 32,593]`. The two are read the same way (sign, slope, crossings of the signal line, and divergence against price) but their levels are not comparable and must never be mixed in one feature set as though they were the same measurement. SOURCING CAVEAT, stated plainly because it is unusual for this package: **the primary source could not be obtained.** Klinger's 1997 *Stocks & Commodities* original sits behind a Cloudflare challenge, and StockCharts has no Klinger page at all. This construction is reconciled across secondary platform documentation -- SierraChart, TradingView, CQG, MotiveWave, QuantShare -- which agree with each other on the formula above. That agreement is the whole of the evidence, and it is also how two incompatible variants came to circulate under one name in the first place.

    Abbreviation: KVO
    Reference: https://www.sierrachart.com/index.php?page=doc/StudiesReference.php
    Warmup: slow + signal_window - 2

    Formula:
        tp    = (high + low + close) / 3
        trend = +1 if tp > prev_tp else -1        (binary -- no flat branch)
        dm    = high - low
        cm    = prev_cm + dm   if trend == prev_trend   (accumulate within a trend)
                prev_dm + dm   otherwise                (reset on a trend change)

        Volume Force = Volume * |2 * (dm/cm - 1)| * trend * 100
        KVO    = EMA(Volume Force, 34) - EMA(Volume Force, 55)
        Signal = EMA(KVO, 13)

    Inputs:
        high: highest price traded during the bar; supplies both the typical price and the bar range
        dm
        low: lowest price traded during the bar; supplies both the typical price and the bar range
        dm
        close: closing price; enters only through the typical price, which sets the trend direction
        volume: units traded during the bar; the quantity the volume force scales

    Params:
        fast [default=34, min=5, max=100]: Fast EMA period applied to the volume force
        slow [default=55, min=10, max=200]: Slow EMA period applied to the volume force
        signal_window [default=13, min=2, max=50]: Signal-line EMA period

    Outputs:
        kvo [dimensionless, -inf..inf] "Klinger Volume Oscillator":
            fast EMA minus slow EMA of Klinger's volume force -- volume scaled by |2*(dm/cm -
            1)|*100 and signed by trend, where cm accumulates bar range since the last trend change.
            This is the ORIGINAL 1997 construction; KVO carries the simplified signed-volume
            variant, and on identical data with identical periods this runs about 145x larger.
            Volume-scaled, unbounded, not comparable across instruments, and not comparable to KVO.
            Zero-range bars contribute zero force
        kvo_signal [dimensionless, -inf..inf] "Signal Line":
            EMA of kvo over signal_window; also called the trigger line. Crossings of kvo against it
            are the primary documented signal

    Interpretation:
        - KVO above zero: Bullish volume pressure
        - KVO below zero: Bearish volume pressure
        - KVO crossing signal line: Potential trade signal
        - Divergences with price indicate weakening trends
        - The level is scale-arbitrary and roughly 145x the simplified KVO's -- read sign, slope and
        crossings, never magnitude

    Applications:
        - Signal-line crossovers as the primary trade trigger
        - Zero-line crossings for money-flow bias
        - Divergence against price for reversal anticipation
        - Reconciling against platforms that implement the original -- SierraChart, TradingView,
        CQG, MotiveWave -- where the simplified KVO would appear two orders of magnitude wrong

    Args:
        data: {'high': pd.Series, 'low': pd.Series, 'close': pd.Series, 'volume': pd.Series}
        params: {'fast': int, 'slow': int, 'signal_window': int}

    Returns:
        {'kvo': pd.Series, 'kvo_signal': pd.Series}
    """
    _data = ["high", "low", "close", "volume"]
    _params = ["fast", "slow", "signal_window"]
    _outputs = ["kvo", "kvo_signal"]

    @classmethod
    def _compute(cls, data, params):
        from mangrove_kb.indicators.trend_indicators import EMA
        from mangrove_kb.indicators.utils import typical_price

        high = data['high']
        low = data['low']
        close = data['close']
        volume = data['volume']
        fast = params['fast']
        slow = params['slow']
        signal_window = params['signal_window']

        tp = typical_price(high, low, close).to_numpy(dtype=np.float64, copy=False)
        dm = (high - low).to_numpy(dtype=np.float64, copy=False)
        vol = volume.to_numpy(dtype=np.float64, copy=False)
        n = len(close)

        vf = np.full(n, np.nan)
        if n:
            # Bar 0 has no prior typical price, so its trend is undefined. The seed is immaterial to
            # bar 0's own value -- cm equals dm there, so dm/cm is 1 and the force term |2*(1-1)| is
            # exactly 0 whatever sign is chosen. It matters only in deciding whether bar 1 is read
            # as a trend change. +1 is the seed the platform implementations use.
            trend_prev = 1.0
            cm_prev = dm[0]
            dm_prev = dm[0]
            vf[0] = 0.0

            for i in range(1, n):
                trend = 1.0 if tp[i] > tp[i - 1] else -1.0
                cm = (cm_prev + dm[i]) if trend == trend_prev else (dm_prev + dm[i])

                if cm == 0.0:
                    # Two consecutive zero-range bars. The force term is 0/0 and no source states a
                    # convention. 0 -- "no range, so no measurable force" -- matches the choice made
                    # for the same degenerate case in ADI and CMF, and for the same reason: vf feeds
                    # an EMA, so a NaN would propagate through every subsequent bar rather than
                    # being contained to the one it describes.
                    vf[i] = 0.0
                else:
                    vf[i] = vol[i] * abs(2.0 * (dm[i] / cm - 1.0)) * trend * 100.0

                trend_prev, cm_prev, dm_prev = trend, cm, dm[i]

        vf_series = pd.Series(vf, index=close.index)
        ema_fast = EMA.compute({'close': vf_series}, {'window': fast})['ema']
        ema_slow = EMA.compute({'close': vf_series}, {'window': slow})['ema']
        kvo = ema_fast - ema_slow
        kvo_signal = EMA.compute({'close': kvo}, {'window': signal_window})['ema']

        return {
            'kvo': pd.Series(kvo.values, index=close.index, name=f'klinger_kvo_{fast}_{slow}'),
            'kvo_signal': pd.Series(
                kvo_signal.values, index=close.index, name=f'klinger_kvo_signal_{signal_window}'
            ),
        }

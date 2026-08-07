"""Regression tests for the defects fixed from the indicator research.

Each test corresponds to a numbered finding on
MangroveTechnologies/MangroveKnowledgeBase#104 and asserts the corrected behaviour, so a revert is
caught here rather than in a consumer.

Usage:
    pytest tests/test_indicator_defect_fixes.py -v
"""

import numpy as np
import pandas as pd
import pytest

from mangrove_kb.indicators import (
    ADX,
    ATR,
    KAMA,
    MAMA,
    NATR,
    OBV,
    TRIX,
    VPT,
    DonchianChannel,
    KeltnerChannel,
    STARCBands,
)


def _idx(n):
    return pd.date_range("2024-01-01", periods=n, freq="h")


@pytest.fixture(scope="module")
def ohlcv():
    rs = np.random.RandomState(5)
    n = 300
    idx = _idx(n)
    close = pd.Series(100 + rs.normal(0, 1.2, n).cumsum(), index=idx)
    return {
        "high": close + np.abs(rs.normal(0, 0.6, n)),
        "low": close - np.abs(rs.normal(0, 0.6, n)),
        "close": close,
        "volume": pd.Series(rs.randint(1_000, 9_000, n).astype(float), index=idx),
    }


# --- 22: OBV honours Granville's three-way rule ---------------------------- #
def test_obv_leaves_unchanged_closes_alone():
    """A flat close must contribute nothing. A two-way test folds it into the up-branch, so OBV
    drifts upward on every unchanged bar -- and OBV is read by its direction."""
    idx = _idx(6)
    close = pd.Series([100.0, 100, 100, 101, 100, 100], index=idx)
    volume = pd.Series([1000.0] * 6, index=idx)
    obv = OBV.compute({"close": close, "volume": volume}, {})["obv"]
    # Bar 0 contributes nothing: with no prior close its direction is undefined, the same reasoning
    # as the flat-close branch. This is the canonical series from the research note.
    assert obv.tolist() == [0.0, 0.0, 0.0, 1000.0, 0.0, 0.0]


# --- 23: VPT keeps the full index ------------------------------------------ #
def test_vpt_has_no_index_shortening_escape_hatch(ohlcv):
    """`compute_frame` guarantees every indicator shares the input index so frames outer-join
    cleanly. `dropnans=True` returned a shorter series starting later, silently breaking that.

    The parameter is removed rather than redefined. Zero-filling instead would have been the same
    defect corrected in ATR and ADX: VPT is a running cumulative total, so 0 is a real reading and
    substituting it makes warmup indistinguishable from a genuinely flat stretch.
    """
    assert "dropnans" not in VPT._params

    data = {"close": ohlcv["close"], "volume": ohlcv["volume"]}
    out = VPT.compute(data, {"smoothing_factor": 5})["vpt"]

    assert len(out) == len(ohlcv["close"])
    assert out.index.equals(ohlcv["close"].index)

    # Warmup is a contiguous NaN block at the head, and nothing after it is NaN -- the shape every
    # other indicator in the package has.
    warmup = int(out.isna().sum())
    assert warmup > 0, "warmup is being filled rather than left undefined"
    assert out.iloc[:warmup].isna().all() and out.iloc[warmup:].notna().all()


# --- 3 / 18: warmup is NaN, never a zero-fill ------------------------------ #
@pytest.mark.parametrize(
    "cls,params,key,expected_nans",
    [
        (ATR, {"window": 14}, "atr", 13),
        (ADX, {"window": 14}, "adx", 27),
    ],
)
def test_warmup_is_nan_not_zero(ohlcv, cls, params, key, expected_nans):
    """Zero is a meaningful reading for both -- ATR zero means no observed range, ADX zero means no
    directional strength. Filling warmup with it made warmup indistinguishable from a flat market,
    with no NaN anywhere to mark it."""
    series = cls.compute({k: ohlcv[k] for k in cls._data}, params)[key]
    assert series.isna().sum() == expected_nans
    assert (series.to_numpy() == 0.0).sum() == 0
    assert series.iloc[:expected_nans].isna().all()
    assert series.iloc[expected_nans:].notna().all()


def test_natr_and_starc_no_longer_carry_their_own_atr_masks(ohlcv):
    """Both used to mask ATR's warmup locally, purely to work around the zero-fill. The NaN now
    propagates on its own, and the values after warmup are unaffected."""
    natr = NATR.compute({k: ohlcv[k] for k in ("high", "low", "close")}, {"window": 14})["natr"]
    assert natr.iloc[:13].isna().all() and natr.iloc[13:].notna().all()

    bands = STARCBands.compute(
        {k: ohlcv[k] for k in ("high", "low", "close")},
        {"window": 20, "window_atr": 14, "multiplier": 2.0},
    )
    assert np.isfinite(bands["starc_hband"].iloc[25:]).all()
    assert np.isfinite(bands["starc_lband"].iloc[25:]).all()


# --- 2: Donchian pband describes the bands the indicator reports ----------- #
def test_donchian_pband_matches_its_own_shipped_bands(ohlcv):
    """pband was computed from the UNSHIFTED bands and then shifted alongside them, so it described
    a different bar's bands. Its visible symptom: it could never leave 0..1, so it could never
    signal a breakout -- on exactly the current-bar-excluded configuration that is now the
    indicator's own behaviour and what both Donchian signals ask for."""
    out = DonchianChannel.compute(
        {k: ohlcv[k] for k in ("high", "low", "close")},
        {"window": 20, "include_current_bar": False},
    )
    expected = (ohlcv["close"] - out["lband"]) / (out["hband"] - out["lband"])
    both = out["pband"].notna() & expected.notna()
    assert both.any()
    assert np.allclose(out["pband"][both], expected[both])
    assert (out["pband"] < 0).any() or (out["pband"] > 1).any(), "pband can no longer break out"


# --- 6: zero-width bands are guarded, matching BollingerBands -------------- #
@pytest.mark.parametrize("cls,params", [
    (DonchianChannel, {"window": 20, "include_current_bar": True}),
    (KeltnerChannel, {"window": 20, "window_atr": None, "original_version": True,
                      "multiplier": None}),
])
def test_zero_width_bands_yield_nan_not_inf(cls, params):
    flat = pd.Series([50.0] * 60, index=_idx(60))
    out = cls.compute(
        {"high": flat, "low": flat, "close": flat + 1.0}, params
    )
    assert not np.isinf(out["pband"]).any(), "zero-width band produced inf"


# --- 5: Keltner's original_version rejects the parameters it cannot use ---- #
def test_keltner_original_version_rejects_inert_parameters(ohlcv):
    """Both were declared in `_params` and surfaced through the metadata API while being silently
    ignored, so a caller tuning them saw no effect and no error.

    The check is on the COMBINATION: on this branch they must be None. An earlier revision compared
    against hardcoded defaults, which accepted a caller who explicitly passed the default even
    though that value is equally ignored.
    """
    data = {k: ohlcv[k] for k in ("high", "low", "close")}
    base = {"window": 20, "window_atr": None, "original_version": True, "multiplier": None}

    KeltnerChannel.compute(data, base)  # None for the inert params is the contract

    # Any value is rejected -- including what happens to be the documented default.
    for param, value in (("window_atr", 99), ("window_atr", 10),
                         ("multiplier", 3.5), ("multiplier", 2.0)):
        with pytest.raises(ValueError, match="ignores"):
            KeltnerChannel.compute(data, {**base, param: value})


# --- 8: Keltner's series names are its own -------------------------------- #
def test_keltner_series_names_are_not_copy_pasted(ohlcv):
    out = KeltnerChannel.compute(
        {k: ohlcv[k] for k in ("high", "low", "close")},
        {"window": 20, "window_atr": 10, "original_version": False, "multiplier": 2.0},
    )
    assert all(s.name.startswith("kc_") for s in out.values()), {k: v.name for k, v in out.items()}


# --- 15 / 16: MAMA consumes median price and masks its unconverged ramp ---- #
def test_mama_consumes_median_price(ohlcv):
    """Ehlers states the input explicitly: "Inputs: Price = (H+L)/2". This consumed close.

    Proven exactly rather than by proximity: two bar series with identical midpoints but very
    different high/low spreads must produce identical output, because only the midpoint is read.
    """
    assert MAMA._data == ["high", "low"], "MAMA no longer declares median price as its input"

    rs = np.random.RandomState(2)
    n = 300
    idx = _idx(n)
    mid = pd.Series(100 + rs.normal(0, 1.0, n).cumsum(), index=idx)
    params = {"fast_limit": 0.5, "slow_limit": 0.05, "warmup_bars": 64}

    narrow = MAMA.compute({"high": mid + 0.5, "low": mid - 0.5}, params)
    wide = MAMA.compute({"high": mid + 7.5, "low": mid - 7.5}, params)

    for key in ("mama", "fama"):
        a, b = narrow[key].dropna(), wide[key].dropna()
        assert len(a) and a.index.equals(b.index)
        assert np.allclose(a, b), f"{key} depends on the spread, so the input is not the midpoint"

    # And it genuinely tracks that midpoint. Correlation rather than an absolute bound, since an
    # adaptive moving average lags and the size of that lag is not what this test is about.
    tracked = narrow["mama"].dropna()
    assert tracked.corr(mid.loc[tracked.index]) > 0.95


def test_mama_masks_the_unconverged_recursion(ohlcv):
    """The recursion starts from an uninitialised zero. Six bars covered the Hilbert FIR depth but
    not the ramp, so bar 6 published a value ~50% below price as an ordinary reading."""
    # warmup is a PARAMETER, not a constant: the count is a tolerance the caller chooses, so it is
    # tunable like every other knob in this package. Asserted at two settings.
    assert "warmup_bars" in MAMA._params

    for warmup in (64, 24):
        out = MAMA.compute({"high": ohlcv["high"], "low": ohlcv["low"]},
                           {"fast_limit": 0.5, "slow_limit": 0.05, "warmup_bars": warmup})
        for key in ("mama", "fama"):
            assert out[key].iloc[:warmup].isna().all()
            assert out[key].iloc[warmup:].notna().all()

    out = MAMA.compute({"high": ohlcv["high"], "low": ohlcv["low"]},
                       {"fast_limit": 0.5, "slow_limit": 0.05, "warmup_bars": 64})

    median = (ohlcv["high"] + ohlcv["low"]) / 2.0
    first = out["mama"].dropna()
    rel = (first - median.loc[first.index]).abs() / median.loc[first.index]
    assert rel.max() < 0.10, "a published MAMA value is still far from price"


# --- 17: KAMA seeds with an SMA ------------------------------------------- #
def test_kama_seeds_with_an_sma(ohlcv):
    """StockCharts step 3 seeds the recursion with an SMA; this seeded with the bar's own close."""
    window = 10
    kama = KAMA.compute({"close": ohlcv["close"]}, {"window": window, "pow1": 2, "pow2": 30})["kama"]
    seed_pos = kama.to_numpy().nonzero()[0]
    first = kama.dropna()
    assert len(first) and len(seed_pos)
    i = ohlcv["close"].index.get_loc(first.index[0])
    sma = ohlcv["close"].iloc[max(0, i - window + 1): i + 1].mean()
    assert np.isclose(first.iloc[0], sma), "KAMA is no longer SMA-seeded"


# --- 19: TRIX emits its signal line --------------------------------------- #
def test_trix_emits_its_signal_line(ohlcv):
    """Signal-line crossovers are TRIX's primary documented signal, and the series was missing."""
    assert "trix_signal" in TRIX._outputs

    out = TRIX.compute({"close": ohlcv["close"]}, {"window": 15, "window_sign": 9})
    from mangrove_kb.indicators import EMA

    expected = EMA.compute({"close": out["trix"]}, {"window": 9})["ema"]
    both = out["trix_signal"].notna() & expected.notna()
    assert both.any()
    assert np.allclose(out["trix_signal"][both], expected[both])


# --- 1: Donchian excludes the current bar, so a breakout is possible ------- #
def test_donchian_excludes_the_current_bar(ohlcv):
    """Including the current bar makes a breakout arithmetically impossible: the current high is one
    of the values the upper band is the maximum of, so close can never exceed it. Every source
    describing Donchian channels specifies the PRECEDING N bars, and StockCharts gives this exact
    reason: "A channel break would not be possible if the most recent period was used."
    """
    data = {k: ohlcv[k] for k in ("high", "low", "close")}

    excluded = DonchianChannel.compute(data, {"window": 20, "include_current_bar": False})
    included = DonchianChannel.compute(data, {"window": 20, "include_current_bar": True})

    assert int((ohlcv["close"] > excluded["hband"]).sum()) > 0
    assert int((ohlcv["close"] < excluded["lband"]).sum()) > 0

    # The inclusive form is retained as a generic rolling-window primitive, and it demonstrates the
    # defect it used to be the default for.
    assert int((ohlcv["close"] > included["hband"]).sum()) == 0
    assert int((ohlcv["close"] < included["lband"]).sum()) == 0

    # The exclusion is a shift by one, NOT a window of window-1: it costs one extra warmup bar.
    assert excluded["hband"].isna().sum() == included["hband"].isna().sum() + 1

    # `offset` is gone rather than silently redefined, so an existing call site fails loudly
    # instead of changing meaning underneath itself.
    assert "offset" not in DonchianChannel._params
    with pytest.raises(ValueError, match="missing params"):
        DonchianChannel.compute(data, {"window": 20, "offset": 1})


# --- 7: wband means the same thing across all three band indicators -------- #
def test_wband_is_normalised_by_each_indicators_own_middle_band(ohlcv):
    """BollingerBands and KeltnerChannel divide the channel width by their own middle band.
    Donchian divided by a rolling mean of close -- a different quantity, and numerically close
    enough (max 1.69% divergence measured over 300 bars) that it never looks like an error."""
    data = {k: ohlcv[k] for k in ("high", "low", "close")}
    out = DonchianChannel.compute(data, {"window": 20, "include_current_bar": False})

    expected = ((out["hband"] - out["lband"]) / out["mband"]) * 100
    both = out["wband"].notna() & expected.notna()
    assert both.any()
    assert np.allclose(out["wband"][both], expected[both])

    # It is no longer the close-normalised series it used to be.
    close_normalised = (
        (out["hband"] - out["lband"]) / ohlcv["close"].rolling(20, min_periods=20).mean()
    ) * 100
    assert not np.allclose(out["wband"][both], close_normalised[both])


# --- 20: APO is gone; its signals read the MACD line ---------------------- #
def test_apo_is_removed_and_its_signals_read_the_macd_line(ohlcv):
    """APO emitted a series byte-identical to MACD.macd -- the same series, not an approximation --
    so the corpus presented one measurement as two independent indicators."""
    import mangrove_kb.indicators as indicators
    import mangrove_kb.signals  # noqa: F401  -- populates the registry
    from mangrove_kb.indicators import EMA, MACD
    from mangrove_kb.registry import RuleRegistry

    assert not hasattr(indicators, "APO")

    registered = set(RuleRegistry._registry)
    assert not [n for n in registered if n.startswith("apo")]
    assert {"macd_line_positive", "macd_line_negative",
            "macd_line_cross_up", "macd_line_cross_down"} <= registered

    # The property that made APO a duplicate, pinned so it is not re-added under another name.
    close = ohlcv["close"]
    macd_line = MACD.compute(
        {"close": close}, {"window_fast": 12, "window_slow": 26, "window_sign": 9}
    )["macd"]
    ema_diff = (EMA.compute({"close": close}, {"window": 12})["ema"]
                - EMA.compute({"close": close}, {"window": 26})["ema"])
    both = macd_line.notna() & ema_diff.notna()
    assert both.any()
    assert float((macd_line[both] - ema_diff[both]).abs().max()) == 0.0


# --- 21: Klinger's original ships alongside the simplified variant --------- #
def test_klinger_original_is_available_and_on_its_own_scale(ohlcv):
    """Two incompatible volume-force definitions circulate as "KVO" and nothing in the name says
    which you have. Both are kept; this pins that they are genuinely different constructions rather
    than one aliasing the other, and that the simplified form is the smaller-scaled one."""
    from mangrove_kb.indicators import KVO, KlingerVolumeOscillator

    data = {k: ohlcv[k] for k in ("high", "low", "close", "volume")}
    params = {"fast": 34, "slow": 55, "signal_window": 13}

    simplified = KVO.compute(data, params)["kvo"]
    original = KlingerVolumeOscillator.compute(data, params)["kvo"]

    assert original.index.equals(ohlcv["close"].index)
    assert not np.isinf(original.dropna()).any()

    a = float(simplified.dropna().abs().max())
    b = float(original.dropna().abs().max())
    assert b > 50 * a, f"the original is not on its own scale: {b:.0f} vs {a:.0f}"

    # cm is a path-dependent accumulator that resets on trend change, so the original cannot be a
    # rescaling of the simplified series.
    assert not np.allclose(simplified.dropna(), original.dropna())


# --- 9 / 13 / 24: one stated convention for the degenerate denominators ---- #
def test_per_bar_oscillators_answer_nan_on_a_zero_range_window():
    """A window whose high equals its low makes %K a 0/0 with no limit to take, and no source
    states a convention. NaN, deliberately -- these are per-bar bounded readings, so the NaN is
    contained to the bar it describes. They previously fell to NaN through pandas' division rather
    than by decision, which also left x/0 -> inf reachable on malformed data."""
    from mangrove_kb.indicators import RSI, StochRSI, StochasticOscillator, WilliamsR

    flat = pd.Series([50.0] * 60, index=_idx(60))

    assert StochasticOscillator.compute(
        {"high": flat, "low": flat, "close": flat}, {"window": 14, "smooth_window": 3}
    )["stoch_k"].isna().all()
    assert WilliamsR.compute(
        {"high": flat, "low": flat, "close": flat}, {"window": 14}
    )["wr"].isna().all()
    assert StochRSI.compute(
        {"close": flat}, {"window": 14, "smooth1": 3, "smooth2": 3}
    )["stochrsi"].isna().all()

    # Finding 24. RSI's guard tested only the denominator, so a perfectly flat series returned
    # 100 -- the all-gains answer for a market with no gains.
    assert RSI.compute({"close": flat}, {"window": 14})["rsi"].isna().all()

    # The genuine limit is untouched: gains and no losses is still 100.
    rising = pd.Series(np.arange(60, dtype=float) + 100, index=_idx(60))
    assert (RSI.compute({"close": rising}, {"window": 14})["rsi"].dropna() == 100.0).all()


def test_cumulative_flow_indicators_answer_zero_on_a_zero_range_bar(ohlcv):
    """Same 0/0, opposite answer, and the difference is not arbitrary: ADI and CMF are running
    sums, so a NaN would propagate through every later bar instead of being contained to the one it
    describes. Zero means "this bar carries no directional information".

    The guard is on `high == low` specifically. It used to be a blanket `.fillna(0.0)`, which also
    swallowed NaNs from missing input data -- a genuine data gap reading as "no flow".
    """
    from mangrove_kb.indicators import ADI, CMF

    high, low = ohlcv["high"].copy(), ohlcv["low"].copy()
    high.iloc[100] = ohlcv["close"].iloc[100]
    low.iloc[100] = ohlcv["close"].iloc[100]
    data = {"high": high, "low": low, "close": ohlcv["close"], "volume": ohlcv["volume"]}

    adi = ADI.compute(data, {})["adi"]
    assert float(adi.iloc[100] - adi.iloc[99]) == 0.0
    assert adi.notna().all()
    # A neighbouring ordinary bar still moves the line, so this is not zeroing everything.
    assert float(adi.iloc[101] - adi.iloc[100]) != 0.0

    assert CMF.compute(data, {"window": 20})["cmf"].iloc[20:].notna().all()

    # Missing input data is no longer swallowed.
    high_gap = high.copy()
    high_gap.iloc[200] = np.nan
    assert pd.isna(ADI.compute({**data, "high": high_gap}, {})["adi"].iloc[200])

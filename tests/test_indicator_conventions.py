"""Regression guards for indicators that are CORRECT but disagree with common libraries.

Twelve implementations in this package deliberately follow the published literature where
pandas-ta, TA-Lib or a charting platform does something else. Diffing our output against one of
those libraries therefore shows a mismatch, and the natural reaction -- "ours is wrong, make it
agree" -- would replace correct code with incorrect code. `CCI` is the worst case: the two forms
differ by more than 180 points on an indicator whose conventional band is +/-100.

Each test below pins the behaviour and records what it is being defended against, so a change made
to satisfy a reference-implementation audit fails here first. None of these is a tolerance check
against a library; each asserts the published construction directly.

Sourcing for every claim is in `ontology/research/*.md`; the audit context is
MangroveTechnologies/MangroveKnowledgeBase#92.

Usage:
    pytest tests/test_indicator_conventions.py -v
"""

import math

import numpy as np
import pandas as pd
import pytest

from mangrove_kb.indicators import (
    ADI,
    CCI,
    DPO,
    EMA,
    HMA,
    KST,
    NVI,
    SMMA,
    TRIMA,
    Aroon,
    EaseOfMovement,
    Vortex,
)


def _idx(n):
    return pd.date_range("2024-01-01", periods=n, freq="h")


@pytest.fixture(scope="module")
def ohlcv():
    """Deterministic OHLCV with enough history for a 30-bar lookback plus smoothing."""
    rs = np.random.RandomState(11)
    n = 400
    idx = _idx(n)
    close = pd.Series(100 + rs.normal(0, 1.2, n).cumsum(), index=idx)
    return {
        "high": close + np.abs(rs.normal(0, 0.7, n)),
        "low": close - np.abs(rs.normal(0, 0.7, n)),
        "close": close,
        "volume": pd.Series(rs.randint(1_000, 9_000, n).astype(float), index=idx),
    }


def _aligned(a, b):
    """Compare two series only where both are defined; warmup lengths differ between forms."""
    both = a.notna() & b.notna()
    assert both.any(), "no overlapping defined region to compare"
    return a[both], b[both]


# --------------------------------------------------------------------------- #
# 1. CCI -- true mean absolute deviation, not the rolling-mean shortcut       #
# --------------------------------------------------------------------------- #
def test_cci_uses_true_mean_absolute_deviation(ohlcv):
    """DEFENDS AGAINST: "our CCI disagrees with pandas-ta, fix it".

    The published formula is MD = (1/n) * SUM|TP_i - SMA_TP|, where every deviation in the window
    is measured against THAT window's own mean. The widespread shortcut rolling-averages
    |tp - rolling_mean| instead, which is a different quantity.
    """
    window, constant = 20, 0.015
    tp = (ohlcv["high"] + ohlcv["low"] + ohlcv["close"]) / 3
    sma = tp.rolling(window).mean()

    mad_published = tp.rolling(window).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    mad_shortcut = (tp - sma).abs().rolling(window).mean()

    ours = CCI.compute(
        {k: ohlcv[k] for k in ("high", "low", "close")},
        {"window": window, "constant": constant},
    )["cci"]

    a, b = _aligned(ours, (tp - sma) / (constant * mad_published))
    assert np.allclose(a, b), "CCI no longer matches the published mean-absolute-deviation form"

    a, b = _aligned(ours, (tp - sma) / (constant * mad_shortcut))
    assert not np.allclose(a, b), "CCI now matches the library shortcut -- this is a regression"


# --------------------------------------------------------------------------- #
# 2. SMMA(n) is exactly EMA(2n-1)                                             #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("n", [10, 14])
def test_smma_is_exactly_ema_of_double_period_minus_one(ohlcv, n):
    """DEFENDS AGAINST: "the literature says *approximately*, so the exact match is a coincidence".

    Sources hedge to "approximately" only because implementations seed differently. Ours seeds both
    identically, so the identity is exact. Do not "fix" the agreement away.
    """
    a, b = _aligned(
        SMMA.compute({"close": ohlcv["close"]}, {"window": n})["smma"],
        EMA.compute({"close": ohlcv["close"]}, {"window": 2 * n - 1})["ema"],
    )
    assert np.array_equal(a.to_numpy(), b.to_numpy()), f"SMMA({n}) no longer equals EMA({2 * n - 1})"


# --------------------------------------------------------------------------- #
# 3. TRIMA's even-period kernel                                               #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("window,kernel", [(7, [1, 2, 3, 4, 3, 2, 1]), (4, [1, 2, 2, 1])])
def test_trima_even_period_kernel(window, kernel):
    """DEFENDS AGAINST: an alternative that uses (n+1)/2 twice for even windows.

    Ours uses n/2 and n/2+1, reproducing the canonical kernels and matching TA-Lib, Tulip and
    QuantConnect. The widely-copied alternative is internally inconsistent with its own published
    weights. Recovered here by impulse response.
    """
    impulse = pd.Series(np.r_[np.zeros(60), 1.0, np.zeros(60)])
    out = TRIMA.compute({"close": impulse}, {"window": window})["trima"].to_numpy()
    nonzero = out[np.isfinite(out) & (np.abs(out) > 1e-12)]
    assert np.round(nonzero / nonzero.min()).astype(int).tolist() == kernel


# --------------------------------------------------------------------------- #
# 4. HMA floors n/2 and sqrt(n)                                               #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("window", [10, 20, 40])
def test_hma_floors_half_period_and_sqrt(ohlcv, window):
    """DEFENDS AGAINST: "StockCharts rounds n/2 up, so ours is off by one".

    Ours floors both, matching Tulip and the Hull Chart manual. Hull's own listing defers to the
    platform, so there is no author-authoritative answer and this is a choice, not an error.
    Warmup is the observable consequence: (window-1) + (floor(sqrt(window))-1).
    """
    warmup = int(HMA.compute({"close": ohlcv["close"]}, {"window": window})["hma"].isna().sum())
    assert warmup == window + math.floor(math.sqrt(window)) - 2


# --------------------------------------------------------------------------- #
# 5. EMA seeds from the first observation                                     #
# --------------------------------------------------------------------------- #
def test_ema_seeds_from_first_observation_not_an_sma(ohlcv):
    """DEFENDS AGAINST: "StockCharts/TradingView/Fidelity seed from an SMA of the first n bars".

    Ours uses the statistics convention. The difference is warmup-only and decays to zero, so the
    cost of the divergence is nil -- but a "fix" would change every EMA-derived series in the
    package.
    """
    window = 10
    ema = EMA.compute({"close": ohlcv["close"]}, {"window": window})["ema"]
    first = ema.dropna().iloc[0]
    sma_seed = ohlcv["close"].iloc[:window].mean()
    assert not math.isclose(first, sma_seed, rel_tol=1e-9), "EMA is now SMA-seeded"


# --------------------------------------------------------------------------- #
# 6. DPO is lookahead-free                                                    #
# --------------------------------------------------------------------------- #
def test_dpo_is_lookahead_free(ohlcv):
    """DEFENDS AGAINST: "charting platforms plot the centred alignment, ours is shifted".

    The centred form reaches window/2+1 bars into the FUTURE and cannot produce a value on the
    latest bar. Ours uses past data only, so it is usable in a live series. Adopting the centred
    form would introduce lookahead into anything consuming it.
    """
    window = 20
    dpo = DPO.compute({"close": ohlcv["close"]}, {"window": window})["dpo"]
    expected = ohlcv["close"].shift(window // 2 + 1) - ohlcv["close"].rolling(window).mean()

    a, b = _aligned(dpo, expected)
    assert np.allclose(a, b), "DPO alignment changed -- check for lookahead"
    assert np.isfinite(dpo.iloc[-1]), "DPO no longer produces a value on the latest bar"


# --------------------------------------------------------------------------- #
# 7. Aroon uses a window+1 lookback, so 0 is attainable                       #
# --------------------------------------------------------------------------- #
def test_aroon_zero_is_attainable(ohlcv):
    """DEFENDS AGAINST: a "fix" to a plain window lookback.

    Ours counts the current bar plus N prior, per ((N - days_since) / N) * 100. The literature
    leaves the indexing ambiguous; ours resolves it so that 0 is reachable when the extreme sits at
    the far end of the window. A plain-N lookback makes 0 unreachable.
    """
    aroon = Aroon.compute({k: ohlcv[k] for k in ("high", "low")}, {"window": 25})
    for key in ("aroon_up", "aroon_down"):
        series = aroon[key].dropna()
        assert series.min() >= 0.0 and series.max() <= 100.0
        assert (series == 0.0).any(), f"{key} can no longer reach 0"


# --------------------------------------------------------------------------- #
# 8. EaseOfMovement smooths with an SMA                                       #
# --------------------------------------------------------------------------- #
def test_ease_of_movement_smoothing_is_an_sma(ohlcv):
    """DEFENDS AGAINST: "every neighbouring indicator here uses an EMA".

    StockCharts specifies a simple moving average for EOM. The surrounding code makes an EMA look
    like the house style, which is exactly how this gets "corrected" by mistake.
    """
    window = 14
    eom = EaseOfMovement.compute(
        {k: ohlcv[k] for k in ("high", "low", "volume")}, {"window": window}
    )
    a, b = _aligned(eom["sma_eom"], eom["eom"].rolling(window).mean())
    assert np.allclose(a, b), "EOM smoothing is no longer a simple moving average"


# --------------------------------------------------------------------------- #
# 9. KST follows Pring's construction                                         #
# --------------------------------------------------------------------------- #
def test_kst_matches_prings_construction(ohlcv):
    """DEFENDS AGAINST: a rewrite that changes the weighting or the ROC/SMA ordering.

    Pring: ROC periods 10/15/20/30, smoothed by SMA 10/10/10/15, weighted 1/2/3/4, signal a
    9-period SMA. Ours computes ROC as a fraction and scales by 100, which is algebraically
    identical to the percent form.
    """
    close = ohlcv["close"]
    params = dict(
        roc1=10, roc2=15, roc3=20, roc4=30,
        window1=10, window2=10, window3=10, window4=15, nsig=9,
    )
    kst = KST.compute({"close": close}, params)

    def roc(series, window):
        return series.diff(window) / series.shift(window)

    expected = (
        roc(close, 10).rolling(10).mean() * 1
        + roc(close, 15).rolling(10).mean() * 2
        + roc(close, 20).rolling(10).mean() * 3
        + roc(close, 30).rolling(15).mean() * 4
    ) * 100

    a, b = _aligned(kst["kst"], expected)
    assert np.allclose(a, b), "KST no longer matches Pring's weighted construction"

    a, b = _aligned(kst["kst_signal"], kst["kst"].rolling(9).mean())
    assert np.allclose(a, b), "KST signal line is no longer a 9-period SMA"


# --------------------------------------------------------------------------- #
# 10. Vortex takes absolute values on BOTH VM terms                           #
# --------------------------------------------------------------------------- #
def test_vortex_absolute_values_keep_vi_non_negative():
    """DEFENDS AGAINST: StockCharts' formula BLOCK, which omits the absolute value.

    Its own prose includes the absolute value; only the formula block drops it. An implementation
    "corrected" against that block admits negative VI readings. Constructed here with a decline
    steeper than the bar range, which makes the raw high[t] - low[t-1] term negative.
    """
    n = 80
    base = np.linspace(300, 50, n)
    idx = _idx(n)
    high = pd.Series(base + 0.5, index=idx)
    low = pd.Series(base - 0.5, index=idx)
    close = pd.Series(base, index=idx)

    raw_vm_plus = (high - low.shift(1)).dropna()
    assert raw_vm_plus.min() < 0, "test data no longer exercises the sign flip"

    vortex = Vortex.compute({"high": high, "low": low, "close": close}, {"window": 14})
    assert vortex["vortex_pos"].dropna().min() >= 0.0, "+VI went negative -- abs() was dropped"
    assert vortex["vortex_neg"].dropna().min() >= 0.0, "-VI went negative -- abs() was dropped"


# --------------------------------------------------------------------------- #
# 11. NVI compounds and seeds at 1000                                         #
# --------------------------------------------------------------------------- #
def test_nvi_is_multiplicative_and_seeds_at_1000(ohlcv):
    """DEFENDS AGAINST: StockCharts' prose ("Add the Percentage Price Change"), read as additive.

    That page never shows an equation. Incredible Charts and cTrader both write the multiplicative
    form explicitly, and ours compounds. The 1000 seed is the dominant convention and is a pure
    scale choice.
    """
    nvi = NVI.compute({k: ohlcv[k] for k in ("close", "volume")}, {"window": 255})["nvi"]
    assert math.isclose(nvi.iloc[0], 1000.0), "NVI seed changed"

    close, volume = ohlcv["close"], ohlcv["volume"]
    expected = 1000.0
    for i in range(1, len(close)):
        if volume.iloc[i] < volume.iloc[i - 1]:
            expected *= close.iloc[i] / close.iloc[i - 1]
    assert math.isclose(nvi.iloc[-1], expected, rel_tol=1e-9), "NVI is no longer multiplicative"


# --------------------------------------------------------------------------- #
# 12. ADI ignores the prior close entirely                                    #
# --------------------------------------------------------------------------- #
def test_adi_ignores_the_prior_close():
    """DEFENDS AGAINST: "ADI should consider the previous close, like OBV and VPT".

    It should not -- that is the defining difference. A security can gap down, close lower than
    yesterday, and still push this line UP if the close sits above its own bar's midpoint. Adding
    a prior-close term would reimplement OBV.
    """
    idx = _idx(2)
    adi = ADI.compute(
        {
            "high": pd.Series([101.0, 95.0], index=idx),
            "low": pd.Series([99.0, 85.0], index=idx),
            "close": pd.Series([100.0, 92.0], index=idx),  # gaps down, but closes above midpoint
            "volume": pd.Series([1000.0, 1000.0], index=idx),
        },
        {},
    )["adi"]
    assert adi.iloc[1] > adi.iloc[0], "ADI now reacts to the prior close"

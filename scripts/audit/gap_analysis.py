"""Gap analysis: MangroveKnowledgeBase indicators/signals vs reference libraries.

Compares our indicators and signals against:
  1. Bukosabino `ta` library (43 indicator classes)
  2. TA-Lib (158 functions across 8 groups)
  3. stock-indicators-python (85 indicator functions)

Outputs audit_results/gap_analysis.md with coverage matrix, missing
indicators by priority, missing signal patterns, and summary stats.
"""

from __future__ import annotations

import inspect
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


class SkipAudit(Exception):
    """Raised when a reference library this audit needs is not on this machine.

    Exits 77 -- the conventional "skipped" code -- so `run_all.py` can report SKIP rather
    than counting it as a pass. A skipped check reported as green is how a suite comes to
    claim coverage it does not have.
    """


# ---------------------------------------------------------------------------
# Step 1: Enumerate OUR indicators
# ---------------------------------------------------------------------------

def get_our_indicators() -> dict[str, list[str]]:
    """Return dict of category -> list of class names for mangrove_kb."""
    import mangrove_kb.indicators as ind_pkg
    from mangrove_kb.indicators import (
        momentum_indicators,
        trend_indicators,
        volatility_indicators,
        volume_indicators,
        pattern_indicators,
        return_indicators,
    )

    categorized: dict[str, list[str]] = {
        "Momentum": [],
        "Trend": [],
        "Volatility": [],
        "Volume": [],
        "Pattern": [],
        "Return": [],
    }

    module_map = {
        "Momentum": momentum_indicators,
        "Trend": trend_indicators,
        "Volatility": volatility_indicators,
        "Volume": volume_indicators,
        "Pattern": pattern_indicators,
        "Return": return_indicators,
    }

    for cat, mod in module_map.items():
        for name, obj in inspect.getmembers(mod):
            if inspect.isclass(obj) and obj.__module__ == mod.__name__:
                # Skip base/utility classes
                if name in ("IndicatorInterface",):
                    continue
                categorized[cat].append(name)
        categorized[cat].sort()

    return categorized


def get_our_signals() -> dict[str, list[str]]:
    """Return dict of category -> list of signal function names.

    Discovered, not hand-listed. The map here named five modules against the old category scheme and
    referenced `patterns` while importing `pattern` -- a NameError that made this script fail on
    every run. It was also stale in a way a typo fix would not have caught: the signal layer was
    reorganised onto the ontology classes, and the hand-written map had no entry for `averaging`
    (55 functions), `oscillator` (30) or `flow` (10), so a third of the library was invisible to the
    gap analysis while it reported a total.

    `patterns` is a deprecated shim re-exporting `pattern`; including it would count every pattern
    signal twice, so modules marked `__deprecated__` are skipped.
    """
    import mangrove_kb.signals as signals_pkg

    modules = [m for m in vars(signals_pkg).values()
               if getattr(m, "__name__", "").startswith("mangrove_kb.signals.")
               and not m.__name__.rsplit(".", 1)[-1].startswith("_")
               and not getattr(m, "__deprecated__", False)]

    categorized: dict[str, list[str]] = {}
    for mod in sorted(modules, key=lambda m: m.__name__):
        cat = mod.__name__.rsplit(".", 1)[-1].capitalize()
        names = sorted(name for name, obj in inspect.getmembers(mod)
                       if inspect.isfunction(obj) and obj.__module__ == mod.__name__
                       and not name.startswith("_"))
        if names:
            categorized[cat] = names
    return categorized


# ---------------------------------------------------------------------------
# Step 2: Enumerate reference library indicators
# ---------------------------------------------------------------------------

def get_bukosabino_indicators() -> dict[str, list[tuple[str, str]]]:
    """Return category -> [(class_name, description)] for Bukosabino ta."""
    import importlib

    modules = {
        "Momentum": "ta.momentum",
        "Trend": "ta.trend",
        "Volatility": "ta.volatility",
        "Volume": "ta.volume",
        "Other": "ta.others",
    }

    result: dict[str, list[tuple[str, str]]] = {}
    for cat, mod_name in modules.items():
        mod = importlib.import_module(mod_name)
        classes = []
        for name, obj in inspect.getmembers(mod):
            if inspect.isclass(obj) and obj.__module__ == mod_name:
                doc = (obj.__doc__ or "").strip().split("\n")[0]
                classes.append((name, doc))
        result[cat] = sorted(classes)

    return result


def get_talib_functions() -> dict[str, list[tuple[str, str]]]:
    """Return group -> [(function_name, description)] for TA-Lib.

    Since TA-Lib C library may not be installed, we parse the .pyi stub
    file to get function names, then classify by known TA-Lib groups.
    """
    # TA-Lib's Python stubs are not on PyPI as a file we can read, so this needs a checkout.
    # Overridable, and absent on any machine that is not this one -- including CI.
    # No default path. This is a public repository, and the previous default was one developer's
    # home directory -- which leaked a username and a local layout, and was wrong for everyone else
    # anyway. Point TALIB_PYI at a ta-lib-python checkout to include TA-Lib in the comparison.
    stub = os.environ.get("TALIB_PYI")
    if not stub or not Path(stub).is_file():
        print("SKIP: TA-Lib stubs not available. Set TALIB_PYI to `talib/_ta_lib.pyi` in a\n"
              "      ta-lib-python checkout to include TA-Lib in the gap analysis.", file=sys.stderr)
        raise SkipAudit()
    pyi_path = Path(stub)

    # Extract all uppercase function names (actual indicators, not stream_ variants)
    func_names = []
    with open(pyi_path) as f:
        for line in f:
            m = re.match(r"^def ([A-Z][A-Z0-9_]*)\(", line)
            if m:
                name = m.group(1)
                if not name.startswith("stream_"):
                    func_names.append(name)

    func_names = sorted(set(func_names))

    # Classify by known TA-Lib groups
    groups = {
        "Overlap Studies": [
            "BBANDS", "DEMA", "EMA", "HT_TRENDLINE", "KAMA", "MA", "MAMA",
            "MAVP", "MIDPOINT", "MIDPRICE", "SAR", "SAREXT", "SMA", "T3",
            "TEMA", "TRIMA", "WMA", "ACCBANDS",
        ],
        "Momentum": [
            "ADX", "ADXR", "APO", "AROON", "AROONOSC", "BOP", "CCI", "CMO",
            "DX", "MACD", "MACDEXT", "MACDFIX", "MFI", "MINUS_DI", "MINUS_DM",
            "MOM", "PLUS_DI", "PLUS_DM", "PPO", "ROC", "ROCP", "ROCR",
            "ROCR100", "RSI", "STOCH", "STOCHF", "STOCHRSI", "TRIX",
            "ULTOSC", "WILLR", "IMI",
        ],
        "Volume": ["AD", "ADOSC", "OBV"],
        "Volatility": ["ATR", "NATR", "TRANGE"],
        "Pattern Recognition": [n for n in func_names if n.startswith("CDL")],
        "Price Transform": ["AVGPRICE", "MEDPRICE", "TYPPRICE", "WCLPRICE"],
        "Cycle": ["HT_DCPERIOD", "HT_DCPHASE", "HT_PHASOR", "HT_SINE", "HT_TRENDMODE"],
        "Statistics": [
            "BETA", "CORREL", "LINEARREG", "LINEARREG_ANGLE",
            "LINEARREG_INTERCEPT", "LINEARREG_SLOPE", "STDDEV", "TSF", "VAR",
            "AVGDEV",
        ],
        "Math Transform": [
            "ACOS", "ASIN", "ATAN", "CEIL", "COS", "COSH", "EXP", "FLOOR",
            "LN", "LOG10", "SIN", "SINH", "SQRT", "TAN", "TANH",
        ],
        "Math Operators": ["ADD", "DIV", "MAX", "MAXINDEX", "MIN", "MININDEX",
                           "MINMAX", "MINMAXINDEX", "MULT", "SUB", "SUM"],
    }

    # Build descriptions
    talib_descriptions = {
        "BBANDS": "Bollinger Bands", "DEMA": "Double EMA", "EMA": "Exponential MA",
        "HT_TRENDLINE": "Hilbert Transform - Instantaneous Trendline",
        "KAMA": "Kaufman Adaptive MA", "MA": "Moving Average (generic)",
        "MAMA": "MESA Adaptive MA", "MAVP": "MA with Variable Period",
        "MIDPOINT": "MidPoint over period", "MIDPRICE": "Midpoint Price",
        "SAR": "Parabolic SAR", "SAREXT": "Parabolic SAR Extended",
        "SMA": "Simple MA", "T3": "Triple EMA (T3)", "TEMA": "Triple EMA",
        "TRIMA": "Triangular MA", "WMA": "Weighted MA", "ACCBANDS": "Acceleration Bands",
        "ADX": "Average Directional Index", "ADXR": "ADX Rating (smoothed ADX)",
        "APO": "Absolute Price Oscillator", "AROON": "Aroon",
        "AROONOSC": "Aroon Oscillator", "BOP": "Balance of Power",
        "CCI": "Commodity Channel Index", "CMO": "Chande Momentum Oscillator",
        "DX": "Directional Movement Index", "MACD": "MACD",
        "MACDEXT": "MACD with controllable MA type",
        "MACDFIX": "MACD Fix 12/26", "MFI": "Money Flow Index",
        "MINUS_DI": "Minus Directional Indicator", "MINUS_DM": "Minus Directional Movement",
        "MOM": "Momentum", "PLUS_DI": "Plus Directional Indicator",
        "PLUS_DM": "Plus Directional Movement", "PPO": "Percentage Price Oscillator",
        "ROC": "Rate of Change", "ROCP": "ROC Percentage",
        "ROCR": "ROC Ratio", "ROCR100": "ROC Ratio 100 scale",
        "RSI": "Relative Strength Index", "STOCH": "Stochastic",
        "STOCHF": "Stochastic Fast", "STOCHRSI": "Stochastic RSI",
        "TRIX": "Triple Smooth EMA ROC", "ULTOSC": "Ultimate Oscillator",
        "WILLR": "Williams %R", "IMI": "Intraday Momentum Index",
        "AD": "Accumulation/Distribution", "ADOSC": "A/D Oscillator (Chaikin)",
        "OBV": "On Balance Volume", "ATR": "Average True Range",
        "NATR": "Normalized ATR", "TRANGE": "True Range",
        "AVGPRICE": "Average Price", "MEDPRICE": "Median Price",
        "TYPPRICE": "Typical Price", "WCLPRICE": "Weighted Close Price",
        "HT_DCPERIOD": "Hilbert Transform - Dominant Cycle Period",
        "HT_DCPHASE": "Hilbert Transform - Dominant Cycle Phase",
        "HT_PHASOR": "Hilbert Transform - Phasor Components",
        "HT_SINE": "Hilbert Transform - SineWave",
        "HT_TRENDMODE": "Hilbert Transform - Trend vs Cycle Mode",
        "BETA": "Beta", "CORREL": "Pearson Correlation",
        "LINEARREG": "Linear Regression", "LINEARREG_ANGLE": "Linear Regression Angle",
        "LINEARREG_INTERCEPT": "Linear Regression Intercept",
        "LINEARREG_SLOPE": "Linear Regression Slope",
        "STDDEV": "Standard Deviation", "TSF": "Time Series Forecast",
        "VAR": "Variance", "AVGDEV": "Average Deviation",
    }

    result: dict[str, list[tuple[str, str]]] = {}
    for group, funcs in groups.items():
        items = []
        for fn in sorted(funcs):
            if fn in func_names:
                desc = talib_descriptions.get(fn, fn)
                items.append((fn, desc))
        result[group] = items

    return result


def get_stock_indicators() -> list[tuple[str, str]]:
    """Return [(indicator_name, description)] from stock-indicators-python."""
    # Parsed from the __init__.py imports and module file names
    indicators = [
        ("adl", "Accumulation/Distribution Line"),
        ("adx", "Average Directional Index"),
        ("alligator", "Williams Alligator (SMMA-based trend)"),
        ("alma", "Arnaud Legoux Moving Average"),
        ("aroon", "Aroon Indicator"),
        ("atr_stop", "ATR Trailing Stop"),
        ("atr", "Average True Range"),
        ("awesome", "Awesome Oscillator"),
        ("basic_quotes", "Basic Quote Transforms"),
        ("beta", "Beta Coefficient"),
        ("bollinger_bands", "Bollinger Bands"),
        ("bop", "Balance of Power"),
        ("cci", "Commodity Channel Index"),
        ("chaikin_oscillator", "Chaikin Oscillator (A/D Oscillator)"),
        ("chandelier", "Chandelier Exit"),
        ("chop", "Choppiness Index"),
        ("cmf", "Chaikin Money Flow"),
        ("cmo", "Chande Momentum Oscillator"),
        ("connors_rsi", "Connors RSI (composite RSI)"),
        ("correlation", "Correlation Coefficient"),
        ("doji", "Doji Pattern"),
        ("donchian", "Donchian Channel"),
        ("dema", "Double EMA"),
        ("dpo", "Detrended Price Oscillator"),
        ("dynamic", "McGinley Dynamic"),
        ("elder_ray", "Elder Ray Index (Bull/Bear Power)"),
        ("ema", "Exponential Moving Average"),
        ("epma", "Endpoint Moving Average"),
        ("fcb", "Fractal Chaos Bands"),
        ("fisher_transform", "Fisher Transform"),
        ("force_index", "Force Index"),
        ("fractal", "Williams Fractal"),
        ("gator", "Gator Oscillator"),
        ("heikin_ashi", "Heikin-Ashi Candles"),
        ("hma", "Hull Moving Average"),
        ("ht_trendline", "Hilbert Transform - Instantaneous Trendline"),
        ("hurst", "Hurst Exponent"),
        ("ichimoku", "Ichimoku Cloud"),
        ("kama", "Kaufman Adaptive Moving Average"),
        ("keltner", "Keltner Channel"),
        ("kvo", "Klinger Volume Oscillator"),
        ("macd", "MACD"),
        ("ma_envelopes", "Moving Average Envelopes"),
        ("mama", "MESA Adaptive Moving Average"),
        ("marubozu", "Marubozu Pattern"),
        ("mfi", "Money Flow Index"),
        ("obv", "On-Balance Volume"),
        ("parabolic_sar", "Parabolic SAR"),
        ("pivot_points", "Pivot Points"),
        ("pivots", "Pivots (Williams Fractal Pivots)"),
        ("pmo", "Price Momentum Oscillator"),
        ("prs", "Price Relative Strength"),
        ("pvo", "Percentage Volume Oscillator"),
        ("renko", "Renko Charts"),
        ("roc", "Rate of Change"),
        ("rolling_pivots", "Rolling Pivot Points"),
        ("rsi", "Relative Strength Index"),
        ("slope", "Slope (Linear Regression)"),
        ("sma", "Simple Moving Average"),
        ("smi", "Stochastic Momentum Index"),
        ("smma", "Smoothed Moving Average (SMMA/RMA)"),
        ("starc_bands", "STARC Bands"),
        ("stc", "Schaff Trend Cycle"),
        ("stdev_channels", "Standard Deviation Channels"),
        ("stdev", "Standard Deviation"),
        ("stoch", "Stochastic Oscillator"),
        ("stoch_rsi", "Stochastic RSI"),
        ("super_trend", "SuperTrend"),
        ("t3", "T3 Moving Average"),
        ("tema", "Triple EMA"),
        ("tr", "True Range"),
        ("trix", "TRIX"),
        ("tsi", "True Strength Index"),
        ("ulcer_index", "Ulcer Index"),
        ("ultimate", "Ultimate Oscillator"),
        ("volatility_stop", "Volatility Stop"),
        ("vortex", "Vortex Indicator"),
        ("vwap", "Volume Weighted Average Price"),
        ("vwma", "Volume Weighted Moving Average"),
        ("williams_r", "Williams %R"),
        ("wma", "Weighted Moving Average"),
        ("zig_zag", "Zig Zag"),
    ]
    return indicators


# ---------------------------------------------------------------------------
# Step 3: Build name mapping (our name -> canonical name -> ref names)
# ---------------------------------------------------------------------------

# Canonical mapping: our class name -> set of equivalent reference names
OUR_TO_CANONICAL = {
    # Momentum
    "RSI": {"RSIIndicator", "RSI", "rsi"},
    "StochasticOscillator": {"StochasticOscillator", "STOCH", "stoch"},
    "StochRSI": {"StochRSIIndicator", "STOCHRSI", "stoch_rsi"},
    "WilliamsR": {"WilliamsRIndicator", "WILLR", "williams_r"},
    "MACD": {"MACD", "MACD", "macd"},
    "ROC": {"ROCIndicator", "ROC", "roc"},
    "TSI": {"TSIIndicator", "TSI", "tsi"},  # note: TSI not in TA-Lib
    "KAMA": {"KAMAIndicator", "KAMA", "kama"},
    "AwesomeOscillator": {"AwesomeOscillatorIndicator", "awesome"},
    "UltimateOscillator": {"UltimateOscillator", "ULTOSC", "ultimate"},
    "PPO": {"PercentagePriceOscillator", "PPO", "ppo"},  # ppo not in stock-indicators
    "PVO": {"PercentageVolumeOscillator", "PVO", "pvo"},
    "STC": {"STCIndicator", "STC", "stc"},
    "KST": {"KSTIndicator"},
    "TRIX": {"TRIXIndicator", "TRIX", "trix"},
    # Trend
    "SMA": {"SMAIndicator", "SMA", "sma"},
    "EMA": {"EMAIndicator", "EMA", "ema"},
    "WMA": {"WMAIndicator", "WMA", "wma"},
    "ADX": {"ADXIndicator", "ADX", "adx"},
    "Aroon": {"AroonIndicator", "AROON", "aroon"},
    "CCI": {"CCIIndicator", "CCI", "cci"},
    "DPO": {"DPOIndicator", "DPO", "dpo"},
    "Ichimoku": {"IchimokuIndicator", "ichimoku"},
    "MassIndex": {"MassIndex"},
    "PSAR": {"PSARIndicator", "SAR", "parabolic_sar"},
    "Vortex": {"VortexIndicator", "vortex"},
    # Volatility
    "ATR": {"AverageTrueRange", "ATR", "atr"},
    "BollingerBands": {"BollingerBands", "BBANDS", "bollinger_bands"},
    "KeltnerChannel": {"KeltnerChannel", "keltner"},
    "DonchianChannel": {"DonchianChannel", "donchian"},
    "UlcerIndex": {"UlcerIndex", "ulcer_index"},
    # Volume
    "ADI": {"AccDistIndexIndicator", "AD", "adl"},
    "CMF": {"ChaikinMoneyFlowIndicator", "cmf"},
    "EaseOfMovement": {"EaseOfMovementIndicator"},
    "ForceIndex": {"ForceIndexIndicator", "force_index"},
    "MFI": {"MFIIndicator", "MFI", "mfi"},
    "NVI": {"NegativeVolumeIndexIndicator"},
    "OBV": {"OnBalanceVolumeIndicator", "OBV", "obv"},
    "VPT": {"VolumePriceTrendIndicator"},
    "VWAP": {"VolumeWeightedAveragePrice", "vwap"},
    # Return
    "DailyReturn": {"DailyReturnIndicator"},
    "DailyLogReturn": {"DailyLogReturnIndicator"},
    "CumulativeReturn": {"CumulativeReturnIndicator"},
    # Patterns
    "Doji": {"doji", "CDLDOJI"},
    "DragonflyDoji": {"CDLDRAGONFLYDOJI"},
    "GravestoneDoji": {"CDLGRAVESTONEDOJI"},
    "LongLeggedDoji": {"CDLLONGLEGGEDDOJI"},
    "Hammer": {"CDLHAMMER"},
    "HangingMan": {"CDLHANGINGMAN"},
    "InvertedHammer": {"CDLINVERTEDHAMMER"},
    "ShootingStar": {"CDLSHOOTINGSTAR"},
    "Engulfing": {"CDLENGULFING"},
    "Harami": {"CDLHARAMI"},
    "DarkCloudCover": {"CDLDARKCLOUDCOVER"},
    "PiercingLine": {"CDLPIERCING"},
    "MorningStar": {"CDLMORNINGSTAR"},
    "EveningStar": {"CDLEVENINGSTAR"},
    "ThreeWhiteSoldiers": {"CDL3WHITESOLDIERS"},
    "ThreeBlackCrows": {"CDL3BLACKCROWS"},
    "ThreeInsideUp": {"CDL3INSIDE"},
    "ThreeInsideDown": {"CDL3INSIDE"},  # same TA-Lib func, direction via sign
    "Marubozu": {"CDLMARUBOZU", "marubozu"},
    "SpinningTop": {"CDLSPINNINGTOP"},
    "InsideBar": set(),  # no direct equivalent in ref libs
    "OutsideBar": set(),
    "PinBar": set(),
    "TweezerBottoms": set(),
    "TweezerTops": set(),
    "TwoBarReversal": set(),
    "NarrowRange": set(),
}


def _normalize(name: str) -> str:
    """Lowercase, remove underscores/hyphens, strip common suffixes."""
    n = name.lower().replace("_", "").replace("-", "")
    for suffix in ("indicator", "oscillator", "index"):
        if n.endswith(suffix) and len(n) > len(suffix):
            n = n[: -len(suffix)]
    return n


# ---------------------------------------------------------------------------
# Step 4: Identify gaps -- reference indicators NOT in our library
# ---------------------------------------------------------------------------

def classify_missing() -> dict[str, list[dict]]:
    """Return {priority: [missing_indicator_info]} for each reference."""
    our_cats = get_our_indicators()
    all_ours = set()
    for names in our_cats.values():
        all_ours.update(names)
    our_normalized = {_normalize(n) for n in all_ours}

    # Also add canonical aliases for matching
    canonical_normalized = set()
    for aliases in OUR_TO_CANONICAL.values():
        for a in aliases:
            canonical_normalized.add(_normalize(a))

    all_known = our_normalized | canonical_normalized

    # Priority A: Standard indicators widely used in production trading
    priority_a_names = {
        # Moving averages
        "dema", "tema", "t3", "trima", "hma", "alma", "smma", "mama",
        "vwma", "epma",
        # Trend
        "supertrend", "chandelierexit", "chandelier", "alligator",
        "heikinashi",
        # Momentum
        "bop", "balanceofpower", "cmo", "chandemomentumosc",
        "mom", "momentum", "apo",
        # Volatility
        "natr", "trange", "truerange", "atrtrailingstop", "atrstop",
        "volatilitystop", "starcbands",
        # Volume
        "adosc", "chaikinoscillator", "kvo", "klingervolumeosc",
    }

    # Priority B: Niche but useful
    priority_b_names = {
        "hurst", "hurstexponent", "elderray", "connorsrsi",
        "fishertransform", "pmo", "pricemomentumoscill",
        "smi", "stochasticmomentum", "stdevchannels", "stdev",
        "slope", "linearreg", "linearregslope", "linearregangle",
        "pivot", "pivotpoints", "rollingpivots", "fractal",
        "gator", "gatoroscillator", "fcb", "fractalchaosbands",
        "zigzag", "renko", "dynamic", "mcginleydynamic",
        "maenvelopes", "prs", "pricerelativestrength",
        "beta", "correl", "correlation",
        "aroonosc",
    }

    # Priority C: Redundant variants, math operators, very niche
    priority_c_names = {
        "adxr", "macdext", "macdfix", "sarext", "mavp", "stochf",
        "rocp", "rocr", "rocr100", "dx", "minusdi", "minusdm",
        "plusdi", "plusdm", "imi",
        "avgprice", "medprice", "typprice", "wclprice",
        "midpoint", "midprice", "tsf", "var", "avgdev",
        "htdcperiod", "htdcphase", "htphasor", "htsine", "httrendmode",
        # Math ops
        "acos", "asin", "atan", "ceil", "cos", "cosh", "exp", "floor",
        "ln", "log10", "sin", "sinh", "sqrt", "tan", "tanh",
        "add", "div", "max", "maxindex", "min", "minindex",
        "minmax", "minmaxindex", "mult", "sub", "sum",
        # CDL patterns present only as niche variants
        "cdl2crows", "cdl3linestrike", "cdl3outside", "cdl3starsinsouth",
        "cdlabandonedbaby", "cdladvanceblock", "cdlbelthold", "cdlbreakaway",
        "cdlclosingmarubozu", "cdlconcealbabyswall", "cdlcounterattack",
        "cdldojistar", "cdleveningdojistar", "cdlgapsidesidewhite",
        "cdlhighwave", "cdlhikkake", "cdlhikkakemod", "cdlhomingpigeon",
        "cdlidentical3crows", "cdlinneck", "cdlkicking", "cdlkickingbylength",
        "cdlladderbottom", "cdllongline", "cdlmatchinglow", "cdlmathold",
        "cdlmorningdojistar", "cdlonneck", "cdlrickshawman",
        "cdlrisefall3methods", "cdlseparatinglines", "cdlshortline",
        "cdlstalledpattern", "cdlsticksandwich", "cdltakuri",
        "cdltasukigap", "cdlthrusting", "cdltristar", "cdlunique3river",
        "cdlupsidegap2crows", "cdlxsidegap3methods",
        "accbands",
        "basicquotes", "basicquote",
    }

    # ---- Check Bukosabino ta ----
    buko = get_bukosabino_indicators()
    buko_missing = []
    for cat, items in buko.items():
        for class_name, desc in items:
            n = _normalize(class_name)
            if n not in all_known:
                buko_missing.append({
                    "name": class_name, "desc": desc,
                    "library": "Bukosabino ta", "category": cat,
                })

    # ---- Check TA-Lib ----
    talib_groups = get_talib_functions()
    talib_missing = []
    for group, items in talib_groups.items():
        for func_name, desc in items:
            n = _normalize(func_name)
            if n not in all_known:
                talib_missing.append({
                    "name": func_name, "desc": desc,
                    "library": "TA-Lib", "category": group,
                })

    # ---- Check stock-indicators-python ----
    stock_ind = get_stock_indicators()
    stock_missing = []
    for ind_name, desc in stock_ind:
        n = _normalize(ind_name)
        if n not in all_known:
            stock_missing.append({
                "name": ind_name, "desc": desc,
                "library": "stock-indicators-python", "category": "",
            })

    # Classify into priorities
    all_missing = buko_missing + talib_missing + stock_missing

    # Cross-library equivalences (different names for the same indicator)
    # Map all aliases to a single canonical normalized name
    cross_lib_aliases = {
        "adosc": "adosc", "chaikinoscillator": "adosc", "chaikinosc": "adosc",
        "trange": "trange", "tr": "trange", "truerange": "trange",
        "stddev": "stddev", "stdev": "stddev",
        "linearregslope": "linearregslope", "slope": "linearregslope",
        "correl": "correl", "correlation": "correl",
        "beta": "beta",
        "httrendline": "httrendline", "httrendlin": "httrendline",
        "bop": "bop", "balanceofpower": "bop",
        "cmo": "cmo", "chandemomentumosc": "cmo",
        "dema": "dema",
        "tema": "tema",
        "t3": "t3",
        "mama": "mama",
        "trima": "trima",
    }

    # Deduplicate by normalized name, merging cross-library aliases
    seen = set()
    deduped: list[dict] = []
    for m in all_missing:
        n = _normalize(m["name"])
        canonical = cross_lib_aliases.get(n, n)
        if canonical not in seen:
            seen.add(canonical)
            # If there's a cross-library match, note both libraries
            other_libs = []
            for m2 in all_missing:
                n2 = _normalize(m2["name"])
                c2 = cross_lib_aliases.get(n2, n2)
                if c2 == canonical and m2["library"] != m["library"]:
                    other_libs.append(m2["library"])
            if other_libs:
                m = dict(m)  # copy
                m["library"] = m["library"] + ", " + ", ".join(sorted(set(other_libs)))
            deduped.append(m)

    priorities: dict[str, list[dict]] = {"A": [], "B": [], "C": []}
    for m in deduped:
        n = _normalize(m["name"])
        if n in priority_a_names:
            priorities["A"].append(m)
        elif n in priority_b_names:
            priorities["B"].append(m)
        elif n in priority_c_names:
            priorities["C"].append(m)
        else:
            # Check if it's a CDL pattern we haven't explicitly classified
            if m["name"].startswith("CDL") or m["name"].startswith("cdl"):
                priorities["C"].append(m)
            else:
                # Default: B (niche but useful)
                priorities["B"].append(m)

    for k in priorities:
        priorities[k].sort(key=lambda x: x["name"])

    return priorities


# ---------------------------------------------------------------------------
# Step 5: Signal gap analysis
# ---------------------------------------------------------------------------

def analyze_signal_gaps() -> dict:
    """Analyze signal coverage for existing indicators and identify patterns we lack."""
    our_inds = get_our_indicators()
    our_sigs = get_our_signals()

    # Flatten indicators
    all_indicators = {}
    for cat, names in our_inds.items():
        for name in names:
            all_indicators[name] = cat

    # Build map: indicator -> signals that reference it
    # Signal naming convention: indicator_name appears in signal function name
    indicator_signal_map: dict[str, list[str]] = defaultdict(list)

    all_sig_names = []
    for cat, sigs in our_sigs.items():
        all_sig_names.extend(sigs)

    # Match signals to indicators via naming patterns
    indicator_patterns = {
        "RSI": ["rsi_"],
        "StochasticOscillator": ["stoch_"],
        "StochRSI": ["stochrsi_"],
        "WilliamsR": ["williams_r_"],
        "MACD": ["macd_"],
        "ROC": ["roc_"],
        "TSI": ["tsi_"],
        "KAMA": ["kama_"],
        "AwesomeOscillator": ["ao_"],
        "UltimateOscillator": ["uo_"],
        "PPO": ["ppo_"],
        "PVO": ["pvo_"],
        "STC": ["stc_"],
        "KST": ["kst_"],
        "TRIX": ["trix_"],
        "SMA": ["sma_", "is_above_sma"],
        "EMA": ["ema_", "price_above_ema"],
        "WMA": ["wma_"],
        "ADX": ["adx_"],
        "Aroon": ["aroon_"],
        "CCI": ["cci_"],
        "DPO": ["dpo_"],
        "Ichimoku": ["ichimoku_"],
        "MassIndex": ["mass_"],
        "PSAR": ["psar_"],
        "Vortex": ["vortex_"],
        "ATR": ["atr_"],
        "BollingerBands": ["bb_"],
        "KeltnerChannel": ["kc_"],
        "DonchianChannel": ["dc_"],
        "UlcerIndex": ["ulcer_"],
        "ADI": ["adi_"],
        "CMF": ["cmf_"],
        "EaseOfMovement": ["eom_"],
        "ForceIndex": ["force_"],
        "MFI": ["mfi_"],
        "NVI": ["nvi_"],
        "OBV": ["obv_"],
        "VPT": ["vpt_"],
        "VWAP": ["vwap_"],
        "DailyReturn": ["daily_return_"],
        "DailyLogReturn": [],
        "CumulativeReturn": ["cumulative_return_"],
    }

    for ind, prefixes in indicator_patterns.items():
        for sig in all_sig_names:
            for prefix in prefixes:
                if sig.startswith(prefix) or sig == prefix.rstrip("_"):
                    indicator_signal_map[ind].append(sig)
                    break

    # Indicators with no signals
    no_signals = []
    for ind in all_indicators:
        if ind not in indicator_signal_map or len(indicator_signal_map[ind]) == 0:
            # Skip pattern indicators (they have pattern trigger signals)
            if all_indicators[ind] == "Pattern":
                continue
            no_signals.append(ind)

    # Indicators with thin signal coverage (only 1 signal)
    thin_coverage = []
    for ind, sigs in indicator_signal_map.items():
        if 0 < len(sigs) <= 1:
            thin_coverage.append((ind, sigs))

    # Missing signal patterns (common patterns we don't implement)
    missing_patterns = [
        {
            "pattern": "Divergence Detection",
            "description": "RSI/MACD/OBV divergence from price (bullish/bearish). "
                           "Price makes new high but indicator doesn't (bearish divergence), or vice versa. "
                           "One of the most reliable reversal signals.",
            "applicable_indicators": ["RSI", "MACD", "OBV", "StochasticOscillator", "CCI", "MFI"],
            "priority": "A",
        },
        {
            "pattern": "Multi-Timeframe Confirmation",
            "description": "Signal on one timeframe confirmed by same or related signal on higher timeframe. "
                           "E.g., RSI oversold on daily AND weekly.",
            "applicable_indicators": ["RSI", "MACD", "SMA", "EMA", "ADX"],
            "priority": "A",
        },
        {
            "pattern": "Moving Average Ribbon",
            "description": "Multiple MAs (e.g., 10/20/50/100/200) alignment for trend strength. "
                           "All MAs in order = strong trend. Tangled = consolidation.",
            "applicable_indicators": ["SMA", "EMA"],
            "priority": "A",
        },
        {
            "pattern": "Volatility Squeeze / Expansion",
            "description": "Bollinger Bands inside Keltner Channel (squeeze) then expansion breakout. "
                           "We have bb_squeeze but not the combined BB+KC squeeze (TTM Squeeze).",
            "applicable_indicators": ["BollingerBands", "KeltnerChannel"],
            "priority": "A",
        },
        {
            "pattern": "Volume Confirmation",
            "description": "Price breakout confirmed by above-average volume. "
                           "Currently signals evaluate volume indicators in isolation.",
            "applicable_indicators": ["OBV", "ADI", "VPT", "VWAP"],
            "priority": "B",
        },
        {
            "pattern": "Support/Resistance Levels",
            "description": "Price at pivot points, round numbers, or historical S/R levels. "
                           "We have no pivot point indicator or S/R detection.",
            "applicable_indicators": [],
            "priority": "B",
        },
        {
            "pattern": "Mean Reversion",
            "description": "Price deviation from mean (z-score based) with reversion signals. "
                           "Bollinger %B is close but explicit z-score signals are absent.",
            "applicable_indicators": ["BollingerBands", "SMA"],
            "priority": "B",
        },
        {
            "pattern": "Trend Strength Composite",
            "description": "Combine ADX + Aroon + Vortex for composite trend strength scoring. "
                           "Individual signals exist but no composite.",
            "applicable_indicators": ["ADX", "Aroon", "Vortex"],
            "priority": "B",
        },
        {
            "pattern": "Candlestick + Indicator Confirmation",
            "description": "Pattern signals confirmed by indicator state (e.g., Hammer at RSI oversold). "
                           "Currently pattern signals and indicator signals are independent.",
            "applicable_indicators": ["Hammer", "RSI", "StochasticOscillator"],
            "priority": "B",
        },
        {
            "pattern": "Range/Consolidation Detection",
            "description": "Detect sideways markets using ADX < threshold + narrowing BB + decreasing ATR. "
                           "Useful as a filter to avoid false breakout signals.",
            "applicable_indicators": ["ADX", "ATR", "BollingerBands"],
            "priority": "B",
        },
    ]

    return {
        "indicator_signal_map": dict(indicator_signal_map),
        "no_signals": sorted(no_signals),
        "thin_coverage": thin_coverage,
        "missing_patterns": missing_patterns,
    }


# ---------------------------------------------------------------------------
# Coverage matrix builder
# ---------------------------------------------------------------------------

def build_coverage_matrix() -> list[dict]:
    """Build per-indicator coverage across all three reference libraries."""
    our_cats = get_our_indicators()

    # All our indicators flat
    all_ours = []
    for cat, names in our_cats.items():
        for name in names:
            all_ours.append({"name": name, "category": cat})

    # Build flat reference sets (normalized names)
    buko = get_bukosabino_indicators()
    buko_names = set()
    for items in buko.values():
        for class_name, _ in items:
            buko_names.add(_normalize(class_name))

    talib_groups = get_talib_functions()
    talib_names = set()
    for items in talib_groups.values():
        for func_name, _ in items:
            talib_names.add(_normalize(func_name))

    stock = get_stock_indicators()
    stock_names = {_normalize(n) for n, _ in stock}

    matrix = []
    for ind in all_ours:
        name = ind["name"]
        aliases = OUR_TO_CANONICAL.get(name, set())
        all_aliases_normalized = {_normalize(name)} | {_normalize(a) for a in aliases}

        in_buko = bool(all_aliases_normalized & buko_names)
        in_talib = bool(all_aliases_normalized & talib_names)
        in_stock = bool(all_aliases_normalized & stock_names)

        matrix.append({
            "name": name,
            "category": ind["category"],
            "in_bukosabino": in_buko,
            "in_talib": in_talib,
            "in_stock_indicators": in_stock,
        })

    return matrix


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report() -> str:
    """Generate the full gap analysis markdown report."""
    lines = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    our_cats = get_our_indicators()
    our_sigs = get_our_signals()
    total_indicators = sum(len(v) for v in our_cats.values())
    total_signals = sum(len(v) for v in our_sigs.values())

    # Reference counts
    buko = get_bukosabino_indicators()
    buko_total = sum(len(v) for v in buko.values())

    talib_groups = get_talib_functions()
    # Exclude math transforms and math operators for meaningful comparison
    talib_trading = {k: v for k, v in talib_groups.items()
                     if k not in ("Math Transform", "Math Operators")}
    talib_total = sum(len(v) for v in talib_groups.values())
    talib_trading_total = sum(len(v) for v in talib_trading.values())

    stock = get_stock_indicators()
    stock_total = len(stock)

    matrix = build_coverage_matrix()
    priorities = classify_missing()
    signal_gaps = analyze_signal_gaps()

    # ---- Header ----
    lines.append("# Gap Analysis: MangroveKnowledgeBase vs Reference Libraries")
    lines.append("")
    lines.append(f"**Generated**: {now}")
    lines.append(f"**Our library**: {total_indicators} indicators, {total_signals} signals")
    lines.append("")

    # ---- Summary Statistics ----
    lines.append("## Summary Statistics")
    lines.append("")

    buko_covered = sum(1 for m in matrix if m["in_bukosabino"])
    talib_covered = sum(1 for m in matrix if m["in_talib"])
    stock_covered = sum(1 for m in matrix if m["in_stock_indicators"])

    lines.append("| Library | Their Total | Our Coverage | Coverage % | Notes |")
    lines.append("|---------|-----------|-------------|-----------|-------|")
    lines.append(f"| Bukosabino `ta` | {buko_total} | {buko_covered}/{buko_total} matched | "
                 f"{buko_covered / buko_total * 100:.0f}% | Full coverage of this library |")
    lines.append(f"| TA-Lib (trading) | {talib_trading_total} | {talib_covered}/{total_indicators} of ours map to TA-Lib | "
                 f"{talib_covered / total_indicators * 100:.0f}% | Excludes {talib_total - talib_trading_total} math/utility functions |")
    lines.append(f"| TA-Lib (all) | {talib_total} | -- | -- | Includes math transforms, operators |")
    lines.append(f"| stock-indicators-python | {stock_total} | {stock_covered}/{total_indicators} of ours map | "
                 f"{stock_covered / total_indicators * 100:.0f}% | Largest reference with {stock_total} indicators |")
    lines.append("")

    lines.append(f"**Missing indicator count by priority**:")
    lines.append(f"- Priority A (should add): {len(priorities['A'])}")
    lines.append(f"- Priority B (nice to have): {len(priorities['B'])}")
    lines.append(f"- Priority C (skip): {len(priorities['C'])}")
    lines.append("")

    # ---- Coverage Matrix ----
    lines.append("## Coverage Matrix")
    lines.append("")
    lines.append("Our indicators and which reference libraries have an equivalent:")
    lines.append("")
    lines.append("| # | Indicator | Category | Bukosabino ta | TA-Lib | stock-indicators |")
    lines.append("|---|-----------|----------|:---:|:---:|:---:|")

    for i, m in enumerate(sorted(matrix, key=lambda x: (x["category"], x["name"])), 1):
        b = "Y" if m["in_bukosabino"] else "-"
        t = "Y" if m["in_talib"] else "-"
        s = "Y" if m["in_stock_indicators"] else "-"
        lines.append(f"| {i} | {m['name']} | {m['category']} | {b} | {t} | {s} |")
    lines.append("")

    # Coverage by category
    lines.append("### Coverage by Category")
    lines.append("")
    lines.append("| Category | Count | In Bukosabino | In TA-Lib | In stock-indicators |")
    lines.append("|----------|-------|:---:|:---:|:---:|")
    for cat in sorted(our_cats.keys()):
        cat_items = [m for m in matrix if m["category"] == cat]
        cb = sum(1 for m in cat_items if m["in_bukosabino"])
        ct = sum(1 for m in cat_items if m["in_talib"])
        cs = sum(1 for m in cat_items if m["in_stock_indicators"])
        lines.append(f"| {cat} | {len(cat_items)} | {cb}/{len(cat_items)} | "
                     f"{ct}/{len(cat_items)} | {cs}/{len(cat_items)} |")
    lines.append("")

    # ---- Missing Indicators by Priority ----
    lines.append("## Missing Indicators by Priority")
    lines.append("")

    lines.append("### Priority A -- Should Add")
    lines.append("")
    lines.append("Standard indicators widely used in production trading systems.")
    lines.append("")
    if priorities["A"]:
        lines.append("| # | Indicator | Description | Found In |")
        lines.append("|---|-----------|-------------|----------|")
        for i, m in enumerate(priorities["A"], 1):
            lines.append(f"| {i} | **{m['name']}** | {m['desc']} | {m['library']} |")
    else:
        lines.append("*None -- full coverage of Priority A indicators.*")
    lines.append("")

    lines.append("### Priority B -- Nice to Have")
    lines.append("")
    lines.append("Niche but useful indicators for specialized strategies.")
    lines.append("")
    if priorities["B"]:
        lines.append("| # | Indicator | Description | Found In |")
        lines.append("|---|-----------|-------------|----------|")
        for i, m in enumerate(priorities["B"], 1):
            lines.append(f"| {i} | {m['name']} | {m['desc']} | {m['library']} |")
    else:
        lines.append("*None.*")
    lines.append("")

    lines.append("### Priority C -- Skip (Unless Requested)")
    lines.append("")
    lines.append("Redundant variants, math utilities, or very niche patterns.")
    lines.append("")
    if priorities["C"]:
        lines.append(f"<details><summary>{len(priorities['C'])} indicators (click to expand)</summary>")
        lines.append("")
        lines.append("| # | Indicator | Description | Found In |")
        lines.append("|---|-----------|-------------|----------|")
        for i, m in enumerate(priorities["C"], 1):
            lines.append(f"| {i} | {m['name']} | {m['desc']} | {m['library']} |")
        lines.append("")
        lines.append("</details>")
    lines.append("")

    # ---- Signal Gap Analysis ----
    lines.append("## Signal Gap Analysis")
    lines.append("")

    # Signal coverage summary
    lines.append("### Signal Coverage per Indicator")
    lines.append("")
    lines.append("| Category | Indicator | Signal Count | Signals |")
    lines.append("|----------|-----------|:-----------:|---------|")

    sig_map = signal_gaps["indicator_signal_map"]
    for cat in sorted(our_cats.keys()):
        if cat == "Pattern":
            continue  # Pattern signals use different naming
        for ind in sorted(our_cats[cat]):
            sigs = sig_map.get(ind, [])
            sig_str = ", ".join(f"`{s}`" for s in sigs) if sigs else "*none*"
            lines.append(f"| {cat} | {ind} | {len(sigs)} | {sig_str} |")
    lines.append("")

    # Indicators with no signals
    lines.append("### Indicators with No Signal Coverage")
    lines.append("")
    if signal_gaps["no_signals"]:
        for ind in signal_gaps["no_signals"]:
            lines.append(f"- **{ind}** ({all_ours_dict.get(ind, '?')})" if False else f"- **{ind}**")
    else:
        lines.append("*All non-pattern indicators have at least one signal.*")
    lines.append("")

    # Missing signal patterns
    lines.append("### Missing Signal Patterns")
    lines.append("")
    lines.append("Common trading signal patterns not currently implemented:")
    lines.append("")

    for i, pat in enumerate(signal_gaps["missing_patterns"], 1):
        pri = pat["priority"]
        lines.append(f"**{i}. {pat['pattern']}** (Priority {pri})")
        lines.append(f"")
        lines.append(f"{pat['description']}")
        if pat["applicable_indicators"]:
            lines.append(f"")
            lines.append(f"Applicable to: {', '.join(pat['applicable_indicators'])}")
        lines.append("")

    # ---- Recommendations ----
    lines.append("## Recommendations")
    lines.append("")
    lines.append("### Immediate (Priority A Indicators)")
    lines.append("")
    a_inds = [m["name"] for m in priorities["A"]]
    if a_inds:
        lines.append(f"Add these {len(a_inds)} indicators to reach parity with standard trading libraries:")
        lines.append("")
        # Group by type
        ma_types = [n for n in a_inds if any(k in n.lower() for k in
                    ["ema", "ma", "hma", "alma", "smma", "vwma", "mama", "epma", "tema", "dema", "t3", "trima"])]
        trend_types = [n for n in a_inds if n not in ma_types and any(k in n.lower() for k in
                       ["trend", "chandelier", "alligator", "heikin"])]
        momentum_types = [n for n in a_inds if n not in ma_types and n not in trend_types and any(k in n.lower() for k in
                          ["bop", "cmo", "mom", "apo"])]
        vol_types = [n for n in a_inds if n not in ma_types and n not in trend_types and n not in momentum_types
                     and any(k in n.lower() for k in ["natr", "trange", "atr", "volatility", "starc"])]
        volume_types = [n for n in a_inds if n not in ma_types and n not in trend_types
                        and n not in momentum_types and n not in vol_types]

        if ma_types:
            lines.append(f"- **Moving Averages**: {', '.join(ma_types)}")
        if trend_types:
            lines.append(f"- **Trend**: {', '.join(trend_types)}")
        if momentum_types:
            lines.append(f"- **Momentum**: {', '.join(momentum_types)}")
        if vol_types:
            lines.append(f"- **Volatility**: {', '.join(vol_types)}")
        if volume_types:
            lines.append(f"- **Volume**: {', '.join(volume_types)}")
    lines.append("")

    lines.append("### High-Impact Signal Patterns")
    lines.append("")
    lines.append("These signal patterns would significantly increase the library's value:")
    lines.append("")
    a_patterns = [p for p in signal_gaps["missing_patterns"] if p["priority"] == "A"]
    for p in a_patterns:
        lines.append(f"1. **{p['pattern']}** -- {p['description'].split('.')[0]}.")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Running MangroveKnowledgeBase gap analysis...")
    print()

    # Step 1: Our indicators
    our_cats = get_our_indicators()
    total = sum(len(v) for v in our_cats.values())
    print(f"Step 1: Found {total} indicators in mangrove_kb")
    for cat, names in sorted(our_cats.items()):
        print(f"  {cat}: {len(names)}")

    # Step 1b: Our signals
    our_sigs = get_our_signals()
    total_sigs = sum(len(v) for v in our_sigs.values())
    print(f"  Signals: {total_sigs} total")
    for cat, names in sorted(our_sigs.items()):
        print(f"    {cat}: {len(names)}")
    print()

    # Step 2: Reference libraries
    print("Step 2: Enumerating reference libraries")
    buko = get_bukosabino_indicators()
    buko_total = sum(len(v) for v in buko.values())
    print(f"  Bukosabino ta: {buko_total} indicator classes")

    talib = get_talib_functions()
    talib_total = sum(len(v) for v in talib.values())
    print(f"  TA-Lib: {talib_total} functions")

    stock = get_stock_indicators()
    print(f"  stock-indicators-python: {len(stock)} indicators")
    print()

    # Step 3-4: Coverage and gaps
    print("Step 3-4: Building coverage matrix and identifying gaps")
    matrix = build_coverage_matrix()
    priorities = classify_missing()
    print(f"  Priority A (should add): {len(priorities['A'])}")
    print(f"  Priority B (nice to have): {len(priorities['B'])}")
    print(f"  Priority C (skip): {len(priorities['C'])}")
    print()

    # Step 5: Signal gaps
    print("Step 5: Analyzing signal coverage")
    sig_gaps = analyze_signal_gaps()
    print(f"  Indicators with no signals: {len(sig_gaps['no_signals'])}")
    print(f"  Missing signal patterns: {len(sig_gaps['missing_patterns'])}")
    print()

    # Generate report
    print("Generating report...")
    report = generate_report()

    output_path = Path(__file__).parent.parent.parent / "audit_results" / "gap_analysis.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report)
    print(f"Report written to: {output_path}")
    print()

    # Print summary to stdout
    print("=" * 70)
    print("GAP ANALYSIS SUMMARY")
    print("=" * 70)
    print(f"Our library: {total} indicators, {total_sigs} signals")
    print(f"Bukosabino ta: {buko_total} classes  |  TA-Lib: {talib_total} funcs  |  stock-indicators: {len(stock)}")
    print()
    print(f"Priority A gaps (should add): {len(priorities['A'])}")
    for m in priorities["A"]:
        print(f"  - {m['name']}: {m['desc']} [{m['library']}]")
    print()
    print(f"Priority B gaps (nice to have): {len(priorities['B'])}")
    for m in priorities["B"]:
        print(f"  - {m['name']}: {m['desc']} [{m['library']}]")
    print()
    print(f"Priority C (skip): {len(priorities['C'])} indicators (math ops, redundant variants, niche patterns)")
    print()

    a_patterns = [p for p in sig_gaps["missing_patterns"] if p["priority"] == "A"]
    print(f"High-impact missing signal patterns:")
    for p in a_patterns:
        print(f"  - {p['pattern']}: {p['description'].split('.')[0]}")


if __name__ == "__main__":
    try:
        main()
    except SkipAudit:
        sys.exit(77)          # see SkipAudit: reported as SKIP, never as a pass

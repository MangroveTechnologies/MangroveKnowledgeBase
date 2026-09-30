"""Signals still grouped by use case, not by ontology class.

`trend` is not one of the seven classes on the ontology's axis -- it is a use-case grouping that
predates the class axis. Every signal that lived here has moved to the file named for the class of
the indicator it reads: `averaging.py`, `momentum.py`, `oscillator.py` and `volatility.py`.

Nothing is defined here now. The module stays because registered signal names never change when a
signal moves, and neither should the import path a consumer already uses: every name that was in
this file when 1.3.4 shipped still resolves from it, with a DeprecationWarning naming the file it
lives in. `mangrove_kb.signals.volume` and `.patterns` show what a rename costs consumers.
"""


from mangrove_kb.signals._common import moved_signals


# Signals that were in this file when 1.3.4 shipped and are now in the file named for
# their ontology class. Reached by name, with a DeprecationWarning.
_MOVED = {
    "averaging": (
        "alligator_bearish", "alligator_bullish", "alligator_sleeping", "alma_cross_down",
        "alma_cross_up", "dema_cross_down", "dema_cross_up", "ema_cross_down", "ema_cross_up",
        "ema_crossover", "epma_cross_down", "epma_cross_up", "heikin_ashi_bearish",
        "heikin_ashi_bullish", "hma_cross_down", "hma_cross_up", "ichimoku_bearish",
        "ichimoku_bullish", "ichimoku_tk_cross", "is_above_alma", "is_above_dema",
        "is_above_epma", "is_above_hma", "is_above_mama", "is_above_sma", "is_above_smma",
        "is_above_t3", "is_above_tema", "is_above_trima", "ma_ribbon_bearish",
        "ma_ribbon_bullish", "ma_ribbon_tangled", "mama_cross_down", "mama_cross_up",
        "price_above_ema", "psar_bearish", "psar_bullish", "psar_reversal",
        "sma_cross_down", "sma_cross_up", "sma_crossover",
        "smma_cross_down", "smma_cross_up", "t3_cross_down", "t3_cross_up", "tema_cross_down",
        "tema_cross_up", "trima_cross_down", "trima_cross_up", "wma_cross_down",
        "wma_cross_up"
    ),
    "momentum": (
        "adx_bullish_di", "adx_strong_trend", "aroon_crossover", "aroon_down_trend",
        "aroon_up_trend", "dpo_negative", "dpo_positive", "kst_bearish_cross",
        "kst_bullish_cross", "macd_bearish_cross", "macd_bullish_cross", "macd_positive",
        "mass_reversal_signal", "multi_tf_trend_bearish", "multi_tf_trend_bullish",
        "rsi_bearish_divergence", "rsi_bullish_divergence", "rsi_hidden_bearish_divergence",
        "rsi_hidden_bullish_divergence", "trix_bearish", "trix_bullish", "vortex_bearish",
        "vortex_bullish", "vortex_crossover"
    ),
    "oscillator": (
        "cci_overbought", "cci_oversold", "stc_overbought", "stc_oversold"
    ),
    "volatility": (
        "chandelier_long_stop_hit", "chandelier_short_stop_hit", "supertrend_flip_down",
        "supertrend_flip_up", "supertrend_long", "supertrend_short", "ttm_squeeze_active",
        "ttm_squeeze_fired_bearish", "ttm_squeeze_fired_bullish"
    ),
}

_moved_getattr = moved_signals("mangrove_kb.signals.trend", _MOVED)

__getattr__ = _moved_getattr

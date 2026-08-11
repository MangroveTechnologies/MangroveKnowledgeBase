"""Deprecated import path. `patterns.py` is now `pattern.py`.

Signal files are named for the ontology class they hold, and the class is `pattern` -- singular,
matching `concept:pattern` in the ontology and the `Pattern` category the API
reports. The plural was the only file name that did not match its class.

**Registered signal names are unchanged.** A stored strategy is unaffected: it names a signal, and
`RuleRegistry.evaluate` looks that name up in a dict. This module exists only so that code which
imports the old *path* keeps working -- it binds names to the functions in `pattern.py` and defines
nothing itself. It does not re-register anything; registration happens when the real module is
imported and is keyed by name.

It does not restore the old `Patterns` category value either -- see
https://github.com/MangroveTechnologies/MangroveKnowledgeBase/issues/107.

Migrate to `mangrove_kb.signals.pattern`; this file is intended to be removed.
"""

import warnings

#: Marks this module as a back-compat shim rather than a home for signals. Importing a shim binds
#: it as an attribute of `mangrove_kb.signals`, so anything discovering signal modules by walking
#: the package namespace would otherwise pick it up and see every re-exported function a second
#: time, under a module that does not define it.
__deprecated__ = True

from mangrove_kb.signals.pattern import (
    bearish_engulfing_trigger,
    bearish_harami_trigger,
    bearish_pattern_recent,
    bearish_pin_bar_trigger,
    bullish_engulfing_trigger,
    bullish_harami_trigger,
    bullish_pattern_recent,
    bullish_pin_bar_trigger,
    continuation_pattern_bearish,
    continuation_pattern_bullish,
    dark_cloud_cover_trigger,
    doji_trigger,
    dragonfly_doji_trigger,
    evening_star_trigger,
    gravestone_doji_trigger,
    hammer_trigger,
    hanging_man_trigger,
    indecision_pattern_recent,
    inside_bar_trigger,
    inverted_hammer_trigger,
    long_legged_doji_trigger,
    marubozu_bearish_trigger,
    marubozu_bullish_trigger,
    morning_star_trigger,
    nr7_trigger,
    outside_bar_trigger,
    piercing_line_trigger,
    reversal_pattern_bearish,
    reversal_pattern_bullish,
    shooting_star_trigger,
    spinning_top_trigger,
    strong_body_recent,
    three_black_crows_trigger,
    three_inside_down_trigger,
    three_inside_up_trigger,
    three_white_soldiers_trigger,
    tweezer_bottoms_trigger,
    tweezer_tops_trigger,
    two_bar_reversal_bearish_trigger,
    two_bar_reversal_bullish_trigger,
)

warnings.warn(
    "mangrove_kb.signals.patterns is deprecated: the module is now mangrove_kb.signals.pattern, "
    "named for the ontology class it holds. Registered signal names are unchanged, so strategies "
    "are unaffected.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "bearish_engulfing_trigger",
    "bearish_harami_trigger",
    "bearish_pattern_recent",
    "bearish_pin_bar_trigger",
    "bullish_engulfing_trigger",
    "bullish_harami_trigger",
    "bullish_pattern_recent",
    "bullish_pin_bar_trigger",
    "continuation_pattern_bearish",
    "continuation_pattern_bullish",
    "dark_cloud_cover_trigger",
    "doji_trigger",
    "dragonfly_doji_trigger",
    "evening_star_trigger",
    "gravestone_doji_trigger",
    "hammer_trigger",
    "hanging_man_trigger",
    "indecision_pattern_recent",
    "inside_bar_trigger",
    "inverted_hammer_trigger",
    "long_legged_doji_trigger",
    "marubozu_bearish_trigger",
    "marubozu_bullish_trigger",
    "morning_star_trigger",
    "nr7_trigger",
    "outside_bar_trigger",
    "piercing_line_trigger",
    "reversal_pattern_bearish",
    "reversal_pattern_bullish",
    "shooting_star_trigger",
    "spinning_top_trigger",
    "strong_body_recent",
    "three_black_crows_trigger",
    "three_inside_down_trigger",
    "three_inside_up_trigger",
    "three_white_soldiers_trigger",
    "tweezer_bottoms_trigger",
    "tweezer_tops_trigger",
    "two_bar_reversal_bearish_trigger",
    "two_bar_reversal_bullish_trigger",
]

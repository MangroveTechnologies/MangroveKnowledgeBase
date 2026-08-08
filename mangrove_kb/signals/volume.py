"""Deprecated import path. `volume.py` was split by ontology class and no longer holds code.

There is no `volume` indicator class: the class of a signal comes from the indicator it reads, and
these 33 signals read indicators from four different classes. Grouping them by the data they happen
to consume put four classes in one file.

    flow        10  running accumulations -- OBV, ADI, VPT, NVI, CumulativeReturn
    momentum    14  rate of change -- ADOSC, ForceIndex, EaseOfMovement, KVO, DailyReturn
    averaging    5  reference levels in price units -- VWAP, VWMA
    oscillator   4  bounded, so absolute thresholds mean something -- CMF, MFI

**Registered signal names are unchanged.** A stored strategy is unaffected: it names a signal, and
`RuleRegistry.evaluate` looks that name up in a dict. This module exists only so that code which
imports the old *path* keeps working -- it binds names to the functions in their new homes and
defines nothing itself.

Two things it deliberately does not do. It does not re-register anything: registration happens when
the real module is imported and is keyed by name, so importing this changes no behaviour. And it
does not restore the old `category` value -- that is derived from where a function is defined, so
`obv_bullish` reports `Flow`. See
https://github.com/MangroveTechnologies/MangroveKnowledgeBase/issues/107.

Migrate to the real modules; this file is intended to be removed.
"""

import warnings

from mangrove_kb.signals.averaging import (
    is_above_vwma,
    vwap_above,
    vwap_below,
    vwma_cross_down,
    vwma_cross_up,
)
from mangrove_kb.signals.flow import (
    adi_bearish,
    adi_bullish,
    cumulative_return_positive,
    cumulative_return_target,
    nvi_bearish,
    nvi_bullish,
    obv_bearish,
    obv_bullish,
    vpt_bearish,
    vpt_bullish,
)
from mangrove_kb.signals.momentum import (
    adosc_bearish,
    adosc_bullish,
    adosc_cross_down,
    adosc_cross_up,
    daily_return_negative,
    daily_return_positive,
    eom_bearish,
    eom_bullish,
    force_bearish,
    force_bullish,
    kvo_bearish,
    kvo_bearish_cross,
    kvo_bullish,
    kvo_bullish_cross,
)
from mangrove_kb.signals.oscillator import (
    cmf_bearish,
    cmf_bullish,
    mfi_overbought,
    mfi_oversold,
)

warnings.warn(
    "mangrove_kb.signals.volume is deprecated: there is no `volume` indicator class, and its "
    "signals moved to flow, momentum, averaging and oscillator by the class of the indicator each "
    "one reads. Registered signal names are unchanged, so strategies are unaffected. Import from "
    "the new modules, or use RuleRegistry, which never depended on the file layout.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "adi_bearish",
    "adi_bullish",
    "adosc_bearish",
    "adosc_bullish",
    "adosc_cross_down",
    "adosc_cross_up",
    "cmf_bearish",
    "cmf_bullish",
    "cumulative_return_positive",
    "cumulative_return_target",
    "daily_return_negative",
    "daily_return_positive",
    "eom_bearish",
    "eom_bullish",
    "force_bearish",
    "force_bullish",
    "is_above_vwma",
    "kvo_bearish",
    "kvo_bearish_cross",
    "kvo_bullish",
    "kvo_bullish_cross",
    "mfi_overbought",
    "mfi_oversold",
    "nvi_bearish",
    "nvi_bullish",
    "obv_bearish",
    "obv_bullish",
    "vpt_bearish",
    "vpt_bullish",
    "vwap_above",
    "vwap_below",
    "vwma_cross_down",
    "vwma_cross_up",
]

#!/usr/bin/env python3
"""Audit volume indicators against Bukosabino ta reference."""
import sys
sys.path.insert(0, "scripts")

from audit import load_btc_daily
from audit.compare import compare_indicator
from audit.config import get_tolerance

from mangrove_kb.indicators.volume_indicators import (
    ADI,
    OBV,
    CMF,
    ForceIndex,
    EaseOfMovement,
    VPT,
    NVI,
    MFI,
    VWAP,
)
import ta.volume


def run_audit():
    df = load_btc_daily()
    close = df['close']
    high = df['high']
    low = df['low']
    volume = df['volume']
    results = []

    # --- ADI ---
    tol, tier = get_tolerance("ADI")
    results.append(compare_indicator(
        indicator_name="ADI",
        category="Volume",
        our_fn=lambda: ADI.compute(
            {'high': high, 'low': low, 'close': close, 'volume': volume}, {}
        ),
        ref_fn=lambda: {
            'adi': ta.volume.AccDistIndexIndicator(
                high=high, low=low, close=close, volume=volume, fillna=False,
            ).acc_dist_index()
        },
        output_keys=['adi'],
        tolerance=tol,
        tolerance_tier=tier,
    ))

    # --- OBV ---
    tol, tier = get_tolerance("OBV")
    results.append(compare_indicator(
        indicator_name="OBV",
        category="Volume",
        # Compare the BAR-TO-BAR CHANGE, not the level. OBV is a running accumulation whose
        # starting point is arbitrary -- `ta` seeds it at volume[0], we seed at 0 -- so the two
        # series differ by a constant equal to the first bar's volume (measured: offset
        # -144210.16219 on every one of 1,294 bars, spread 2.97e-09). The level carries no meaning
        # on its own; the direction does, which is exactly why the ontology puts OBV in the `flow`
        # class: "running accumulation whose level is arbitrary but whose direction carries
        # meaning". Differencing removes the seed and tests the thing that means something --
        # measured max |diff of diffs| = 4.66e-10.
        our_fn=lambda: {
            'obv': OBV.compute({'close': close, 'volume': volume}, {})['obv'].diff()
        },
        ref_fn=lambda: {
            'obv': ta.volume.OnBalanceVolumeIndicator(
                close=close, volume=volume, fillna=False,
            ).on_balance_volume().diff()
        },
        output_keys=['obv'],
        tolerance=tol,
        tolerance_tier=tier,
        # Relative: the compared values are volumes (~1e5) and a cumulative sum of 1,294 such terms
        # cannot be bit-identical to one summed in a different order. The residual is 4.66e-10
        # absolute, about 5e-15 relative.
        relative=True,
        notes="Compared as bar-to-bar change: the accumulation's origin is arbitrary and the two "
              "libraries seed it differently (ta at volume[0], we at 0).",
    ))

    # --- CMF ---
    cmf_window = 20
    tol, tier = get_tolerance("CMF")
    results.append(compare_indicator(
        indicator_name="CMF",
        category="Volume",
        our_fn=lambda: CMF.compute(
            {'high': high, 'low': low, 'close': close, 'volume': volume},
            {'window': cmf_window},
        ),
        ref_fn=lambda: {
            'cmf': ta.volume.ChaikinMoneyFlowIndicator(
                high=high, low=low, close=close, volume=volume,
                window=cmf_window, fillna=False,
            ).chaikin_money_flow()
        },
        output_keys=['cmf'],
        tolerance=tol,
        tolerance_tier=tier,
    ))

    # --- ForceIndex ---
    fi_window = 13
    tol, tier = get_tolerance("ForceIndex")
    results.append(compare_indicator(
        indicator_name="ForceIndex",
        category="Volume",
        our_fn=lambda: ForceIndex.compute(
            {'close': close, 'volume': volume},
            {'window': fi_window},
        ),
        ref_fn=lambda: {
            'fi': ta.volume.ForceIndexIndicator(
                close=close, volume=volume, window=fi_window, fillna=False,
            ).force_index()
        },
        output_keys=['fi'],
        tolerance=tol,
        tolerance_tier=tier,
    ))

    # --- EaseOfMovement ---
    eom_window = 14
    tol, tier = get_tolerance("EaseOfMovement")
    results.append(compare_indicator(
        indicator_name="EaseOfMovement",
        category="Volume",
        our_fn=lambda: EaseOfMovement.compute(
            {'high': high, 'low': low, 'volume': volume},
            {'window': eom_window},
        ),
        ref_fn=lambda: {
            'eom': ta.volume.EaseOfMovementIndicator(
                high=high, low=low, volume=volume,
                window=eom_window, fillna=False,
            ).ease_of_movement(),
            'sma_eom': ta.volume.EaseOfMovementIndicator(
                high=high, low=low, volume=volume,
                window=eom_window, fillna=False,
            ).sma_ease_of_movement(),
        },
        output_keys=['eom', 'sma_eom'],
        tolerance=tol,
        tolerance_tier=tier,
    ))

    # --- VPT ---
    tol, tier = get_tolerance("VPT")
    results.append(compare_indicator(
        indicator_name="VPT",
        category="Volume",
        our_fn=lambda: VPT.compute(
            {'close': close, 'volume': volume},
            {'smoothing_factor': None, 'dropnans': False},
        ),
        ref_fn=lambda: {
            'vpt': ta.volume.VolumePriceTrendIndicator(
                close=close, volume=volume, fillna=False,
                smoothing_factor=None, dropnans=False,
            ).volume_price_trend()
        },
        output_keys=['vpt'],
        tolerance=tol,
        tolerance_tier=tier,
    ))

    # --- NVI ---
    tol, tier = get_tolerance("NVI")
    results.append(compare_indicator(
        indicator_name="NVI",
        category="Volume",
        our_fn=lambda: NVI.compute(
            {'close': close, 'volume': volume},
            {'window': 255},
        ),
        ref_fn=lambda: {
            'nvi': ta.volume.NegativeVolumeIndexIndicator(
                close=close, volume=volume, fillna=False,
            ).negative_volume_index()
        },
        output_keys=['nvi'],
        tolerance=tol,
        tolerance_tier=tier,
        notes="comparing nvi only (ref has no nvi_ema output)",
    ))

    # --- MFI ---
    mfi_window = 14
    tol, tier = get_tolerance("MFI")
    results.append(compare_indicator(
        indicator_name="MFI",
        category="Volume",
        our_fn=lambda: MFI.compute(
            {'high': high, 'low': low, 'close': close, 'volume': volume},
            {'window': mfi_window},
        ),
        ref_fn=lambda: {
            'mfi': ta.volume.MFIIndicator(
                high=high, low=low, close=close, volume=volume,
                window=mfi_window, fillna=False,
            ).money_flow_index()
        },
        output_keys=['mfi'],
        tolerance=tol,
        tolerance_tier=tier,
    ))

    # --- VWAP ---
    vwap_window = 14
    tol, tier = get_tolerance("VWAP")
    results.append(compare_indicator(
        indicator_name="VWAP",
        category="Volume",
        our_fn=lambda: VWAP.compute(
            {'high': high, 'low': low, 'close': close, 'volume': volume},
            {'window': vwap_window},
        ),
        ref_fn=lambda: {
            'vwap': ta.volume.VolumeWeightedAveragePrice(
                high=high, low=low, close=close, volume=volume,
                window=vwap_window, fillna=False,
            ).volume_weighted_average_price()
        },
        output_keys=['vwap'],
        tolerance=tol,
        tolerance_tier=tier,
    ))

    return results


if __name__ == "__main__":
    results = run_audit()
    for r in results:
        status = "PASS" if r.pass_fail else "FAIL"
        errors = ", ".join(f"{k}={v.max_abs_error:.2e}" for k, v in r.outputs.items())
        notes = f" [{r.notes}]" if r.notes else ""
        print(f"  {r.indicator_name}: {status} ({errors}){notes}")

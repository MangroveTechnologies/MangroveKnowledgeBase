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
        our_fn=lambda: OBV.compute(
            {'close': close, 'volume': volume}, {}
        ),
        ref_fn=lambda: {
            'obv': ta.volume.OnBalanceVolumeIndicator(
                close=close, volume=volume, fillna=False,
            ).on_balance_volume()
        },
        output_keys=['obv'],
        tolerance=tol,
        tolerance_tier=tier,
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

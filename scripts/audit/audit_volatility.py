#!/usr/bin/env python3
"""Audit volatility indicators against Bukosabino ta reference."""
import sys
sys.path.insert(0, "scripts")

from audit import load_btc_daily
from audit.compare import compare_indicator
from audit.config import get_tolerance

from mangrove_kb.indicators.volatility_indicators import (
    ATR,
    BollingerBands,
    KeltnerChannel,
    DonchianChannel,
    UlcerIndex,
)
import ta.volatility


def run_audit():
    df = load_btc_daily()
    close = df['close']
    high = df['high']
    low = df['low']
    results = []

    # --- ATR ---
    window = 14
    tol, tier = get_tolerance("ATR")
    results.append(compare_indicator(
        indicator_name="ATR",
        category="Volatility",
        our_fn=lambda: ATR.compute(
            {'high': high, 'low': low, 'close': close},
            {'window': window},
        ),
        ref_fn=lambda: {
            'atr': ta.volatility.AverageTrueRange(
                high=high, low=low, close=close, window=window, fillna=False
            ).average_true_range()
        },
        output_keys=['atr'],
        tolerance=tol,
        tolerance_tier=tier,
    ))

    # --- BollingerBands ---
    bb_window = 20
    bb_dev = 2
    tol, tier = get_tolerance("BollingerBands")
    results.append(compare_indicator(
        indicator_name="BollingerBands",
        category="Volatility",
        our_fn=lambda: BollingerBands.compute(
            {'close': close},
            {'window': bb_window, 'window_dev': bb_dev},
        ),
        ref_fn=lambda: {
            'mavg': ta.volatility.BollingerBands(
                close=close, window=bb_window, window_dev=bb_dev, fillna=False
            ).bollinger_mavg(),
            'hband': ta.volatility.BollingerBands(
                close=close, window=bb_window, window_dev=bb_dev, fillna=False
            ).bollinger_hband(),
            'lband': ta.volatility.BollingerBands(
                close=close, window=bb_window, window_dev=bb_dev, fillna=False
            ).bollinger_lband(),
        },
        output_keys=['mavg', 'hband', 'lband'],
        tolerance=tol,
        tolerance_tier=tier,
    ))

    # --- KeltnerChannel (original_version=True) ---
    kc_window = 20
    kc_window_atr = 10
    kc_multiplier = 2
    tol, tier = get_tolerance("KeltnerChannel")
    results.append(compare_indicator(
        indicator_name="KeltnerChannel",
        category="Volatility",
        our_fn=lambda: {
            'kc_hband': KeltnerChannel.compute(
                {'high': high, 'low': low, 'close': close},
                {'window': kc_window, 'window_atr': kc_window_atr,
                 'original_version': True, 'multiplier': kc_multiplier},
            )['hband'],
            'kc_lband': KeltnerChannel.compute(
                {'high': high, 'low': low, 'close': close},
                {'window': kc_window, 'window_atr': kc_window_atr,
                 'original_version': True, 'multiplier': kc_multiplier},
            )['lband'],
            'kc_mband': KeltnerChannel.compute(
                {'high': high, 'low': low, 'close': close},
                {'window': kc_window, 'window_atr': kc_window_atr,
                 'original_version': True, 'multiplier': kc_multiplier},
            )['mband'],
        },
        ref_fn=lambda: {
            'kc_hband': ta.volatility.KeltnerChannel(
                high=high, low=low, close=close, window=kc_window,
                window_atr=kc_window_atr, original_version=True,
                multiplier=kc_multiplier, fillna=False,
            ).keltner_channel_hband(),
            'kc_lband': ta.volatility.KeltnerChannel(
                high=high, low=low, close=close, window=kc_window,
                window_atr=kc_window_atr, original_version=True,
                multiplier=kc_multiplier, fillna=False,
            ).keltner_channel_lband(),
            'kc_mband': ta.volatility.KeltnerChannel(
                high=high, low=low, close=close, window=kc_window,
                window_atr=kc_window_atr, original_version=True,
                multiplier=kc_multiplier, fillna=False,
            ).keltner_channel_mband(),
        },
        output_keys=['kc_hband', 'kc_lband', 'kc_mband'],
        tolerance=tol,
        tolerance_tier=tier,
        notes="original_version=True",
    ))

    # --- DonchianChannel ---
    dc_window = 20
    tol, tier = get_tolerance("DonchianChannel")
    results.append(compare_indicator(
        indicator_name="DonchianChannel",
        category="Volatility",
        our_fn=lambda: {
            'dc_hband': DonchianChannel.compute(
                {'high': high, 'low': low, 'close': close},
                {'window': dc_window, 'offset': 0},
            )['hband'],
            'dc_lband': DonchianChannel.compute(
                {'high': high, 'low': low, 'close': close},
                {'window': dc_window, 'offset': 0},
            )['lband'],
            'dc_mband': DonchianChannel.compute(
                {'high': high, 'low': low, 'close': close},
                {'window': dc_window, 'offset': 0},
            )['mband'],
        },
        ref_fn=lambda: {
            'dc_hband': ta.volatility.DonchianChannel(
                high=high, low=low, close=close, window=dc_window,
                offset=0, fillna=False,
            ).donchian_channel_hband(),
            'dc_lband': ta.volatility.DonchianChannel(
                high=high, low=low, close=close, window=dc_window,
                offset=0, fillna=False,
            ).donchian_channel_lband(),
            'dc_mband': ta.volatility.DonchianChannel(
                high=high, low=low, close=close, window=dc_window,
                offset=0, fillna=False,
            ).donchian_channel_mband(),
        },
        output_keys=['dc_hband', 'dc_lband', 'dc_mband'],
        tolerance=tol,
        tolerance_tier=tier,
    ))

    # --- UlcerIndex ---
    ui_window = 14
    tol, tier = get_tolerance("UlcerIndex")
    results.append(compare_indicator(
        indicator_name="UlcerIndex",
        category="Volatility",
        our_fn=lambda: UlcerIndex.compute(
            {'close': close},
            {'window': ui_window},
        ),
        ref_fn=lambda: {
            'ulcer_index': ta.volatility.UlcerIndex(
                close=close, window=ui_window, fillna=False,
            ).ulcer_index()
        },
        output_keys=['ulcer_index'],
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

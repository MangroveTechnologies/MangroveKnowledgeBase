#!/usr/bin/env python3
"""Audit volatility indicators against Bukosabino ta reference, and the band-state signals.

The band-state signals (bb_above_upper / bb_below_lower / kc_above_upper / kc_below_lower)
carry what used to be the `hband_indicator` / `lband_indicator` outputs on BollingerBands and
KeltnerChannel. They are verified bar-by-bar against the band comparison they encode, to the
same zero-false-positive / zero-false-negative standard as every other signal in the package.
"""
import sys
sys.path.insert(0, "scripts")

from audit import load_btc_daily
from audit.compare import compare_indicator, verify_signal
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
    # Both are None on our side: the original_version branch derives its bands from SMA(high - low)
    # and never reads them, and passing a value is now rejected instead of silently ignored. The
    # reference library still accepts them and ignores them just the same, so the comparison holds.
    kc_window_atr = 10
    kc_multiplier = 2
    tol, tier = get_tolerance("KeltnerChannel")
    results.append(compare_indicator(
        indicator_name="KeltnerChannel",
        category="Volatility",
        our_fn=lambda: {
            'kc_hband': KeltnerChannel.compute(
                {'high': high, 'low': low, 'close': close},
                {'window': kc_window, 'window_atr': None,
                 'original_version': True, 'multiplier': None},
            )['hband'],
            'kc_lband': KeltnerChannel.compute(
                {'high': high, 'low': low, 'close': close},
                {'window': kc_window, 'window_atr': None,
                 'original_version': True, 'multiplier': None},
            )['lband'],
            'kc_mband': KeltnerChannel.compute(
                {'high': high, 'low': low, 'close': close},
                {'window': kc_window, 'window_atr': None,
                 'original_version': True, 'multiplier': None},
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
    # include_current_bar=True to match the reference: bukosabino/ta's DonchianChannel is a generic
    # rolling max/min that folds in the current bar. That is NOT the Donchian convention -- every
    # source specifies the preceding N bars, and including the current one makes a breakout
    # arithmetically impossible -- so our default is the opposite. Comparing like with like here.
    dc_window = 20
    tol, tier = get_tolerance("DonchianChannel")
    results.append(compare_indicator(
        indicator_name="DonchianChannel",
        category="Volatility",
        our_fn=lambda: {
            'dc_hband': DonchianChannel.compute(
                {'high': high, 'low': low, 'close': close},
                {'window': dc_window, 'include_current_bar': True},
            )['hband'],
            'dc_lband': DonchianChannel.compute(
                {'high': high, 'low': low, 'close': close},
                {'window': dc_window, 'include_current_bar': True},
            )['lband'],
            'dc_mband': DonchianChannel.compute(
                {'high': high, 'low': low, 'close': close},
                {'window': dc_window, 'include_current_bar': True},
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


def run_signal_audit():
    """Verify the band-state signals bar-by-bar over the real BTC daily fixture.

    Ground truth is the band comparison itself -- `close > hband` / `close < lband` -- computed on the
    full series, against which each signal is replayed through a sliding window. These signals hold
    for as long as price sits outside the band, unlike the *_breakout signals, which fire only on the
    crossing bar.
    """
    df = load_btc_daily()
    close = df['close']

    bb = BollingerBands.compute({'close': close}, {'window': 20, 'window_dev': 2})
    kc = KeltnerChannel.compute(
        {'high': df['high'], 'low': df['low'], 'close': close},
        {'window': 20, 'window_atr': 10, 'original_version': False, 'multiplier': 2.0},
    )

    bb_params = {'window': 20, 'window_dev': 2}
    kc_params = {'window': 20, 'window_atr': 10, 'multiplier': 2.0}
    cases = [
        ('bb_above_upper', bb_params, close > bb['hband']),
        ('bb_below_lower', bb_params, close < bb['lband']),
        ('kc_above_upper', kc_params, close > kc['hband']),
        ('kc_below_lower', kc_params, close < kc['lband']),
    ]
    return [
        verify_signal(name, params, df, truth.fillna(False).to_numpy(dtype=bool))
        for name, params, truth in cases
    ]


if __name__ == "__main__":
    print("=== Volatility: Indicator audit ===")
    results = run_audit()
    for r in results:
        status = "PASS" if r.pass_fail else "FAIL"
        errors = ", ".join(f"{k}={v.max_abs_error:.2e}" for k, v in r.outputs.items())
        notes = f" [{r.notes}]" if r.notes else ""
        print(f"  {r.indicator_name}: {status} ({errors}){notes}")

    print("\n=== Volatility: Band-state signal audit (bar-by-bar ground truth) ===")
    sig_results = run_signal_audit()
    for r in sig_results:
        status = "PASS" if r.pass_fail else "FAIL"
        print(f"  {r.signal_name}: {status} (fires={r.fires}, expected={r.expected_fires}, "
              f"FP={r.false_positives}, FN={r.false_negatives})")

    failed = sum(1 for r in results + sig_results if not r.pass_fail)
    total = len(results) + len(sig_results)
    print(f"\nVolatility total: {total - failed}/{total} PASS")
    sys.exit(0 if failed == 0 else 1)

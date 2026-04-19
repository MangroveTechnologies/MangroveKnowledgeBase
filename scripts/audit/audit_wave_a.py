#!/usr/bin/env python3
"""Audit Wave A indicators (simple moving averages) against pandas-ta reference.

Wave A indicators: DEMA, TEMA, TRIMA, SMMA, EPMA, VWMA.

Notes on tolerance:
- DEMA/TEMA use post-warmup FLOAT tolerance because pandas-ta pre-seeds with SMA
  (TA-Lib compatibility) while we use pure ewm (matching our EMA convention).
  Post-warmup the two converge; pre-warmup diverges by up to ~2e-6 relative.
- TRIMA uses FLOAT tolerance for odd windows. Even-window convention differs from
  pandas-ta (which uses round((n+1)/2) vs our TA-Lib-style n/2 + n/2+1 split),
  so audit uses odd window only.
- SMMA/EPMA/VWMA use EXACT tolerance (match pandas-ta bit-for-bit).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import pandas_ta as ta

from audit import load_btc_daily
from audit.compare import (
    compare_indicator,
    verify_signal,
    truth_is_above,
    truth_crossover,
)
from mangrove_kb.indicators import DEMA, TEMA, TRIMA, SMMA, EPMA, VWMA


def run_audit():
    df = load_btc_daily()
    close = df['close']
    volume = df['volume']

    results = []

    # DEMA: post-warmup RELATIVE tolerance (pure ewm vs pandas-ta's presma seeding)
    results.append(compare_indicator(
        indicator_name='DEMA',
        category='Trend',
        our_fn=lambda: DEMA.compute({'close': close}, {'window': 10}),
        ref_fn=lambda: {'dema': ta.dema(close, length=10)},
        output_keys=['dema'],
        tolerance=1e-5,
        tolerance_tier='RELATIVE_1e-5',
        skip_warmup=100,
        relative=True,
        reference_library='pandas-ta',
        notes='pandas-ta uses TA-Lib SMA presma; we use pure ewm. Converges post-warmup.',
    ))

    # TEMA: post-warmup RELATIVE tolerance (same reason as DEMA, 3 EMAs chained amplifies divergence)
    results.append(compare_indicator(
        indicator_name='TEMA',
        category='Trend',
        our_fn=lambda: TEMA.compute({'close': close}, {'window': 10}),
        ref_fn=lambda: {'tema': ta.tema(close, length=10)},
        output_keys=['tema'],
        tolerance=1e-5,
        tolerance_tier='RELATIVE_1e-5',
        skip_warmup=120,
        relative=True,
        reference_library='pandas-ta',
        notes='pandas-ta uses TA-Lib SMA presma; we use pure ewm. Converges post-warmup.',
    ))

    # TRIMA: odd window matches exactly; even window convention differs
    results.append(compare_indicator(
        indicator_name='TRIMA',
        category='Trend',
        our_fn=lambda: TRIMA.compute({'close': close}, {'window': 11}),
        ref_fn=lambda: {'trima': ta.trima(close, length=11)},
        output_keys=['trima'],
        tolerance=1e-6,
        tolerance_tier='FLOAT',
        reference_library='pandas-ta',
        notes='Odd window matches exactly; even window uses TA-Lib convention (differs from pandas-ta round-half).',
    ))

    # SMMA: matches ta.rma (Wilder) exactly
    results.append(compare_indicator(
        indicator_name='SMMA',
        category='Trend',
        our_fn=lambda: SMMA.compute({'close': close}, {'window': 14}),
        ref_fn=lambda: {'smma': ta.rma(close, length=14)},
        output_keys=['smma'],
        tolerance=1e-10,
        tolerance_tier='EXACT',
        reference_library='pandas-ta (rma)',
    ))

    # EPMA: matches ta.linreg (linear regression endpoint) to float precision
    results.append(compare_indicator(
        indicator_name='EPMA',
        category='Trend',
        our_fn=lambda: EPMA.compute({'close': close}, {'window': 10}),
        ref_fn=lambda: {'epma': ta.linreg(close, length=10)},
        output_keys=['epma'],
        tolerance=1e-9,
        tolerance_tier='FLOAT',
        reference_library='pandas-ta (linreg)',
    ))

    # VWMA: matches ta.vwma exactly
    results.append(compare_indicator(
        indicator_name='VWMA',
        category='Volume',
        our_fn=lambda: VWMA.compute({'close': close, 'volume': volume}, {'window': 10}),
        ref_fn=lambda: {'vwma': ta.vwma(close, volume, length=10)},
        output_keys=['vwma'],
        tolerance=1e-9,
        tolerance_tier='FLOAT',
        reference_library='pandas-ta',
    ))

    return results


def run_signal_audit():
    """Verify every Wave A signal bar-by-bar against ground truth from indicators."""
    df = load_btc_daily()
    # Signals expect capitalized OHLCV columns; load_btc_daily provides both.
    close = df['close']
    volume = df['volume']

    results = []

    # FILTER signals: is_above_<ma>
    filter_specs = [
        ('is_above_dema', DEMA, 'dema', {'window': 21}, {'close': close}),
        ('is_above_tema', TEMA, 'tema', {'window': 21}, {'close': close}),
        ('is_above_trima', TRIMA, 'trima', {'window': 20}, {'close': close}),
        ('is_above_smma', SMMA, 'smma', {'window': 14}, {'close': close}),
        ('is_above_epma', EPMA, 'epma', {'window': 20}, {'close': close}),
        ('is_above_vwma', VWMA, 'vwma', {'window': 20}, {'close': close, 'volume': volume}),
    ]
    for name, cls, key, params, data in filter_specs:
        indicator = cls.compute(data, params)[key]
        truth = truth_is_above(close, indicator)
        results.append(verify_signal(name, params, df, truth))

    # TRIGGER signals: <ma>_cross_up / <ma>_cross_down
    cross_specs = [
        # (ma_name, cls, key, (window_fast, window_slow), extra_params, data)
        ('dema', DEMA, 'dema', (9, 21), {}, {'close': close}),
        ('tema', TEMA, 'tema', (9, 21), {}, {'close': close}),
        ('trima', TRIMA, 'trima', (10, 30), {}, {'close': close}),
        ('smma', SMMA, 'smma', (14, 50), {}, {'close': close}),
        ('epma', EPMA, 'epma', (10, 30), {}, {'close': close}),
        ('vwma', VWMA, 'vwma', (9, 21), {}, {'close': close, 'volume': volume}),
    ]
    for ma_name, cls, key, (wf, ws), extra, data in cross_specs:
        fast = cls.compute(data, {'window': wf, **extra})[key]
        slow = cls.compute(data, {'window': ws, **extra})[key]
        params = {'window_fast': wf, 'window_slow': ws, **extra}
        results.append(verify_signal(f"{ma_name}_cross_up", params, df, truth_crossover(fast, slow, 'up')))
        results.append(verify_signal(f"{ma_name}_cross_down", params, df, truth_crossover(fast, slow, 'down')))

    return results


if __name__ == '__main__':
    print('=== Wave A: Indicator audit ===')
    ind_results = run_audit()
    for r in ind_results:
        status = 'PASS' if r.pass_fail else 'FAIL'
        errors = ', '.join(f'{k}={v.max_abs_error:.2e}' for k, v in r.outputs.items())
        notes = f' [{r.notes}]' if r.notes else ''
        print(f'  {r.indicator_name}: {status} ({errors}){notes}')
    ind_failed = sum(1 for r in ind_results if not r.pass_fail)

    print('\n=== Wave A: Signal audit (bar-by-bar ground truth) ===')
    sig_results = run_signal_audit()
    for r in sig_results:
        status = 'PASS' if r.pass_fail else 'FAIL'
        print(f'  {r.signal_name}: {status} (fires={r.fires}, expected={r.expected_fires}, '
              f'FP={r.false_positives}, FN={r.false_negatives})')
    sig_failed = sum(1 for r in sig_results if not r.pass_fail)

    total_pass = (len(ind_results) - ind_failed) + (len(sig_results) - sig_failed)
    total = len(ind_results) + len(sig_results)
    print(f'\nWave A total: {total_pass}/{total} PASS '
          f'(indicators {len(ind_results) - ind_failed}/{len(ind_results)}, '
          f'signals {len(sig_results) - sig_failed}/{len(sig_results)})')
    sys.exit(0 if (ind_failed + sig_failed) == 0 else 1)

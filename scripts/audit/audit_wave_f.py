#!/usr/bin/env python3
"""Audit Wave F indicators (volume) against pandas-ta.

Wave F indicators: ADOSC, KVO.

Notes:
- ADOSC: EMA of the AD line. Our AD line is bit-exact; the ADOSC divergence
  comes only from the EMA presma seeding difference (same as DEMA/TEMA).
  Converges quickly; skip=100 gives 6.5e-10 relative error.
- KVO: chains 55-period EMA with 13-period signal EMA, so presma-seeding
  divergence takes ~400-500 bars to fully decay. Uses larger skip + relative
  tolerance.

Signal verification: every signal runs bar-by-bar (zero FP/FN required).
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
    bench_indicator,
)
from mangrove_kb.indicators import ADOSC, KVO


def run_audit():
    df = load_btc_daily()
    high = df['high']
    low = df['low']
    close = df['close']
    volume = df['volume']

    results = []

    results.append(compare_indicator(
        indicator_name='ADOSC',
        category='Volume',
        our_fn=lambda: ADOSC.compute({'high': high, 'low': low, 'close': close, 'volume': volume}, {'fast': 3, 'slow': 10}),
        ref_fn=lambda: {'adosc': ta.adosc(high, low, close, volume, fast=3, slow=10, talib=False)},
        output_keys=['adosc'],
        tolerance=1e-8,
        tolerance_tier='RELATIVE_1e-8',
        skip_warmup=100,
        relative=True,
        reference_library='pandas-ta (talib=False)',
        notes='ADI bit-exact; divergence is only from EMA presma seeding (same pattern as DEMA/TEMA).',
    ))

    ref_kvo = ta.kvo(high, low, close, volume, fast=34, slow=55, signal=13, talib=False)
    results.append(compare_indicator(
        indicator_name='KVO',
        category='Volume',
        our_fn=lambda: KVO.compute({'high': high, 'low': low, 'close': close, 'volume': volume}, {'fast': 34, 'slow': 55, 'signal_window': 13}),
        ref_fn=lambda: {
            'kvo': ref_kvo['KVO_34_55_13'],
            'kvo_signal': ref_kvo['KVOs_34_55_13'],
        },
        output_keys=['kvo', 'kvo_signal'],
        tolerance=1e-4,
        tolerance_tier='RELATIVE_1e-4',
        skip_warmup=500,
        relative=True,
        reference_library='pandas-ta (talib=False)',
        notes='Chained 55+13 EMAs amplify presma-seeding divergence; requires skip=500 to fully converge. Signed volume is bit-exact vs pandas-ta.',
    ))

    return results


def run_signal_audit():
    df = load_btc_daily()
    high = df['high']; low = df['low']; close = df['close']; volume = df['volume']

    results = []

    # ADOSC signals
    adosc_params = {'fast': 3, 'slow': 10}
    adosc = ADOSC.compute({'high': high, 'low': low, 'close': close, 'volume': volume}, adosc_params)['adosc']
    truth_bull = (adosc > 0).fillna(False).to_numpy()
    truth_bear = (adosc < 0).fillna(False).to_numpy()
    prev = adosc.shift(1)
    truth_cross_up = ((prev <= 0) & (adosc > 0)).fillna(False).to_numpy()
    truth_cross_down = ((prev >= 0) & (adosc < 0)).fillna(False).to_numpy()
    results.append(verify_signal('adosc_bullish', adosc_params, df, truth_bull))
    results.append(verify_signal('adosc_bearish', adosc_params, df, truth_bear))
    results.append(verify_signal('adosc_cross_up', adosc_params, df, truth_cross_up))
    results.append(verify_signal('adosc_cross_down', adosc_params, df, truth_cross_down))

    # KVO signals
    kvo_params = {'fast': 34, 'slow': 55, 'signal_window': 13}
    kvo_out = KVO.compute({'high': high, 'low': low, 'close': close, 'volume': volume}, kvo_params)
    kvo_line = kvo_out['kvo']
    kvo_sig = kvo_out['kvo_signal']
    truth_bull_filter = (kvo_line > kvo_sig).fillna(False).to_numpy()
    truth_bear_filter = (kvo_line < kvo_sig).fillna(False).to_numpy()
    prev_kvo, prev_sig = kvo_line.shift(1), kvo_sig.shift(1)
    truth_bull_cross = ((prev_kvo <= prev_sig) & (kvo_line > kvo_sig)).fillna(False).to_numpy()
    truth_bear_cross = ((prev_kvo >= prev_sig) & (kvo_line < kvo_sig)).fillna(False).to_numpy()
    results.append(verify_signal('kvo_bullish', kvo_params, df, truth_bull_filter))
    results.append(verify_signal('kvo_bearish', kvo_params, df, truth_bear_filter))
    results.append(verify_signal('kvo_bullish_cross', kvo_params, df, truth_bull_cross))
    results.append(verify_signal('kvo_bearish_cross', kvo_params, df, truth_bear_cross))

    return results


def run_benchmark():
    df = load_btc_daily()
    high, low, close, volume = df['high'], df['low'], df['close'], df['volume']
    bars = len(df)

    return [
        bench_indicator('ADOSC(3,10)', lambda: ADOSC.compute({'high': high, 'low': low, 'close': close, 'volume': volume}, {'fast': 3, 'slow': 10}), bars),
        bench_indicator('KVO(34,55,13)', lambda: KVO.compute({'high': high, 'low': low, 'close': close, 'volume': volume}, {'fast': 34, 'slow': 55, 'signal_window': 13}), bars),
    ]


if __name__ == '__main__':
    print('=== Wave F: Indicator audit ===')
    ind_results = run_audit()
    for r in ind_results:
        status = 'PASS' if r.pass_fail else 'FAIL'
        errors = ', '.join(f'{k}={v.max_abs_error:.2e}' for k, v in r.outputs.items())
        notes = f' [{r.notes}]' if r.notes else ''
        print(f'  {r.indicator_name}: {status} ({errors}){notes}')
    ind_failed = sum(1 for r in ind_results if not r.pass_fail)

    print('\n=== Wave F: Signal audit (bar-by-bar ground truth) ===')
    sig_results = run_signal_audit()
    for r in sig_results:
        status = 'PASS' if r.pass_fail else 'FAIL'
        print(f'  {r.signal_name}: {status} (fires={r.fires}, expected={r.expected_fires}, '
              f'FP={r.false_positives}, FN={r.false_negatives})')
    sig_failed = sum(1 for r in sig_results if not r.pass_fail)

    print('\n=== Wave F: Benchmark (1294-bar BTC daily) ===')
    for b in run_benchmark():
        flag = '  <- PATHOLOGICAL' if b.tier == 'pathological' else ('  <- slow' if b.tier == 'slow' else '')
        print(f'  {b.indicator_name:25s}: {b.mean_ms:>7.3f} ms  [{b.tier}]{flag}')

    total_pass = (len(ind_results) - ind_failed) + (len(sig_results) - sig_failed)
    total = len(ind_results) + len(sig_results)
    print(f'\nWave F total: {total_pass}/{total} PASS '
          f'(indicators {len(ind_results) - ind_failed}/{len(ind_results)}, '
          f'signals {len(sig_results) - sig_failed}/{len(sig_results)})')
    sys.exit(0 if (ind_failed + sig_failed) == 0 else 1)

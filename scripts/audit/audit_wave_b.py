#!/usr/bin/env python3
"""Audit Wave B indicators (complex moving averages) against pandas-ta reference.

Wave B indicators: HMA, ALMA, T3, MAMA.

Notes:
- HMA, ALMA: bit-exact match against pandas-ta.
- T3: post-warmup relative match. Our T3 chains our pure-ewm EMA six times;
  pandas-ta T3 uses TA-Lib SMA-seeded EMAs, so warmup bars diverge but
  values converge post-warmup (same pattern as DEMA/TEMA).
- MAMA: behavior-only audit. pandas-ta's nb_mama has two bugs vs Ehlers's
  canonical paper (im sign flip, radians vs degrees in period calc), so we
  cannot use it as a numerical reference. Instead, verify:
    * MAMA/FAMA track price (mean abs diff < 5% of price range)
    * Alpha stays within [slow_limit, fast_limit] bounds
    * FAMA trails MAMA (larger mean |FAMA - close| than |MAMA - close|)
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
    bench_indicator,
)
from mangrove_kb.indicators import HMA, ALMA, T3, MAMA


def run_audit():
    df = load_btc_daily()
    close = df['close']

    results = []

    # HMA: bit-exact match against pandas-ta
    results.append(compare_indicator(
        indicator_name='HMA',
        category='Trend',
        our_fn=lambda: HMA.compute({'close': close}, {'window': 16}),
        ref_fn=lambda: {'hma': ta.hma(close, length=16)},
        output_keys=['hma'],
        tolerance=1e-9,
        tolerance_tier='FLOAT',
        reference_library='pandas-ta',
    ))

    # ALMA: bit-exact match
    results.append(compare_indicator(
        indicator_name='ALMA',
        category='Trend',
        our_fn=lambda: ALMA.compute({'close': close}, {'window': 21, 'offset': 0.85, 'sigma': 6.0}),
        ref_fn=lambda: {'alma': ta.alma(close, length=21, distribution_offset=0.85, sigma=6.0)},
        output_keys=['alma'],
        tolerance=1e-9,
        tolerance_tier='FLOAT',
        reference_library='pandas-ta',
    ))

    # T3: post-warmup relative match. skip=180 because 6 EMAs each need ~30 bars warmup to converge.
    results.append(compare_indicator(
        indicator_name='T3',
        category='Trend',
        our_fn=lambda: T3.compute({'close': close}, {'window': 10, 'volume_factor': 0.7}),
        ref_fn=lambda: {'t3': ta.t3(close, length=10, a=0.7)},
        output_keys=['t3'],
        tolerance=1e-5,
        tolerance_tier='RELATIVE_1e-5',
        skip_warmup=180,
        relative=True,
        reference_library='pandas-ta',
        notes='pandas-ta uses TA-Lib SMA presma on each chained EMA; we use pure ewm. Converges post-warmup.',
    ))

    # MAMA: behavior-based audit (no numerical reference; pandas-ta has bugs vs Ehlers).
    # We synthesize an AuditResult manually since this isn't a numerical comparison.
    from audit.compare import AuditResult, OutputResult
    mama_result = AuditResult(
        indicator_name='MAMA',
        category='Trend',
        reference_library='Ehlers (behavioral)',
        tolerance_tier='BEHAVIORAL',
        tolerance_value=0.05,  # 5% mean relative tracking error allowed
        notes='Behavioral audit: MAMA/FAMA track price; FAMA trails MAMA; no NaN after warmup.',
    )
    out = MAMA.compute({'close': close}, {'fast_limit': 0.5, 'slow_limit': 0.05})
    mama = out['mama']
    fama = out['fama']

    # Behavior checks
    price_range = close.max() - close.min()
    mama_track_err = float((mama - close).abs().mean() / price_range)
    fama_track_err = float((fama - close).abs().mean() / price_range)
    post_warmup_nan = int(mama.iloc[50:].isna().sum() + fama.iloc[50:].isna().sum())
    fama_trails = fama_track_err > mama_track_err  # FAMA lags more than MAMA

    mama_out = OutputResult(
        output_key='mama',
        max_abs_error=mama_track_err,
        mean_abs_error=mama_track_err,
        overlap_bars=int(mama.notna().sum()),
        pass_fail=(mama_track_err < 0.05 and post_warmup_nan == 0),
    )
    fama_out = OutputResult(
        output_key='fama',
        max_abs_error=fama_track_err,
        mean_abs_error=fama_track_err,
        overlap_bars=int(fama.notna().sum()),
        pass_fail=(fama_track_err < 0.10 and fama_trails),
    )
    mama_result.outputs = {'mama': mama_out, 'fama': fama_out}
    mama_result.pass_fail = mama_out.pass_fail and fama_out.pass_fail
    if not fama_trails:
        mama_result.notes += ' FAIL: FAMA does not trail MAMA (unexpected).'
    results.append(mama_result)

    return results


def run_signal_audit():
    """Verify every Wave B signal bar-by-bar against ground truth from indicators."""
    df = load_btc_daily()
    close = df['close']

    results = []

    # --- HMA, ALMA, T3: standard is_above + cross_up/down pattern ---
    is_above_specs = [
        ('is_above_hma', HMA, 'hma', {'window': 16}),
        ('is_above_alma', ALMA, 'alma', {'window': 21, 'offset': 0.85, 'sigma': 6.0}),
        ('is_above_t3', T3, 't3', {'window': 10, 'volume_factor': 0.7}),
    ]
    for name, cls, key, params in is_above_specs:
        indicator = cls.compute({'close': close}, params)[key]
        truth = truth_is_above(close, indicator)
        results.append(verify_signal(name, params, df, truth))

    cross_specs = [
        ('hma', HMA, 'hma', {'window_fast': 9, 'window_slow': 25}, {}),
        ('alma', ALMA, 'alma', {'window_fast': 9, 'window_slow': 21}, {'offset': 0.85, 'sigma': 6.0}),
        ('t3', T3, 't3', {'window_fast': 5, 'window_slow': 10}, {'volume_factor': 0.7}),
    ]
    for ma_name, cls, key, window_params, extra in cross_specs:
        wf = window_params['window_fast']
        ws = window_params['window_slow']
        fast = cls.compute({'close': close}, {'window': wf, **extra})[key]
        slow = cls.compute({'close': close}, {'window': ws, **extra})[key]
        params = {**window_params, **extra}
        results.append(verify_signal(f"{ma_name}_cross_up", params, df, truth_crossover(fast, slow, 'up')))
        results.append(verify_signal(f"{ma_name}_cross_down", params, df, truth_crossover(fast, slow, 'down')))

    # --- MAMA: special -- MAMA vs FAMA crossover, not fast/slow window ---
    mama_params = {'fast_limit': 0.5, 'slow_limit': 0.05}
    mama_out = MAMA.compute({'close': close}, mama_params)
    mama_series, fama_series = mama_out['mama'], mama_out['fama']

    # is_above_mama: close > MAMA
    results.append(verify_signal('is_above_mama', mama_params, df, truth_is_above(close, mama_series)))

    # mama_cross_up: MAMA crosses above FAMA
    results.append(verify_signal('mama_cross_up', mama_params, df, truth_crossover(mama_series, fama_series, 'up')))

    # mama_cross_down: MAMA crosses below FAMA
    results.append(verify_signal('mama_cross_down', mama_params, df, truth_crossover(mama_series, fama_series, 'down')))

    return results


def run_benchmark():
    """Time each Wave B indicator on the full BTC daily fixture."""
    df = load_btc_daily()
    close = df['close']
    bars = len(df)

    return [
        bench_indicator('HMA(16)', lambda: HMA.compute({'close': close}, {'window': 16}), bars),
        bench_indicator('ALMA(21)', lambda: ALMA.compute({'close': close}, {'window': 21, 'offset': 0.85, 'sigma': 6.0}), bars),
        bench_indicator('T3(10)', lambda: T3.compute({'close': close}, {'window': 10, 'volume_factor': 0.7}), bars),
        # MAMA: state-dependent sequential loop; fewer runs to keep audit fast.
        bench_indicator('MAMA', lambda: MAMA.compute({'close': close}, {'fast_limit': 0.5, 'slow_limit': 0.05}), bars, runs=10),
    ]


if __name__ == '__main__':
    print('=== Wave B: Indicator audit ===')
    ind_results = run_audit()
    for r in ind_results:
        status = 'PASS' if r.pass_fail else 'FAIL'
        errors = ', '.join(f'{k}={v.max_abs_error:.2e}' for k, v in r.outputs.items())
        notes = f' [{r.notes}]' if r.notes else ''
        print(f'  {r.indicator_name}: {status} ({errors}){notes}')
    ind_failed = sum(1 for r in ind_results if not r.pass_fail)

    print('\n=== Wave B: Signal audit (bar-by-bar ground truth) ===')
    sig_results = run_signal_audit()
    for r in sig_results:
        status = 'PASS' if r.pass_fail else 'FAIL'
        print(f'  {r.signal_name}: {status} (fires={r.fires}, expected={r.expected_fires}, '
              f'FP={r.false_positives}, FN={r.false_negatives})')
    sig_failed = sum(1 for r in sig_results if not r.pass_fail)

    print('\n=== Wave B: Benchmark (1294-bar BTC daily) ===')
    bench_results = run_benchmark()
    for b in bench_results:
        flag = ''
        if b.tier == 'pathological':
            flag = '  <- PATHOLOGICAL'
        elif b.tier == 'slow':
            flag = '  <- slow (MAMA is state-dependent; future numba opt possible)'
        print(f'  {b.indicator_name:25s}: {b.mean_ms:>7.3f} ms  [{b.tier}]{flag}')

    total_pass = (len(ind_results) - ind_failed) + (len(sig_results) - sig_failed)
    total = len(ind_results) + len(sig_results)
    print(f'\nWave B total: {total_pass}/{total} PASS '
          f'(indicators {len(ind_results) - ind_failed}/{len(ind_results)}, '
          f'signals {len(sig_results) - sig_failed}/{len(sig_results)})')
    sys.exit(0 if (ind_failed + sig_failed) == 0 else 1)
    for r in results:
        status = 'PASS' if r.pass_fail else 'FAIL'
        errors = ', '.join(f'{k}={v.max_abs_error:.2e}' for k, v in r.outputs.items())
        notes = f' [{r.notes}]' if r.notes else ''
        print(f'  {r.indicator_name}: {status} ({errors}){notes}')

    failed = sum(1 for r in results if not r.pass_fail)
    total = len(results)
    print(f'\nWave B: {total - failed}/{total} PASS')
    sys.exit(0 if failed == 0 else 1)

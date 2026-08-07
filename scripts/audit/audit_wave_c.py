#!/usr/bin/env python3
"""Audit Wave C indicators (momentum) against pandas-ta reference.

Wave C indicators: MOM, BOP, CMO.

Notes:
- MOM, BOP: bit-exact match against pandas-ta.
- APO was removed from the package: it emitted a series byte-identical to
  MACD.macd (max diff 0.00e+00 over 400 bars). Its four signals are now the
  macd_line_* family and are covered by the MACD audit.
- CMO: compared against pandas-ta with talib=False (rolling-sum definition,
  matching our implementation). pandas-ta's default talib=True uses an
  RMA-smoothed variant which is a different algorithm.

Signal verification: every signal runs bar-by-bar via sliding window and is
compared against indicator-derived ground truth. Zero FP/FN required to pass.
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
from mangrove_kb.indicators import MOM, BOP, CMO


def run_audit():
    df = load_btc_daily()
    open_ = df['open']
    high = df['high']
    low = df['low']
    close = df['close']

    results = []

    # MOM: bit-exact match
    results.append(compare_indicator(
        indicator_name='MOM',
        category='Momentum',
        our_fn=lambda: MOM.compute({'close': close}, {'window': 10}),
        ref_fn=lambda: {'mom': ta.mom(close, length=10)},
        output_keys=['mom'],
        tolerance=1e-10,
        tolerance_tier='EXACT',
        reference_library='pandas-ta',
    ))

    # BOP: bit-exact match
    results.append(compare_indicator(
        indicator_name='BOP',
        category='Momentum',
        our_fn=lambda: BOP.compute({'open': open_, 'high': high, 'low': low, 'close': close}, {}),
        ref_fn=lambda: {'bop': ta.bop(open_, high, low, close)},
        output_keys=['bop'],
        tolerance=1e-10,
        tolerance_tier='EXACT',
        reference_library='pandas-ta',
    ))

    # CMO: rolling-sum definition (talib=False)
    results.append(compare_indicator(
        indicator_name='CMO',
        category='Momentum',
        our_fn=lambda: CMO.compute({'close': close}, {'window': 14}),
        ref_fn=lambda: {'cmo': ta.cmo(close, length=14, talib=False)},
        output_keys=['cmo'],
        tolerance=1e-10,
        tolerance_tier='EXACT',
        reference_library='pandas-ta (talib=False)',
        notes='Rolling-sum CMO definition. pandas-ta talib=True uses an RMA-smoothed variant.',
    ))

    return results


def _truth_bullish(series: pd.Series) -> np.ndarray:
    """Ground truth for bullish filter: series > 0, NaN -> False."""
    return (series > 0).fillna(False).to_numpy()


def _truth_bearish(series: pd.Series) -> np.ndarray:
    """Ground truth for bearish filter: series < 0, NaN -> False."""
    return (series < 0).fillna(False).to_numpy()


def _truth_zero_cross(series: pd.Series, direction: str) -> np.ndarray:
    """Ground truth for zero-line crossover: prev<=0<curr (up) or prev>=0>curr (down)."""
    prev = series.shift(1)
    curr = series
    if direction == "up":
        cond = (prev <= 0) & (curr > 0)
    elif direction == "down":
        cond = (prev >= 0) & (curr < 0)
    else:
        raise ValueError(f"direction must be 'up' or 'down', got {direction!r}")
    return cond.fillna(False).to_numpy()


def _truth_threshold_ge(series: pd.Series, threshold: float) -> np.ndarray:
    """Ground truth for CMO overbought: series >= threshold."""
    return (series >= threshold).fillna(False).to_numpy()


def _truth_threshold_le(series: pd.Series, threshold: float) -> np.ndarray:
    """Ground truth for CMO oversold: series <= threshold."""
    return (series <= threshold).fillna(False).to_numpy()


def _truth_threshold_cross_up(series: pd.Series, threshold: float) -> np.ndarray:
    """Ground truth for CMO cross up: prev<=threshold<curr."""
    prev = series.shift(1)
    return ((prev <= threshold) & (series > threshold)).fillna(False).to_numpy()


def _truth_threshold_cross_down(series: pd.Series, threshold: float) -> np.ndarray:
    """Ground truth for CMO cross down: prev>=threshold>curr."""
    prev = series.shift(1)
    return ((prev >= threshold) & (series < threshold)).fillna(False).to_numpy()


def run_signal_audit():
    """Verify every Wave C signal bar-by-bar against ground truth from indicators."""
    df = load_btc_daily()
    open_ = df['open']
    high = df['high']
    low = df['low']
    close = df['close']

    results = []

    # --- MOM signals ---
    mom = MOM.compute({'close': close}, {'window': 10})['mom']
    results.append(verify_signal('mom_bullish', {'window': 10}, df, _truth_bullish(mom)))
    results.append(verify_signal('mom_bearish', {'window': 10}, df, _truth_bearish(mom)))
    results.append(verify_signal('mom_cross_up', {'window': 10}, df, _truth_zero_cross(mom, 'up')))
    results.append(verify_signal('mom_cross_down', {'window': 10}, df, _truth_zero_cross(mom, 'down')))

    # --- BOP signals ---
    bop = BOP.compute({'open': open_, 'high': high, 'low': low, 'close': close}, {})['bop']
    results.append(verify_signal('bop_bullish', {}, df, _truth_bullish(bop)))
    results.append(verify_signal('bop_bearish', {}, df, _truth_bearish(bop)))
    results.append(verify_signal('bop_cross_up', {}, df, _truth_zero_cross(bop, 'up')))
    results.append(verify_signal('bop_cross_down', {}, df, _truth_zero_cross(bop, 'down')))

    # --- CMO signals ---
    cmo = CMO.compute({'close': close}, {'window': 14})['cmo']
    results.append(verify_signal('cmo_overbought', {'window': 14, 'threshold': 50.0}, df, _truth_threshold_ge(cmo, 50.0)))
    results.append(verify_signal('cmo_oversold', {'window': 14, 'threshold': -50.0}, df, _truth_threshold_le(cmo, -50.0)))
    results.append(verify_signal('cmo_cross_up', {'window': 14, 'threshold': -50.0}, df, _truth_threshold_cross_up(cmo, -50.0)))
    results.append(verify_signal('cmo_cross_down', {'window': 14, 'threshold': 50.0}, df, _truth_threshold_cross_down(cmo, 50.0)))

    return results


def run_benchmark():
    """Time each Wave C indicator on the full BTC daily fixture."""
    df = load_btc_daily()
    open_ = df['open']; high = df['high']; low = df['low']; close = df['close']
    bars = len(df)

    return [
        bench_indicator('MOM(10)', lambda: MOM.compute({'close': close}, {'window': 10}), bars),
        bench_indicator('BOP', lambda: BOP.compute({'open': open_, 'high': high, 'low': low, 'close': close}, {}), bars),
        bench_indicator('CMO(14)', lambda: CMO.compute({'close': close}, {'window': 14}), bars),
    ]


if __name__ == '__main__':
    print('=== Wave C: Indicator audit ===')
    ind_results = run_audit()
    for r in ind_results:
        status = 'PASS' if r.pass_fail else 'FAIL'
        errors = ', '.join(f'{k}={v.max_abs_error:.2e}' for k, v in r.outputs.items())
        notes = f' [{r.notes}]' if r.notes else ''
        print(f'  {r.indicator_name}: {status} ({errors}){notes}')
    ind_failed = sum(1 for r in ind_results if not r.pass_fail)

    print('\n=== Wave C: Signal audit (bar-by-bar ground truth) ===')
    sig_results = run_signal_audit()
    for r in sig_results:
        status = 'PASS' if r.pass_fail else 'FAIL'
        print(f'  {r.signal_name}: {status} (fires={r.fires}, expected={r.expected_fires}, '
              f'FP={r.false_positives}, FN={r.false_negatives})')
    sig_failed = sum(1 for r in sig_results if not r.pass_fail)

    print('\n=== Wave C: Benchmark (1294-bar BTC daily) ===')
    bench_results = run_benchmark()
    for b in bench_results:
        flag = ''
        if b.tier == 'pathological':
            flag = '  <- PATHOLOGICAL (likely has python loop / rolling.apply)'
        elif b.tier == 'slow':
            flag = '  <- slow (acceptable for state-dependent algos)'
        print(f'  {b.indicator_name:25s}: {b.mean_ms:>7.3f} ms  [{b.tier}]{flag}')

    total_pass = (len(ind_results) - ind_failed) + (len(sig_results) - sig_failed)
    total = len(ind_results) + len(sig_results)
    print(f'\nWave C total: {total_pass}/{total} PASS '
          f'(indicators {len(ind_results) - ind_failed}/{len(ind_results)}, '
          f'signals {len(sig_results) - sig_failed}/{len(sig_results)})')
    sys.exit(0 if (ind_failed + sig_failed) == 0 else 1)

#!/usr/bin/env python3
"""Audit Wave E indicators (trend) against pandas-ta / behavioral tests.

Wave E indicators: HeikinAshi, ChandelierLevels, WilliamsAlligator, SuperTrend.

Notes:
- HeikinAshi, SuperTrend: numerical match against pandas-ta (bit-exact).
- WilliamsAlligator: no pandas-ta reference matches Bill Williams's canonical
  definition (pandas-ta uses close instead of median price and skips the
  forward offset). Behavioral audit: post-warmup non-NaN, meaningful number
  of bullish and bearish alignments.
- ChandelierLevels: not in pandas-ta. Behavioral audit: long_stop below
  rolling_highest_high, short_stop above rolling_lowest_low, both > 0.

Signal verification: every signal runs bar-by-bar via sliding window and is
compared against indicator-derived ground truth (zero FP/FN required).

Benchmark: each indicator timed on the 1294-bar BTC daily fixture.
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
    AuditResult,
    OutputResult,
)
from mangrove_kb.indicators import (
    HeikinAshi,
    ChandelierLevels,
    WilliamsAlligator,
    SuperTrend,
)


def run_audit():
    df = load_btc_daily()
    open_ = df['open']
    high = df['high']
    low = df['low']
    close = df['close']

    results = []

    # HeikinAshi: bit-exact vs pandas-ta, all 4 outputs
    ref_ha = ta.ha(open_, high, low, close)
    results.append(compare_indicator(
        indicator_name='HeikinAshi',
        category='Trend',
        our_fn=lambda: HeikinAshi.compute({'open': open_, 'high': high, 'low': low, 'close': close}, {}),
        ref_fn=lambda: {
            'ha_open': ref_ha['HA_open'],
            'ha_high': ref_ha['HA_high'],
            'ha_low': ref_ha['HA_low'],
            'ha_close': ref_ha['HA_close'],
        },
        output_keys=['ha_open', 'ha_high', 'ha_low', 'ha_close'],
        tolerance=1e-10,
        tolerance_tier='EXACT',
        reference_library='pandas-ta',
    ))

    # SuperTrend: bit-exact vs pandas-ta (supertrend line and direction)
    ref_st = ta.supertrend(high, low, close, length=10, multiplier=3.0)
    results.append(compare_indicator(
        indicator_name='SuperTrend',
        category='Trend',
        our_fn=lambda: SuperTrend.compute({'high': high, 'low': low, 'close': close}, {'window': 10, 'multiplier': 3.0}),
        ref_fn=lambda: {
            'supertrend': ref_st['SUPERT_10_3.0'],
            'direction': ref_st['SUPERTd_10_3.0'],
        },
        output_keys=['supertrend', 'direction'],
        tolerance=1e-10,
        tolerance_tier='EXACT',
        skip_warmup=12,
        reference_library='pandas-ta',
    ))

    # Behavioral audits for the two without direct pandas-ta matches
    results.append(_audit_chandelier(high, low, close))
    results.append(_audit_alligator(high, low))

    return results


def _audit_chandelier(high, low, close) -> AuditResult:
    """Behavioral: long_stop < rolling_high, short_stop > rolling_low."""
    params = {'window': 22, 'multiplier': 3.0}
    out = ChandelierLevels.compute({'high': high, 'low': low, 'close': close}, params)
    ls, ss = out['high_offset'], out['low_offset']

    rolling_high = high.rolling(22, min_periods=22).max()
    rolling_low = low.rolling(22, min_periods=22).min()

    valid = ls.notna() & ss.notna() & rolling_high.notna() & rolling_low.notna()
    long_ok = bool(((ls < rolling_high) | ls.isna())[valid].all())
    short_ok = bool(((ss > rolling_low) | ss.isna())[valid].all())
    # Both stops should be positive (on a positive-price asset)
    positive = bool(((ls > 0) & (ss > 0))[valid].all())

    pass_fail = long_ok and short_ok and positive
    result = AuditResult(
        indicator_name='ChandelierLevels',
        category='Trend',
        reference_library='behavioral',
        tolerance_tier='BEHAVIORAL',
        tolerance_value=0.0,
        pass_fail=pass_fail,
        notes=f'long<rolling_high={long_ok}, short>rolling_low={short_ok}, positive={positive}, valid={int(valid.sum())}',
    )
    for key, series in [('high_offset', ls), ('low_offset', ss)]:
        result.outputs[key] = OutputResult(
            output_key=key,
            max_abs_error=0.0,
            mean_abs_error=0.0,
            overlap_bars=int(series.notna().sum()),
            pass_fail=pass_fail,
        )
    return result


def _audit_alligator(high, low) -> AuditResult:
    """Behavioral: no post-warmup NaN; meaningful bullish+bearish alignment counts."""
    params = {'jaw': 13, 'teeth': 8, 'lips': 5, 'jaw_offset': 8, 'teeth_offset': 5, 'lips_offset': 3}
    out = WilliamsAlligator.compute({'high': high, 'low': low}, params)
    jaw, teeth, lips = out['jaw'], out['teeth'], out['lips']

    # All three should be populated after (max_window + max_offset) bars
    warmup = 13 + 8
    post_warmup_nan = int(jaw.iloc[warmup + 10:].isna().sum() + teeth.iloc[warmup + 10:].isna().sum() + lips.iloc[warmup + 10:].isna().sum())

    bullish = int(((lips > teeth) & (teeth > jaw)).sum())
    bearish = int(((lips < teeth) & (teeth < jaw)).sum())
    # Sanity: both regimes appear, each in at least 5% of dataset
    n = len(jaw)
    both_appear = (bullish > 0.05 * n) and (bearish > 0.05 * n)

    pass_fail = post_warmup_nan == 0 and both_appear
    result = AuditResult(
        indicator_name='WilliamsAlligator',
        category='Trend',
        reference_library='behavioral (Bill Williams)',
        tolerance_tier='BEHAVIORAL',
        tolerance_value=0.0,
        pass_fail=pass_fail,
        notes=f'bullish_alignment={bullish}, bearish_alignment={bearish}, post_warmup_nan={post_warmup_nan}',
    )
    for key, series in [('jaw', jaw), ('teeth', teeth), ('lips', lips)]:
        result.outputs[key] = OutputResult(
            output_key=key,
            max_abs_error=0.0,
            mean_abs_error=0.0,
            overlap_bars=int(series.notna().sum()),
            pass_fail=pass_fail,
        )
    return result


def run_signal_audit():
    """Verify every Wave E signal bar-by-bar against ground truth."""
    df = load_btc_daily()
    open_, high, low, close = df['open'], df['high'], df['low'], df['close']

    results = []

    # --- HeikinAshi signals: bullish (close > open) / bearish (close < open)
    ha = HeikinAshi.compute({'open': open_, 'high': high, 'low': low, 'close': close}, {})
    truth_bull = (ha['ha_close'] > ha['ha_open']).fillna(False).to_numpy()
    truth_bear = (ha['ha_close'] < ha['ha_open']).fillna(False).to_numpy()
    results.append(verify_signal('heikin_ashi_bullish', {}, df, truth_bull))
    results.append(verify_signal('heikin_ashi_bearish', {}, df, truth_bear))

    # --- ChandelierLevels signals
    ce_params = {'window': 22, 'multiplier': 3.0}
    ce = ChandelierLevels.compute({'high': high, 'low': low, 'close': close}, ce_params)
    # Close below long_stop: stop hit if in long
    truth_long_hit = (close < ce['high_offset']).fillna(False).to_numpy()
    truth_short_hit = (close > ce['low_offset']).fillna(False).to_numpy()
    results.append(verify_signal('cl_below_high_offset', ce_params, df, truth_long_hit))
    results.append(verify_signal('cl_above_low_offset', ce_params, df, truth_short_hit))

    # --- WilliamsAlligator signals: three regime filters + one awakening trigger
    alg_params = {'jaw': 13, 'teeth': 8, 'lips': 5, 'jaw_offset': 8, 'teeth_offset': 5, 'lips_offset': 3}
    alg = WilliamsAlligator.compute({'high': high, 'low': low}, alg_params)
    jaw, teeth, lips = alg['jaw'], alg['teeth'], alg['lips']
    truth_bull = ((lips > teeth) & (teeth > jaw)).fillna(False).to_numpy()
    truth_bear = ((lips < teeth) & (teeth < jaw)).fillna(False).to_numpy()
    # "Sleeping": lines tangled (neither strictly bullish nor bearish aligned)
    sleeping = ~(truth_bull | truth_bear)
    truth_sleeping = sleeping
    results.append(verify_signal('alligator_bullish', alg_params, df, truth_bull))
    results.append(verify_signal('alligator_bearish', alg_params, df, truth_bear))
    results.append(verify_signal('alligator_sleeping', alg_params, df, truth_sleeping))

    # --- SuperTrend signals
    st_params = {'window': 10, 'multiplier': 3.0}
    st = SuperTrend.compute({'high': high, 'low': low, 'close': close}, st_params)
    direction = st['direction']
    truth_long = (direction == 1).fillna(False).to_numpy()
    truth_short = (direction == -1).fillna(False).to_numpy()
    prev = direction.shift(1)
    truth_flip_up = ((prev == -1) & (direction == 1)).fillna(False).to_numpy()
    truth_flip_down = ((prev == 1) & (direction == -1)).fillna(False).to_numpy()
    results.append(verify_signal('supertrend_long', st_params, df, truth_long))
    results.append(verify_signal('supertrend_short', st_params, df, truth_short))
    results.append(verify_signal('supertrend_flip_up', st_params, df, truth_flip_up))
    results.append(verify_signal('supertrend_flip_down', st_params, df, truth_flip_down))

    return results


def run_benchmark():
    """Time each Wave E indicator on the full BTC daily fixture."""
    df = load_btc_daily()
    open_, high, low, close = df['open'], df['high'], df['low'], df['close']
    bars = len(df)

    return [
        bench_indicator('HeikinAshi', lambda: HeikinAshi.compute({'open': open_, 'high': high, 'low': low, 'close': close}, {}), bars, runs=20),
        bench_indicator('ChandelierLevels(22,3)', lambda: ChandelierLevels.compute({'high': high, 'low': low, 'close': close}, {'window': 22, 'multiplier': 3.0}), bars),
        bench_indicator('WilliamsAlligator', lambda: WilliamsAlligator.compute({'high': high, 'low': low}, {'jaw': 13, 'teeth': 8, 'lips': 5, 'jaw_offset': 8, 'teeth_offset': 5, 'lips_offset': 3}), bars),
        bench_indicator('SuperTrend(10,3)', lambda: SuperTrend.compute({'high': high, 'low': low, 'close': close}, {'window': 10, 'multiplier': 3.0}), bars, runs=20),
    ]


if __name__ == '__main__':
    print('=== Wave E: Indicator audit ===')
    ind_results = run_audit()
    for r in ind_results:
        status = 'PASS' if r.pass_fail else 'FAIL'
        errors = ', '.join(f'{k}={v.max_abs_error:.2e}' for k, v in r.outputs.items())
        notes = f' [{r.notes}]' if r.notes else ''
        print(f'  {r.indicator_name}: {status} ({errors}){notes}')
    ind_failed = sum(1 for r in ind_results if not r.pass_fail)

    print('\n=== Wave E: Signal audit (bar-by-bar ground truth) ===')
    sig_results = run_signal_audit()
    for r in sig_results:
        status = 'PASS' if r.pass_fail else 'FAIL'
        print(f'  {r.signal_name}: {status} (fires={r.fires}, expected={r.expected_fires}, '
              f'FP={r.false_positives}, FN={r.false_negatives})')
    sig_failed = sum(1 for r in sig_results if not r.pass_fail)

    print('\n=== Wave E: Benchmark (1294-bar BTC daily) ===')
    bench_results = run_benchmark()
    for b in bench_results:
        flag = ''
        if b.tier == 'pathological':
            flag = '  <- PATHOLOGICAL'
        elif b.tier == 'slow':
            flag = '  <- slow'
        print(f'  {b.indicator_name:25s}: {b.mean_ms:>7.3f} ms  [{b.tier}]{flag}')

    total_pass = (len(ind_results) - ind_failed) + (len(sig_results) - sig_failed)
    total = len(ind_results) + len(sig_results)
    print(f'\nWave E total: {total_pass}/{total} PASS '
          f'(indicators {len(ind_results) - ind_failed}/{len(ind_results)}, '
          f'signals {len(sig_results) - sig_failed}/{len(sig_results)})')
    sys.exit(0 if (ind_failed + sig_failed) == 0 else 1)

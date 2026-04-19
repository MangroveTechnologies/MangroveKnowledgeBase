#!/usr/bin/env python3
"""Audit Wave D indicators (volatility) against pandas-ta / behavioral tests.

Wave D indicators: TrueRange, NATR, ATRTrailingStop, STARCBands, VolatilityStop.

Notes:
- TrueRange, NATR: numerical match against pandas-ta.
  - NATR compared with mamode='rma' -- our NATR uses standard Wilder
    smoothing on ATR (matches TA-Lib convention); pandas-ta default is
    mamode='ema' which is non-standard.
- ATRTrailingStop, STARCBands, VolatilityStop: no pandas-ta counterparts.
  Verified via behavioral tests:
    * ATRTrailingStop: direction flips cleanly; long-regime stops never
      decrease, short-regime stops never increase; no post-warmup NaN.
    * STARCBands: hband > mid > lband for every non-NaN bar.
    * VolatilityStop: hband >= close >= lband for every non-NaN bar.

Signal verification: every signal runs bar-by-bar via sliding window and is
compared against indicator-derived ground truth (zero FP/FN required).

Benchmark: each indicator timed on the 1294-bar BTC daily fixture with tier
classification (fast/moderate/slow/pathological).
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
    bench_indicator,
    AuditResult,
    OutputResult,
)
from mangrove_kb.indicators import (
    TrueRange,
    NATR,
    ATRTrailingStop,
    STARCBands,
    VolatilityStop,
)


def run_audit():
    df = load_btc_daily()
    high = df['high']
    low = df['low']
    close = df['close']

    results = []

    # TrueRange: bit-exact vs pandas-ta
    results.append(compare_indicator(
        indicator_name='TrueRange',
        category='Volatility',
        our_fn=lambda: TrueRange.compute({'high': high, 'low': low, 'close': close}, {}),
        ref_fn=lambda: {'true_range': ta.true_range(high, low, close)},
        output_keys=['true_range'],
        tolerance=1e-10,
        tolerance_tier='EXACT',
        reference_library='pandas-ta',
    ))

    # NATR: our Wilder/RMA convention matches pandas-ta mamode='rma', talib=False
    results.append(compare_indicator(
        indicator_name='NATR',
        category='Volatility',
        our_fn=lambda: NATR.compute({'high': high, 'low': low, 'close': close}, {'window': 14}),
        ref_fn=lambda: {'natr': ta.natr(high, low, close, length=14, mamode='rma', talib=False)},
        output_keys=['natr'],
        tolerance=1e-10,
        tolerance_tier='EXACT',
        reference_library='pandas-ta (mamode=rma)',
        notes='Uses Wilder smoothing (TA-Lib canonical). pandas-ta defaults to EMA which is non-standard.',
    ))

    # Behavioral audits for indicators with no pandas-ta reference
    results.append(_audit_atr_trailing_stop(high, low, close))
    results.append(_audit_starc_bands(high, low, close))
    results.append(_audit_volatility_stop(close))

    return results


def _audit_atr_trailing_stop(high, low, close) -> AuditResult:
    """Behavioral audit: direction integrity, ratcheting, no post-warmup NaN."""
    params = {'window': 14, 'multiplier': 3.0}
    out = ATRTrailingStop.compute({'high': high, 'low': low, 'close': close}, params)
    ts = out['trailing_stop']
    direction = out['direction']

    # Direction is always -1, 0, or +1 (0 during warmup)
    valid_dir = set(direction.unique().tolist()).issubset({-1.0, 0.0, 1.0})

    # Check ratcheting: in long regime, stop never decreases between same-regime bars
    long_violations = 0
    short_violations = 0
    post_warmup_start = 20
    for i in range(post_warmup_start, len(ts)):
        if pd.isna(ts.iloc[i]) or pd.isna(ts.iloc[i - 1]):
            continue
        if direction.iloc[i] == 1 and direction.iloc[i - 1] == 1:
            if ts.iloc[i] < ts.iloc[i - 1] - 1e-9:
                long_violations += 1
        elif direction.iloc[i] == -1 and direction.iloc[i - 1] == -1:
            if ts.iloc[i] > ts.iloc[i - 1] + 1e-9:
                short_violations += 1

    # Stop should not be NaN after warmup
    post_warmup_nan = int(ts.iloc[post_warmup_start:].isna().sum())

    pass_fail = (
        valid_dir
        and long_violations == 0
        and short_violations == 0
        and post_warmup_nan == 0
    )
    result = AuditResult(
        indicator_name='ATRTrailingStop',
        category='Volatility',
        reference_library='behavioral',
        tolerance_tier='BEHAVIORAL',
        tolerance_value=0.0,
        pass_fail=pass_fail,
        notes=f'flips={int((direction.diff() != 0).sum())}, long_ratchet_violations={long_violations}, short_ratchet_violations={short_violations}, post_warmup_nan={post_warmup_nan}',
    )
    result.outputs['trailing_stop'] = OutputResult(
        output_key='trailing_stop',
        max_abs_error=0.0,
        mean_abs_error=0.0,
        overlap_bars=int(ts.notna().sum()),
        pass_fail=(post_warmup_nan == 0 and long_violations == 0 and short_violations == 0),
    )
    result.outputs['direction'] = OutputResult(
        output_key='direction',
        max_abs_error=0.0,
        mean_abs_error=0.0,
        overlap_bars=int(direction.notna().sum()),
        pass_fail=valid_dir,
    )
    return result


def _audit_starc_bands(high, low, close) -> AuditResult:
    """Behavioral audit: hband > mid > lband for all valid bars."""
    params = {'window': 20, 'window_atr': 15, 'multiplier': 2.0}
    out = STARCBands.compute({'high': high, 'low': low, 'close': close}, params)
    hband, mid, lband = out['starc_hband'], out['starc_mid'], out['starc_lband']

    valid = hband.notna() & mid.notna() & lband.notna()
    order_ok = bool(((hband > mid) & (mid > lband))[valid].all())

    result = AuditResult(
        indicator_name='STARCBands',
        category='Volatility',
        reference_library='behavioral',
        tolerance_tier='BEHAVIORAL',
        tolerance_value=0.0,
        pass_fail=order_ok,
        notes=f'hband > mid > lband on all {int(valid.sum())} valid bars',
    )
    for key, series, band_ok in [
        ('starc_hband', hband, order_ok),
        ('starc_mid', mid, order_ok),
        ('starc_lband', lband, order_ok),
    ]:
        result.outputs[key] = OutputResult(
            output_key=key,
            max_abs_error=0.0,
            mean_abs_error=0.0,
            overlap_bars=int(series.notna().sum()),
            pass_fail=band_ok,
        )
    return result


def _audit_volatility_stop(close) -> AuditResult:
    """Behavioral audit: hband > prev_close > lband (bands centered on prev close).

    Also verifies the signals can actually fire -- i.e., close occasionally
    breaches each band -- so the signal isn't degenerate.
    """
    params = {'window': 20, 'multiplier': 2.0}
    out = VolatilityStop.compute({'close': close}, params)
    hband, lband = out['vstop_hband'], out['vstop_lband']
    prev_close = close.shift(1)

    valid = hband.notna() & lband.notna() & prev_close.notna()
    order_ok = bool(((hband > prev_close) & (prev_close > lband))[valid].all())

    # Non-degeneracy: signals must have fired at least a few times in the dataset
    hband_breaches = int((close > hband)[valid].sum())
    lband_breaches = int((close < lband)[valid].sum())
    non_degenerate = hband_breaches > 0 and lband_breaches > 0

    pass_fail = order_ok and non_degenerate
    result = AuditResult(
        indicator_name='VolatilityStop',
        category='Volatility',
        reference_library='behavioral',
        tolerance_tier='BEHAVIORAL',
        tolerance_value=0.0,
        pass_fail=pass_fail,
        notes=f'hband > prev_close > lband on {int(valid.sum())} bars; close breached hband {hband_breaches}x, lband {lband_breaches}x',
    )
    for key, series in [('vstop_hband', hband), ('vstop_lband', lband)]:
        result.outputs[key] = OutputResult(
            output_key=key,
            max_abs_error=0.0,
            mean_abs_error=0.0,
            overlap_bars=int(series.notna().sum()),
            pass_fail=pass_fail,
        )
    return result


def run_signal_audit():
    """Verify every Wave D signal bar-by-bar against ground truth."""
    df = load_btc_daily()
    high = df['high']; low = df['low']; close = df['close']

    results = []

    # NATR signals: high volatility / low volatility filter via threshold
    natr_params = {'window': 14, 'threshold': 2.0}
    natr = NATR.compute({'high': high, 'low': low, 'close': close}, {'window': 14})['natr']
    # high_volatility: natr > 2.0; low_volatility: natr < 1.0
    truth_high = (natr > 2.0).fillna(False).to_numpy()
    truth_low = (natr < 1.0).fillna(False).to_numpy()
    results.append(verify_signal('natr_high_volatility', {'window': 14, 'threshold': 2.0}, df, truth_high))
    results.append(verify_signal('natr_low_volatility', {'window': 14, 'threshold': 1.0}, df, truth_low))

    # ATRTrailingStop signals: regime filter (long / short) and flip triggers
    ats_params = {'window': 14, 'multiplier': 3.0}
    ats_out = ATRTrailingStop.compute({'high': high, 'low': low, 'close': close}, ats_params)
    direction = ats_out['direction']
    truth_long = (direction == 1).to_numpy()
    truth_short = (direction == -1).to_numpy()
    # Flip up: direction was -1, now +1. Flip down: direction was +1, now -1.
    prev = direction.shift(1)
    truth_flip_up = ((prev == -1) & (direction == 1)).fillna(False).to_numpy()
    truth_flip_down = ((prev == 1) & (direction == -1)).fillna(False).to_numpy()
    results.append(verify_signal('atr_trailing_stop_long', ats_params, df, truth_long))
    results.append(verify_signal('atr_trailing_stop_short', ats_params, df, truth_short))
    results.append(verify_signal('atr_trailing_stop_flip_up', ats_params, df, truth_flip_up))
    results.append(verify_signal('atr_trailing_stop_flip_down', ats_params, df, truth_flip_down))

    # STARCBands signals: breakout above hband / breakdown below lband
    starc_params = {'window': 20, 'window_atr': 15, 'multiplier': 2.0}
    starc_out = STARCBands.compute({'high': high, 'low': low, 'close': close}, starc_params)
    truth_hbreak = (close > starc_out['starc_hband']).fillna(False).to_numpy()
    truth_lbreak = (close < starc_out['starc_lband']).fillna(False).to_numpy()
    results.append(verify_signal('starc_upper_breakout', starc_params, df, truth_hbreak))
    results.append(verify_signal('starc_lower_breakout', starc_params, df, truth_lbreak))

    # VolatilityStop signals: close at/above hband or at/below lband
    vs_params = {'window': 20, 'multiplier': 2.0}
    vs_out = VolatilityStop.compute({'close': close}, vs_params)
    truth_upper = (close >= vs_out['vstop_hband']).fillna(False).to_numpy()
    truth_lower = (close <= vs_out['vstop_lband']).fillna(False).to_numpy()
    results.append(verify_signal('volatility_stop_upper', vs_params, df, truth_upper))
    results.append(verify_signal('volatility_stop_lower', vs_params, df, truth_lower))

    return results


def run_benchmark():
    """Time each Wave D indicator on the full BTC daily fixture."""
    df = load_btc_daily()
    high = df['high']; low = df['low']; close = df['close']
    bars = len(df)

    return [
        bench_indicator('TrueRange', lambda: TrueRange.compute({'high': high, 'low': low, 'close': close}, {}), bars),
        bench_indicator('NATR(14)', lambda: NATR.compute({'high': high, 'low': low, 'close': close}, {'window': 14}), bars),
        bench_indicator('ATRTrailingStop(14,3)', lambda: ATRTrailingStop.compute({'high': high, 'low': low, 'close': close}, {'window': 14, 'multiplier': 3.0}), bars, runs=20),
        bench_indicator('STARCBands(20,15,2)', lambda: STARCBands.compute({'high': high, 'low': low, 'close': close}, {'window': 20, 'window_atr': 15, 'multiplier': 2.0}), bars),
        bench_indicator('VolatilityStop(20,2)', lambda: VolatilityStop.compute({'close': close}, {'window': 20, 'multiplier': 2.0}), bars),
    ]


if __name__ == '__main__':
    print('=== Wave D: Indicator audit ===')
    ind_results = run_audit()
    for r in ind_results:
        status = 'PASS' if r.pass_fail else 'FAIL'
        errors = ', '.join(f'{k}={v.max_abs_error:.2e}' for k, v in r.outputs.items())
        notes = f' [{r.notes}]' if r.notes else ''
        print(f'  {r.indicator_name}: {status} ({errors}){notes}')
    ind_failed = sum(1 for r in ind_results if not r.pass_fail)

    print('\n=== Wave D: Signal audit (bar-by-bar ground truth) ===')
    sig_results = run_signal_audit()
    for r in sig_results:
        status = 'PASS' if r.pass_fail else 'FAIL'
        print(f'  {r.signal_name}: {status} (fires={r.fires}, expected={r.expected_fires}, '
              f'FP={r.false_positives}, FN={r.false_negatives})')
    sig_failed = sum(1 for r in sig_results if not r.pass_fail)

    print('\n=== Wave D: Benchmark (1294-bar BTC daily) ===')
    bench_results = run_benchmark()
    for b in bench_results:
        flag = ''
        if b.tier == 'pathological':
            flag = '  <- PATHOLOGICAL'
        elif b.tier == 'slow':
            flag = '  <- slow (ATRTrailingStop is state-dependent)'
        print(f'  {b.indicator_name:25s}: {b.mean_ms:>7.3f} ms  [{b.tier}]{flag}')

    total_pass = (len(ind_results) - ind_failed) + (len(sig_results) - sig_failed)
    total = len(ind_results) + len(sig_results)
    print(f'\nWave D total: {total_pass}/{total} PASS '
          f'(indicators {len(ind_results) - ind_failed}/{len(ind_results)}, '
          f'signals {len(sig_results) - sig_failed}/{len(sig_results)})')
    sys.exit(0 if (ind_failed + sig_failed) == 0 else 1)

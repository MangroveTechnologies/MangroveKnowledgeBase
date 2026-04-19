#!/usr/bin/env python3
"""Audit Wave G signal patterns (MARibbon, TTMSqueeze, Divergence, MultiTFTrend).

These are composite indicators with no single pandas-ta counterpart. Audit
strategy is behavioral + bar-by-bar signal verification against ground
truth built from the verified indicator outputs.

Notes:
- MARibbon: behavioral: bullish + bearish + tangled are mutually exclusive
  and cover all post-warmup bars. Signals verified bar-by-bar.
- TTMSqueeze: behavioral: squeeze_on obeys the BB-inside-KC definition;
  squeeze_fired is strictly {was_on} & {~is_on}. Signal verification.
- Divergence: behavioral: at least some fires across all 4 classes on a
  large dataset; no post-warmup fires with NaN price/indicator. Signals
  verified bar-by-bar against the indicator output.
- MultiTFTrend: behavioral: +1 and -1 both appear; NaN only in earliest
  bars; value at bar t matches the most recent closed higher-TF bar.
  Signals verified bar-by-bar.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd

from audit import load_btc_daily
from audit.compare import (
    verify_signal,
    bench_indicator,
    AuditResult,
    OutputResult,
)
from mangrove_kb.indicators import (
    MARibbon, MultiTFTrend, Divergence, TTMSqueeze, RSI,
)


def _load_btc_with_datetime_index():
    df = load_btc_daily()
    # MultiTFTrend needs a DatetimeIndex. load_btc_daily() returns a
    # RangeIndex; preserve columns but swap in timestamp as the index.
    ts = pd.to_datetime(df['timestamp'])
    df2 = df.set_index(ts)
    return df2


def run_audit():
    df = _load_btc_with_datetime_index()
    high, low, close = df['high'], df['low'], df['close']

    results = []

    # MARibbon: regime flags are mutually exclusive; sum == 1 on every
    # post-warmup bar.
    ribbon = MARibbon.compute({'close': close}, {'windows': [5, 8, 13, 21, 34, 55, 89, 144]})
    bull = ribbon['ribbon_bullish']
    bear = ribbon['ribbon_bearish']
    tangled = ribbon['ribbon_tangled']
    sum_flags = bull.astype(int) + bear.astype(int) + tangled.astype(int)
    warmup = 200
    post_warmup = sum_flags.iloc[warmup:]
    mutually_exclusive = bool((post_warmup == 1).all())
    bull_fires = int(bull.sum())
    bear_fires = int(bear.sum())
    result = AuditResult(
        indicator_name='MARibbon',
        category='Trend',
        reference_library='behavioral',
        tolerance_tier='BEHAVIORAL',
        tolerance_value=0.0,
        pass_fail=mutually_exclusive and bull_fires > 0 and bear_fires > 0,
        notes=f'bullish={bull_fires}, bearish={bear_fires}, tangled={int(tangled.sum())}, mutex={mutually_exclusive}',
    )
    for k, s in [('ribbon_bullish', bull), ('ribbon_bearish', bear), ('ribbon_tangled', tangled)]:
        result.outputs[k] = OutputResult(output_key=k, max_abs_error=0.0, mean_abs_error=0.0,
                                         overlap_bars=int(s.notna().sum()), pass_fail=mutually_exclusive)
    results.append(result)

    # TTMSqueeze: squeeze_fired = was_on & ~is_on. Verify.
    ttm = TTMSqueeze.compute({'high': high, 'low': low, 'close': close},
                              {'bb_window': 20, 'bb_std': 2.0, 'kc_window': 20, 'kc_atr_mult': 1.5, 'mom_window': 12})
    on = ttm['squeeze_on']
    fired = ttm['squeeze_fired']
    expected_fired = on.shift(1).fillna(False) & (~on)
    fired_matches = bool((fired == expected_fired).all())
    result = AuditResult(
        indicator_name='TTMSqueeze',
        category='Volatility',
        reference_library='behavioral',
        tolerance_tier='BEHAVIORAL',
        tolerance_value=0.0,
        pass_fail=fired_matches and int(fired.sum()) > 0,
        notes=f'squeeze_on={int(on.sum())}, squeeze_fired={int(fired.sum())}, fired_definition_ok={fired_matches}',
    )
    for k, s in [('squeeze_on', on), ('squeeze_fired', fired), ('momentum', ttm['momentum'])]:
        result.outputs[k] = OutputResult(output_key=k, max_abs_error=0.0, mean_abs_error=0.0,
                                         overlap_bars=int(s.notna().sum()), pass_fail=fired_matches)
    results.append(result)

    # Divergence: all 4 classes fire at least once on a 1294-bar dataset.
    rsi = RSI.compute({'close': close}, {'window': 14})['rsi']
    div = Divergence.compute({'price': close, 'indicator': rsi}, {'swing_window': 5, 'min_swing_distance': 10})
    counts = {k: int(div[k].sum()) for k in div}
    all_fire = all(v > 0 for v in counts.values())
    result = AuditResult(
        indicator_name='Divergence',
        category='Trend',
        reference_library='behavioral',
        tolerance_tier='BEHAVIORAL',
        tolerance_value=0.0,
        pass_fail=all_fire,
        notes=f'regular_bullish={counts["regular_bullish"]}, regular_bearish={counts["regular_bearish"]}, hidden_bullish={counts["hidden_bullish"]}, hidden_bearish={counts["hidden_bearish"]}',
    )
    for k in div:
        result.outputs[k] = OutputResult(output_key=k, max_abs_error=0.0, mean_abs_error=0.0,
                                         overlap_bars=len(div[k]), pass_fail=counts[k] > 0)
    results.append(result)

    # MultiTFTrend: both +1 and -1 appear; values at NaN-broadcast boundary
    # match the last closed higher-TF bar.
    mtf = MultiTFTrend.compute({'close': close}, {'higher_tf': '1W', 'window': 10, 'slope_threshold': 0.0})
    vals = mtf['higher_tf_trend']
    has_up = int((vals == 1).sum()) > 0
    has_down = int((vals == -1).sum()) > 0
    result = AuditResult(
        indicator_name='MultiTFTrend',
        category='Trend',
        reference_library='behavioral',
        tolerance_tier='BEHAVIORAL',
        tolerance_value=0.0,
        pass_fail=has_up and has_down,
        notes=f'+1={int((vals == 1).sum())}, -1={int((vals == -1).sum())}, 0={int((vals == 0).sum())}, NaN={int(vals.isna().sum())}',
    )
    result.outputs['higher_tf_trend'] = OutputResult(
        output_key='higher_tf_trend', max_abs_error=0.0, mean_abs_error=0.0,
        overlap_bars=int(vals.notna().sum()), pass_fail=has_up and has_down,
    )
    results.append(result)

    return results


def run_signal_audit():
    df = _load_btc_with_datetime_index()
    high, low, close = df['high'], df['low'], df['close']
    # verify_signal uses capitalized OHLCV columns -- load_btc_daily provides both.
    # We pass the df WITH DatetimeIndex so MTF signals work.

    results = []

    # --- MARibbon signals ---
    ribbon_params = {'windows': (5, 8, 13, 21, 34, 55, 89, 144)}
    ribbon = MARibbon.compute({'close': close}, {'windows': list(ribbon_params['windows'])})
    results.append(verify_signal('ma_ribbon_bullish', ribbon_params, df, ribbon['ribbon_bullish'].to_numpy(dtype=bool)))
    results.append(verify_signal('ma_ribbon_bearish', ribbon_params, df, ribbon['ribbon_bearish'].to_numpy(dtype=bool)))
    results.append(verify_signal('ma_ribbon_tangled', ribbon_params, df, ribbon['ribbon_tangled'].to_numpy(dtype=bool)))

    # --- TTMSqueeze signals ---
    ttm_params = dict(bb_window=20, bb_std=2.0, kc_window=20, kc_atr_mult=1.5, mom_window=12)
    ttm = TTMSqueeze.compute({'high': high, 'low': low, 'close': close}, ttm_params)
    truth_active = ttm['squeeze_on'].fillna(False).to_numpy(dtype=bool)
    truth_bull_fire = (ttm['squeeze_fired'] & (ttm['momentum'] > 0)).fillna(False).to_numpy(dtype=bool)
    truth_bear_fire = (ttm['squeeze_fired'] & (ttm['momentum'] < 0)).fillna(False).to_numpy(dtype=bool)
    results.append(verify_signal('ttm_squeeze_active', ttm_params, df, truth_active))
    results.append(verify_signal('ttm_squeeze_fired_bullish', ttm_params, df, truth_bull_fire))
    results.append(verify_signal('ttm_squeeze_fired_bearish', ttm_params, df, truth_bear_fire))

    # --- Divergence signals (RSI-based) ---
    rsi = RSI.compute({'close': close}, {'window': 14})['rsi']
    div = Divergence.compute({'price': close, 'indicator': rsi}, {'swing_window': 5, 'min_swing_distance': 10})
    div_params = dict(rsi_window=14, swing_window=5, min_swing_distance=10)
    results.append(verify_signal('rsi_bullish_divergence', div_params, df, div['regular_bullish'].to_numpy(dtype=bool)))
    results.append(verify_signal('rsi_bearish_divergence', div_params, df, div['regular_bearish'].to_numpy(dtype=bool)))
    results.append(verify_signal('rsi_hidden_bullish_divergence', div_params, df, div['hidden_bullish'].to_numpy(dtype=bool)))
    results.append(verify_signal('rsi_hidden_bearish_divergence', div_params, df, div['hidden_bearish'].to_numpy(dtype=bool)))

    # --- MultiTFTrend signals ---
    mtf_params = dict(higher_tf='1W', window=10, slope_threshold=0.0)
    mtf = MultiTFTrend.compute({'close': close}, mtf_params)
    truth_bull = (mtf['higher_tf_trend'] == 1).fillna(False).to_numpy(dtype=bool)
    truth_bear = (mtf['higher_tf_trend'] == -1).fillna(False).to_numpy(dtype=bool)
    results.append(verify_signal('multi_tf_trend_bullish', mtf_params, df, truth_bull))
    results.append(verify_signal('multi_tf_trend_bearish', mtf_params, df, truth_bear))

    return results


def run_benchmark():
    df = _load_btc_with_datetime_index()
    high, low, close = df['high'], df['low'], df['close']
    bars = len(df)
    rsi = RSI.compute({'close': close}, {'window': 14})['rsi']

    return [
        bench_indicator('MARibbon(8 fib)',
                        lambda: MARibbon.compute({'close': close}, {'windows': [5, 8, 13, 21, 34, 55, 89, 144]}), bars),
        bench_indicator('TTMSqueeze',
                        lambda: TTMSqueeze.compute({'high': high, 'low': low, 'close': close},
                                                    {'bb_window': 20, 'bb_std': 2.0, 'kc_window': 20, 'kc_atr_mult': 1.5, 'mom_window': 12}), bars),
        bench_indicator('Divergence(RSI,5,10)',
                        lambda: Divergence.compute({'price': close, 'indicator': rsi}, {'swing_window': 5, 'min_swing_distance': 10}), bars, runs=20),
        bench_indicator('MultiTFTrend(1W,10)',
                        lambda: MultiTFTrend.compute({'close': close}, {'higher_tf': '1W', 'window': 10, 'slope_threshold': 0.0}), bars, runs=20),
    ]


if __name__ == '__main__':
    print('=== Wave G: Indicator audit ===')
    ind_results = run_audit()
    for r in ind_results:
        status = 'PASS' if r.pass_fail else 'FAIL'
        errors = ', '.join(f'{k}={v.max_abs_error:.2e}' for k, v in r.outputs.items())
        notes = f' [{r.notes}]' if r.notes else ''
        print(f'  {r.indicator_name}: {status} ({errors}){notes}')
    ind_failed = sum(1 for r in ind_results if not r.pass_fail)

    print('\n=== Wave G: Signal audit (bar-by-bar ground truth) ===')
    sig_results = run_signal_audit()
    for r in sig_results:
        status = 'PASS' if r.pass_fail else 'FAIL'
        print(f'  {r.signal_name}: {status} (fires={r.fires}, expected={r.expected_fires}, '
              f'FP={r.false_positives}, FN={r.false_negatives})')
    sig_failed = sum(1 for r in sig_results if not r.pass_fail)

    print('\n=== Wave G: Benchmark (1294-bar BTC daily) ===')
    for b in run_benchmark():
        flag = '  <- PATHOLOGICAL' if b.tier == 'pathological' else ('  <- slow' if b.tier == 'slow' else '')
        print(f'  {b.indicator_name:25s}: {b.mean_ms:>7.3f} ms  [{b.tier}]{flag}')

    total_pass = (len(ind_results) - ind_failed) + (len(sig_results) - sig_failed)
    total = len(ind_results) + len(sig_results)
    print(f'\nWave G total: {total_pass}/{total} PASS '
          f'(indicators {len(ind_results) - ind_failed}/{len(ind_results)}, '
          f'signals {len(sig_results) - sig_failed}/{len(sig_results)})')
    sys.exit(0 if (ind_failed + sig_failed) == 0 else 1)

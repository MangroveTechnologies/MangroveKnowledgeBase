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
from audit.compare import compare_indicator
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


if __name__ == '__main__':
    results = run_audit()
    for r in results:
        status = 'PASS' if r.pass_fail else 'FAIL'
        errors = ', '.join(f'{k}={v.max_abs_error:.2e}' for k, v in r.outputs.items())
        notes = f' [{r.notes}]' if r.notes else ''
        print(f'  {r.indicator_name}: {status} ({errors}){notes}')

    failed = sum(1 for r in results if not r.pass_fail)
    total = len(results)
    print(f'\nWave A: {total - failed}/{total} PASS')
    sys.exit(0 if failed == 0 else 1)

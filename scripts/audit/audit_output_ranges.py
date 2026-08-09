#!/usr/bin/env python3
"""Check every declared output `range` in the ontology against real market data.

A range is a CLAIM about an indicator: "this output never leaves these bounds". Nothing was
testing it, and the claim is easy to get wrong in a way that reads as reasonable -- ten signed
outputs were given a lower bound of 0 because they are measured in price units, when a difference
of two prices is not a price and crosses zero constantly. `macd` was declared non-negative while
being negative on 582 of 1,294 bars.

This runs every indicator over every fixture and reports any observed value outside its declared
range. It would have caught all ten immediately.

Seven fixtures rather than one, deliberately: a wrong bound can survive on a single asset that
never happens to exercise it. BTC daily alone leaves a bound that only breaks on a low-priced or
fast-timeframe asset undetected.

    PYTHONPATH=. python3 scripts/audit/audit_output_ranges.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd  # noqa: E402

import mangrove_kb  # noqa: E402

if "site-packages" in mangrove_kb.__file__:  # pragma: no cover - guardrail
    raise SystemExit(f"ABORT: mangrove_kb resolved to {mangrove_kb.__file__}; use PYTHONPATH=<repo root>")

import mangrove_kb.indicators as I  # noqa: E402

GRAPH = Path(__file__).resolve().parents[2] / "ontology" / "signal-indicator-ontology.json"
DATA_DIR = Path(__file__).resolve().parents[2] / "data"

#: Params for indicators whose docstrings declare no default. Without these the indicator is
#: skipped, and a silent skip is how a range goes unchecked while the report still says PASS.
EXPLICIT_PARAMS = {
    "SMA": {"window": 20}, "DEMA": {"window": 20}, "TEMA": {"window": 20},
    "TRIMA": {"window": 20}, "SMMA": {"window": 20}, "HMA": {"window": 16},
    "EPMA": {"window": 20}, "WMA": {"window": 20},
    "AwesomeOscillator": {"window1": 5, "window2": 34},
    "Ichimoku": {"window1": 9, "window2": 26, "window3": 52, "visual": False},
    "KST": {"roc1": 10, "roc2": 15, "roc3": 20, "roc4": 30, "window1": 10, "window2": 10,
            "window3": 10, "window4": 15, "nsig": 9},
    "MultiTFSlope": {"higher_tf": "W", "window": 10},
    "SwingDelta": {"swing_window": 5, "min_swing_distance": 10},
    "MAMA": {"fast_limit": 0.5, "slow_limit": 0.05, "warmup_bars": 64},
    "DonchianChannel": {"window": 20, "include_current_bar": False},
    "KeltnerChannel": {"window": 20, "window_atr": 10, "original_version": False, "multiplier": 2.0},
    "UltimateOscillator": {"window1": 7, "window2": 14, "window3": 28,
                           "weight1": 4.0, "weight2": 2.0, "weight3": 1.0},
    "VPT": {"smoothing_factor": 0},
}

TOL = 1e-9


def load(path: Path) -> pd.DataFrame:
    d = pd.read_csv(path)
    d.columns = [c.strip().lower() for c in d.columns]
    d["timestamp"] = pd.to_datetime(d["timestamp"])
    d = d.sort_values("timestamp")
    return pd.DataFrame(
        {"Open": d["open"].values, "High": d["high"].values, "Low": d["low"].values,
         "Close": d["close"].values, "Volume": d["volume"].values},
        index=pd.DatetimeIndex(d["timestamp"]),
    )


def main() -> int:
    graph = json.loads(GRAPH.read_text())
    indicators = [a for a in graph["atoms"] if a["id"].startswith("procedure:indicator")]

    violations, skipped, total = [], set(), 0
    for path in sorted(DATA_DIR.glob("*.csv")):
        df = load(path)
        rsi = I.RSI.compute({"close": df["Close"]}, {"window": 14})["rsi"]
        series = {"open": df["Open"], "high": df["High"], "low": df["Low"], "close": df["Close"],
                  "volume": df["Volume"], "price": df["Close"], "indicator": rsi}
        n = 0
        for atom in indicators:
            name = atom["title"]
            cls = getattr(I, name, None)
            outputs = atom["props"].get("outputs") or {}
            if cls is None or not hasattr(cls, "compute") or not outputs:
                continue
            params = {k: v.get("default") for k, v in (atom["props"].get("params") or {}).items()}
            params.update(EXPLICIT_PARAMS.get(name, {}))
            if any(v is None for v in params.values()):
                skipped.add((name, "parameter with no default and none supplied here"))
                continue
            data = {k: series[k] for k in cls._data if k in series}
            if len(data) != len(cls._data):
                skipped.add((name, f"needs {cls._data}"))
                continue
            try:
                result = cls.compute(data, params)
            except Exception as exc:
                skipped.add((name, f"{type(exc).__name__}: {exc}"))
                continue
            for out_name, spec in outputs.items():
                rng = spec.get("range")
                if not isinstance(rng, list) or out_name not in result:
                    continue
                s = pd.to_numeric(pd.Series(result[out_name]), errors="coerce").dropna()
                if s.empty:
                    continue
                n += 1
                lo, hi = rng
                if lo is not None and s.min() < lo - TOL:
                    violations.append((path.name, name, out_name, rng, f"observed min {s.min():.6g}"))
                if hi is not None and s.max() > hi + TOL:
                    violations.append((path.name, name, out_name, rng, f"observed max {s.max():.6g}"))
        total += n
        print(f"  {path.name:40} {len(df):6} bars   {n:4} ranges checked")

    print()
    print(f"output-range conformance: {total} checks across {len(list(DATA_DIR.glob('*.csv')))} "
          f"assets/timeframes")
    if violations:
        print(f"VIOLATIONS: {len(violations)}")
        for fixture, ind, out, rng, detail in violations:
            print(f"   {ind}.{out} declared {rng} but {detail}   [{fixture}]")
    else:
        print("VIOLATIONS: 0")
    if skipped:
        print(f"\nnot checked ({len(skipped)}) -- these ranges are UNVERIFIED, not passing:")
        for name, why in sorted(skipped):
            print(f"   {name:24} {why}")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())

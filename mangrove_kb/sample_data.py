"""Sample OHLCV data generator.

Provides a deterministic, dependency-free helper so every quickstart snippet
runs out of the box -- no CSV file, no download, no network call. The generated
DataFrame uses the canonical **lowercase** ``open/high/low/close/volume`` columns
that the signals and indicators in this package expect, so the sample data agrees
with what the knowledge graph publishes for every node.

Capitalized frames are still accepted -- signals normalize OHLCV column case at
the registry boundary -- but lowercase is what this package produces and states.

Example:
    >>> from mangrove_kb import sample_ohlcv, RuleRegistry
    >>> df = sample_ohlcv()
    >>> RuleRegistry.evaluate({"name": "rsi_oversold", "params": {"window": 14}}, df)
    True
"""
import numpy as np
import pandas as pd

__all__ = ["sample_ohlcv"]


def sample_ohlcv(
    rows: int = 200,
    trend: str = "down",
    start_price: float = 100.0,
    volatility: float = 0.02,
    seed: int = 10,
) -> pd.DataFrame:
    """Generate a deterministic synthetic OHLCV DataFrame for examples and tests.

    The output is a geometric random walk with a mild directional drift, shaped
    into realistic candles. It is fully self-contained -- no file, no download,
    no network -- so quickstart snippets run immediately on a clean install.

    Args:
        rows (int): Number of bars (rows) to generate. Range: 2-100000. Default: 200.
        trend (str): Directional drift, one of "down", "up", or "flat". The
            default "down" lets oversold-style signals (e.g. ``rsi_oversold``)
            actually fire, matching the common first example. Default: "down".
        start_price (float): Close price of the first bar. Range: >0. Default: 100.0.
        volatility (float): Per-bar standard deviation of log-returns. Range: >=0.
            Default: 0.02.
        seed (int): Seed for the random generator so the data is reproducible.
            Default: 10 (a downtrend that makes the rsi_oversold quickstart
            example actually fire).

    Returns:
        pd.DataFrame: ``rows`` rows indexed by a daily ``DatetimeIndex`` named
        ``Timestamp``, with float columns ``open``, ``high``, ``low``,
        ``close``, ``volume`` -- the canonical lowercase OHLCV schema the
        signals and indicators expect.

    Raises:
        ValueError: If ``rows`` < 2, ``start_price`` <= 0, ``volatility`` < 0, or
            ``trend`` is not one of "down", "up", "flat".
    """
    if rows < 2:
        raise ValueError(f"rows must be >= 2, got {rows}")
    if start_price <= 0:
        raise ValueError(f"start_price must be > 0, got {start_price}")
    if volatility < 0:
        raise ValueError(f"volatility must be >= 0, got {volatility}")

    drift_by_trend = {"down": -0.004, "up": 0.004, "flat": 0.0}
    if trend not in drift_by_trend:
        raise ValueError(f"trend must be one of {sorted(drift_by_trend)}, got {trend!r}")
    drift = drift_by_trend[trend]

    rng = np.random.default_rng(seed)

    # Close as a geometric random walk: log-returns are drift + gaussian noise.
    log_returns = drift + volatility * rng.standard_normal(rows)
    close = start_price * np.exp(np.cumsum(log_returns))

    # Open at the prior bar's close (first bar opens at start_price).
    open_ = np.empty(rows)
    open_[0] = start_price
    open_[1:] = close[:-1]

    # High/Low straddle the open-close body with a positive intrabar wick.
    body_high = np.maximum(open_, close)
    body_low = np.minimum(open_, close)
    wick = volatility * np.abs(rng.standard_normal(rows))
    high = body_high * (1.0 + wick)
    low = body_low * (1.0 - wick)

    # Volume: positive, lognormally distributed around a realistic base.
    volume = 1_000.0 * np.exp(0.3 * rng.standard_normal(rows))

    index = pd.date_range("2024-01-01", periods=rows, freq="D", name="Timestamp")
    return pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=index,
    )

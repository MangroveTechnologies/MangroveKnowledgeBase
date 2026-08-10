import functools
import warnings

import numpy as np
import pandas as pd


def _to_native(value):
    """Coerce numpy return types to native Python / pandas containers.

    Signal functions compute their result by comparing numpy/pandas scalars
    (e.g. ``close.iloc[-1] > sma.iloc[-1]``), which yields a ``numpy.bool_``
    rather than a native Python ``bool``. ``numpy.bool_`` is not
    JSON-serializable, so passing a signal result straight into
    ``json.dumps()`` or a webhook payload raises
    ``TypeError: Object of type bool_ is not JSON serializable`` and silently
    halts downstream automation.

    Normalizing here -- at the single point every signal is registered through
    -- guarantees the public return-type contract (native ``bool`` or a native
    ``pd.Series``) for every signal, whether it is called directly or via
    :meth:`RuleRegistry.evaluate`.
    """
    if isinstance(value, np.generic):  # numpy scalar (bool_, int64, float64, ...)
        return value.item()
    if isinstance(value, np.ndarray):  # array result -> native boolean container
        return pd.Series(value)
    return value


#: The canonical OHLCV column names. Lowercase, matching the indicator layer -- `ATR._data` is
#: `['high', 'low', 'close']` and `ATR.compute` reads `data['high']`.
OHLCV = ("open", "high", "low", "close", "volume")


def _canonical_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return `df` with its OHLCV columns lowercased. Everything else is left exactly as it is.

    Signals used to require capitalised columns while indicators required lowercase ones, so the
    library contradicted itself at the boundary between them and the knowledge graph could not state
    a single truth: it published `['high', 'low', 'close']` for every signal, and passing a frame
    with those columns raised ``KeyError: 'High'``. Lowercase wins because it is already the
    indicator contract and the wider convention.

    Capitalised frames keep working -- this is a rename at the boundary, not a break. Normalizing
    here, at the single point every signal is registered through, is the same argument that puts
    :func:`_to_native` here.

    **Only the five OHLCV names are touched.** Lowercasing the whole frame would quietly rewrite a
    caller's own columns -- SwingDelta reads a companion indicator column, and `MyIndicator` becoming
    `myindicator` would be a silent data bug introduced by a convenience.
    """
    present = set(df.columns)
    renames = {c: c.lower() for c in df.columns
               if isinstance(c, str) and c.lower() in OHLCV and c != c.lower()
               and c.lower() not in present}      # a frame holding BOTH `Close` and `close` keeps both
    return df.rename(columns=renames) if renames else df


class RuleRegistry:
    _registry = {}

    #: Retired signal names -> the name that replaced them. A deprecated name must keep evaluating,
    #: because a stored strategy holds the name as a string and cannot be migrated by us. It must
    #: NOT appear in `names()` or the catalogue, or every rename would inflate the signal count and
    #: show the same signal twice. Registering the old name as a second signal did exactly that:
    #: 247 became 249.
    _aliases = {}

    @classmethod
    def register(cls, name):
        def wrapper(fn):
            @functools.wraps(fn)
            def coerced(*args, **kwargs):
                # Every signal takes the frame first; `evaluate` and every caller pass it
                # positionally, but accept it by name too rather than silently skipping the
                # normalization for a caller who spells it out.
                if args and isinstance(args[0], pd.DataFrame):
                    args = (_canonical_columns(args[0]),) + args[1:]
                elif isinstance(kwargs.get("df"), pd.DataFrame):
                    kwargs = {**kwargs, "df": _canonical_columns(kwargs["df"])}
                return _to_native(fn(*args, **kwargs))

            cls._registry[name] = coerced
            return coerced

        return wrapper

    @classmethod
    def alias(cls, old_name: str, new_name: str):
        """Record `old_name` as a retired spelling of `new_name`."""
        cls._aliases[old_name] = new_name

    @classmethod
    def resolve(cls, name: str) -> str:
        """The current name for `name`, warning if a retired one was used."""
        target = cls._aliases.get(name)
        if target is None:
            return name
        warnings.warn(
            f"signal {name!r} has been renamed to {target!r}; the old name still evaluates but "
            f"will be removed. Registered names are the strategy-facing contract, so this is a "
            f"rename with a grace period, not a break.",
            DeprecationWarning, stacklevel=3,
        )
        return target

    @classmethod
    def names(cls) -> frozenset:
        """Return the set of registered signal names.

        Supported API for "which signals exist?" -- previously answerable only by reading the
        private ``_registry``, which MangroveAI does today from a request-validation hot path.

        The need is concrete: an unregistered signal name used to reach evaluation, where the
        ``ValueError`` below was swallowed into ``return False``, and the response came back
        successful with no orders -- indistinguishable from a valid signal that simply did not fire.

        Reflects whatever is registered at call time, not an import-time snapshot: a consumer
        registering its own signals must validate against the registry it evaluates with, and
        MangroveAI does register additional signals of its own.
        """
        return frozenset(cls._registry)

    @classmethod
    def has(cls, name: str) -> bool:
        """Whether `name` is a registered signal. Membership test without evaluating.

        `evaluate` needs a DataFrame, so it was not usable as a validity check.
        """
        return name in cls._registry or name in cls._aliases

    @classmethod
    def evaluate(cls, rule, df):
        rule_name = cls.resolve(rule["name"])
        if rule_name not in cls._registry:
            raise ValueError(f"Unknown rule name: {rule_name}")

        # Get parameters (support both "params" and "parameters" keys)
        params = dict(rule.get("parameters", rule.get("params", {})))

        # Map common parameter name variations for backward compatibility
        if "short_period" in params and "window_fast" not in params:
            params["window_fast"] = params.pop("short_period")
        if "long_period" in params and "window_slow" not in params:
            params["window_slow"] = params.pop("long_period")
        if "lookback" in params and "window" not in params:
            params["window"] = params.pop("lookback")
        if "period" in params and "window" not in params:
            params["window"] = params.pop("period")

        return cls._registry[rule_name](df, **params)

class RuleRegistry:
    _registry = {}

    @classmethod
    def register(cls, name):
        def wrapper(fn):
            cls._registry[name] = fn
            return fn

        return wrapper

    @classmethod
    def evaluate(cls, rule, df):
        rule_name = rule["name"]
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

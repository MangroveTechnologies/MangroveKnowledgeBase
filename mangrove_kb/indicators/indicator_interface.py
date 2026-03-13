"""Interface for all technical indicators."""
import pandas as pd


class IndicatorInterface:
    """
    Base interface for all technical indicators.

    Indicators are stateless - all computation via classmethods.

    Subclasses define:
        _data: List of required data series (e.g., ["close"])
        _params: List of required parameters (e.g., ["window"])
        _outputs: List of output names (e.g., ["rsi"])
        _compute(): Classmethod implementing calculation
    """

    name = None        # Auto-set from class name
    _data = []         # Required data series
    _params = []       # Required parameters
    _outputs = []      # Output names

    def __init_subclass__(cls):
        """Auto-set name from class name if not provided."""
        if cls.name is None:
            cls.name = cls.__name__

    def __init__(self):
        """Prevent instantiation."""
        raise TypeError(
            f"{self.__class__.__name__} should not be instantiated. "
            f"Use {self.__class__.__name__}.compute() instead."
        )

    @classmethod
    def inputs(cls) -> dict:
        """Return {'data': [...], 'params': [...]}"""
        return {'data': cls._data, 'params': cls._params}

    @classmethod
    def outputs(cls) -> dict:
        """Return {'names': [...], 'count': N}"""
        return {'names': cls._outputs, 'count': len(cls._outputs)}

    @classmethod
    def compute(cls, data: dict[str, pd.Series], params: dict[str, any]) -> dict[str, pd.Series]:
        """
        Compute the indicator.

        Args:
            data: {'close': series, 'high': series, ...}
            params: {'window': 14, ...}

        Returns:
            {'rsi': series, ...}
        """
        cls._validate(data, params)
        return cls._compute(data, params)

    @classmethod
    def _validate(cls, data: dict, params: dict):
        """Validate inputs."""
        missing_data = [f for f in cls._data if f not in data]
        if missing_data:
            raise ValueError(f"{cls.name} missing data: {missing_data}")

        missing_params = [f for f in cls._params if f not in params]
        if missing_params:
            raise ValueError(f"{cls.name} missing params: {missing_params}")

    @classmethod
    def _compute(cls, data: dict, params: dict) -> dict:
        """Implement calculation. Override in subclasses."""
        raise NotImplementedError(f"{cls.name} must implement _compute()")

# Contributing to MangroveKnowledgeBase

We welcome contributions to the signals library, indicator implementations, and knowledge base content.

## Getting Started

```bash
git clone https://github.com/MangroveTechnologies/MangroveKnowledgeBase.git
cd MangroveKnowledgeBase
pip install -e ".[dev]"
pytest tests/ -v
```

## Adding a Signal

1. Choose the correct module in `mangrove_knowledge_base/signals/` (momentum, trend, volume, volatility, or patterns)

2. Write the signal function with the required docstring format:

```python
@RuleRegistry.register("your_signal_name")
def your_signal_name(df: pd.DataFrame, window: int = 14, threshold: float = 70.0) -> bool:
    """
    One-line description of what this signal detects.

    Type: TRIGGER
    Requires: Close

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data.
        window (int): Lookback period. Range: 2-100. Default: 14.
        threshold (float): Threshold value. Range: 0.0-100.0. Default: 70.0.

    Returns:
        bool: True if condition met, False otherwise.
    """
```

3. The docstring IS the metadata. Include:
   - `Type:` TRIGGER or FILTER
   - `Requires:` comma-separated column names (Open, High, Low, Close, Volume)
   - Every parameter with `Range: min-max` and `Default: value`

4. Run tests: `pytest tests/ -v`

## Adding an Indicator

1. Add the class to the appropriate module in `mangrove_knowledge_base/indicators/`

2. Follow the IndicatorInterface pattern:

```python
class YourIndicator(IndicatorInterface):
    """Description of the indicator."""

    _data = ["close"]                    # required input columns
    _params = ["window"]                 # required parameters
    _outputs = ["your_output"]           # output column names

    @classmethod
    def _compute(cls, data, params):
        close = data["close"]
        window = params["window"]
        result = close.rolling(window).mean()
        return {"your_output": pd.Series(result, name="your_output")}
```

3. Export it in `mangrove_knowledge_base/indicators/__init__.py`

## Code Standards

- Pure Python only (no C extensions, no TA-Lib dependency)
- All computations must be vectorized (pandas/numpy, no Python loops over bars)
- Indicators are stateless classmethods -- no instance state
- Signals return bool, indicators return dict of pd.Series
- No hardcoded magic numbers -- use parameters with documented ranges
- Line length: 120 characters max

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_signal_service.py -v

# Run with coverage (if installed)
pytest tests/ --cov=mangrove_knowledge_base
```

Every new signal must be parseable by the docstring parser. The existing tests in `test_docstring_parser.py` validate this automatically for all registered signals.

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`feat/your-signal-name`)
3. Add the signal or indicator with proper docstring
4. Run `pytest tests/ -v` -- all tests must pass
5. Run `flake8 mangrove_knowledge_base/ --max-line-length=120`
6. Submit a PR with a description of what the signal/indicator does and references (textbooks, papers, or trading resources)

## Knowledge Base Content

The 11 markdown documents in `knowledge-base/` are the source of truth for trading education content. To contribute:

1. Edit the relevant `.md` file in `knowledge-base/`
2. Follow the existing section numbering and formatting
3. Add glossary terms to `09-glossary.md` if introducing new concepts
4. Cross-references are automatically detected by the KB server

## Questions

Open an issue on [GitHub](https://github.com/MangroveTechnologies/MangroveKnowledgeBase/issues) or contact the team at team@mangrovetechnologies.ai.

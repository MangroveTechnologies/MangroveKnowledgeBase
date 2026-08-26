"""A docstring's authored bounds and defaults must reach the graph.

Two lift defects emitted authored values as null, and null means "nobody chose this" to
every consumer -- so the corruption was invisible until the graph was diffed against the
docstrings it was built from:

* `_RANGE`'s upper bound was greedy, so `Range: 0.0-100.0.` captured `100.0.` (sentence
  period included), `float()` rejected it, and the maximum became null. Integer maxima
  survived (`float("15.")` parses), which is why the damage landed exactly on the 91
  decimal-valued bounds.
* `_num` answers only for numeric and boolean literals, so a str default
  (`Default: bullish`) and a tuple default (`Default: (5, 8, 13, ...)`) both lifted as
  null -- 13 authored defaults looked unauthored.

These assertions read the committed record. `test_build_is_deterministic.py` proves the
builder reproduces that record from the tree, so pinning the record pins the lift.
"""
import json
from pathlib import Path

import pytest

COMMITTED = Path(__file__).resolve().parent.parent / "ontology" / "signal-indicator-ontology.json"


@pytest.fixture(scope="module")
def params():
    atoms = json.loads(COMMITTED.read_text())["atoms"]
    return {a["id"]: (a.get("props") or {}).get("params") or {} for a in atoms}


def test_a_decimal_maximum_survives_the_sentence_period(params):
    p = params["procedure:signal-ao-bullish"]["threshold"]
    assert p["max"] == 100.0, "the docstring declares Range: 0.0-100.0"
    assert p["min"] == 0.0


def test_a_str_default_is_authored_not_null(params):
    assert params["procedure:signal-ema-crossover"]["direction"]["default"] == "bullish"
    assert params["procedure:signal-multi-tf-trend-bullish"]["higher_tf"]["default"] == "1W"


def test_a_tuple_default_lands_as_a_list(params):
    assert params["procedure:signal-ma-ribbon-bullish"]["windows"]["default"] == \
        [5, 8, 13, 21, 34, 55, 89, 144]


def test_no_signal_declares_a_range_the_graph_dropped(params):
    """The general form: a param whose docstring declares `Range: a-b` carries both bounds.

    Asserted structurally rather than by re-parsing docstrings: a lifted `min` without a
    `max` was the defect's exact signature (the two are captured by one regex, so a
    legitimate half-open range cannot come out of it).
    """
    import re
    import inspect
    import mangrove_kb.signals  # noqa: F401 -- registers every signal
    from mangrove_kb.registry import RuleRegistry

    # The lift's own numeric pattern. A non-numeric span (`Range: 1min-1Y` on a str
    # timeframe, `Range: true-false` on a bool) states a domain, not bounds, and null
    # min/max is the correct lift for it -- so only a numeric declaration obligates.
    rng = re.compile(r"Range:\s*(-?[\d.]+?)\s*-\s*(-?[\d.]+?)[.,]?(?=\s|$)")
    broken = []
    for sid, ps in params.items():
        if not sid.startswith("procedure:signal-"):
            continue
        name = sid.removeprefix("procedure:signal-").replace("-", "_")
        fn = RuleRegistry._registry.get(name)
        doc = inspect.getdoc(fn) or "" if fn else ""
        for pname, spec in ps.items():
            line = re.search(
                rf"^\s*{re.escape(pname)}\s*\([^)]*\)\s*:\s*(.+)$", doc, re.M)
            if line and rng.search(line.group(1)) and \
                    (spec.get("min") is None or spec.get("max") is None):
                broken.append(f"{name}.{pname}")
    assert not broken, f"declared ranges dropped by the lift: {broken[:10]}"

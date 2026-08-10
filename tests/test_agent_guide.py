"""Guard: the outputs printed in the agent guide must still be what the graph returns.

`skills/knowledge-graph/GUIDE.md` shows real output under every use case, because a guide that only shows calls
cannot be checked and does not tell a reader what shape to expect. But pasted output is prose, and
prose rots -- the same failure the counts guard exists for.

So each use case is re-executed here and its load-bearing claim asserted. Deliberately NOT a
character-for-character match against the markdown: formatting churn would fail constantly and teach
everyone to ignore it. What is pinned is what a reader would act on -- the counts, the ordering, the
specific values quoted.

If one of these fails, fix the guide (or the graph), not the test.
"""
import re
from pathlib import Path

import pytest

from mangrove_kb.graph import KnowledgeGraph

GUIDE = Path(__file__).resolve().parent.parent / "skills" / "knowledge-graph" / "GUIDE.md"


@pytest.fixture(scope="module")
def kg():
    return KnowledgeGraph.load()


@pytest.fixture(scope="module")
def guide():
    return GUIDE.read_text()


def test_guide_exists_and_covers_ten_use_cases(guide):
    headings = re.findall(r"^## (\d+)\. ", guide, re.M)
    assert headings == [str(i) for i in range(1, 11)], f"expected use cases 1-10, found {headings}"


def test_uc1_orientation_values(kg, guide):
    s = kg.stats()
    assert s["roles"] == ["property:role-filter", "property:role-trigger"]
    assert len(kg.schema()) == 10, "the guide says '10 shapes in total'"
    assert "10 shapes in total" in guide
    for k in s["kinds"]:                      # every kind the guide lists must still exist
        if k.startswith("concept:indicator-class-"):
            assert k in guide, f"guide's kind list is missing {k}"


def test_uc2_divergence_search(kg, guide):
    r = kg.find("divergence", limit=None)
    assert r.total == 37, "the guide says 37 matches"
    assert "37 matches" in guide and "10 of 37" in guide
    top4 = [x["id"] for x in r.items[:4]]
    assert all("divergence" in i for i in top4), "name matches must still lead"
    for i in top4:
        assert i in guide, f"guide quotes results that no longer rank in the top 4: missing {i}"


def test_uc3_rsi_readers(kg, guide):
    r = kg.neighbors("procedure:indicator-rsi", relation="uses", direction="in", limit=None)
    assert r.total == 8 and "8 readers" in guide
    assert {tuple(x.get("inputs", {})) for x in r.items} == {("rsi",)}, \
        "the guide says all eight read the same single output"


def test_uc4_both_axes_counts(kg, guide):
    t = kg.find(kind="momentum", role="trigger", limit=None).total
    f = kg.find(kind="volatility", role="filter", limit=None).total
    assert (t, f) == (25, 16), f"guide says 25 / 16, graph says {t} / {f}"
    assert "momentum triggers   25" in guide and "volatility filters  16" in guide


def test_uc5_rsi_oversold_requirements(kg, guide):
    sig = kg.get("procedure:signal-rsi-oversold")
    assert sig["params"]["window"]["default"] == 14, "the guide reasons from window=14"
    assert sig["warmup_bars"] == "window"
    assert list(sig["inputs"]) == ["close"]
    assert "it needs 14 bars, and 50 is plenty" in guide


def test_uc6_comparability(kg, guide):
    rng = lambda i, o: kg.get(i)["outputs"][o]["range"]
    assert rng("procedure:indicator-rsi", "rsi") == [0, 100]
    assert rng("procedure:indicator-adx", "adx") == [0, 100]
    obv = rng("procedure:indicator-obv", "obv")
    assert obv[0] == float("-inf") and obv[1] == float("inf"), \
        "the guide uses OBV as the unbounded counter-example"


def test_uc7_deprecation(kg, guide):
    assert kg.get("procedure:signal-hanging-man-trigger")["status"] == "deprecated"
    sup = kg.neighbors("procedure:signal-hanging-man-trigger",
                       relation="supersedes", direction="in", limit=None).items
    assert [x["id"] for x in sup] == ["procedure:signal-hammer-trigger"]
    assert sup[0]["why"] == "computes the same thing under the canonical name"
    assert sup[0]["why"] in guide


def test_uc8_derivation_path(kg, guide):
    p = kg.path("procedure:signal-adosc-bearish", "concept:indicator-class-momentum")
    assert p is not None and len(p) == 3, "the guide shows a three-step derivation"
    assert [s["node"]["id"] for s in p] == ["procedure:signal-adosc-bearish",
                                            "procedure:indicator-adosc",
                                            "concept:indicator-class-momentum"]
    assert [s["via"]["relation"] for s in p[1:]] == ["uses", "instance-of"]


def test_uc9_output_index(kg, guide):
    rows = kg.outputs(bounded=True, kind="oscillator", limit=None)
    assert rows.total == 48, f"guide says 48 outputs, graph says {rows.total}"
    assert "48 outputs" in guide
    for name in ("bop", "cmf", "cmo", "mfi", "rsi", "stc"):        # the six the guide prints
        assert any(r["output"] == name for r in rows), f"guide quotes {name}, no longer in the result"

    hist = kg.outputs("histogram", limit=None).items
    assert [r["id"] for r in hist] == ["procedure:indicator-macd"]
    assert hist[0]["description"].startswith("macd minus signal. Crosses zero exactly when macd")
    assert hist[0]["description"][:60] in guide

    assert kg.outputs(units="percent", limit=None).total == 26 and "percent` matches 26" in guide
    # The guide's trap rests on SwingDelta's unit being DEFERRED -- it is whatever the companion
    # indicator carries. If that ever became a concrete unit the trap would be misinformation.
    assert {r["id"] for r in kg.outputs(units="indicator units", limit=None)} == \
           {"procedure:indicator-swingdelta"}


def test_uc10_status_and_requires(kg, guide):
    dep = kg.find(status="deprecated", limit=None)
    assert dep.total == 2 and "deprecated        2" in guide
    for x in dep:
        assert x["id"] in guide

    vol = kg.find(requires="volume", role="trigger", limit=None)
    assert vol.total == 8 and "volume triggers   8" in guide

    assert kg.stats()["input_columns"] == ["close", "high", "indicator", "low", "open",
                                           "price", "volume"]
    assert kg.stats()["statuses"] == ["deprecated", "ratified"]
    assert "close, high, indicator, low, open," in guide and "deprecated, ratified" in guide


def test_every_documented_example_actually_runs():
    """Execute every ```python block in both docs. A doc whose examples raise is worse than none.

    The other tests here re-derive each use case's *claim*. This runs the code as printed, which is
    what catches a snippet that is merely wrong Python -- a `set()` over unhashable result rows, a
    renamed keyword -- rather than wrong about the graph.
    """
    import re
    ns = {"KnowledgeGraph": KnowledgeGraph, "kg": KnowledgeGraph.load()}
    ran = 0
    for doc in (GUIDE, GUIDE.parent / "SKILL.md"):
        for i, block in enumerate(re.findall(r"```python\n(.*?)```", doc.read_text(), re.S), 1):
            try:
                exec(compile(block, f"{doc.name}#{i}", "exec"), ns)
            except Exception as e:                       # noqa: BLE001 -- report which block
                raise AssertionError(f"{doc.name} block {i} raised {type(e).__name__}: {e}\n{block}")
            ran += 1
    assert ran >= 20, f"expected the docs to carry runnable examples, found {ran}"

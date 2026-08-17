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


def test_guide_exists_and_covers_every_use_case(guide):
    headings = re.findall(r"^## (\d+)\. ", guide, re.M)
    assert headings == [str(i) for i in range(1, 16)], f"expected use cases 1-15, found {headings}"


def test_the_knowledge_layer_has_worked_cases_of_its_own(kg, guide):
    """The guide covered signals, indicators and strategies only, while half the graph is now the
    knowledge base. An agent reading it would not learn that the market layer exists."""
    assert "## 14." in guide and "## 15." in guide

    # Every value the two new cases quote, checked against the graph rather than trusted.
    liq = kg.get("concept:liquidity")
    assert liq["summary"][:60] in guide
    # Incoming `about` carries two different claims and the guide teaches the difference, so the
    # two readings are checked separately -- a measurement is not a concept stated of the subject.
    quantifiers = {e["id"] for e in kg.neighbors("concept:liquidity", why="quantifies",
                                                 direction="in", limit=None)}
    stated = {e["id"] for e in kg.neighbors("concept:liquidity", why="principle",
                                            direction="in", limit=None)}
    assert quantifiers and stated, "the case's output is stale"
    assert not (quantifiers & stated), "the guide's distinction has stopped being a distinction"
    for q in quantifiers:
        assert q in guide, f"{q} quantifies liquidity and the guide does not show it"
    # The guide shows a representative few of the stated concepts rather than all of them, so it
    # must not claim a count -- but every id it DOES show must still be real.
    shown = {i for i in stated if i in guide}
    assert shown, "the guide shows none of the concepts stated of liquidity"

    scope = kg.find(under="market foundations", limit=None)
    assert f"{scope.total} nodes" in guide, f"the guide's subject size is stale ({scope.total})"

    # The reasoning is reached from the concept now, not read out of the lists -- so the guide is
    # checked against the EDGES, which is where a wired statement lives.
    reached = {e["id"]: e["why"] for e in
               kg.neighbors("concept:market-impact", relation="about", direction="out", limit=None)}
    assert reached, "market impact should carry the statements that concern it"
    # The guide wraps at 100 columns, so compare against text with its line breaks collapsed --
    # otherwise a quote is "missing" purely because it spans two lines.
    flat = " ".join(guide.split())
    for why in reached.values():
        first = why.split(" · ")[0].split(":")[0]
        assert " ".join(first.split()) in flat, f"the guide does not quote {first[:50]!r}"

    assert "chapter_variants" in guide and kg.get("procedure:indicator-atr")["chapter_variants"]


def test_uc1_orientation_values(kg, guide):
    s = kg.stats()
    assert s["roles"] == ["property:role-filter", "property:role-trigger"]
    assert len(kg.schema()) == 42, "the guide says '42 shapes in total'"
    assert "42 shapes in total" in guide
    for c in s["classes"]:                    # every class the guide lists must still exist
        assert c in guide, f"guide's class list is missing {c}"


def test_uc2_divergence_search(kg, guide):
    r = kg.find("divergence", limit=None)
    assert r.total == 38, "the guide says 38 matches"
    assert "38 matches" in guide and "10 of 38" in guide
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
    """The guide answers this with `uses` first, then `all_paths`, and only warns about `path`.

    The lead answer must not depend on shortest-path behaviour at all -- that dependency is what
    broke this use case when the `about` edge was added, turning a three-step explanation into a
    one-hop assertion with no warning.
    """
    used = kg.neighbors("adosc_bearish", relation="uses", direction="out", limit=None)
    assert [n["id"] for n in used.items] == ["procedure:indicator-adosc"], \
        "the guide's lead answer is one `uses` hop"
    assert "concept:momentum" in {e.dst for e in kg.edges
                                  if e.src == "procedure:indicator-adosc"
                                  and e.relation == "instance-of"}

    both = kg.all_paths("adosc_bearish", "momentum")
    assert both.total == 2 and both.truncated is False, "the guide prints 2 paths"
    assert [[s["via"]["relation"] for s in p[1:]] for p in both.items] == \
        [["about"], ["uses", "instance-of"]], "the guide prints the claim then the reason"

    claim = kg.path("procedure:signal-adosc-bearish", "concept:momentum")
    assert claim is not None and len(claim) == 2, "the guide shows a one-hop `about` claim"
    assert claim[-1]["via"]["relation"] == "about"

    why = kg.path("procedure:signal-adosc-bearish", "concept:momentum",
                  relations=["uses", "instance-of"])
    assert why is not None and len(why) == 3, "the guide shows a three-step derivation"
    assert [s["node"]["id"] for s in why] == ["procedure:signal-adosc-bearish",
                                              "procedure:indicator-adosc",
                                              "concept:momentum"]
    assert [s["via"]["relation"] for s in why[1:]] == ["uses", "instance-of"]


def test_uc9_output_index(kg, guide):
    rows = kg.outputs(bounded=True, kind="oscillator", limit=None)
    assert rows.total == 48, f"guide says 48 outputs, graph says {rows.total}"
    assert "rows.total                       # 48" in guide

    # The point of the case: bounded does NOT mean same-scale. If these ever collapsed to one
    # range the guide's warning would be misinformation.
    spread = {tuple(r["range"]) for r in rows}
    assert len(spread) > 1, f"bounded oscillators now share one range ({spread}); the trap is gone"

    panel = [r for r in rows if r["range"] == [0, 100]]
    assert len(panel) == 6, f"guide says 6 of 48 are on [0, 100], graph says {len(panel)}"
    assert "6 of 48 are actually on [0, 100]" in guide
    for name in ("mfi", "rsi", "stc", "stoch_d", "stoch_k", "ultimate_oscillator"):
        assert any(r["output"] == name for r in panel), f"guide quotes {name}, no longer on [0, 100]"

    hist = kg.outputs("histogram", limit=None).items
    assert [r["id"] for r in hist] == ["procedure:indicator-macd"]
    assert hist[0]["description"].startswith("macd minus signal. Crosses zero exactly when macd")
    assert hist[0]["description"][:60] in guide

    assert kg.outputs(units="percent", limit=None).total == 28 and "percent` matches 28" in guide
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

    # The implemented indicators' columns are the ones a caller reaches for, and they must stay
    # enumerable. The list is no longer closed at seven -- every chapter formula declares its own
    # terms (`bid`, `ask`, `adv`) -- so this asserts the OHLCV core is intact rather than pinning a
    # literal that grows with each chapter and says nothing when it changes.
    cols = kg.stats()["input_columns"]
    assert {"close", "high", "low", "open", "volume"} <= set(cols)
    assert cols == sorted(cols), "the column vocabulary must be ordered to be readable"
    assert kg.stats()["statuses"] == ["deprecated", "draft", "ratified"]
    assert "close, high, low, open, volume" in guide and "draft, deprecated, ratified" in guide


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


def test_uc11_resolve_and_recover(kg, guide):
    from mangrove_kb.graph import NodeNotFound

    assert kg.resolve("rsi_oversold") == "procedure:signal-rsi-oversold"
    assert kg.resolve("RSI") == "procedure:indicator-rsi"
    assert kg.resolve("bollingerbands") == "procedure:indicator-bollingerbands"

    with pytest.raises(NodeNotFound) as e:
        kg.resolve("rsi_over")
    assert set(e.value.suggestions) >= {"procedure:signal-rsi-overbought",
                                        "procedure:signal-rsi-oversold"}
    for s in e.value.suggestions[:2]:
        assert s in guide, f"guide quotes suggestions that no longer come back: {s}"

    with pytest.raises(NodeNotFound):
        kg.resolve("rsi oversold")          # a phrase matches nothing; the guide says so

    # The guide warns the first hit is not necessarily the intended one.
    assert kg.find("oversold").items[0]["id"] == "procedure:signal-cci-oversold"


def test_uc12_graph_to_evaluation(kg, guide):
    """The join the whole loop rests on: a node's `name` IS the registered signal name."""
    from mangrove_kb import RuleRegistry, sample_ohlcv
    import mangrove_kb.signals.momentum, mangrove_kb.signals.volatility  # noqa: F401

    t = kg.get(kg.find(kind="momentum", role="trigger", limit=None).items[0]["id"])
    f = kg.get(kg.find(kind="volatility", role="filter", limit=None).items[0]["id"])
    assert (t["name"], f["name"]) == ("adosc_cross_down", "atr_high_volatility")
    assert t["name"] in guide and f["name"] in guide
    assert sorted(set(t["inputs"]) | set(f["inputs"])) == ["close", "high", "low", "volume"]
    assert (t["warmup_bars"], f["warmup_bars"]) == ("slow + 1", "window - 1")

    shared = ({n["id"] for n in kg.neighbors(t["id"], relation="uses", direction="out")}
              & {n["id"] for n in kg.neighbors(f["id"], relation="uses", direction="out")})
    assert not shared, "the guide says these two are independent"

    df = sample_ohlcv()
    assert RuleRegistry.evaluate({"name": t["name"], "params": {"fast": 3, "slow": 10}}, df) is True
    assert RuleRegistry.evaluate({"name": f["name"],
                                  "params": {"window": 14, "threshold_pct": 3.0}}, df) is True

    sg = kg.subgraph(t["id"], radius=1)
    assert (len(sg["nodes"]), len(sg["edges"])) == (5, 5), "the guide prints 5 nodes, 5 edges"


def test_uc13_usage_example_runs_as_printed(kg, guide):
    """`usage_example` is advertised as copy-pasteable, so it has to be."""
    from mangrove_kb import sample_ohlcv
    import mangrove_kb.indicators as indicators

    df = sample_ohlcv()
    for node_id in ("procedure:indicator-rsi", "procedure:indicator-adx"):
        example = kg.get(node_id)["usage_example"]
        assert example in guide, f"the guide quotes a usage_example that changed: {example}"
        # `value` is a placeholder -- substitute the declared default, then run it verbatim.
        default = kg.get(node_id)["params"]["window"]["default"]
        runnable = example.replace("'window': value", f"'window': {default}")
        out = eval(runnable, {"df": df, **vars(indicators)})           # noqa: S307
        assert out, f"{node_id} usage_example produced nothing"


def test_no_use_case_hardcodes_an_id_the_task_handed_over_as_a_name(kg, guide):
    """A task that says `rsi_oversold` must not silently become `procedure:signal-rsi-oversold`.

    The translation is not guessable -- underscores become hyphens and a `procedure:signal-` prefix
    appears -- so hardcoding it teaches a reader to invent ids. `get()` and `path()` resolve names,
    which is both shorter and the thing use case 11 exists to teach.
    """
    sections = re.split(r"^## ", guide, flags=re.M)
    for name in ("rsi_oversold", "hanging_man_trigger", "adosc_bearish"):
        node_id = kg.resolve(name)
        assert kg.get(name)["id"] == node_id, "get() must accept the bare name"

        # EVERY section that names it, not the first one found. Picking the first let a broken
        # section 5 fall through to section 11 -- which uses the name correctly -- and pass.
        naming = [c for c in sections if f'"{name}"' in c or f"`{name}`" in c]
        assert naming, f"no use case mentions {name}"
        for section in naming:
            title = section.splitlines()[0].strip()
            code = "\n".join(re.findall(r"```python\n(.*?)```", section, re.S))
            assert f'"{node_id}"' not in code, (
                f"'{title}' hardcodes {node_id} instead of resolving {name!r}")

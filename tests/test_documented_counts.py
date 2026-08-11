"""Guard: every count stated as CURRENT FACT must match the graph.

Hand-authored numbers go stale silently. The skill said "70 indicators" one commit after a 71st was
added; three files still said "136 signals" after the count reached 216; the library docstring said
"209 of 216 signals resolve" after a fix made it 216 of 216. Nothing failed, because prose is not
executed.

So this executes it. Each entry below pins a sentence in a document to a value derived from the
committed graph. Change the graph without updating the prose and CI says which file and which line.

**Historical statements are deliberately excluded**, and that distinction is the whole reason this is
a table rather than a repo-wide regex:

* ``CHANGELOG.md`` entries under a *released* version were true when written. Rewriting them would
  falsify the record. Only the ``[Unreleased]`` section describes the present.
* ``docs/research/*`` states "graph at time of survey" for the same reason.

A generator was considered instead and rejected: these numbers sit inside prose sentences, so
generating them needs either templating markers in every sentence (unreadable in source) or regex
rewriting of prose (which will eventually corrupt a sentence). A guard needs neither and catches the
same drift at the same moment.
"""
import inspect
import re
from collections import Counter
from pathlib import Path

import pytest

from mangrove_kb.graph import KnowledgeGraph

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def counts():
    """Graph counts AND library counts -- the two are different and both get quoted.

    The graph holds what is *modelled* (71 indicators, 218 signals); the library ships more than it
    models (249 registered signals, 80 indicator classes). Documents quote both, and quoting the
    wrong denominator is how README came to claim 247/70 and PKG_README 223/99 while SKILL.md --
    the only one previously guarded -- was right.
    """
    import importlib

    from mangrove_kb import indicators
    from mangrove_kb.registry import RuleRegistry

    for module in ("averaging", "flow", "momentum", "oscillator", "pattern", "trend",
                   "volatility", "onchain", "defi_pro"):
        importlib.import_module(f"mangrove_kb.signals.{module}")

    kg = KnowledgeGraph.load()
    registered = RuleRegistry.names()
    types = Counter()
    for name in registered:
        doc = inspect.getdoc(RuleRegistry._registry[name]) or ""
        m = re.search(r"^Type:\s*(.+)$", doc, re.M)
        if m:
            types[m.group(1).strip()] += 1

    return {
        "nodes": len(kg.nodes),
        "edges": len(kg.edges),
        "indicators": sum(1 for n in kg.nodes if n.startswith("procedure:indicator-")),
        "signals": sum(1 for n in kg.nodes if n.startswith("procedure:signal-")),
        "registered_signals": len(registered),
        "indicator_classes": sum(1 for c in vars(indicators).values()
                                 if isinstance(c, type) and hasattr(c, "_outputs")),
        "triggers": types["TRIGGER"],
        "filters": types["FILTER"],
    }


#: (file, regex capturing ONE number, which count it must equal). The regex must be specific enough
#: that it cannot drift onto a different sentence.
CLAIMS = [
    ("README.md",                      r"(\d+) nodes and [\d,]+ edges",     "nodes"),
    ("README.md",                      r"[\d,]+ nodes and (\d+) edges",     "edges"),
    # The shields.io badge states the size too, and is the first thing a reader sees. It was
    # unguarded prose in an <img> URL, which is exactly where a stale number hides longest.
    ("README.md",                      r"graph-(\d+)%20nodes",               "nodes"),
    ("README.md",                      r"nodes%20%C2%B7%20(\d+)%20edges",    "edges"),
    ("CHANGELOG.md",                   r"-- (\d+) nodes, [\d,]+ edges, in", "nodes"),
    ("CHANGELOG.md",                   r"-- [\d,]+ nodes, (\d+) edges, in", "edges"),
    ("skills/knowledge-graph/SKILL.md", r"\*\*(\d+) nodes, [\d,]+ edges\*\*", "nodes"),
    ("skills/knowledge-graph/SKILL.md", r"\*\*[\d,]+ nodes, (\d+) edges\*\*", "edges"),
    ("skills/knowledge-graph/SKILL.md", r"covering (\d+) indicators",        "indicators"),
    ("skills/knowledge-graph/SKILL.md", r"and\s+(\d+) signals",              "signals"),
    ("skills/knowledge-graph/SKILL.md", r"All (\d+) signals carry an",       "signals"),
    ("mangrove_kb/graph.py",           r"\((\d+) of [\d,]+ nodes carry both\)", "signals"),
    ("mangrove_kb/graph.py",           r"\([\d,]+ of (\d+) nodes carry both\)", "nodes"),
    ("mangrove_kb/graph.py",           r"All (\d+) signals resolve this way", "signals"),
    ("skills/knowledge-graph/GUIDE.md", r"nodes, edges  (\d+) [\d,]+",   "nodes"),
    ("skills/knowledge-graph/GUIDE.md", r"nodes, edges  [\d,]+ (\d+)",   "edges"),
    ("skills/knowledge-graph/GUIDE.md", r's\["edges"\]\s+# (\d+), [\d,]+', "nodes"),
    ("skills/knowledge-graph/GUIDE.md", r's\["edges"\]\s+# [\d,]+, (\d+)', "edges"),
    ("skills/knowledge-graph/GUIDE.md", r"only 2 of (\d+) nodes",         "nodes"),
    # The library-wide headline numbers. README claimed 247/70 and PKG_README 223/99 against a
    # real 249/80 -- three documents, three different answers, none of them guarded.
    ("README.md",      r"\*\*(\d+) trading signal functions\*\*",    "registered_signals"),
    ("README.md",      r"functions\*\* \((\d+) TRIGGER",              "triggers"),
    ("README.md",      r"TRIGGER, (\d+) FILTER",                       "filters"),
    ("README.md",      r"\*\*(\d+) technical indicator classes\*\*", "indicator_classes"),
    ("README.md",      r"Of \*\*(\d+) registered signals\*\*",         "registered_signals"),
    ("README.md",      r"\*\*(\d+) are modelled\*\*",                    "signals"),
    ("README.md",      r"(\d+) of the [\d,]+ indicator\s*\n?classes",   "indicators"),
    ("README.md",      r"[\d,]+ of the (\d+) indicator\s*\n?classes",   "indicator_classes"),
    ("PKG_README.md",  r"\*\*(\d+) trading signals\*\*",             "registered_signals"),
    ("PKG_README.md",  r"\*\*(\d+) technical indicators\*\*",        "indicator_classes"),
    # The PyPI front page stated 755 edges after the graph reached 1049, and nothing caught it:
    # the guard covered its signal and indicator counts but not the graph size.
    ("PKG_README.md",  r"-- (\d+) nodes, [\d,]+ edges, queryable",     "nodes"),
    ("PKG_README.md",  r"-- [\d,]+ nodes, (\d+) edges, queryable",     "edges"),
    # CLAUDE.md is what an agent reads before touching this repo, and it had drifted furthest:
    # "102 tests", "233 signal functions", "99 indicator classes", and a curl example still using
    # capitalised OHLCV after lowercase became canonical. Nothing was watching it.
    ("CLAUDE.md",      r"(\d+) signal functions",                     "registered_signals"),
    ("CLAUDE.md",      r"(\d+) indicator classes",                    "indicator_classes"),
    ("CLAUDE.md",      r"(\d+) registered \(",                        "registered_signals"),
    ("CLAUDE.md",      r"registered \((\d+) TRIGGER",                 "triggers"),
    ("CLAUDE.md",      r"TRIGGER, (\d+) FILTER",                      "filters"),
    ("CLAUDE.md",      r"(\d+) are modelled in the graph",            "signals"),
    ("CLAUDE.md",      r"(\d+) nodes\n?and [\d,]+ edges",             "nodes"),
    ("CLAUDE.md",      r"[\d,]+ nodes\n?and (\d+) edges",             "edges"),
]

#: Files whose numbers are historical and MUST NOT be "corrected". Listed so the exclusion is a
#: decision on the record rather than an omission someone later mistakes for an oversight.
HISTORICAL = ("docs/research/graph-query-api-and-mcp-surface.md",)


@pytest.mark.parametrize("relpath,pattern,key", CLAIMS,
                         ids=[f"{p}:{k}:{i}" for i, (p, _, k) in enumerate(CLAIMS)])
def test_documented_count_matches_the_graph(relpath, pattern, key, counts):
    path = REPO / relpath
    assert path.is_file(), f"{relpath} is gone -- remove its entry from CLAIMS"
    text = path.read_text()
    m = re.search(pattern, text)
    assert m, (f"{relpath}: the sentence this guard pins has changed shape.\n"
               f"  pattern: {pattern}\n"
               f"  Update CLAIMS, or the guard silently stops guarding.")
    stated = int(m.group(1).replace(",", ""))
    assert stated == counts[key], (
        f"{relpath} says {stated} {key}, the graph has {counts[key]}.\n"
        f"  Update the prose (or the graph), then rerun. Matched: {m.group(0)!r}")


def test_every_claim_target_exists():
    """A typo'd path would make a claim vacuously pass. Fail on it instead."""
    for relpath, _, _ in CLAIMS:
        assert (REPO / relpath).is_file(), f"CLAIMS points at a missing file: {relpath}"


def test_historical_documents_are_left_alone():
    """These carry point-in-time numbers on purpose; the guard must never be pointed at them."""
    guarded = {c[0] for c in CLAIMS}
    for h in HISTORICAL:
        assert h not in guarded, (
            f"{h} states historical counts and must not be guarded -- "
            "'fixing' it would falsify a dated record")

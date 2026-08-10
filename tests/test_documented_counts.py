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
* ``audit_results/gap_analysis.md`` carries a ``Generated: <date>`` stamp -- it is a dated report.
* ``docs/research/*`` states "graph at time of survey" for the same reason.
* ``SESSION-SUMMARY.md`` is a record of a session, not a description of now.

A generator was considered instead and rejected: these numbers sit inside prose sentences, so
generating them needs either templating markers in every sentence (unreadable in source) or regex
rewriting of prose (which will eventually corrupt a sentence). A guard needs neither and catches the
same drift at the same moment.
"""
import re
from pathlib import Path

import pytest

from mangrove_kb.graph import KnowledgeGraph

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def counts():
    kg = KnowledgeGraph.load()
    return {
        "nodes": len(kg.nodes),
        "edges": len(kg.edges),
        "indicators": sum(1 for n in kg.nodes if n.startswith("procedure:indicator-")),
        "signals": sum(1 for n in kg.nodes if n.startswith("procedure:signal-")),
    }


#: (file, regex capturing ONE number, which count it must equal). The regex must be specific enough
#: that it cannot drift onto a different sentence.
CLAIMS = [
    ("README.md",                      r"-- (\d+) nodes and [\d,]+ edges",  "nodes"),
    ("README.md",                      r"-- [\d,]+ nodes and (\d+) edges",  "edges"),
    ("README.md",                      r"\((\d+) nodes, [\d,]+ edges\)",    "nodes"),
    ("README.md",                      r"\([\d,]+ nodes, (\d+) edges\)",    "edges"),
    ("CHANGELOG.md",                   r"-- (\d+) nodes, [\d,]+ edges, in", "nodes"),
    ("CHANGELOG.md",                   r"-- [\d,]+ nodes, (\d+) edges, in", "edges"),
    ("skills/knowledge-graph/SKILL.md", r"\*\*(\d+) nodes, [\d,]+ edges\*\*", "nodes"),
    ("skills/knowledge-graph/SKILL.md", r"\*\*[\d,]+ nodes, (\d+) edges\*\*", "edges"),
    ("skills/knowledge-graph/SKILL.md", r"covering (\d+) indicators",        "indicators"),
    ("skills/knowledge-graph/SKILL.md", r"and\s+(\d+) signals",              "signals"),
    ("skills/knowledge-graph/SKILL.md", r"All (\d+) signals resolve",        "signals"),
    ("mangrove_kb/graph.py",           r"\((\d+) of [\d,]+ nodes carry both\)", "signals"),
    ("mangrove_kb/graph.py",           r"\([\d,]+ of (\d+) nodes carry both\)", "nodes"),
    ("mangrove_kb/graph.py",           r"All (\d+) signals resolve this way", "signals"),
    ("kb-next-steps.md",               r"(\d+) signals, [\d,]+ indicators",  "signals"),
    ("kb-next-steps.md",               r"[\d,]+ signals, (\d+) indicators",  "indicators"),
    ("skills/knowledge-graph/GUIDE.md", r"nodes, edges  (\d+) [\d,]+",   "nodes"),
    ("skills/knowledge-graph/GUIDE.md", r"nodes, edges  [\d,]+ (\d+)",   "edges"),
    ("skills/knowledge-graph/GUIDE.md", r's\["edges"\]\s+# (\d+), [\d,]+', "nodes"),
    ("skills/knowledge-graph/GUIDE.md", r's\["edges"\]\s+# [\d,]+, (\d+)', "edges"),
    ("skills/knowledge-graph/GUIDE.md", r"only 2 of (\d+) nodes",         "nodes"),
    # STATUS.md states what is true NOW, which is exactly the kind of claim that rots first.
    ("STATUS.md",                      r"graph\s+(\d+) atoms, [\d,]+ relations", "nodes"),
    ("STATUS.md",                      r"graph\s+[\d,]+ atoms, (\d+) relations", "edges"),
]

#: Files whose numbers are historical and MUST NOT be "corrected". Listed so the exclusion is a
#: decision on the record rather than an omission someone later mistakes for an oversight.
HISTORICAL = ("audit_results/gap_analysis.md", "SESSION-SUMMARY.md",
              "docs/research/graph-query-api-and-mcp-surface.md")


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

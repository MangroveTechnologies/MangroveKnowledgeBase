"""An id says what a thing IS. It must never say what a thing BELONGS TO.

Two halves, and only the first is mechanically checkable.

**Says what it is.** Every atom's id prefix is its primitive, lowercased: `procedure:indicator-rsi`
is a Procedure, `concept:momentum` is a Concept. That held for 300 of 303 atoms and silently failed
for three -- `concept:indicator` and `concept:signal` were `Procedure` (the primitive of their
INSTANCES, not of themselves), and `concept:strategy` was a `Schema`. Nothing checked it, so the
disagreement survived every rebuild. This test is that check.

**Never says what it belongs to.** `concept:indicator-class-momentum` asserted, inside an identifier,
that momentum was a class OF INDICATORS -- a claim about a different node, which the graph also made
as an edge, and which was wrong. When the edge was corrected the id still said the old thing. There
is no honest mechanical test for this half: any rule general enough to catch it would fire on
legitimate compound names like `procedure:signal-rsi-oversold`, where `rsi` names a real node and the
segment is just the signal's own name. It is a review rule, stated on `atom()` where ids are minted
and in SKILL.md where consumers read them. The one instance we know of is pinned below so a
regression is loud.
"""
import json
from pathlib import Path

import pytest

GRAPH = Path(__file__).resolve().parent.parent / "ontology" / "signal-indicator-ontology.json"


@pytest.fixture(scope="module")
def atoms():
    return json.loads(GRAPH.read_text())["atoms"]


def test_every_id_prefix_is_its_primitive(atoms):
    wrong = [f"{a['id']}  (kind={a['kind']}, so the prefix must be {a['kind'].lower()}:)"
             for a in atoms if a["id"].split(":")[0] != a["kind"].lower()]
    assert not wrong, ("these ids disagree with their own primitive:\n  " + "\n  ".join(wrong)
                       + "\n  Change one or the other -- an id that lies about its type is worse "
                         "than an opaque one, because it reads as documentation.")


def test_the_character_classes_do_not_name_indicator(atoms):
    """The regression this convention was written for.

    The six classes span indicators (`instance-of`, they measure it) and signals (`about`, they are
    concerned with it). An id claiming otherwise contradicts the edges in the same file.
    """
    ids = {a["id"] for a in atoms}
    offenders = sorted(i for i in ids if "indicator-class" in i)
    assert not offenders, f"class ids must not embed 'indicator': {offenders}"
    assert {"concept:momentum", "concept:oscillator", "concept:averaging",
            "concept:volatility", "concept:flow", "concept:pattern"} <= ids

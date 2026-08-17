"""Every summary written by hand must be the summary the graph ships.

`AUTHORED` is a table keyed by node id, applied only to atoms a chapter CREATES. Nothing checked
that the key still names a node, or that the sentence survived to the record -- so nineteen authored
summaries were deleted by a text edit that removed a range between two keys, and the graph went back
to reading "Left Shoulder: Rally and decline" as the definition of head and shoulders. Every test
passed. The question set caught it, three commits later.

Two failure modes, both silent without this:

* an entry whose key names no node -- a typo, or a node renamed after the prose was written;
* an entry that exists but never reaches the record, because nothing folds onto that node.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
RECORD = REPO / "ontology" / "signal-indicator-ontology.json"


@pytest.fixture(scope="module")
def authored() -> dict:
    sys.path.insert(0, str(REPO / "ontology"))
    from chapter_to_atoms import AUTHORED

    return AUTHORED


@pytest.fixture(scope="module")
def atoms() -> dict:
    return {a["id"]: a for a in json.loads(RECORD.read_text())["atoms"]}


def test_every_authored_entry_names_a_node(authored, atoms):
    missing = sorted(k for k in authored if k not in atoms)
    assert not missing, (
        f"{len(missing)} authored entries name no node -- renamed, or the prose was written "
        f"against an id that never existed: {missing[:8]}")


def test_every_authored_summary_is_the_one_the_graph_ships(authored, atoms):
    """The whole point of writing it. An entry that does not reach the record is dead text."""
    def flat(s: str) -> str:
        return " ".join(s.split())

    unapplied = [k for k, (summary, _) in authored.items()
                 if k in atoms and flat(atoms[k]["summary"]) != flat(summary)]
    # A code-derived node is only reached when a chapter folds onto it, and two of them are
    # deliberately protected: `procedure:indicator-vwap` is settled by hand, and the entry for
    # `procedure:indicator-atr` describes the indicator where the chapter's definition won.
    allowed = {"procedure:indicator-vwap", "procedure:indicator-atr"}
    stranded = sorted(set(unapplied) - allowed)
    assert not stranded, (
        f"{len(stranded)} authored summaries never reached the graph: {stranded[:8]}")


def test_the_chapters_that_needed_prose_still_have_it(authored, atoms):
    """A spot check with teeth: nodes whose parsed summary is a fragment of a list, and which are
    readable only because someone wrote a definition for them."""
    for nid, opening in (("concept:head-and-shoulders", "Three peaks"),
                         ("concept:triangle", "Converging boundaries"),
                         ("procedure:garch-family-model", "Models tomorrow"),
                         ("concept:risk-dimension", "One of the separate ways")):
        assert atoms[nid]["summary"].startswith(opening), \
            f"{nid} is back to its parsed fragment: {atoms[nid]['summary'][:60]!r}"

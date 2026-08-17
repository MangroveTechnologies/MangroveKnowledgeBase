"""Every edge in the record must join two nodes that exist.

A chapter may name a node a LATER chapter creates -- chapter 1 advises "avoid trading patterns that
reveal your strategy" and the node it names is chapter 2's -- so the extractor cannot check the
endpoint at the moment it draws the edge. The check moves here, to the finished record, which is
where the guarantee has to hold anyway.

Without this, a typo in a `wired` or `edges` declaration writes an edge into nothing and the graph
answers a question with a node id that resolves to no node.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

RECORD = Path(__file__).resolve().parent.parent / "ontology" / "signal-indicator-ontology.json"


@pytest.fixture(scope="module")
def record() -> dict:
    return json.loads(RECORD.read_text())


def test_no_edge_points_at_a_missing_node(record):
    ids = {a["id"] for a in record["atoms"]}
    dangling = [(r["from_id"], r["rel"], r["to_id"]) for r in record["relations"]
                if r["from_id"] not in ids or r["to_id"] not in ids]
    assert not dangling, f"{len(dangling)} edges point at a node that does not exist: {dangling[:5]}"


def test_no_node_is_reachable_by_one_edge_without_a_reason(record):
    """A node with a single edge is reachable by walking down from its parent and by no other
    question. The exceptions are stated here rather than tolerated silently."""
    import collections

    allowed = {
        # The chapter names it in one row of a comparison table and says nothing else about it.
        "concept:position-trading",
    }
    degree = collections.Counter()
    for r in record["relations"]:
        degree[r["from_id"]] += 1
        degree[r["to_id"]] += 1
    lonely = {a["id"] for a in record["atoms"] if degree[a["id"]] <= 1} - allowed
    assert not lonely, f"reachable by one edge and unexplained: {sorted(lonely)}"


def test_every_chapter_tag_names_a_chapter_that_was_ingested(record):
    """`reference_chapter` is how a reader asks what a chapter contributed. A tag naming no chapter
    -- `strategy-design-modeling`, the old filename -- puts a node outside every such question."""
    import sys

    sys.path.insert(0, str(RECORD.parent))
    from chapter_to_atoms import CHAPTERS

    known = set(CHAPTERS)
    tagged = {c for a in record["atoms"] for c in (a["props"].get("reference_chapter") or ())}
    assert tagged <= known, f"tags naming no ingested chapter: {sorted(tagged - known)}"

"""The graph must be reproducible from the tree alone.

This is the property the whole backfill exists to establish: delete the JSON, run the builder, get
the committed file back. The old builder could not do that -- ~1,270 of its values came from the
file it was writing, so the artifact was its own input and git was their only backup. Three separate
incidents nearly destroyed them.

The test therefore runs the builder against an EMPTY output path. If anything still reads the
previous graph, the rebuild comes back missing those values and the comparison fails.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
BUILDER = REPO / "ontology" / "build_signal_indicator_ontology.py"
COMMITTED = REPO / "ontology" / "signal-indicator-ontology.json"


@pytest.fixture(scope="module")
def rebuilt(tmp_path_factory):
    """The graph, built from scratch to a path that does not exist."""
    out = tmp_path_factory.mktemp("build") / "rebuilt.json"
    env = {**os.environ, "ONTOLOGY_OUT": str(out)}
    proc = subprocess.run([sys.executable, str(BUILDER)], cwd=REPO, env=env,
                          capture_output=True, text=True, timeout=600)
    assert proc.returncode == 0, f"builder failed:\n{proc.stderr[-3000:]}"
    assert out.is_file(), "builder produced no output"
    return json.loads(out.read_text())


@pytest.fixture(scope="module")
def committed():
    return json.loads(COMMITTED.read_text())


def _code_derived(graph):
    """The committed record is the code build plus the wiki merge. This strips the second half.

    Determinism is a claim about the builder: given the tree, it reproduces what it wrote. The
    doc-derived nodes are not its output and it has never heard of them, so including them here
    would assert the builder produces something it does not. They have their own guard --
    `test_doc_derived_atoms.py` fails if the merge is skipped, which is the failure this test
    would otherwise be mistaken for.
    """
    doc = {a["id"] for a in graph["atoms"] if "source_chapter" in (a.get("props") or {})}
    return ({a["id"]: a for a in graph["atoms"] if a["id"] not in doc},
            [r for r in graph["relations"] if r["from_id"] not in doc and r["to_id"] not in doc])


def test_atoms_are_reproduced_exactly(rebuilt, committed):
    got = {a["id"]: a for a in rebuilt["atoms"]}
    want, _ = _code_derived(committed)
    assert set(got) == set(want), "the node SET changed"
    differing = [i for i in want if got[i] != want[i]]
    assert not differing, (
        f"{len(differing)} atoms differ, e.g. {differing[:3]}\n"
        + "\n".join(f"  {i}: {json.dumps(got[i])[:200]}" for i in differing[:2]))


def test_relations_are_reproduced_exactly(rebuilt, committed):
    _, want = _code_derived(committed)
    assert rebuilt["relations"] == want


def test_nothing_is_carried_forward(rebuilt):
    """The counters that reported borrowing from the previous build are gone, not merely zero."""
    meta = rebuilt["meta"]
    for dead in ("carried_forward_from_previous_build", "kb_doc_sections_matched",
                 "kb_doc_sections_unmatched", "bootstrapped_from_docstring"):
        assert dead not in meta, f"{dead} is still reported -- a borrowed source survives"


def test_only_one_builder_exists():
    """A second builder is how the two drift apart and nobody notices which one ran."""
    builders = sorted(p.name for p in (REPO / "ontology").glob("build*.py"))
    assert builders == ["build_signal_indicator_ontology.py"], builders


def test_only_one_graph_file_exists():
    graphs = sorted(p.name for p in (REPO / "ontology").glob("*.json"))
    assert graphs == ["signal-indicator-ontology.json"], graphs

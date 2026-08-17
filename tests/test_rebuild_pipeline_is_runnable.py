"""The documented rebuild can actually be run by someone who is not me.

Half the graph is derived from markdown by `wiki-to-graph`, and the toolkit is invoked as a
subprocess rather than imported -- so nothing in the test suite would notice if it were missing,
mis-versioned, or reachable only from one machine's checkout. The docstrings in
`ontology/wiki_to_atoms.py` and `ontology/chapter_to_atoms.py` would go on documenting a rebuild
that only worked here.

`--vocab` is the specific capability at stake: it is what makes the wiki carry OUR relation
vocabulary instead of the toolkit's four defaults, and without it every node in the build reports
degree 0 while the edge counts look correct. It is on `main` and not in the published 0.2.0, which
is why the dependency is pinned to a commit in `pyproject.toml`.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
CONFIG = REPO / "ontology" / "wiki-config"

wiki_to_graph = pytest.importorskip(
    "wiki_to_graph",
    reason="wiki-to-graph is a declared dev dependency; install the dev extra")


def test_the_toolkit_supports_our_vocabulary():
    """Without `--vocab` the build silently produces a graph in which every node is an orphan."""
    assert hasattr(wiki_to_graph, "load_vocab"), (
        "the installed wiki-to-graph predates --vocab (0.2.0 does). The pin in pyproject.toml "
        "exists to prevent exactly this; it has been loosened or overridden.")


def test_our_vocabulary_files_load_and_declare_the_relations_we_write():
    """The vocabulary the wiki compiles against must be the one the query library can classify."""
    from mangrove_kb.graph import RELATIONS

    vocab = json.loads((CONFIG / "vocab.json").read_text())
    assert set(vocab["concept_edges"]) == set(RELATIONS), (
        "wiki-config/vocab.json and mangrove_kb.graph.RELATIONS have drifted: the wiki can express "
        "a relation no consumer can categorise, or cannot express one that is in use")

    mapping = json.loads((CONFIG / "map.json").read_text())
    sections = {v for k, v in mapping.items() if not k.startswith("_")}
    assert sections <= set(vocab["concept_edges"]), (
        f"a section maps to a relation outside the vocabulary: {sections - set(vocab['concept_edges'])}")


def test_the_wiki_builds_and_validates_as_documented(tmp_path):
    """The exact command in the adapter's docstring, run end to end."""
    out = tmp_path / "wiki-graph.json"
    common = ["--map", str(CONFIG / "map.json"), "--vocab", str(CONFIG / "vocab.json"),
              "--dag-edges", "part-of,kind-of,instance-of,supersedes"]
    build = subprocess.run(
        [sys.executable, "-m", "wiki_to_graph", "build", str(REPO / "ontology" / "wiki"),
         "-o", str(out), *common],
        capture_output=True, text=True, timeout=120)
    assert build.returncode == 0, build.stderr[-2000:]
    assert out.is_file()

    graph = json.loads(out.read_text())
    assert graph["nodes"], "the wiki compiled to an empty graph"
    # Degree is what `--vocab` actually fixes, and orphans are how its absence shows up.
    assert not graph["meta"]["warnings"]["orphans"], graph["meta"]["warnings"]["orphans"]
    assert not graph["meta"]["warnings"]["dangling"], graph["meta"]["warnings"]["dangling"]

    validate = subprocess.run(
        [sys.executable, "-m", "wiki_to_graph", "validate", str(out), *common[2:]],
        capture_output=True, text=True, timeout=120)
    assert validate.returncode == 0, validate.stdout + validate.stderr

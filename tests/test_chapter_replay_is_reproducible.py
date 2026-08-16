"""The whole record must be reproducible from the tree, not just the code-derived half.

`test_build_is_deterministic.py` rebuilds `build_signal_indicator_ontology.py` and stops there. Four
of the five stages that produce the shipped graph -- the wiki adapter and one invocation per
ingested chapter -- were covered by nothing, so "delete the JSON and run the pipeline" was a claim
resting on whoever last ran it by hand. Every extractor change in the chapter work was checked that
way, which is exactly the kind of guarantee that survives until the day someone forgets.

The chain, each stage taking the previous output as its `--ontology`:

    build_signal_indicator_ontology.py  ->  the code-derived nodes
    wiki_to_graph + wiki_to_atoms       ->  the authored subject-area anchors
    chapter_to_atoms.py x N             ->  one merge per chapter in `ontology/raw/`

`wiki-to-graph` is a dev dependency pinned to a commit, so the replay skips where it is absent
rather than failing an install that never claimed to have it.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
ONTOLOGY = REPO / "ontology"
COMMITTED = ONTOLOGY / "signal-indicator-ontology.json"
RAW = ONTOLOGY / "raw"

#: Chapter file -> (chapter id, the subject-area anchor it hangs off). The anchor is authored in
#: `ontology/wiki/` and must exist before the chapter merges; a chapter with no anchor page is the
#: one setup step the procedure used to leave unsaid.
CHAPTERS = {
    "01-market-foundations.md": ("market-foundations", "concept:market-foundations"),
    "02-instruments-market-mechanics.md": ("instruments-market-mechanics",
                                           "concept:market-mechanics"),
    "03-core-trading-concepts.md": ("core-trading-concepts", "concept:price-action"),
    "04-strategy-design.md": ("strategy-design", "concept:strategy-design"),
}


def run(args: list[str], **kw) -> None:
    proc = subprocess.run([sys.executable, *args], cwd=REPO, capture_output=True, text=True,
                          timeout=900, **kw)
    assert proc.returncode == 0, f"{args[0]} failed:\n{proc.stdout[-2000:]}\n{proc.stderr[-3000:]}"


def test_every_ingested_chapter_has_a_raw_copy_and_a_declaration():
    """A chapter merged from a file nobody kept cannot be replayed at all."""
    sys.path.insert(0, str(ONTOLOGY))
    from chapter_to_atoms import CHAPTERS as DECLARED

    for name, (chapter_id, _) in CHAPTERS.items():
        assert (RAW / name).is_file(), f"{name} is not in ontology/raw/"
        assert chapter_id in DECLARED, f"{chapter_id} has no entry in CHAPTERS"


def test_every_chapter_anchor_exists_in_the_committed_graph():
    """The `--parent` of each chapter, which `ontology/wiki/` has to supply before it merges."""
    atoms = {a["id"] for a in json.loads(COMMITTED.read_text())["atoms"]}
    for name, (_, parent) in CHAPTERS.items():
        assert parent in atoms, f"{name} hangs off {parent}, which no wiki page authors"


@pytest.mark.skipif(__import__("importlib").util.find_spec("wiki_to_graph") is None,
                    reason="wiki-to-graph is a pinned dev dependency; install it to replay")
def test_the_pipeline_reproduces_the_committed_record(tmp_path):
    env = {**os.environ, "ONTOLOGY_OUT": str(tmp_path / "code.json"),
           "PYTHONPATH": str(REPO)}
    subprocess.run([sys.executable, str(ONTOLOGY / "build_signal_indicator_ontology.py")],
                   cwd=REPO, env=env, capture_output=True, text=True, timeout=900, check=True)

    wiki = tmp_path / "wiki.json"
    run(["-m", "wiki_to_graph", "build", str(ONTOLOGY / "wiki"), "-o", str(wiki),
         "--map", str(ONTOLOGY / "wiki-config" / "map.json"),
         "--vocab", str(ONTOLOGY / "wiki-config" / "vocab.json"),
         "--dag-edges", "part-of,kind-of,instance-of,supersedes"])
    current = tmp_path / "r1.json"
    run([str(ONTOLOGY / "wiki_to_atoms.py"), "--wiki", str(ONTOLOGY / "wiki"),
         "--graph", str(wiki), "--ontology", str(tmp_path / "code.json"), "--out", str(current)])

    for i, (name, (chapter_id, parent)) in enumerate(sorted(CHAPTERS.items()), 1):
        out = tmp_path / f"ch{i}.json"
        run([str(ONTOLOGY / "chapter_to_atoms.py"), str(RAW / name),
             "--chapter-id", chapter_id, "--parent", parent,
             "--ontology", str(current), "--merge", "--out", str(out)])
        current = out

    rebuilt = json.loads(current.read_text())
    committed = json.loads(COMMITTED.read_text())

    old = {a["id"]: a for a in committed["atoms"]}
    new = {a["id"]: a for a in rebuilt["atoms"]}
    assert set(old) == set(new), (f"replay lost {sorted(set(old) - set(new))[:8]} / "
                                  f"invented {sorted(set(new) - set(old))[:8]}")
    differing = [i for i in old if old[i] != new[i]]
    assert not differing, f"{len(differing)} atoms differ from the record, e.g. {differing[:5]}"

    def triples(rec):
        return {(r["from_id"], r["rel"], r["to_id"], r["why"]) for r in rec["relations"]}

    assert triples(committed) == triples(rebuilt), (
        f"edges differ: {len(triples(committed) - triples(rebuilt))} missing, "
        f"{len(triples(rebuilt) - triples(committed))} extra")

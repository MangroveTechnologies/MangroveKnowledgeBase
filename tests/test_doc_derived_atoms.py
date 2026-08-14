"""The doc-derived half of the graph survives in the committed ontology.

`build_signal_indicator_ontology.py` writes the record from the library's source and knows nothing
about the wiki, so running it alone and committing silently drops every doc-derived node. Nothing
else would notice: the code-derived atoms would all still be there and the suite would be green.
These tests are what notices.

The pipeline is two stages, in this order:

    python3 ontology/build_signal_indicator_ontology.py
    python3 -m wiki_to_graph build ontology/wiki -o build/wiki-graph.json \\
            --map ontology/wiki-config/map.json --vocab ontology/wiki-config/vocab.json
    python3 ontology/wiki_to_atoms.py --wiki ontology/wiki --graph build/wiki-graph.json \\
            --ontology ontology/signal-indicator-ontology.json --out build/record.json
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from mangrove_kb.graph import RELATIONS, KnowledgeGraph

REPO = Path(__file__).resolve().parent.parent
WIKI = REPO / "ontology" / "wiki"


@pytest.fixture(scope="module")
def kg() -> KnowledgeGraph:
    return KnowledgeGraph.load()


def wiki_pages() -> dict[str, dict]:
    """Every page, by the id the adapter derives for it: ``{kind}:{slug(title)}``."""
    out = {}
    for path in sorted(WIKI.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        kind = (m.group(1) if (m := re.search(r"^kind:\s*(\w+)", text, re.M)) else "concept").lower()
        title = re.search(r"^# (.+)$", text, re.M).group(1).strip()
        chapter = m.group(1) if (m := re.search(r"^chapter:\s*(\S+)", text, re.M)) else None
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        out[f"{kind}:{slug}"] = {"file": path.name, "chapter": chapter, "title": title}
    return out


def test_every_authored_page_reached_the_graph(kg):
    """A page that builds but never lands is the failure this whole path exists to prevent."""
    missing = [f"{nid} ({p['file']})" for nid, p in wiki_pages().items() if nid not in kg.nodes]
    assert not missing, (
        "the committed ontology is missing doc-derived nodes -- the code builder was almost "
        f"certainly run without the wiki merge that follows it: {missing}")


def test_doc_nodes_record_the_chapter_they_came_from(kg):
    """Provenance is the whole claim to trustworthiness for a node nobody can re-derive from code."""
    for nid, page in wiki_pages().items():
        if page["chapter"] is None:          # anchors carry no chapter; they are code-derived
            continue
        node = kg.get(nid)
        assert page["chapter"] in (node.get("reference_chapter") or []), \
            f"{nid} should record chapter {page['chapter']}, got {node.get('reference_chapter')!r}"


def test_doc_nodes_are_searchable_by_their_body(kg):
    """`explanation` is in SEARCH_TIERS, so a term named only in the page body is findable.

    Before it was carried, `find("head and shoulders")` returned nothing while the chart-pattern
    page named the formation in its first line -- a search that answers "do we have anything for
    X?" with a false no is worse than no search.
    """
    hits = [r["id"] for r in kg.find("head and shoulders", limit=5).items]
    assert "concept:chart-pattern" in hits, hits


def test_doc_edges_use_only_relations_the_library_can_classify(kg):
    """The wiki can express any section name; only these seven mean anything to a consumer."""
    doc_ids = set(wiki_pages())
    for edge in kg.edges:
        if edge.src in doc_ids or edge.dst in doc_ids:
            assert edge.relation in RELATIONS, f"{edge.src} --{edge.relation}--> {edge.dst}"


def test_every_doc_edge_records_why_it_holds(kg):
    """Our relations carry a rationale; the adapter refuses an edge without one, so none exist."""
    doc_ids = set(wiki_pages())
    bare = [f"{e.src} --{e.relation}--> {e.dst}" for e in kg.edges
            if (e.src in doc_ids or e.dst in doc_ids) and not e.why.strip()]
    assert not bare, bare


def test_the_record_is_the_merged_graph_not_the_code_build_alone():
    """The committed file must be the second stage's output -- meta says how many doc atoms it holds."""
    record = json.loads((REPO / "ontology" / "signal-indicator-ontology.json").read_text())
    authored = sum(1 for p in wiki_pages().values() if p["chapter"])
    assert record["meta"].get("doc_atoms") == authored, (
        "meta.doc_atoms is missing or stale -- the record was written by the code builder without "
        f"the wiki merge (expected {authored})")


def test_a_wired_statement_lives_on_the_edge_and_not_in_the_list(kg):
    """A principle or practice MOVES when it earns an edge; it is never in both places.

    The list is the backlog: what remains in it is exactly what has not been connected yet, so an
    empty list means the chapter is fully wired. A line left behind after its edge was drawn would
    make that number meaningless and give the same sentence two copies to drift apart.
    """
    lists = {"fact:market-foundations-core-principles": "principles",
             "judgment:market-foundations-best-practices": "practices"}
    for nid, field in lists.items():
        held = kg.get(nid)[field]
        for edge in kg.neighbors(nid, relation="about", direction="in", limit=None):
            reason = edge["why"].strip()
            assert reason, f"{nid} -> {edge['id']} carries no statement"
            assert not any(reason in line for line in held), (
                f"{nid}: the statement wired to {edge['id']} is still in `{field}` -- it must move, "
                "not be copied")


def test_a_wired_concept_is_reachable_from_its_statement(kg):
    """The point of moving it: the concept stops being a leaf and the advice is one hop away."""
    out = kg.neighbors("concept:iceberg-order", direction="out", relation="about", limit=None)
    kinds = {e["id"].split(":", 1)[0] for e in out}
    assert {"fact", "judgment"} <= kinds, (
        "a concept points AT the principles and practices that govern it, so both should be "
        f"outgoing from iceberg-order; got {kinds}")
    assert all(e["why"].strip() for e in out), "every wired edge carries the statement it moved"


def test_the_graph_carries_no_document_numbering(kg):
    """A chapter or section number says where a thing sits in a file, not what it is.

    `01-market-foundations`, `§1.1` and a `1.4 ` prefix on every practice are all artifacts of the
    document. They also broke things: keying the taxonomy declarations on section numbers made every
    one of them silently inert on any other chapter.
    """
    import re
    numbered = re.compile(r"^\d+[-.]|\s§?\d+\.\d+\b")
    for nid in kg.nodes:
        node = kg.get(nid)
        for chapter in node.get("reference_chapter") or []:
            assert not numbered.match(chapter), f"{nid}: reference_chapter {chapter!r} is numbered"
        for field in ("principles", "practices"):
            for line in node.get(field) or []:
                assert not numbered.match(line), f"{nid}.{field}: {line[:60]!r} is numbered"
    for edge in kg.edges:
        assert not numbered.search(edge.why), f"{edge.src} -> {edge.dst}: why is numbered ({edge.why!r})"


def test_a_chapter_with_no_declarations_refuses_to_build():
    """Building one without them emitted a graph with no taxonomy and said nothing about it."""
    import subprocess
    import sys
    from pathlib import Path

    repo = Path(__file__).resolve().parent.parent
    src = repo / "knowledge-base" / "03-core-trading-concepts.md"
    if not src.is_file():
        import pytest
        pytest.skip("chapter 02 source not in this checkout")
    r = subprocess.run(
        [sys.executable, str(repo / "ontology" / "chapter_to_atoms.py"), str(src),
         "--chapter-id", "core-trading-concepts", "--parent", "concept:price-action",
         "--ontology", str(repo / "ontology" / "signal-indicator-ontology.json"), "--table"],
        capture_output=True, text=True, timeout=120)
    assert r.returncode != 0, "an undeclared chapter built anyway"
    assert "no declarations for chapter" in r.stderr + r.stdout


def test_a_section_with_several_subjects_attaches_each_thing_to_its_own(kg):
    """§1.4 defines liquidity, slippage and market impact. Everything used to attach to the first.

    `simple slippage` was declared to be about LIQUIDITY and `low volatility regime` was made a kind
    of VOLATILITY rather than of market regime -- a taxonomy error, not just an imprecise edge.
    """
    expected = {
        "property:simple-slippage": "concept:slippage",
        "procedure:almgren-chriss-market-impact-model": "concept:market-impact",
        "fact:square-root-market-impact-rule": "concept:market-impact",
        "concept:low-volatility-regime": "concept:market-regime",
        "concept:high-volatility-regime": "concept:market-regime",
    }
    for nid, want in expected.items():
        got = {e["id"] for e in kg.neighbors(nid, direction="out", limit=None)
               if e["relation"] in ("about", "kind-of")}
        assert want in got, f"{nid} should attach to {want}, got {got or 'nothing'}"


def test_a_near_duplicate_across_the_two_halves_is_related_not_left_adjacent(kg):
    """The chapter's VWAP is an execution schedule; the library's is the price series it targets.

    Same name, different things, so neither folds into the other -- but sitting side by side
    unconnected is what makes a graph look like it has duplicates.
    """
    linked = {e["id"] for e in kg.neighbors("procedure:vwap", direction="out", limit=None)}
    assert "procedure:indicator-vwap" in linked, \
        "the execution algorithm and the indicator of the same name must be joined"


def test_a_stated_formula_is_not_automatically_a_procedure(kg):
    """What a formula DEFINES decides the primitive, not the section it sits in.

    Reading every `### Mathematical Rules/Formulas` entry as a Procedure gave chapter 2 thirty-two
    of them and the whole graph three Properties -- because that path could not emit one. A formula
    can define a quantity (Property), state an identity (Fact), name a family (Concept), or specify
    a method (Procedure), and only the last is something you run.
    """
    expect = {
        "property:quoted-spread": "Property",        # a number a book has
        "property:basis": "Property",                # futures minus spot
        "property:margin-ratio": "Property",
        "fact:put-call-parity": "Fact",              # holds, or there is an arbitrage
        "fact:cost-of-carry-relationship": "Fact",
        "procedure:black-scholes-call-price": "Procedure",   # a model you run
        "procedure:garch-model": "Procedure",
        "concept:greeks": "Concept",                 # five sensitivities, not one calculation
    }
    for nid, primitive in expect.items():
        if nid not in kg.nodes:
            continue                                  # its chapter is not merged yet
        assert kg.get(nid)["primitive"] == primitive, \
            f"{nid} should be {primitive}, is {kg.get(nid)['primitive']}"


def test_the_graph_actually_holds_quantities(kg):
    """The count is the tell: three Properties in the whole graph meant the parser could not make
    one, not that the knowledge base states no quantities."""
    quantities = [i for i in kg.nodes if i.startswith("property:") and "role" not in i]
    assert len(quantities) >= 10, f"only {len(quantities)} quantities; the default has regressed"

#!/usr/bin/env python3
"""Merge the doc-derived wiki into the signal/indicator ontology.

The graph has two sources and one output. Chapter 06 (indicators) and chapter 10 (signals) are
derived from the library's own source by ``build_signal_indicator_ontology.py`` -- exact, not
extracted. The remaining chapters have no code to derive from, so their source of truth is an
LLM-wiki (one concept per page, typed ``##`` sections, ``[[links]]``) compiled by ``wiki-to-graph``.

This adapter is the join. It never writes an atom whose id already exists: the code-derived half is
authoritative and a wiki page for such a node is an *anchor*, present only so links resolve.

Three things it adds that ``wiki-to-graph`` does not carry into our shape:

* **``why`` on every edge.** Our relations record a rationale ("layer of the domain"); the wiki
  format stores ``{target, type, via, weight}`` with no such field. The convention is the text after
  ``--`` on the link's own line, and it is *required* -- an edge without one fails the build rather
  than entering the graph unexplained.
* **``reference_chapter``.** Which knowledge-base chapter a node was authored from, taken from the
  page's ``chapter:`` frontmatter. A property rather than an edge, so the subject axis stays clean
  and provenance does not double the edge count.
* **``explanation``.** The page body, which is the node's actual content -- ``graph.SEARCH_TIERS``
  reads it in the same tier as a computation's formula and outputs.

Ids are ``{kind}:{slug(title)}`` -- the page's ``kind:`` frontmatter supplies the prefix. The
code-derived half namespaces its procedures as ``procedure:indicator-*`` / ``procedure:signal-*``,
so the two id spaces cannot collide by construction; the merge asserts it anyway.

Usage::

    python3 ontology/wiki_to_atoms.py \\
        --wiki ontology/wiki --graph build/wiki-graph.json \\
        --ontology ontology/signal-indicator-ontology.json --out build/merged.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

#: Relations this path may write. Mirrors ``wiki-config/vocab.json``; kept here so the adapter fails on a
#: vocabulary drift instead of importing a relation the query library cannot categorise.
ALLOWED = {"instance-of", "kind-of", "part-of", "has-role", "about", "uses", "supersedes"}

#: Primitive names as the ontology spells them (the wiki writes them lowercase in frontmatter).
PRIMITIVE = {"object": "Object", "property": "Property", "concept": "Concept", "fact": "Fact",
             "experience": "Experience", "procedure": "Procedure", "schema": "Schema",
             "context": "Context", "judgment": "Judgment", "atom": "Atom"}

LINK = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
H1 = re.compile(r"^# (.+)$")
H2 = re.compile(r"^## (.+)$")


class MergeError(RuntimeError):
    """A defect in the wiki that must be fixed at the source rather than merged around."""


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-") or "untitled"


def read_pages(wiki_dir: Path) -> dict[str, dict]:
    """Parse each page for its frontmatter and, per typed section, each link's rationale.

    Returns ``{slug: {"title", "kind", "chapter", "why": {(section, target): why}}}``. Only the
    fields ``wiki-to-graph`` does not already give us are collected here -- the graph structure
    comes from its build output, so there is exactly one parser of record for the topology.
    """
    pages: dict[str, dict] = {}
    for path in sorted(wiki_dir.glob("*.md")):
        lines = path.read_text(encoding="utf-8").split("\n")
        meta, i = {}, 0
        if lines and lines[0].strip() == "---":
            j = 1
            while j < len(lines) and lines[j].strip() != "---":
                if m := re.match(r"\s*(\w+)\s*:\s*(.+?)\s*$", lines[j]):
                    meta[m.group(1).lower()] = m.group(2)
                j += 1
            i = j + 1

        title, section, why = None, None, {}
        for raw in lines[i:]:
            if (m := H1.match(raw)) and title is None:
                title = m.group(1).strip()
            elif m := H2.match(raw):
                section = m.group(1).strip().lower()
            elif section:
                for target, _alias in LINK.findall(raw):
                    tail = raw.split("]]", 1)[1] if "]]" in raw else ""
                    reason = tail.split("--", 1)[1].strip() if "--" in tail else ""
                    why[(section, target.strip().lower())] = reason

        title = title or path.stem
        kind = (meta.get("kind") or "concept").lower()
        if kind not in PRIMITIVE:
            raise MergeError(f"{path.name}: kind {kind!r} is not one of the nine primitives")
        pages[slug(title)] = {"title": title, "kind": kind,
                              "chapter": meta.get("chapter"), "why": why, "file": path.name}
    return pages


def merge(wiki_dir: Path, graph_path: Path, onto_path: Path) -> tuple[dict, dict]:
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    onto = json.loads(onto_path.read_text(encoding="utf-8"))
    pages = read_pages(wiki_dir)

    existing = {a["id"]: a for a in onto["atoms"]}
    ident = {n["id"]: f'{n.get("kind") or "concept"}:{n["id"]}' for n in graph["nodes"]}

    for node_id in ident:
        if node_id not in pages:
            raise MergeError(f"graph node {node_id!r} has no page -- wiki and build are out of step")

    new_atoms, anchors = [], []
    for node in graph["nodes"]:
        oid, page = ident[node["id"]], pages[node["id"]]
        if oid in existing:
            if node.get("summary", "").strip():
                raise MergeError(
                    f"{page['file']}: {oid} already exists in the ontology, so this page is an "
                    "anchor and its summary would never reach the graph. Remove the Summary section.")
            anchors.append(oid)
            continue
        if not node.get("summary", "").strip():
            raise MergeError(f"{page['file']}: no Summary section -- every new node needs one")
        props = {}
        if page["chapter"]:
            props["reference_chapter"] = page["chapter"]
        # The body is the node's content, not decoration: for a doc-derived node it plays the part
        # formula/params/outputs play for a computation, and `graph.SEARCH_TIERS` reads it in the
        # same tier. Dropping it would leave `find("head and shoulders")` empty on the very page
        # that names the formation.
        if body := " ".join(node.get("explanation", "").split()):
            props["explanation"] = body
        new_atoms.append({"id": oid, "title": page["title"], "kind": PRIMITIVE[page["kind"]],
                          "summary": " ".join(node["summary"].split()),
                          "epistemic": "observed", "status": "ratified", "props": props})

    known = set(existing) | {a["id"] for a in new_atoms}
    new_rels = []
    for link in graph["links"]:
        rel = link["type"]
        if rel not in ALLOWED:
            raise MergeError(
                f"relation {rel!r} is outside the vocabulary. A link in an untyped section (Summary, "
                "Explanation) lands here: put links only in a typed section.")
        src, dst = ident[link["source"]], ident[link["target"]]
        for end in (src, dst):
            if end not in known:
                raise MergeError(f"edge endpoint {end!r} resolves to no atom")
        page = pages[link["source"]]
        why = page["why"].get((link["via"].strip().lower(), graph_title(graph, link["target"])), "")
        if not why:
            raise MergeError(
                f"{page['file']}: edge {rel} -> {dst} has no rationale. Write it after '--' on the "
                "link's own line; every relation in this graph records why it holds.")
        new_rels.append({"from": pages[link["source"]]["title"], "rel": rel,
                         "to": pages[link["target"]]["title"], "why": why,
                         "from_id": src, "to_id": dst})

    seen = {(r["from_id"], r["rel"], r["to_id"]) for r in onto["relations"]}
    dupes = [r for r in new_rels if (r["from_id"], r["rel"], r["to_id"]) in seen]
    if dupes:
        raise MergeError(f"{len(dupes)} relation(s) already exist in the ontology: {dupes[:3]}")

    merged = {"atoms": onto["atoms"] + new_atoms,
              "relations": onto["relations"] + new_rels,
              # The ids, not just the count: the determinism test needs to separate the two halves
              # exactly, and `reference_chapter` cannot do it -- code-derived nodes carry that key
              # too, because it says which chapter DOCUMENTS a node, not where the node came from.
              "meta": {**onto["meta"], "doc_atoms": len(new_atoms),
                       "doc_atom_ids": sorted(a["id"] for a in new_atoms),
                       "doc_relations": len(new_rels), "doc_anchors": sorted(anchors)}}
    return merged, {"new_atoms": new_atoms, "new_relations": new_rels, "anchors": anchors}


def graph_title(graph: dict, node_id: str) -> str:
    for n in graph["nodes"]:
        if n["id"] == node_id:
            return n["title"].strip().lower()
    return node_id


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--wiki", required=True, type=Path)
    ap.add_argument("--graph", required=True, type=Path)
    ap.add_argument("--ontology", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    if args.out.resolve() == args.ontology.resolve():
        raise SystemExit("refusing to write over the input ontology; use a build path for --out")

    try:
        merged, added = merge(args.wiki, args.graph, args.ontology)
    except MergeError as exc:
        print(f"MERGE FAILED: {exc}", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    # `indent=1` is not cosmetic: it is what `build_signal_indicator_ontology.py` writes, and the
    # record is reviewed as a diff. At indent=2 a six-node merge rewrites all 27,000 lines and the
    # six additions become unreadable among them.
    args.out.write_text(json.dumps(merged, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"anchors (untouched) : {len(added['anchors'])}  {', '.join(added['anchors'])}")
    print(f"new atoms           : {len(added['new_atoms'])}")
    for a in added["new_atoms"]:
        print(f"   {a['id']:34} {a['kind']:9} chapter={a['props'].get('reference_chapter')}")
    print(f"new relations       : {len(added['new_relations'])}")
    for r in added["new_relations"]:
        print(f"   {r['from_id']:34} --{r['rel']}--> {r['to_id']}   ({r['why']})")
    print(f"totals              : {len(merged['atoms'])} atoms, {len(merged['relations'])} relations")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

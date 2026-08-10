# VENDORED from mangrove-one/jarvis @ 3a5c27f
# Licensed CC BY-NC-SA 4.0 — Tim Darrah / Mangrove Technologies.
# Do not edit here: change it upstream in jarvis, then re-run vendor/sync.py.
# Only import paths are rewritten; the body is verbatim.
"""GraphStore — the self-model graph's storage + traversal (#101).

One generic typed graph in the same jarvis.sqlite: `nodes` / `edges` / `graph_meta` (schema.sql).
GENERATIONAL: a rebuild writes generation N+1 completely, then `flip()` moves the live pointer and
drops old generations in ONE transaction — readers only ever see a complete graph. Persistent nodes
(concepts, L2) live at generation -1 and survive every rebuild.

Reads always span {live_generation, -1}. Traversal is plain BFS over the edges table — stdlib only,
comfortably fast at this repo's scale (~10^2 modules, ~10^3 edges).
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from . import ontology as ont

PERSISTENT = -1  # the concepts generation — never dropped by a rebuild


class BackboneCycle(ValueError):
    """An ordering-relation edge was rejected because it would close a cycle in its own topology
    (#185, C1). The ordering relations (part-of, is-a, requires, derived-from, …) each form a DAG."""


class GraphStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(db_path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        # schema.sql (in jarvis/session/) is loaded via the shared loader that substitutes the
        # ontology CHECK lists from ontology.py — the single source for the primitive/relation vocab.
        from .schema import schema_ddl
        self._db.executescript(schema_ddl())
        self._migrate_ontology()
        self._ensure_journal_schema()
        self._reseed_seq: int | None = None   # #225: set by mark_reseed() during a rebuild; stamped
                                              # onto every write so sweep_persistent() can find atoms
                                              # NOT re-produced this run (genuine removals).

    def _ensure_journal_schema(self) -> None:
        """Provenance journal (#225): an append-only, PROV-shaped record of what changed in the
        knowledge layer each rebuild, plus a per-generation commit row. Idempotent (IF NOT EXISTS)."""
        with self._db:
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS graph_journal ("
                " id INTEGER PRIMARY KEY AUTOINCREMENT,"
                " ts TEXT NOT NULL DEFAULT (datetime('now')),"   # transaction-time (append-only)
                " generation INTEGER NOT NULL,"
                " op TEXT NOT NULL,"                              # PROV: generated|invalidated|revised
                " entity_kind TEXT NOT NULL,"                    # node | edge
                " entity_id TEXT NOT NULL,"
                " source TEXT,"                                  # where-provenance (seed origin)
                " detail TEXT,"                                  # JSON
                " outcome TEXT NOT NULL DEFAULT 'ok')")          # CADF outcome
            self._db.execute(
                "CREATE INDEX IF NOT EXISTS idx_graph_journal_entity ON graph_journal(entity_id, id)")
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS graph_generations ("
                " generation INTEGER PRIMARY KEY,"
                " built_at TEXT NOT NULL DEFAULT (datetime('now')),"
                " git_sha TEXT, parent INTEGER,"
                " node_count INTEGER, edge_count INTEGER,"
                " added INTEGER, revised INTEGER, invalidated INTEGER)")

    def _migrate_ontology(self) -> None:
        """Idempotent (#185): add the ontology columns (`nodes.primitive_type`, `edges.relation`) to
        pre-ontology DBs. CREATE TABLE (fresh DBs) already declares them; `IF NOT EXISTS` skips the
        create there, so only old DBs need this ALTER. We DO NOT backfill: the code graph is left
        untyped (referenced from object:self, not migrated onto primitives) — nodes/edges are typed
        only when authored through the ontology write path."""
        with self._db:
            ncols = {r["name"] for r in self._db.execute("PRAGMA table_info(nodes)")}
            if "primitive_type" not in ncols:
                self._db.execute("ALTER TABLE nodes ADD COLUMN primitive_type TEXT")
            if "reseed_seq" not in ncols:  # #225 mark-and-sweep: stamp of the last reseed that wrote this row
                self._db.execute("ALTER TABLE nodes ADD COLUMN reseed_seq INTEGER")
            ecols = {r["name"] for r in self._db.execute("PRAGMA table_info(edges)")}
            if "relation" not in ecols:
                self._db.execute("ALTER TABLE edges ADD COLUMN relation TEXT")
            if "reseed_seq" not in ecols:
                self._db.execute("ALTER TABLE edges ADD COLUMN reseed_seq INTEGER")

    # --- generations -------------------------------------------------------------------------
    def live_generation(self) -> int:
        r = self._db.execute("SELECT value FROM graph_meta WHERE key='live_generation'").fetchone()
        return int(r["value"]) if r else 0          # 0 = no graph built yet

    def begin_generation(self) -> int:
        """The next generation number to build into (does not flip anything)."""
        return self.live_generation() + 1

    def flip(self, generation: int) -> None:
        """Make `generation` live and drop every other non-persistent generation — atomically.
        A crash before commit leaves the previous generation fully live (crash-safe rebuild)."""
        with self._db:  # one transaction
            self._db.execute(
                "INSERT INTO graph_meta(key, value) VALUES('live_generation', ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(generation),))
            self._db.execute("DELETE FROM nodes WHERE generation NOT IN (?, ?)", (generation, PERSISTENT))
            self._db.execute("DELETE FROM edges WHERE generation NOT IN (?, ?)", (generation, PERSISTENT))

    # --- provenance journal (#225) -----------------------------------------------------------
    def mark_reseed(self) -> int:
        """Begin a reseed: bump + return a monotonic token stamped onto every write this run (nodes/
        edges get `reseed_seq`). Persistent atoms NOT re-stamped this run are genuine removals that
        `sweep_persistent()` retires — making the reseed a true migration (adds, edits, AND deletes)."""
        r = self._db.execute("SELECT value FROM graph_meta WHERE key='reseed_seq'").fetchone()
        seq = (int(r["value"]) if r else 0) + 1
        with self._db:
            self._db.execute("INSERT INTO graph_meta(key, value) VALUES('reseed_seq', ?) "
                             "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(seq),))
        self._reseed_seq = seq
        return seq

    def sweep_persistent(self, seq: int) -> dict:
        """After a reseed, retire persistent (-1) atoms a reseed PREVIOUSLY wrote but did NOT
        re-produce this run (`reseed_seq IS NOT NULL AND != seq`) — a genuine removal. Nodes are
        **deprecated** (retained tombstone, KST-consistent) so they drop out of `persistent_snapshot`
        and journal as `invalidated`; edges (no tombstone concept) are **deleted**.

        CRITICAL — the `IS NOT NULL` guard protects **runtime-proposed atoms** (`propose_atom` writes
        drafts at generation -1 with `reseed_seq` NULL, since no reseed is in progress): they are
        never touched by the sweep. Only seeder-produced atoms (stamped by a reseed) are swept.
        No-op without a token (never sweep blind). Returns {nodes_deprecated, edges_removed}."""
        if not seq:
            return {"nodes_deprecated": 0, "edges_removed": 0}
        with self._db:
            cur = self._db.execute(
                "UPDATE nodes SET status='deprecated' WHERE generation=? AND status!='deprecated' "
                "AND reseed_seq IS NOT NULL AND reseed_seq != ?", (PERSISTENT, seq))
            nd = cur.rowcount
            cur = self._db.execute(
                "DELETE FROM edges WHERE generation=? AND reseed_seq IS NOT NULL AND reseed_seq != ?",
                (PERSISTENT, seq))
            er = cur.rowcount
        self._reseed_seq = None   # reseed complete
        return {"nodes_deprecated": nd, "edges_removed": er}

    def persistent_snapshot(self) -> dict[str, dict]:
        """A content snapshot of the PERSISTENT (-1) knowledge layer — {key: {entity_kind, entity_id,
        hash, source, detail}} — for diff-at-flip journaling. Only the knowledge layer: the derived
        code graph is disposable per generation and its provenance is git, not the graph (#225)."""
        snap: dict[str, dict] = {}
        for r in self._db.execute(
                "SELECT id, kind, name, props, status, primitive_type FROM nodes "
                "WHERE generation=? AND status!='deprecated'",   # deprecated = retired ⇒ out of the live set
                (PERSISTENT,)):
            props = r["props"] or ""
            h = hashlib.sha1(
                f"{r['kind']}|{r['name']}|{props}|{r['status']}|{r['primitive_type']}".encode()).hexdigest()
            try:
                seed = (json.loads(props) if props else {}).get("seed")
            except Exception:
                seed = None
            snap[f"node:{r['id']}"] = {
                "entity_kind": "node", "entity_id": r["id"], "hash": h,
                "source": seed or "authored",
                "detail": {"name": r["name"], "primitive": r["primitive_type"], "status": r["status"]}}
        for r in self._db.execute(
                "SELECT src, dst, type, relation, props, weight FROM edges WHERE generation=?",
                (PERSISTENT,)):
            key = f"{r['src']}->{r['dst']}:{r['type']}"
            h = hashlib.sha1(f"{r['relation']}|{r['props'] or ''}|{r['weight']}".encode()).hexdigest()
            snap[f"edge:{key}"] = {
                "entity_kind": "edge", "entity_id": key, "hash": h, "source": "derived",
                "detail": {"relation": r["relation"]}}
        return snap

    def record_generation(self, generation: int, before: dict, after: dict, *,
                          git_sha: str | None = None) -> dict:
        """Diff two persistent-layer snapshots and APPEND the deltas to graph_journal, PROV-shaped
        (generated / revised / invalidated), plus a graph_generations commit row. Diff-at-flip, NOT
        per-write: a reseed re-writes ~everything, so only genuine changes are journaled. Idempotent
        per generation (the commit row upserts). Returns {added, revised, invalidated}."""
        rows, added, revised, invalidated = [], 0, 0, 0
        for key, av in after.items():
            bv = before.get(key)
            if bv is None:
                op, added = "generated", added + 1
            elif bv["hash"] != av["hash"]:
                op, revised = "revised", revised + 1
            else:
                continue
            rows.append((generation, op, av["entity_kind"], av["entity_id"], av["source"],
                         json.dumps(av["detail"])))
        for key, bv in before.items():
            if key not in after:
                invalidated += 1
                rows.append((generation, "invalidated", bv["entity_kind"], bv["entity_id"],
                             bv["source"], json.dumps(bv["detail"])))
        with self._db:
            if rows:
                self._db.executemany(
                    "INSERT INTO graph_journal(generation, op, entity_kind, entity_id, source, detail) "
                    "VALUES(?,?,?,?,?,?)", rows)
            nc = self._db.execute("SELECT count(*) c FROM nodes WHERE generation IN (?, ?)",
                                  (generation, PERSISTENT)).fetchone()["c"]
            ec = self._db.execute("SELECT count(*) c FROM edges WHERE generation IN (?, ?)",
                                  (generation, PERSISTENT)).fetchone()["c"]
            self._db.execute(
                "INSERT INTO graph_generations(generation, git_sha, parent, node_count, edge_count, "
                "added, revised, invalidated) VALUES(?,?,?,?,?,?,?,?) "
                "ON CONFLICT(generation) DO UPDATE SET built_at=datetime('now'), git_sha=excluded.git_sha, "
                "node_count=excluded.node_count, edge_count=excluded.edge_count, added=excluded.added, "
                "revised=excluded.revised, invalidated=excluded.invalidated",
                (generation, git_sha, generation - 1, nc, ec, added, revised, invalidated))
        return {"added": added, "revised": revised, "invalidated": invalidated}

    def graph_history(self, entity_id: str | None = None, *, limit: int = 50) -> list[dict]:
        """Recent journal events, newest first — optionally for one entity ('when did X change?')."""
        if entity_id:
            rows = self._db.execute(
                "SELECT ts, generation, op, entity_kind, entity_id, source FROM graph_journal "
                "WHERE entity_id=? ORDER BY id DESC LIMIT ?", (entity_id, int(limit))).fetchall()
        else:
            rows = self._db.execute(
                "SELECT ts, generation, op, entity_kind, entity_id, source FROM graph_journal "
                "ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()
        return [dict(r) for r in rows]

    def purge_node(self, node_id: str) -> dict | None:
        """HARD-PURGE a PERSISTENT (-1) knowledge node: delete the node AND every edge touching it
        (no dangling edges), and journal the removal as PROV `invalidated` at purge-time — the
        journal IS the tombstone (#229), so `graph_history(node_id)` still resolves a purged node.
        Unlike the reseed's diff-at-flip, a runtime purge happens BETWEEN deploys, so we append the
        journal row directly here (the next reseed's before-snapshot won't contain the node).
        Returns {node, edges_removed} or None if the node is absent at the persistent layer."""
        row = self._db.execute(
            "SELECT id, kind, name, props, status, primitive_type FROM nodes "
            "WHERE id=? AND generation=?", (node_id, PERSISTENT)).fetchone()
        if not row:
            return None
        try:
            seed = (json.loads(row["props"]) if row["props"] else {}).get("seed")
        except Exception:
            seed = None
        with self._db:
            cur = self._db.execute(
                "DELETE FROM edges WHERE (src=? OR dst=?) AND generation=?",
                (node_id, node_id, PERSISTENT))
            edges_removed = cur.rowcount
            self._db.execute("DELETE FROM nodes WHERE id=? AND generation=?", (node_id, PERSISTENT))
            self._db.execute(
                "INSERT INTO graph_journal(generation, op, entity_kind, entity_id, source, detail) "
                "VALUES(?,?,?,?,?,?)",
                (self.live_generation(), "invalidated", "node", node_id, seed or "authored",
                 json.dumps({"name": row["name"], "primitive": row["primitive_type"],
                             "status": row["status"], "via": "runtime-retirement (#229)"})))
        return {"node": node_id, "edges_removed": edges_removed}

    def first_seen(self, node_id: str) -> str | None:
        """The preserved first-seen (created_at) of a node — the valid-time that survives reseed."""
        r = self._db.execute(
            "SELECT created_at FROM nodes WHERE id=? ORDER BY created_at ASC LIMIT 1", (node_id,)).fetchone()
        return r["created_at"] if r else None

    # --- writes (deriver / concept layer) ----------------------------------------------------
    def add_node(self, generation: int, id: str, kind: str, name: str, *, props: dict | None = None,
                 status: str = "ratified", epistemic: str = "observed", confidence: float = 1.0,
                 primitive_type: str | None = None, subject: str = "world") -> None:
        """Write a node. Ontology nodes pass `primitive_type` (one of the 9 §Part-I primitives) — it
        is validated and a props.classification block (subject + subtype=kind) is stamped if the
        caller didn't supply one. Code-graph / legacy nodes omit it and stay untyped (NULL) — the
        AST graph is referenced from object:self, not migrated onto primitives (#185)."""
        if primitive_type is not None:
            if not ont.is_primitive(primitive_type):
                raise ValueError(f"primitive_type {primitive_type!r} not in the ontology "
                                 f"(must be one of {sorted(ont.PRIMITIVES)})")
            props = dict(props or {})
            props.setdefault("classification", ont.new_classification(subject=subject, subtype=kind))
        # UPSERT that PRESERVES created_at (#225): INSERT OR REPLACE deletes+reinserts, which reset
        # created_at every reseed and destroyed first-seen provenance. ON CONFLICT updates only the
        # mutable columns — created_at keeps its original value (valid-time carried forward on the
        # (id, generation) key). Persistent nodes (generation=-1) are stable across deploys, so a
        # re-derived atom keeps its birth date; a genuinely new atom gets DEFAULT datetime('now').
        self._db.execute(
            "INSERT INTO nodes(id, kind, name, props, status, epistemic, confidence, "
            "generation, primitive_type, reseed_seq) VALUES(?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(id, generation) DO UPDATE SET "
            "kind=excluded.kind, name=excluded.name, props=excluded.props, status=excluded.status, "
            "epistemic=excluded.epistemic, confidence=excluded.confidence, "
            "primitive_type=excluded.primitive_type, reseed_seq=excluded.reseed_seq",
            (id, kind, name, json.dumps(props) if props else None, status, epistemic, confidence,
             generation, primitive_type, self._reseed_seq))

    def add_edge(self, generation: int, src: str, dst: str, type: str, *,
                 weight: float = 1.0, props: dict | None = None, relation: str | None = None) -> None:
        """Write an edge. Ontology edges pass `relation` — a node in the §Part-IV hierarchy rooted at
        `associated-with`. It is validated, and if it is an ordering relation its own topology is
        kept acyclic (C1): an edge that would close a cycle among same-`relation` edges is rejected.
        Code-graph / legacy edges omit it and stay untyped (NULL) — no defaulting, no cycle check
        (the code graph is left alone). The ontology's "default to associated-with then refine"
        (§4 principle 3) lives in the authoring layer, which passes the root explicitly."""
        if relation is not None:
            if not ont.is_relation(relation):
                raise ValueError(f"relation {relation!r} not in the ontology "
                                 f"(must be one of {sorted(ont.RELATIONS)})")
            if ont.is_acyclic(relation):       # this relation's OWN topology must stay a DAG (#185, C1)
                if src == dst:
                    raise BackboneCycle(f"self-loop rejected on {relation} edge {type}: {src}")
                if self._reaches(generation, dst, src, relation):
                    raise BackboneCycle(
                        f"{type} {src}->{dst} rejected: would close a cycle in the {relation} topology "
                        f"({dst} already reaches {src} via {relation})")
        self._db.execute(
            "INSERT OR REPLACE INTO edges(src, dst, type, weight, props, generation, relation, "
            "reseed_seq) VALUES(?,?,?,?,?,?,?,?)",
            (src, dst, type, weight, json.dumps(props) if props else None, generation, relation,
             self._reseed_seq))

    def _reaches(self, generation: int, start: str, target: str, relation: str) -> bool:
        """Does `start` reach `target` following edges of THIS ONE relation in `generation`?
        Each ordering relation is its own topology over the shared node universe (C1) — a
        compositional path never blocks a taxonomic edge, etc. BFS, stdlib only."""
        seen, frontier = {start}, [start]
        while frontier:
            nxt = []
            rows = self._db.execute(
                f"SELECT dst FROM edges WHERE generation=? AND relation=? AND src IN "
                f"({','.join('?' * len(frontier))})",
                (generation, relation, *frontier)).fetchall()
            for r in rows:
                d = r["dst"]
                if d == target:
                    return True
                if d not in seen:
                    seen.add(d); nxt.append(d)
            frontier = nxt
        return False

    def commit(self) -> None:
        self._db.commit()

    # --- reads (always live ∪ persistent) ----------------------------------------------------
    def _gens(self) -> tuple[int, int]:
        return (self.live_generation(), PERSISTENT)

    def node(self, id: str) -> dict[str, Any] | None:
        r = self._db.execute(
            "SELECT * FROM nodes WHERE id=? AND generation IN (?, ?)", (id, *self._gens())).fetchone()
        return dict(r) if r else None

    def nodes(self, kind: str | None = None) -> list[dict[str, Any]]:
        if kind:
            rows = self._db.execute(
                "SELECT * FROM nodes WHERE kind=? AND generation IN (?, ?) ORDER BY id",
                (kind, *self._gens())).fetchall()
        else:
            rows = self._db.execute(
                "SELECT * FROM nodes WHERE generation IN (?, ?) ORDER BY id", self._gens()).fetchall()
        return [dict(r) for r in rows]

    def edges(self, *, src: str | None = None, dst: str | None = None,
              types: list[str] | None = None) -> list[dict[str, Any]]:
        sql, args = "SELECT * FROM edges WHERE generation IN (?, ?)", list(self._gens())
        if src:
            sql += " AND src=?"; args.append(src)
        if dst:
            sql += " AND dst=?"; args.append(dst)
        if types:
            sql += f" AND type IN ({','.join('?' * len(types))})"; args.extend(types)
        return [dict(r) for r in self._db.execute(sql, tuple(args)).fetchall()]

    def counts(self) -> dict[str, Any]:
        """Node counts by kind + edge counts by type for the LIVE graph (the drift check's raw)."""
        g = self._gens()
        nk = {r["kind"]: r["c"] for r in self._db.execute(
            "SELECT kind, count(*) c FROM nodes WHERE generation IN (?, ?) GROUP BY kind", g)}
        et = {r["type"]: r["c"] for r in self._db.execute(
            "SELECT type, count(*) c FROM edges WHERE generation IN (?, ?) GROUP BY type", g)}
        return {"generation": self.live_generation(), "nodes": nk, "edges": et}

    # --- the KST / knowledge boundary ------------------------------------------------------------
    def knowledge_nodes(self, *, status: str | None = None) -> list[dict[str, Any]]:
        """THE separation seam (#185): the knowledge layer = every node carrying a `primitive_type`.
        The code graph (derived, `primitive_type IS NULL`) is INVISIBLE here — KST/recall/activation
        read only this, so the KST ontology and the code-graph machinery never touch. Optionally
        filter by status (e.g. exclude 'deprecated')."""
        sql = ("SELECT * FROM nodes WHERE primitive_type IS NOT NULL AND generation IN (?, ?)")
        args: list[Any] = list(self._gens())
        if status is not None:
            sql += " AND status=?"; args.append(status)
        return [dict(r) for r in self._db.execute(sql + " ORDER BY id", tuple(args)).fetchall()]

    def knowledge_orphans(self) -> list[str]:
        """Knowledge nodes with NO edge to another knowledge node (#185 invariant: no orphans — every
        node must connect within the knowledge layer). Cross-layer edges to the code graph don't
        count — KST can't see them, so a node reachable only through the code graph is still an
        orphan here. This is the check the seed must satisfy and `validate` enforces."""
        g = self._gens()
        kids = {r["id"] for r in self._db.execute(
            "SELECT id FROM nodes WHERE primitive_type IS NOT NULL AND generation IN (?, ?)", g)}
        connected: set[str] = set()
        for e in self._db.execute(
                "SELECT src, dst FROM edges WHERE generation IN (?, ?)", g):
            if e["src"] in kids and e["dst"] in kids:
                connected.add(e["src"]); connected.add(e["dst"])
        return sorted(kids - connected)

    def knowledge_disconnected(self, anchor: str = "object:self") -> list[str]:
        """Knowledge nodes NOT reachable from `anchor` over the knowledge-layer edges (a STRONGER
        invariant than knowledge_orphans: it catches an island of nodes that link to each other but
        not to the graph rooted at self — the "floater" case knowledge_orphans misses). The knowledge
        graph must be ONE connected component rooted at object:self; the viz collapse + KST rely on it."""
        g = self._gens()
        kids = {r["id"] for r in self._db.execute(
            "SELECT id FROM nodes WHERE primitive_type IS NOT NULL AND generation IN (?, ?)", g)}
        if anchor not in kids:
            return sorted(kids)
        adj: dict[str, list[str]] = {}
        for e in self._db.execute("SELECT src, dst FROM edges WHERE generation IN (?, ?)", g):
            if e["src"] in kids and e["dst"] in kids:      # undirected within the knowledge layer
                adj.setdefault(e["src"], []).append(e["dst"])
                adj.setdefault(e["dst"], []).append(e["src"])
        seen, stack = {anchor}, [anchor]
        while stack:
            for v in adj.get(stack.pop(), ()):
                if v not in seen:
                    seen.add(v); stack.append(v)
        return sorted(kids - seen)

    # --- cross-cut views: slice the knowledge space by node primitive OR by relation ------------
    def nodes_by_primitive(self, primitive: str) -> list[dict[str, Any]]:
        """Every node of one §Part-I primitive type (a node-type cross-cut of the space)."""
        if not ont.is_primitive(primitive):
            raise ValueError(f"unknown primitive {primitive!r}")
        rows = self._db.execute(
            "SELECT * FROM nodes WHERE primitive_type=? AND generation IN (?, ?) ORDER BY id",
            (primitive, *self._gens())).fetchall()
        return [dict(r) for r in rows]

    def edges_by_relation(self, relation: str, *, include_subtypes: bool = True) -> list[dict[str, Any]]:
        """Every edge of one relation (an edge-type cross-cut). `include_subtypes` honours the §4
        hierarchy: asking for `causal` returns causes/enables/prevents/requires too; a leaf returns
        just itself. This is query-at-any-granularity (§4 principle 1)."""
        wanted = sorted(ont.relation_descendants(relation)) if include_subtypes else [relation]
        if not ont.is_relation(relation):
            raise ValueError(f"unknown relation {relation!r}")
        rows = self._db.execute(
            f"SELECT * FROM edges WHERE relation IN ({','.join('?' * len(wanted))}) "
            f"AND generation IN (?, ?) ORDER BY src, dst",
            (*wanted, *self._gens())).fetchall()
        return [dict(r) for r in rows]

    def ontology_coverage(self) -> dict[str, Any]:
        """What fraction of the ontology the live graph exercises — primitives used / relations used
        (counting a used leaf as covering its category too), for the ≥50%-coverage acceptance check."""
        g = self._gens()
        prims = {r["primitive_type"] for r in self._db.execute(
            "SELECT DISTINCT primitive_type FROM nodes WHERE primitive_type IS NOT NULL "
            "AND generation IN (?, ?)", g)}
        rels = {r["relation"] for r in self._db.execute(
            "SELECT DISTINCT relation FROM edges WHERE relation IS NOT NULL AND generation IN (?, ?)", g)}
        # a used relation covers itself + all its ancestors (its category, the root)
        rel_closure: set[str] = set()
        for r in rels:
            rel_closure.update(ont.relation_ancestors(r))
        return {
            "primitives_used": sorted(prims),
            "primitive_coverage": len(prims) / len(ont.PRIMITIVES),
            "relations_used": sorted(rels),
            "categories_used": sorted(rel_closure & set(ont.CATEGORIES)),
            "relation_coverage": len(rel_closure & set(ont.RELATIONS)) / len(ont.RELATIONS),
        }

    # --- resolution + traversal ---------------------------------------------------------------
    def resolve(self, ref: str) -> list[str]:
        """Fuzzy node lookup: exact id → name → id/name substring. Returns candidate ids (best first)."""
        g = self._gens()
        if self._db.execute("SELECT 1 FROM nodes WHERE id=? AND generation IN (?, ?)", (ref, *g)).fetchone():
            return [ref]
        rows = self._db.execute(
            "SELECT id FROM nodes WHERE name=? AND generation IN (?, ?) ORDER BY id", (ref, *g)).fetchall()
        if rows:
            return [r["id"] for r in rows]
        # substring: 'store.py' → module path ending in .store; 'session/store.py' → dotted path
        needle = ref.replace("/", ".").removesuffix(".py")
        rows = self._db.execute(
            "SELECT id FROM nodes WHERE (id LIKE ? OR name LIKE ?) AND generation IN (?, ?) "
            "ORDER BY length(id) LIMIT 12", (f"%{needle}%", f"%{needle}%", *g)).fetchall()
        return [r["id"] for r in rows]

    def traverse(self, start: str, *, direction: str = "out", types: list[str] | None = None,
                 depth: int = 3) -> list[dict[str, Any]]:
        """BFS from `start` following edges `direction` ('out' src→dst, 'in' dst→src), returning
        [{id, via, depth}] excluding the start. Depth-capped; cycle-safe."""
        seen, frontier, out = {start}, [start], []
        for d in range(1, max(1, depth) + 1):
            nxt: list[str] = []
            for nid in frontier:
                es = self.edges(src=nid, types=types) if direction == "out" \
                    else self.edges(dst=nid, types=types)
                for e in es:
                    other = e["dst"] if direction == "out" else e["src"]
                    if other in seen:
                        continue
                    seen.add(other)
                    out.append({"id": other, "via": e["type"], "depth": d})
                    nxt.append(other)
            frontier = nxt
            if not frontier:
                break
        return out

    def _containing_module(self, node_id: str, *, hops: int = 4) -> str | None:
        """Walk reverse-`contains` up to the owning module — EXACT (the graph knows its structure;
        never guess module boundaries from dotted names: package __init__ nodes make rsplit ambiguous)."""
        cur = node_id
        for _ in range(hops):
            if cur.startswith("module:"):
                return cur
            parents = self.edges(dst=cur, types=["contains"])
            if not parents:
                return None
            cur = parents[0]["src"]
        return cur if cur.startswith("module:") else None

    def impact(self, id: str, *, depth: int = 4) -> dict[str, list[str]]:
        """The pre-self-edit blast radius (US-1): transitive DEPENDENTS (reverse imports/contains),
        the tests covering the zone, and the policies whose ENFORCEMENT touches the zone. Policies
        never point at modules directly — they enforce tests/guardrails/hook-files — so the policy
        set is reached through the zone's covering tests and the guardrails implemented by the
        zone's classes (guardrail --implements--> class)."""
        dependents = [h["id"] for h in self.traverse(id, direction="in",
                                                     types=["imports", "contains"], depth=depth)]
        zone = {id, *dependents}
        zone_classes = {e["dst"] for n in zone for e in self.edges(src=n, types=["contains"])}
        tests = sorted({e["src"] for n in zone for e in self.edges(dst=n, types=["tests"])})
        guardrails = {e["src"] for c in zone_classes for e in self.edges(dst=c, types=["implements"])
                      if e["src"].startswith("guardrail:")}
        anchors = set(tests) | guardrails | zone
        policies = sorted({e["src"] for a in anchors for e in self.edges(dst=a, types=["enforces"])})
        # PROBABLE users — critical-review finding: jarvis wires consumers via dependency injection
        # (app.py passes `store` into tools/loop/router), so import-level dependents UNDERSTATE the
        # blast radius (impact(session.store) missed all six DI consumers). Recover them through the
        # best-effort `calls` edges: any module whose functions call INTO the zone's functions is a
        # probable user. Kept as a SEPARATE, clearly-labeled list — the exact lists stay exact.
        zone_functions = {e["dst"] for c in zone_classes | zone
                          for e in self.edges(src=c, types=["contains"])}
        caller_modules: set[str] = set()
        for f in zone_functions:
            for e in self.edges(dst=f, types=["calls"]):
                mod = self._containing_module(e["src"])
                if mod and mod not in zone:
                    caller_modules.add(mod)
        return {"dependents": sorted(d for d in dependents if not d.startswith("test:")),
                "probable_users": sorted(caller_modules),
                "tests": tests, "policies": policies}

-- VENDORED from mangrove-one/jarvis @ 3a5c27f — the three graph tables only.
-- CC BY-NC-SA 4.0. Placeholders are filled by schema.py from ontology.py.

CREATE TABLE IF NOT EXISTS nodes (
    id         TEXT NOT NULL,
    kind       TEXT NOT NULL,       -- module|class|function|tool|guardrail|policy|test|file|concept
    name       TEXT NOT NULL,
    props      TEXT,                -- JSON: file, lines, docstring, capability, severity, order, ...
    status     TEXT NOT NULL DEFAULT 'ratified',   -- ratified | draft (L1 derived = ratified)
    epistemic  TEXT NOT NULL DEFAULT 'observed',   -- observed|inferred|hypothesized|assumed
    primitive_type TEXT CHECK(primitive_type IS NULL OR primitive_type IN
        (__PRIMITIVE_TYPES__)),  -- ontology primitive (#185, design/01 Part I): the atom's type. The IN-list is substituted at load time from ontology.PRIMITIVE_TYPES (single source — do NOT hand-list here). 'Atom' = the GENERIC root (unrefined, the fringe; refines to one of the nine — mirrors 'associated-with' for edges). NULL = the untyped code graph (invisible to KST — a different thing from generic). props.classification carries subject(self|world|other)+the 11 dims.
    confidence REAL NOT NULL DEFAULT 1.0,
    generation INTEGER NOT NULL DEFAULT 0,         -- L1 rebuild generation; -1 = persistent (concepts)
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (id, generation)
);
CREATE INDEX IF NOT EXISTS idx_nodes_kind ON nodes(kind, generation);

CREATE TABLE IF NOT EXISTS edges (
    src        TEXT NOT NULL,
    dst        TEXT NOT NULL,
    type       TEXT NOT NULL,       -- free-text edge label (code graph: contains|imports|calls|inherits|…). The ontology `relation` below is the governed classification; `type` is kept as the caller's own subtype label.
    relation   TEXT CHECK(relation IS NULL OR relation IN
        (__RELATIONS__)),  -- ontology relation (#185, docs/memory/design/01 Part IV): a node in the hierarchy rooted at 'associated-with'. The IN-list is substituted at load time from ontology.RELATIONS (single source — do NOT hand-list here). NULL on code-graph/legacy edges (left untyped). Ordering relations (part-of|is-a|requires|derived-from|…) are DAG-enforced per-relation at write.
    weight     REAL NOT NULL DEFAULT 1.0,
    props      TEXT,                -- JSON (e.g. line; best_effort:true on calls)
    generation INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (src, dst, type, generation)
);
CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src, generation);
CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst, generation);

CREATE TABLE IF NOT EXISTS graph_meta (
    key   TEXT PRIMARY KEY,          -- 'live_generation'
    value TEXT NOT NULL
);

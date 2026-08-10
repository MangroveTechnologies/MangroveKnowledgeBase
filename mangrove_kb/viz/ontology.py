# VENDORED from mangrove-one/jarvis @ 3a5c27f
# Licensed CC BY-NC-SA 4.0 — Tim Darrah / Mangrove Technologies.
# Do not edit here: change it upstream in jarvis, then re-run vendor/sync.py.
# Only import paths are rewritten; the body is verbatim.
"""The ontology — the single source of truth for what a node/edge may BE (#185).

Faithful to `docs/memory/design/01-knowledge-ontology.md`:

  * Part I  — the 10 knowledge PRIMITIVES. Nine are node types (Object, Property, Concept, Fact,
              Experience, Procedure, Schema, Context, Judgment); the tenth, **Association, IS the
              edge**. A **node IS a Primitive** — its type is one of the nine. There is **no `atom`
              and no `concept` bucket**: "atom" was never a type, and "Concept" is exactly one of the
              nine, not a container. The class model that enforces this lives in `graph/primitives.py`.
  * Part IV — how elements are RELATED. Relationships form a **hierarchy** (the Biolink pattern):
              every relation inherits from the generic root `associated-with`; under it sit six
              categories (structural, causal, descriptive, associative, temporal, meta), and under
              those the fine relations. A query can work at ANY granularity — ask for all `causal`
              edges without caring whether each is `causes` / `enables` / `prevents` / `requires`.
  * Part V  — every atom/edge also occupies a position in an 11-dimensional polythetic feature space.
  * Part II — knowledge is organized along five axes simultaneously.

Two principles from §4 drive the write path:
  * **Default to the root.** An edge whose specific relation is not yet known enters as
    `associated-with` (§4 principle 3: "forcing classification into the wrong type is worse than
    using a generic type"). This lets an atom join the fringe under incomplete information and be
    *refined* to a more specific relation as evidence accrues — `supersedes` being the exception
    that retires an edge rather than refining it.
  * **Some relations must stay acyclic** (our C1 design, endorsed by the owner): the ordering
    relations (composition, classification, dependency, provenance, time, meta-ordering) each form a
    DAG over the shared node universe so KST / toposort / fringe are well-defined. This is enforced
    per-relation at write; the non-order relations are left free.
"""
from __future__ import annotations

from typing import NamedTuple

# --- Part I: the 9 node primitives (the 10th primitive, Association, IS the edge) --------------
# A node is an ATOM; its `primitive_type` is one of these nine. `Atom` (ROOT_PRIMITIVE) is the
# GENERIC root — the type-neutral umbrella that mirrors `associated-with` for edges: an atom may
# enter generic (`primitive_type='Atom'`, the fringe) when we know it is knowledge but not yet what
# KIND, and REFINE to one of the nine as evidence accrues. `Atom` is a real value, never NULL —
# NULL `primitive_type` means the untyped code graph (invisible to KST), which is a different thing.
ROOT_PRIMITIVE = "Atom"

PRIMITIVES: frozenset[str] = frozenset({
    "Object",      # DOLCE endurant — a persistent, individuable entity (a service, a person, a file)
    "Property",    # DOLCE quality — a characteristic value of an object ("latency = 3.2s")
    "Concept",     # Rosch prototype — a category grouping objects by shared structure ("backend service")
    "Fact",        # Floridi semantic info — a truth-apt claim binding objects/properties/concepts
    "Experience",  # Tulving episodic — a temporally-anchored episode ("the March 15 deploy failed")
    "Procedure",   # Squire procedural — how to do something (a deploy runbook, a test)
    "Schema",      # Piaget schema — a structured expectation / template (a guardrail, a policy)
    "Context",     # Barsalou ad hoc — an active frame that reshapes retrieval ("reviewing for security")
    "Judgment",    # Ackoff wisdom — an evaluative/normative stance carrying its "why"
})

# --- Part IV: the relation hierarchy (child -> parent); the root is `associated-with` -----------
# Every relation inherits from ROOT. The six mid-level nodes are the categories from §4; the leaves
# are the fine relations. Query at any level: `relation_descendants("causal")` == the causal leaves.
ROOT_RELATION = "associated-with"

class RelSpec(NamedTuple):
    """One relation's metadata. `parent` places it in the hierarchy (None for the root); `acyclic`
    marks it as an ordering relation whose own topology must stay a DAG (write-time cycle-rejected).
    Both `CATEGORIES` and `ACYCLIC` are DERIVED from these — declare a relation ONCE, right here."""
    parent: str | None
    acyclic: bool = False


# child -> RelSpec(parent, acyclic). This is the ONE declaration of the relation hierarchy AND which
# relations are ordering/acyclic — CATEGORIES (direct children of the root) and ACYCLIC (the DAG set)
# are computed from it below, never hand-listed a second time.
RELATIONS: dict[str, RelSpec] = {
    ROOT_RELATION: RelSpec(None),                       # the generic catch-all + the tree root (§4 principle 1 & 3)
    # ---- the six categories (§4) -----------------------------------------------------------
    "structural":  RelSpec(ROOT_RELATION),              # what IS something (taxonomy + composition)
    "causal":      RelSpec(ROOT_RELATION),              # what CAUSES / enables / requires what
    "descriptive": RelSpec(ROOT_RELATION),              # what PROPERTIES / state / role something has
    "associative": RelSpec(ROOT_RELATION),              # what loosely GOES WITH what (similarity, genealogy)
    "temporal":    RelSpec(ROOT_RELATION),              # what HAPPENED WHEN
    "meta":        RelSpec(ROOT_RELATION),              # knowledge ABOUT knowledge
    # ---- structural leaves (composition + classification are ordering => acyclic) ----------
    "is-a":        RelSpec("structural", acyclic=True), # category membership (graded)
    "kind-of":     RelSpec("structural", acyclic=True), # subcategory
    "part-of":     RelSpec("structural", acyclic=True), # composition
    "instance-of": RelSpec("structural", acyclic=True), # specific exemplar of a concept
    # ---- causal leaves (dependency/causation are ordering; `prevents` is not) --------------
    "causes":      RelSpec("causal", acyclic=True),
    "enables":     RelSpec("causal", acyclic=True),
    "prevents":    RelSpec("causal"),
    "requires":    RelSpec("causal", acyclic=True),     # prerequisite — the KST surmise relation
    # ---- descriptive leaves ----------------------------------------------------------------
    "has-property": RelSpec("descriptive"),
    "has-state":    RelSpec("descriptive"),
    "has-role":     RelSpec("descriptive"),
    "about":        RelSpec("descriptive"),             # subject/topic — dcterms:subject. What a thing
                                                        # is CONCERNED WITH, never what it IS: a signal
                                                        # is about momentum, an indicator measures it.
    # ---- associative leaves (the root `associated-with` is the generic member) --------------
    "similar-to":     RelSpec("associative"),           # shared features / structure
    "contrasts-with": RelSpec("associative"),           # notable difference
    "derived-from":   RelSpec("associative", acyclic=True),  # genealogy / provenance (ordering)
    "uses":           RelSpec("associative"),           # runtime invocation/orchestration (skill→tool,
                                                        # procedure→tool). NOT a prerequisite (that's the
                                                        # KST `requires`) — deliberately associative so it
                                                        # stays OUT of the surmise lattice.
    # ---- temporal leaves (time ordering => acyclic; co-occurrence is symmetric) ------------
    "preceded-by":      RelSpec("temporal", acyclic=True),
    "co-occurred-with": RelSpec("temporal"),
    "led-to":           RelSpec("temporal", acyclic=True),   # temporal + causal
    # ---- meta leaves (supersede/consolidate are ordering => acyclic) -----------------------
    "justified-by": RelSpec("meta"),                    # why we believe this ("store the because")
    "contradicts":  RelSpec("meta"),                    # conflicting knowledge (symmetric)
    "supersedes":   RelSpec("meta", acyclic=True),      # newer replaces older
    "consolidates": RelSpec("meta", acyclic=True),      # generalization from episodes
}

# BOTH derived from RELATIONS (single source — never hand-listed):
# CATEGORIES = the direct children of the root, in doc order (dict insertion order).
CATEGORIES: tuple[str, ...] = tuple(r for r, spec in RELATIONS.items() if spec.parent == ROOT_RELATION)
# ACYCLIC = the ordering relations that MUST stay a DAG (C1): each is its own DAG over the shared node
# universe (a compositional cycle never blocks a taxonomic edge), enforced per-relation at write.
# Everything else (the root, similarity/contrast, descriptive, co-occurrence, prevents, justified-by,
# contradicts) is left free; activation spreading is cycle-safe over the full graph.
ACYCLIC: frozenset[str] = frozenset(r for r, spec in RELATIONS.items() if spec.acyclic)

# --- Part V: the 11 polythetic dimensions + the self/world subject axis (graded; stored in props)
DIMENSIONS: tuple[str, ...] = (
    "abstraction", "codification", "confidence", "depth", "generality", "scope",
    "temporal_anchoring", "functional_role", "typicality", "automation", "epistemic_status",
)
# --- Part II: the 5 organizational axes knowledge is arranged along simultaneously --------------
AXES: tuple[str, ...] = (
    "abstraction", "domain_clustering", "codification", "temporal_anchoring", "scope",
)
SUBJECTS: frozenset[str] = frozenset({"self", "world", "other"})

# Value vocabularies shared by the FCO family — the single source for the epistemic-status and
# admission-status ranges (so fco/atom validation, the schema comments, and any UI derive from here,
# never re-type the members). `epistemic` = how the belief was arrived at; `status` = KST admission
# state (K = ratified).
EPISTEMIC: frozenset[str] = frozenset({"observed", "inferred", "hypothesized", "assumed"})
STATUS: frozenset[str] = frozenset({"draft", "ratified", "deprecated"})

# The root atom that IS jarvis. `self` is ONE Object node; the code graph (modules/classes/…) is
# referenced from it and expanded on demand — never materialized as hundreds of atoms.
SELF_ID = "object:self"


# every valid primitive_type value: the generic root `Atom` + the nine refined types.
PRIMITIVE_TYPES: frozenset[str] = PRIMITIVES | {ROOT_PRIMITIVE}


# --- predicates ---------------------------------------------------------------------------------
def is_primitive(p: str) -> bool:
    """True for any valid primitive_type — the nine refined types OR the generic root `Atom`."""
    return p in PRIMITIVE_TYPES


def is_relation(r: str) -> bool:
    return r in RELATIONS


def is_acyclic(relation: str) -> bool:
    """True if this relation's own topology must stay a DAG (write-time cycle-rejected)."""
    return relation in ACYCLIC


# --- relation-hierarchy navigation (query-at-any-granularity, §4 principle 1) -------------------
def parent_of(relation: str) -> str | None:
    """The relation this one directly inherits from (None for the root)."""
    if relation not in RELATIONS:
        raise ValueError(f"unknown relation {relation!r}")
    return RELATIONS[relation].parent


def relation_ancestors(relation: str) -> list[str]:
    """The chain from `relation` up to (and including) the root, nearest first."""
    chain, cur = [], relation
    while cur is not None:
        if cur not in RELATIONS:
            raise ValueError(f"unknown relation {cur!r}")
        chain.append(cur)
        cur = RELATIONS[cur].parent
    return chain


def relation_category(relation: str) -> str | None:
    """The top-level §4 category `relation` falls under (itself if it IS a category; None for root)."""
    for anc in relation_ancestors(relation):
        if anc in CATEGORIES:
            return anc
    return None


def relation_descendants(relation: str) -> frozenset[str]:
    """`relation` plus every relation that inherits from it (transitively). Asking for `causal`
    returns {causal, causes, enables, prevents, requires}; asking for a leaf returns just itself."""
    if relation not in RELATIONS:
        raise ValueError(f"unknown relation {relation!r}")
    out = {relation}
    changed = True
    while changed:
        changed = False
        for child, spec in RELATIONS.items():
            if spec.parent in out and child not in out:
                out.add(child); changed = True
    return frozenset(out)


def is_kind_of(relation: str, ancestor: str) -> bool:
    """True if `relation` is `ancestor` or inherits from it — the granularity test for filters."""
    return ancestor in relation_ancestors(relation)


# --- classification block builder ----------------------------------------------------------------
def new_classification(*, subject: str = "world", subtype: str | None = None, **dims) -> dict:
    """Build a props.classification block: subject + optional subtype label + any graded dimensions.
    Unknown subjects or dimension keys raise (a typo'd dim must never silently vanish)."""
    if subject not in SUBJECTS:
        raise ValueError(f"unknown subject {subject!r} (must be one of {sorted(SUBJECTS)})")
    bad = set(dims) - set(DIMENSIONS)
    if bad:
        raise ValueError(f"unknown dimension(s) {sorted(bad)} (known: {DIMENSIONS})")
    c: dict = {"subject": subject}
    if subtype:
        c["subtype"] = subtype
    c.update(dims)
    return c

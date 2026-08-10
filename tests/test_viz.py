"""The visualizer ships with the package and renders the graph the package carries."""
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def page():
    proc = subprocess.run([sys.executable, "-m", "mangrove_kb.viz"], cwd=REPO,
                          capture_output=True, text=True, timeout=600)
    assert proc.returncode == 0, proc.stderr[-2000:]
    return proc.stdout


def test_it_renders_the_whole_graph(page):
    from mangrove_kb.graph import KnowledgeGraph

    kg = KnowledgeGraph.load()
    m = re.search(r"const DATA = (\{.*?\});\s*\n", page, re.S)
    assert m, "the page carries no DATA payload"
    import json
    data = json.loads(m.group(1))
    assert len(data["nodes"]) == len(kg.nodes)
    assert len(data["edges"]) == len(kg.edges)


def test_it_is_self_contained(page):
    """No CDN, no build step -- one file that opens from disk."""
    external = re.findall(r'(?:src|href)="(https?://[^"]+)"', page)
    assert not external, f"the page fetches from the network: {external}"


def test_the_root_is_the_collapse_anchor(page):
    """Collapse is containment-reachability from one root. Without a match it silently no-ops."""
    assert 'const ANCHOR="object:mangrove-knowledge-space";' in page


def test_the_page_carries_the_mangrove_palette(page):
    """The platform's tokens, not the viewer's originals. Lifted from globals.css on origin/dev."""
    assert "--dev-accent:#42a7c6" in page and "--dev-highlight:#ff9e18" in page
    assert "--radius:0.625rem" in page


def test_no_token_three_js_reads_is_written_in_oklch(page):
    """The 3D view hands `--bg` straight to three.js, whose parser has no oklch.

    An unparseable value threw inside the bundle ("process is not defined") and the whole WebGL
    scene stopped rendering, while the DOM labels kept drawing -- so the graph looked like floating
    text with no nodes, and nothing in the page reported an error. Caught only by driving it.
    """
    blocks = [b.split("}", 1)[0] for b in page.split(":root")[1:]]
    brand = [b for b in blocks if "--dev-accent" in b or "--background" in b]
    assert brand, "no brand token block found"
    for b in brand:
        # Strip CSS comments first: the comment that EXPLAINS this fix names oklch, and matching it
        # failed the guard for the wrong reason.
        code = re.sub(r"/\*.*?\*/", "", b, flags=re.S)
        bad = [d.strip() for d in code.split(";") if "oklch(" in d]
        assert not bad, f"a token three.js may read is declared in oklch: {bad}"


def test_the_graph_is_drawn_in_brand_colours(page):
    """Node colour is the loudest thing on the page; leaving the stock palette makes the rebrand
    cosmetic. Every primitive and category colour must come from the logo's own four hues."""
    import json

    from mangrove_kb.viz.render import BRAND

    m = re.search(r'"primitiveColor": (\{.*?\})', page, re.S)
    c = re.search(r'"categoryColor": (\{.*?\})', page, re.S)
    assert m and c, "the payload carries no colour maps"
    prim, cat = json.loads(m.group(1)), json.loads(c.group(1))
    allowed = set(BRAND.values())
    used = {prim[k] for k in ("Procedure", "Concept", "Property", "Object", "Schema")}
    used |= {cat[k] for k in ("structural", "descriptive", "associative", "meta")}
    assert used <= allowed, f"off-brand colours in use: {sorted(used - allowed)}"
    assert prim["Procedure"] == "#42a7c6", "the bulk of the graph should carry the primary mark"


def test_the_real_logo_ships_in_both_variants(page):
    """A hand-drawn stand-in is not the brand. Both wordmarks, inlined so the page stays offline."""
    assert page.count("data:image/svg+xml;base64,") == 2, "expected a light and a dark wordmark"
    for variant in ("light-only", "dark-only"):
        assert f'class="logo {variant}"' in page
    # Which one shows follows the same three-state rule as the palette.
    assert ':root[data-theme="dark"] #brandbar .dark-only{display:block}' in page
    assert ':root[data-theme="light"] #brandbar .light-only{display:block}' in page


def test_all_three_theme_states_are_defined(page):
    """Light, dark and system. A colour defined in only one place is how a toggle works one way."""
    assert "@media (prefers-color-scheme:dark)" in page
    assert ':root:not([data-theme="light"])' in page, "an explicit light choice must beat a dark OS"
    assert ':root[data-theme="dark"]' in page, "an explicit dark choice must beat a light OS"
    # Every colour the dark blocks touch must also exist on bare :root -- specifically the BRAND
    # :root, not the viewer's own earlier one. Splitting on the first `:root{` found that one and
    # failed for the wrong reason.
    blocks = [b.split("}", 1)[0] for b in page.split(":root{")[1:]]
    brand = [b for b in blocks if "--dev-accent" in b]
    assert len(brand) == 1, f"expected exactly one brand :root block, found {len(brand)}"
    for token in ("--background", "--foreground", "--sidebar", "--muted-fg", "--border", "--chip-bg"):
        assert token in brand[0], f"{token} has no base definition, only a themed one"


def test_the_theme_is_set_before_first_paint(page):
    """Stamping data-theme after the stylesheet applies flashes the wrong theme on every load."""
    head = page.split("</head>", 1)[0]
    assert "mangrove-kb-theme" in head, "the pre-paint script is not in <head>"


def test_no_jarvis_vocabulary_survives(page):
    """This is a public Mangrove product; it must not show the vocabulary of the tool it came from."""
    for term in ("ACT-R",):
        assert page.count(term) == 0 or "el.textContent.includes" in page, term


def test_search_ranks_exactly_as_find_does(page):
    """One definition of search. A second one hand-written in JS would drift from kg.find()."""
    import json

    from mangrove_kb.graph import SEARCH_TIERS, KnowledgeGraph

    m = re.search(r"const IDX = (\[.*?\]);\n", page, re.S)
    assert m, "the page carries no search index"
    idx = json.loads(m.group(1))
    kg = KnowledgeGraph.load()
    assert len(idx) == len(kg.nodes)
    assert all(len(r["t"]) == len(SEARCH_TIERS) for r in idx), "a tier is missing from the export"

    # Re-run the page's ranking in Python and compare it against find() itself.
    for query in ("divergence", "rsi", "mean reversion", "histogram", "oversold"):
        q = query.lower()
        hits = [(next(i for i, h in enumerate(r["t"]) if q in h), r["id"])
                for r in idx if any(q in h for h in r["t"])]
        hits.sort()
        assert [h[1] for h in hits] == [r["id"] for r in kg.find(query, limit=None)], \
            f"the page and kg.find() disagree on {query!r}"


def test_search_says_when_it_truncates(page):
    """A short list reads as 'that is all there is'. Result.truncated exists for this reason.

    Asserting only that the message EXISTS is not enough: changing `total` to the truncated length
    leaves the message intact and the number wrong, and the guard stayed green when I tried it. So
    the count must come from the FULL result set, before the slice.
    """
    assert "showing '+hits.length+' of '+hits.total" in page, "no truncation notice"
    assert "const shown=res.slice(0,LIMIT);" in page
    assert "shown.total=res.length;" in page, \
        "the reported total must be the full match count, not the truncated one"


# --- two-level facets ----------------------------------------------------------------------------

def test_every_sub_kind_has_a_colour_and_shades_its_parent():
    """Sub-kinds are shades of their parent's hue, never new hues.

    The rail grouped 289 of 303 nodes into one "Procedure" row. Splitting it is only useful if the
    split is visible on the canvas too -- but a distinct colour per sub-kind is thirteen colours
    against a four-hue brand palette, and it loses the thing the grouping is for.
    """
    import json
    from mangrove_kb.viz.render import (CATEGORY_COLOR, DOMAIN_ID, KIND_COLOR, PRIMITIVE_COLOR,
                                        RELATION_COLOR, _kind)
    from mangrove_kb.graph import RELATIONS

    g = json.loads((REPO / "ontology" / "signal-indicator-ontology.json").read_text())
    classes = frozenset(r["from_id"] for r in g["relations"]
                        if r["rel"] == "kind-of" and r["to_id"] == DOMAIN_ID)

    kinds = {_kind(a["id"], classes) for a in g["atoms"]}
    assert kinds <= set(KIND_COLOR), f"node kinds with no colour: {sorted(kinds - set(KIND_COLOR))}"
    assert "node" not in kinds, "a node fell through to the fallback label; give its prefix a name"
    assert set(RELATIONS) == set(RELATION_COLOR), "every relation needs a colour"

    # Distinct within a parent (so the split is visible), and never equal to another parent's hue
    # (so a shade is never mistaken for a different family).
    for palette, parents in ((KIND_COLOR, PRIMITIVE_COLOR), (RELATION_COLOR, CATEGORY_COLOR)):
        assert len(set(palette.values())) == len(palette), f"two sub-kinds share a colour: {palette}"
        for name, colour in palette.items():
            clashes = [p for p, c in parents.items() if c == colour]
            assert len(clashes) <= 1, f"{name} takes a hue owned by several parents: {clashes}"


def test_the_root_and_the_domain_have_their_own_labels():
    """`Object` used to render as kind "node" -- the fallback -- and technical analysis was lumped
    in with Indicator and Signal as an "entity type". Two are layers of the domain; one IS it."""
    from mangrove_kb.viz.render import DOMAIN_ID, _kind
    assert _kind("object:mangrove-knowledge-space") == "root:knowledge-graph"
    assert _kind(DOMAIN_ID) == "domain"
    assert _kind("concept:indicator") == "entity type"
    assert _kind("procedure:indicator-rsi") == "indicator"
    assert _kind("procedure:signal-rsi-oversold") == "signal"


def test_both_facet_levels_reach_the_draw_calls(page):
    """The sub-kind colour must apply on every surface that paints, not just the rail.

    Five lookups paint: 2D edge stroke, 2D arrowhead, 2D node fill, 3D nodeColor, 3D linkColor. If
    upstream `viz.py` rewrites one, `render.py` aborts -- but only the ones it knows about, so pin
    the count here as well.
    """
    assert page.count("window.KC&&window.KC[n.kind]") == 2, "node colour: 2D fill + 3D nodeColor"
    assert page.count("window.RC&&window.RC[e.relation]") == 3, \
        "edge colour: 2D stroke + 2D arrowhead + 3D linkColor"
    assert '"kindColor"' in page and '"relationColor"' in page, "the palettes must reach the page"
    # Both levels are AND-ed in all four predicates -- 2D and 3D, nodes and edges.
    for pred in ("visN = function", "visE = function",
                 "nodeVisById = function", "linkVis3 = function"):
        assert pred in page, f"{pred} is not overridden; one surface would ignore the sub-filter"
    # Exactly the four predicates: nodes gate on `kind` in 2D and 3D, edges on
    # `relation` in 2D and 3D. A count that drifts means a surface was missed or doubled.
    assert page.count("on.kind[") == 2 and page.count("on.rel[") == 2

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


def test_only_exceptional_status_is_ringed_and_selection_grows_outward(page):
    """A ring on `ratified` is a ring on 301 of 303 nodes -- decoration, not information.

    Dropping the key makes `STATUS[n.status]` undefined for it, so the ring is skipped rather than
    drawn in the background colour. `draft` and `deprecated` keep theirs, and deprecated is yellow:
    the signal still runs, it just has a canonical replacement, and red read as broken.

    Selection is drawn at r+2.2 on its own path. A stroke is centred on its path, so stroking the
    fill circle spent half its width covering the node -- the marker shrank the thing it marked.
    """
    assert "const STATUS={draft:'--draft',deprecated:'--dep'};" in page, \
        "ratified must carry no ring"
    assert "ratified:'--rat'" not in page

    assert "--dep:var(--warn)" in page and "--warn:#eab308" in page, "deprecated rings are yellow"
    # Every colour in all three theme states, or the toggle works in one direction only.
    assert page.count("--warn:#facc15") == 2, "--warn needs a dark value under both dark selectors"

    assert "if(sc){ctx.lineWidth=1.2;" in page, "the status ring should be thin"
    assert "if(sc){ctx.lineWidth=2;" not in page

    sel = ("if(n===sel||n===hov){ctx.lineWidth=3.6;ctx.strokeStyle=cssv('--ok');"
           "ctx.beginPath();ctx.arc(n.x,n.y,r+2.2,0,6.2832);ctx.stroke();}")
    assert sel in page, "selection must be a green ring on its OWN path, outside the fill"
    assert "if(n===sel||n===hov){ctx.lineWidth=2;ctx.strokeStyle=cssv('--ink');ctx.stroke();}" \
        not in page, "the old selection stroke reused the fill path and ate the node's area"


def test_the_focused_node_labels_itself_louder(page):
    """Bigger and bold for the selected node, on the same `foc` the ring uses.

    The x-offset moves with the font: the ring's outer edge is r+4.0 and the label started at r+3,
    so a 14px label would have been printed across the ring it accompanies.
    """
    assert "ctx.font=foc?'bold 14px sans-serif':'11px sans-serif';" in page
    assert "n.x+r+(foc?6:3)" in page, "the label must clear the ring it sits beside"
    assert "ctx.font='11px sans-serif';\n      ctx.fillText" not in page, \
        "the unconditional label font is still in place; selection would look identical"


# --- the inspector's property block ---------------------------------------------------------------

def _run_in_node(page: str, driver: str, tmp_path: Path):
    """Execute the panel's formatters exactly as the browser would, over the page's own DATA.

    The overlay is deliberately pure -- no DOM, no reads of the viewer's scope -- so it can be
    eval'd here. That matters more than it sounds: the bug this block fixes was `JSON.stringify`
    turning `Infinity` into `null`, and an assertion that the SOURCE TEXT is present would have
    passed against the broken version. The only way to know is to run it on the real payload.
    """
    import json
    import shutil
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed; the panel's formatters cannot be executed")
    (tmp_path / "graph.html").write_text(page)
    (tmp_path / "d.mjs").write_text("""
import {readFileSync} from 'fs';
const page = readFileSync(process.argv[2],'utf8');
// The DATA payload is a JS literal, not JSON -- `Infinity` is a real number here, exactly as the
// browser sees it. Parsing it as JSON would destroy the very distinction under test.
globalThis.window = {};
const DATA = eval('(' + page.match(/const DATA = (\\{[\\s\\S]*?\\});\\s*\\n/)[1] + ')');
const at = page.indexOf('window.KVPROPS =');
const js = page.slice(page.lastIndexOf('<script>', at) + 8, page.indexOf('</script>', at));
eval(js);
const nodeById = id => DATA.nodes.find(n => n.id === id);
const edgesOf = t => DATA.edges.filter(e => e.type === t);
""" + driver)
    proc = subprocess.run([node, str(tmp_path / "d.mjs"), str(tmp_path / "graph.html")],
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr[-2000:]
    return json.loads(proc.stdout)


def test_the_panel_never_prints_raw_json(page, tmp_path):
    """`JSON.stringify` on `inputs`/`params`/`outputs` was a 1,400-character wall of braces.

    Every node is rendered, so a shape this file has not seen fails here rather than in someone's
    browser -- and the assertion is on the OUTPUT, not on the source of the formatter.
    """
    out = _run_in_node(page, """
const bad = [], braces = [];
for(const n of DATA.nodes){
  let h; try{ h = window.KVPROPS(n); }catch(e){ bad.push([n.id, e.message]); continue; }
  if(/\\{&quot;|\\{"/.test(h)) braces.push(n.id);          // a stringified object reached the panel
}
console.log(JSON.stringify({threw: bad, braces, count: DATA.nodes.length}));
""", tmp_path)
    assert out["threw"] == [], f"the formatter threw on {out['threw']}"
    assert out["braces"] == [], f"raw JSON still reaches the panel for {out['braces']}"
    assert out["count"] == 303


def test_unbounded_and_unauthored_are_different_things(page, tmp_path):
    """The bug that started this. `JSON.stringify([0, Infinity])` is `[0,null]`.

    SKILL.md makes the distinction load-bearing -- "unbounded is `[-inf, inf]`, not `null`" -- and
    161 endpoints in this graph are non-finite, so the panel was reporting "not authored" for all
    of them. The synthetic cases cover the endpoints the real graph has no example of.
    """
    out = _run_in_node(page, """
const R = spec => window.KVPROPS({props:{outputs:{o:{...spec, description:'d'}}}});
const cases = {
  '0..100':     R({type:'series', units:'x', range:[0,100]}),
  'lower':      R({type:'series', units:'x', range:[0,Infinity]}),
  'upper':      R({type:'series', units:'x', range:[-Infinity,100]}),
  'unbounded':  R({type:'series', units:'x', range:[-Infinity,Infinity]}),
  'bool':       R({type:'bool',   units:'boolean', range:[0,1]}),
  'unauthored': R({type:'series', units:'x', range:[null,null]}),
};
const real = {
  pband: window.KVPROPS(nodeById('procedure:indicator-bollingerbands')),
  fired: window.KVPROPS(nodeById('procedure:signal-rsi-cross-up')),
};
console.log(JSON.stringify({cases, real}));
""", tmp_path)
    c = out["cases"]
    assert "0 … 100" in c["0..100"]
    assert "≥ 0" in c["lower"], "a finite floor with an infinite ceiling reads as a floor"
    assert "≤ 100" in c["upper"]
    assert "unbounded" in c["unbounded"]
    assert "true/false" in c["bool"], "a 0/1 bool is not a numeric interval"
    assert "not authored" in c["unauthored"], "an unstated range must not read as unbounded"
    assert "not authored" not in c["unbounded"] and "unbounded" not in c["unauthored"]

    # And on the real nodes: BollingerBands' pband is the ratio that is explicitly NOT clamped.
    assert "unbounded" in out["real"]["pband"] and "≥ 0" in out["real"]["pband"]
    assert "true/false" in out["real"]["fired"]


def test_the_panel_shows_what_a_reader_asked_for_and_folds_the_rest(page, tmp_path):
    """Description, then inputs/params/outputs, then formula. Provenance behind a disclosure.

    `source_module` and `usage_example` are provenance -- SKILL.md's words are "not the answer" --
    and they used to lead the block because the dump was in insertion order.
    """
    out = _run_in_node(page, """
const bb = window.KVPROPS(nodeById('procedure:indicator-bollingerbands'));
const concept = window.KVPROPS(nodeById('concept:momentum'));
const pos = s => bb.indexOf(s);
console.log(JSON.stringify({bb, concept, order: {
  inputs: pos('>inputs<'), params: pos('>parameters<'), outputs: pos('>outputs<'),
  formula: pos('>formula<'), details: pos('<details')}}));
""", tmp_path)
    o = out["order"]
    assert -1 < o["inputs"] < o["params"] < o["outputs"] < o["formula"] < o["details"]
    bb = out["bb"]
    assert "volatility_indicators" in bb and bb.index("<details") < bb.index("volatility_indicators"), \
        "source_module is provenance; it belongs inside the fold"
    assert "BandWidth" in bb, "a canonical name that is not 'none' is the one thing worth printing"
    assert bb.count("none") == 0, "246 of 355 outputs say canonical_name 'none' -- that is noise"
    assert "warm-up <code>window - 1</code>" in bb, \
        "warmup_bars is an EXPRESSION in these params, not a bar count"
    assert "abbreviation" not in bb.lower() or "BB" in bb
    # 224 nodes have a null abbreviation and 56 a null reference. A label with nothing after it is
    # worse than no label.
    assert "null" not in bb
    # The 14 concept nodes carry no props at all: a disclosure triangle over one word is theatre.
    assert "<details" not in out["concept"] and "observed" in out["concept"]


def test_an_edge_says_which_outputs_it_uses(page, tmp_path):
    """`uses` carries the indicator outputs that flow into the signal -- 233 edges do.

    It rendered as `{"adi":{"type":"series"}}`, where the type is identical on all 233 and the
    names are the whole point.
    """
    out = _run_in_node(page, """
const e = edgesOf('uses').find(e => Object.keys(e.props.inputs || {}).length > 1)
       || edgesOf('uses')[0];
console.log(JSON.stringify({html: window.KVEDGE(e), names: Object.keys(e.props.inputs)}));
""", tmp_path)
    for name in out["names"]:
        assert f"<code>{name}</code>" in out["html"], f"the edge does not name {name}"
    assert '{"' not in out["html"] and "{&quot;" not in out["html"]


def test_the_panel_falls_back_rather_than_going_blank(page):
    """Both call sites are guarded, so a page that loses the overlay degrades to the old dump.

    The count is pinned for the same reason the colour patches are: an upstream rename would revert
    the inspector to raw JSON, which looks like nothing changed rather than like a failure.
    """
    assert page.count("window.KVPROPS?window.KVPROPS(n):kv('properties',n.props)") == 1
    assert page.count("window.KVEDGE?window.KVEDGE(e):kv('other properties'") == 1
    assert "+kv('properties',n.props)" not in page, "the unguarded call site is still in place"


def test_the_panel_is_legible_in_both_themes(page):
    """The accent is a mid teal: measured 6.47:1 on the dark panel and 2.66:1 on the light one.

    It is the token the eye lands on first -- the type of every input, param and output -- so it
    cannot be the one you have to squint at. Light gets a darkened value (measured 6.22:1) and dark
    keeps the brand accent, declared across all three theme states like every other colour here:
    an explicit choice in either direction, and the OS preference when there is none.

    Contrast itself is measured out of a real browser rather than asserted here; this pins the
    three declarations, because losing the `[data-theme="dark"]` one leaves the toggle working in
    one direction only and that is invisible until someone uses it.
    """
    assert "--kb-ty:#12667f" in page, "the light-mode type colour is missing"
    assert page.count("#inspect{--kb-ty:var(--act)}") == 2, \
        "both dark states -- the OS preference and the explicit choice -- restore the brand accent"
    assert '[data-theme="dark"] #inspect{--kb-ty:var(--act)}' in page, \
        "an explicit dark choice would fall back to the light-mode colour"
    assert ':root:not([data-theme="light"]) #inspect{--kb-ty:var(--act)}' in page, \
        "an explicit light choice on a dark OS must keep the readable colour"
    # The description IS the answer to "what is this". It was rendered in --muted, like provenance.
    assert "#inspect .kbd{color:var(--ink)" in page, "descriptions must be full-contrast body text"

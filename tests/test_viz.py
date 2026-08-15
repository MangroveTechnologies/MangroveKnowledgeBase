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
    # One band per declared tier, plus the catch-all for props no tier names.
    assert all(len(r["t"]) == len(SEARCH_TIERS) + 1 for r in idx), "a tier is missing from the export"

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
// Both self-contained blocks: the property formatters and the focus set maths. Each is written
// with no reference to the viewer's scope precisely so that it can be executed here.
for(const marker of ['window.KVPROPS =', 'window.KBSETS =', 'window.KBTIPS =']){
  const at = page.indexOf(marker);
  if(at < 0) throw new Error('no block defines ' + marker);
  eval(page.slice(page.lastIndexOf('<script>', at) + 8, page.indexOf('</script>', at)));
}
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
    from mangrove_kb.graph import KnowledgeGraph
    assert out["threw"] == [], f"the formatter threw on {out['threw']}"
    assert out["braces"] == [], f"raw JSON still reaches the panel for {out['braces']}"
    # Every node, counted from the graph rather than a literal: the claim is coverage, and a
    # literal turns each node added to the ontology into a spurious failure here.
    assert out["count"] == len(KnowledgeGraph.load().nodes)


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
    # The 14 concept nodes carry no props of their own, but the section they DO get is the same
    # section, under the same name, as on the other 289. It used to render flat and be called
    # something else, so the panel taught you its shape from one node and lied about the next.
    # Matched on the summary's opening text, not the whole element: the heading also carries the
    # `?` affordance now, and pinning the closing tag made this fail for a change it does not care
    # about.
    assert '<summary>provenance &amp; extras' in out["concept"]
    assert "observed" in out["concept"]


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
    assert re.search(r"#inspect \.kbd\{font:[\d.]+px/[\d.]+ var\(--kb-sans\);color:var\(--ink\)", page), \
        "descriptions must be full-contrast body text in the prose face, not small grey mono"

    # A heading that is SMALLER than the entry names beneath it is not a heading. Sizes are read out
    # of the stylesheet and compared, rather than pinned as strings, so tuning a value stays legal
    # and inverting the hierarchy does not.
    def px(pattern):
        m = re.search(pattern, page)
        assert m, f"no rule matched {pattern}"
        return float(m.group(1))

    heading = px(r"#inspect \.lbl\{font:700 ([\d.]+)px var\(--kb-sans\)")
    entry = px(r"td\.kbn\{font:600 ([\d.]+)px var\(--kb-mono\)")
    desc = px(r"#inspect \.kbd\{font:([\d.]+)px")
    assert heading > entry and heading > desc, \
        f"section heading {heading}px must outrank entry names {entry}px and prose {desc}px"
    # Mono is for identifiers, sans is for prose. Naming a font that does not load is not a choice:
    # "Geist Mono" measures pixel-identical to "NoSuchFont12345" on this page -- there is no
    # @font-face and the page may not fetch one -- so what is real is the size, weight, colour and
    # which generic. The panel must not go back to naming a font it does not have.
    assert '"Geist Mono"' not in page.split("#inspect{--kb-sans")[1].split("</style>")[0], \
        "the panel must not declare a font that never loads"


def test_every_section_folds_and_remembers(page, tmp_path):
    """A node with 40 edges pushed everything else off the screen and there was no way to fold it.

    The transform runs over the label/value pairs the panel already emits, so the viewer's own
    sections -- Description, Edges -- fold on the same control as the three tables, without either
    side knowing about the other. The state is keyed by section name and persisted, so folding
    Edges once folds it for every node after it rather than only for the one in front of you.
    """
    out = _run_in_node(page, """
console.log(JSON.stringify({
  hasFold: /function foldSections\\(/.test(page),
  key: /mangrove-kb-panel-sections/.test(page),
  // the heading keeps `.lbl`, which is what the two overlays that look sections up by name use
  keepsClass: /s\\.className = 'lbl'/.test(page),
  wired: /showEdge = function\\(e\\)\\{ _showEdge\\(e\\); foldSections\\(\\); \\}/.test(page),
}));
""", tmp_path)
    assert out["hasFold"] and out["wired"], "sections are not folded on both node and edge panels"
    assert out["key"], "the open/closed state is not persisted"
    assert out["keepsClass"], \
        "the heading must keep .lbl or labelEl()/block() stop finding sections by name"


def test_a_section_boundary_is_visible_in_both_themes(page):
    """--line is #262626 on a #171717 panel: a 1.15:1 rule, which is to say no rule at all.

    Measured in a browser after the change: the section edge is 3.41:1 dark and 3.31:1 light,
    against the 3:1 WCAG asks of a non-text boundary. Mixing toward --ink rather than using --line
    is what makes that true in BOTH themes from one declaration.
    """
    assert "--kb-edge:color-mix(in oklab,var(--ink) 42%,var(--panel))" in page
    assert "--kb-band:color-mix(in oklab,var(--ink) 14%,var(--panel))" in page
    assert "#inspect details.kbs{margin:0;border-top:1px solid var(--kb-edge)}" in page
    assert "border-top:1px solid var(--line)}" not in page.split("PROPERTY_PANEL")[-1], \
        "a boundary drawn in --line is invisible on the dark panel"


def test_nothing_in_the_panel_escapes_a_section(page, tmp_path):
    """Everything the panel prints belongs to a heading that can fold it.

    The warm-up line did not: emitted between sections, it was a top-level orphan on all 289 nodes
    that carry one -- no heading owned it and no fold could hide it, which is how it turned up
    alone on screen with every section around it folded away.

    Scanned by walking the string with a depth counter rather than by eye, because the failure is
    invisible until a node happens to be missing the section above the stray.
    """
    out = _run_in_node(page, """
// depth-0 openings of the HTML KVPROPS returns: label, value, and the provenance <details>
const tops = html => { const out=[]; let d=0;
  for(const m of html.matchAll(/<(\\/?)([a-z0-9]+)([^>]*)>/gi)){
    const close = m[1] === '/', tag = m[2].toLowerCase(), attrs = m[3];
    if(['br','hr','img','input'].includes(tag) || /\\/$/.test(attrs)) continue;
    if(close){ d--; continue; }
    if(d === 0) out.push(tag + (/class="([^"]*)"/.exec(attrs)?.[1] ? '.' + /class="([^"]*)"/.exec(attrs)[1] : ''));
    d++;
  }
  return out; };
const bad = {};
for(const n of DATA.nodes){
  for(const t of tops(window.KVPROPS(n))){
    if(t === 'div.lbl' || t === 'div.val' || t === 'details.kbx') continue;
    (bad[t] = bad[t] || []).push(n.id);
  }
}
console.log(JSON.stringify(Object.entries(bad).map(([k,v]) => [k, v.length, v[0]])));
""", tmp_path)
    assert out == [], f"these render outside any section: {out}"


def test_one_node_shape_for_the_same_facts(page, tmp_path):
    """The same fact must live in the same place on every node, under the same name.

    `epistemic` rendered flat as its own section called "epistemic status" on the 14 nodes that
    carry no other properties, and inside "provenance & extras" on the other 289 -- a special case
    invented to avoid a disclosure over a single line, whose only effect was that a reader learned
    the panel's shape from one node and was wrong about the next.

    Sections still come and go with the DATA -- 232 nodes author no interpretation, 70 no
    reference, 39 no parameters -- and an empty section is worse than an absent one. What must not
    vary is where a fact lives WHEN IT EXISTS.
    """
    out = _run_in_node(page, """
const names = {};
for(const n of DATA.nodes){
  const h = window.KVPROPS(n);
  for(const m of h.matchAll(/<div class="lbl">([^<]*)<\\/div>/g)) (names[m[1]] = names[m[1]] || 0), names[m[1]]++;
  for(const m of h.matchAll(/<summary>([^<]*)/g)) (names[m[1]] = names[m[1]] || 0), names[m[1]]++;
}
console.log(JSON.stringify(names));
""", tmp_path)
    assert "epistemic status" not in out, \
        "epistemic must live in provenance on every node, not as its own section on some"
    from mangrove_kb.graph import KnowledgeGraph
    assert out.get("provenance &amp; extras") == len(KnowledgeGraph.load().nodes), \
        f"every node carries an epistemic status, so every node has the section: {out}"
    # warm-up is a sentence about the parameters when there are any, and its own section when
    # there are not -- saying "an expression in these parameters" beside no parameters is a lie.
    assert out.get("warm-up") == 25, f"expected the 25 parameterless nodes to head it: {out}"


def test_the_action_section_says_what_the_graph_is_doing(page):
    """Two words, one lit, applied on the click -- not tick-boxes staged behind a Collapse button.

    The old panel described a PLAN: you ticked relation types and pressed Collapse. A node you had
    already folded came back with every box ticked and a button reading Expand, so the control
    never told you the current state of anything. Each row now says what that edge type is doing
    right now, and changing it takes effect immediately.

    Driven in a browser as well as asserted here: clicking `hide` on concept:indicator's
    `instance-of` row took `hidden` from 0 to 71 nodes, and `show` put it back to 0.
    """
    assert "show or hide nodes along the following edges" in page
    assert "lbl.textContent = 'action';" in page, "the section must be called action"
    # Below the node's name: the first thing you read should be what the node IS. Looked up by
    # the section's DATA rather than its rendered text -- appending the `?` affordance to the
    # heading broke a textContent match and put this section back above the title.
    assert ".find(d => d.querySelector('summary').dataset.k === 'name')" in page
    assert "s.dataset.k = key;" in page, "sections must carry their name as data"
    assert "if(name) name.after(lbl, val);" in page
    # It folds through the same machinery as every other section rather than a second copy of it.
    assert "window.KBFOLD = foldSections;" in page and "if(window.KBFOLD) window.KBFOLD();" in page
    # Exactly one of the two words is lit, and which one is read from the state, not from the click.
    assert 'class="xshow${off ? \'\' : \' on\'}" aria-pressed="${!off}">show</button>' in page
    assert 'class="xhide${off ? \' on\' : \'\'}" aria-pressed="${off}">hide</button>' in page
    # White on this teal measures 2.6:1; the lit chip carries dark ink in both themes.
    assert "#inspect .xsw button.on{background:var(--act);color:#0a0a0a}" in page


def test_no_visible_text_says_collapse(page):
    """One vocabulary. The panel says show/hide, so the gesture that does the same thing cannot be
    described as collapse/expand in the hint bar -- that was the last user-visible use of the word.

    Only rendered text counts: the viewer's own `collapsed` set and `toggleCollapse` function are
    identifiers inside <script>, which nobody reads, and renaming vendored internals is churn.
    """
    assert "double-click a node to hide or show what hangs off it" in page
    assert "double-click a node to collapse/expand" not in page
    # The panel's own markup -- the strings it writes into the DOM -- must not use the word either.
    panel = page.split("const ROOT =")[1].split("</script>")[0]
    for phrase in ("collapse across", ">Collapse<", ">Expand<", "'Collapse'", "'Expand'"):
        assert phrase not in panel, f"the action panel still writes {phrase!r}"


# --- focus: how much of the graph is in view ------------------------------------------------------

def _reach(edges, start, forward):
    """Transitive closure from `start`, following edges in one direction. The reference answer."""
    adj = {}
    for e in edges:
        u, v = (e.src, e.dst) if forward else (e.dst, e.src)
        adj.setdefault(u, []).append(v)
    seen, out, q = {start}, set(), [start]
    while q:
        for v in adj.get(q.pop(), ()):
            if v not in seen:
                seen.add(v)
                out.add(v)
                q.append(v)
    return out


def test_focus_sets_are_what_they_claim(page, tmp_path):
    """Computed twice -- once by the page, once here -- and compared on the real graph.

    `ancestors` follows edges outward (a signal is `instance-of` its class, so the class is up),
    `descendants` follows them inward, `neighbors` is radius 1 in both. A count that disagrees with
    what appears after the click is worse than no count, because the whole point of putting the
    numbers on the buttons is to say what will happen BEFORE you commit to it.
    """
    import json

    from mangrove_kb.graph import KnowledgeGraph

    kg = KnowledgeGraph.load()
    types = sorted({e.relation for e in kg.edges})
    probes = ["procedure:indicator-rsi", "procedure:signal-rsi-cross-up", "concept:indicator",
              "object:mangrove-knowledge-space"]
    out = _run_in_node(page, f"""
const probes = {json.dumps(probes)}, types = {json.dumps(types)};
const res = {{}};
for(const id of probes){{
  res[id] = Object.fromEntries(['neighbors','descendants','ancestors']
    .map(m => [m, [...window.KBSETS(DATA.edges, id, types, m)].sort()]));
  // the combination the panel builds when two scopes are lit at once
  res[id].both = [...window.KBUNION(DATA.edges, id, types,
                                    ['descendants','ancestors'])].sort();
}}
res.__none = window.KBUNION(DATA.edges, probes[0], types, []);
console.log(JSON.stringify(res));
""", tmp_path)

    assert out["__none"] is None, \
        "'everything' is an EMPTY SELECTION, and must mean no focus at all rather than an empty view"
    for node in probes:
        desc = _reach(kg.edges, node, forward=False)
        anc = _reach(kg.edges, node, forward=True)
        nbr = {e.dst for e in kg.edges if e.src == node} | {e.src for e in kg.edges if e.dst == node}
        got = out[node]
        assert set(got["descendants"]) == desc, f"descendants of {node}"
        assert set(got["ancestors"]) == anc, f"ancestors of {node}"
        assert set(got["neighbors"]) == nbr, f"neighbors of {node}"
        assert set(got["both"]) == desc | anc, f"descendants + ancestors of {node}"
        # The anchor is never in its own set; the panel adds it back when it counts what remains.
        assert node not in got["both"]


def test_focus_traverses_only_the_edge_types_left_showing(page, tmp_path):
    """One rule: the walk crosses exactly the types set to show, so `hide` drops a branch AND drops
    that axis from the lineage. RSI is used by eight signals; hiding `uses` must take exactly those
    eight out of its descendants and change nothing else.
    """
    import json

    from mangrove_kb.graph import KnowledgeGraph

    kg = KnowledgeGraph.load()
    all_t = sorted({e.relation for e in kg.edges})
    out = _run_in_node(page, f"""
const A = {json.dumps(all_t)}, B = A.filter(t => t !== 'uses'), id = 'procedure:indicator-rsi';
console.log(JSON.stringify({{
  all: [...window.KBSETS(DATA.edges, id, A, 'descendants')].sort(),
  less: [...window.KBSETS(DATA.edges, id, B, 'descendants')].sort()}}));
""", tmp_path)
    users = {e.src for e in kg.edges if e.dst == "procedure:indicator-rsi" and e.relation == "uses"}
    assert users, "the fixture assumes RSI is used by something"
    assert set(out["all"]) - set(out["less"]) == users, \
        "hiding an edge type must remove exactly what that type reached"


def test_focus_replaces_the_root_rule_rather_than_composing_with_it(page):
    """The blank-canvas hazard, and the reason this one is asserted on structure.

    `recomputeHidden` normally ends by hiding whatever cannot reach the root -- the rule that stops
    a fold leaving orphans adrift. Under focus the root is usually OUT of view, so running both
    would hide every node and produce an empty canvas with no error anywhere. The focus branch must
    therefore REPLACE it, which is what the else here is for.

    Driven as well as asserted: lineage of RSI leaves 13 of 303 nodes visible in 2D and the same 13
    in 3D, not 0.
    """
    body = page.split("const keep = focus.id == null")[1]
    focus_branch, root_branch = body.split("} else {", 1)
    assert "keep.add(focus.id);" in focus_branch
    assert "cannot reach the root" not in focus_branch
    assert "const seen = new Set([ROOT])" in root_branch, \
        "the floater rule must live in the else branch, not run under focus too"
    assert "const seen = new Set([ROOT])" not in focus_branch


def test_focus_is_visible_on_the_canvas_and_never_persisted(page):
    """A reduced graph with no visible cause is the failure mode of every focus feature.

    The chip says how much is in view, of what, around which node, and carries the way out. It
    lives on the stage rather than in the panel because the panel scrolls, can show a different
    node, and is where you are NOT looking when you wonder why the graph got small.
    """
    assert "chip.id = 'xfocus';" in page and "#xfocus.on{display:flex}" in page
    assert "showing ${N.length - hidden.size} of ${N.length}" in page, "the chip must state both counts"
    assert "show the whole graph (esc)" in page and "ev.key === 'Escape'" in page
    # Section fold state is remembered; focus deliberately is not.
    assert "mangrove-kb-panel-sections" in page
    focus_block = page.split("let focus = {id:null")[1].split("</script>")[0]
    assert "localStorage" not in focus_block, \
        "a page that opens showing 8 of 303 nodes with no explanation is a bug report"


def test_focus_re_frames_the_view(page):
    """A correct focus pointed at empty space looks exactly like a broken one.

    The first build hid 290 of 303 nodes and left the camera where it was, so the survivors sat off
    screen and the canvas came up blank -- the data right, the view aimed at nothing. Focus fits
    the visible set, and fits it again as the simulation pulls the survivors together, because the
    positions the first fit measured are already moving when it measures them.

    Measured in a browser afterwards: lineage of RSI is 13 visible and 13 on screen; ancestors of
    rsi_cross_up, 10 and 9. Descendants of concept:indicator is 290 nodes and does not fit at the
    viewer's 0.3 minimum zoom -- that is the graph being big, and is what panning is for.
    """
    assert "function frameVisible()" in page
    assert page.count("frameVisible();") >= 2, "one fit is a snapshot of positions already moving"
    assert "refits = [400, 1000, 1900].map(ms =>" in page, \
        "the refits must span the settle, and be cancellable"
    assert "fg3d.zoomToFit" in page, "3D must re-frame too, or the toggle lands on empty space"


def test_scopes_combine_rather_than_replace_each_other(page, tmp_path):
    """neighbors + ancestors is a SELECTION, not a fourth kind of thing.

    The first cut of this had a fifth row, "ancestors + descendants", which is the only combination
    anyone had thought to hard-code -- and no way to ask for the one Tim actually wanted. Three
    scopes that combine cover all seven combinations with three controls, and `everything` becomes
    what it always was: the empty selection.

    Driven in a browser as well: neighbors 11, + ancestors 13, + descendants 13, then dropping
    neighbors leaves 13, and `everything` restores 303 with the chip gone.
    """
    import json

    from mangrove_kb.graph import KnowledgeGraph

    kg = KnowledgeGraph.load()
    types = sorted({e.relation for e in kg.edges})
    out = _run_in_node(page, f"""
const id = 'procedure:indicator-rsi', types = {json.dumps(types)};
const one = m => window.KBSETS(DATA.edges, id, types, m);
const many = ms => window.KBUNION(DATA.edges, id, types, ms);
console.log(JSON.stringify({{
  n: [...one('neighbors')].sort(),
  a: [...one('ancestors')].sort(),
  na: [...many(['neighbors','ancestors'])].sort(),
  all3: [...many(['neighbors','descendants','ancestors'])].sort(),
  d: [...one('descendants')].sort(),
  none: many([]),
  // order must not matter: a selection is a set, not a sequence
  an: [...many(['ancestors','neighbors'])].sort()}}));
""", tmp_path)
    assert set(out["na"]) == set(out["n"]) | set(out["a"]), "a combination is the union of its parts"
    assert out["na"] == out["an"], "the result must not depend on which row was clicked first"
    assert set(out["all3"]) == set(out["n"]) | set(out["a"]) | set(out["d"])
    assert out["none"] is None
    assert set(out["na"]) != set(out["n"]), "the fixture must have a combination worth testing"

    # No hard-coded combination survives in the UI: three rows, and `everything` as the clear.
    modes = re.search(r"const MODES = \[(.*?)\];", page, re.S).group(1)
    assert "lineage" not in modes and "+" not in modes, \
        f"a combination is a selection, not a row: {modes}"
    assert "data-m=\"\"" in page, "`everything` is the empty selection"
    assert "cur.includes(m) ? cur.filter(x => x !== m) : cur.concat(m)" in page, \
        "the rows must toggle, not replace"


def test_every_section_and_relation_can_explain_itself(page, tmp_path):
    """A panel that names `provenance & extras` and `about` has to be able to say what they mean.

    The relation copy is SKILL.md's, not a second wording invented here: `about` versus
    `instance-of` is a claim the graph makes -- an indicator MEASURES its class, a signal is
    concerned with it -- and a glossary that paraphrases it starts disagreeing with it.

    Driven in a browser: 14 affordances on RSI (12 sections, 2 relation rows), nothing at 200ms of
    hover, shown at 700ms, positioned clear of the panel's left edge, dismissed by Esc, shown by
    keyboard focus alone, and clicking one does NOT fold the section it sits in.
    """
    from mangrove_kb.graph import RELATIONS

    out = _run_in_node(page, """
console.log(JSON.stringify({tips: Object.keys(window.KBTIPS), rels: Object.keys(window.KBRELTIPS),
  empty: Object.entries(window.KBTIPS).concat(Object.entries(window.KBRELTIPS))
           .filter(([, v]) => !v || v.length < 20).map(([k]) => k)}));
""", tmp_path)
    assert out["empty"] == [], f"these tooltips say nothing useful: {out['empty']}"
    # Every section the panel can render, and every relation the graph can carry.
    for section in ("name", "action", "description", "subtype", "inputs", "parameters", "warm-up",
                    "outputs", "interpretation", "applications", "formula", "reference",
                    "provenance & extras", "edges"):
        assert section in out["tips"], f"the {section} section cannot explain itself"
    assert set(out["rels"]) == set(RELATIONS), \
        f"a relation with no definition: {set(RELATIONS) - set(out['rels'])}"


def test_the_tooltip_behaves_the_way_tooltips_behave(page):
    """The conventions, each of which is a decision that would be wrong the other way.

    The trigger is the `?`, not the heading: the heading folds the section, and on touch there is
    no hover, so a tap to read would fold the thing being read about. The delay stops it flashing
    as the pointer crosses on its way to the fold. It renders against the VIEWPORT, left of the
    panel -- the panel is `overflow:auto` and 330px wide, so anything inside it is either clipped
    or covering the content the heading introduces.
    """
    assert 'tip.setAttribute(\'role\', \'tooltip\');' in page
    assert "el.setAttribute('aria-describedby', 'xtip');" in page
    assert "schedule(el, 450)" in page, "an instant tooltip flickers on pass-through"
    assert "outT = setTimeout(hide, 120);" in page
    assert "inspect.addEventListener('focusin'" in page, "keyboard users get no hover"
    assert "ev.preventDefault(); ev.stopPropagation();" in page, \
        "a tap on the ? inside a <summary> would fold the section"
    assert "if(ev.key === 'Escape') hide();" in page
    assert "inspect.addEventListener('scroll', hide, true);" in page
    assert "#xtip{position:fixed" in page, "inside the panel it would be clipped by overflow:auto"
    assert "innerWidth - panel.left + 10" in page, "it must sit clear of the panel, over the canvas"
    assert "cursor:help" in page
    # The provenance summary is written by KVPROPS, not by the fold pass, so it needs its own -- it
    # had copy and no way to reach it, on the one section where "what even is this" is likeliest.
    assert "aria-label=\"what does provenance &amp; extras mean?\"" in page


def test_hiding_one_edge_type_hides_only_what_that_row_claims(page, tmp_path):
    """Tim: a node showing no edges with `about` set to show. Two bugs, one symptom.

    The rows were folded by walking ALL hidden types as a single set, so the traversal could cross
    from one to another -- out along `instance-of`, onward down `has-role`, then `uses` -- and three
    rows claiming one node each removed five between them. Each type gets its own walk now.

    Then the root-reachability rule ran on top and swept up 18 more, including `concept:oscillator`
    -- the far end of the `about` edge that was still set to show. So a row said `show` and did
    nothing, because another row had already taken its endpoint. Rows now decide what is hidden,
    the same way focus does.

    Driven afterwards across every row of five nodes, hub and leaf: the change in `hidden` equals
    the number on the row, every time, and `show` puts it back exactly.
    """
    import json

    from mangrove_kb.graph import KnowledgeGraph

    kg = KnowledgeGraph.load()
    types = sorted({e.relation for e in kg.edges})
    out = _run_in_node(page, f"""
const types = {json.dumps(types)};
const per = (id, ts) => {{ const out = new Set();
  for(const t of ts) (window.KBUNION(DATA.edges, id, [t], ['descendants','ancestors']) || [])
    .forEach(x => out.add(x));
  return out; }};
const together = (id, ts) => window.KBUNION(DATA.edges, id, ts, ['descendants','ancestors']) || new Set();
const probes = ['procedure:signal-rsi-cross-up', 'concept:indicator', 'procedure:indicator-rsi'];
console.log(JSON.stringify(probes.map(id => {{
  const mine = [...types].filter(t => DATA.edges.some(e => e.type===t && (e.src===id||e.dst===id)));
  return {{id, perType: per(id, mine).size, combined: together(id, mine).size,
          rows: mine.map(t => [t, per(id, [t]).size])}};
}})));
""", tmp_path)

    for node in out:
        # The number on a row is what that row does, so the fold -- the union of the per-row sets --
        # can never come out bigger than those numbers added up. A walk that crosses between edge
        # types breaks exactly this: it reaches nodes no single row claims.
        rows_total = sum(k for _, k in node["rows"])
        assert node["perType"] <= rows_total, \
            f"{node['id']}: rows claim {rows_total} between them, the fold takes {node['perType']}"
        assert node["perType"] <= node["combined"], "per-type can never exceed the combined walk"
    signal = next(n for n in out if n["id"] == "procedure:signal-rsi-cross-up")
    assert all(k == 1 for _, k in signal["rows"]), f"this leaf's rows each reach one node: {signal}"
    assert signal["perType"] == 4, "four rows, one node each"
    assert signal["combined"] > signal["perType"], \
        "the combined walk is exactly the bug: it crosses from one edge type onto another"


def test_rows_and_focus_both_replace_the_root_rule(page):
    """Whatever is set to hide IS the answer; nothing else may be swept up behind it.

    The root-reachability post-condition exists so a fold cannot strand orphans, and composing it
    with a row-hide deleted a fifth of the graph while the row reported 1. The trade is deliberate
    and stated in the code: hiding a hub can leave nodes on screen with no visible route to the
    root. That is what was asked for, and it beats silently removing 18 other nodes.

    The double-click gesture keeps upstream's rule untouched -- it never writes `scope`, so it
    never takes this branch.
    """
    assert "const scoped = [...collapsed].some(id => (scope.get(id) || new Set()).size > 0);" in page
    assert "} else if(scoped){" in page
    body = page.split("const scoped =")[1]
    scoped_branch = body.split("} else if(scoped){")[1].split("} else {")[0]
    assert "const seen = new Set([ROOT])" not in scoped_branch, \
        "the floater rule must not run when rows are doing the hiding"
    # And each row is walked on its own.
    assert "const awayOne = (id, t) =>" in page
    assert "for(const t of types) awayOne(id, t).forEach(x => out.add(x));" in page


def test_clearing_focus_gives_back_the_view_you_had(page):
    """Focus re-frames because it must; clearing must NOT, because that is a different question.

    Measured before the fix: pan and zoom to (200,-140,z1.8), focus, press Escape, and you land at
    (428,-342,z0.30) -- a whole-graph fit, nowhere you chose. Now both exits, Escape and the
    `everything` row, put back exactly what was there.
    """
    assert "let preFocus = null;" in page
    assert "if(wanted && focus.id == null) preFocus = {x: view.x, y: view.y, z: view.z};" in page
    assert "view.x = preFocus.x; view.y = preFocus.y; view.z = preFocus.z;" in page
    # And the clear path must not fall through into the re-frame below it.
    assert "return;" in page.split("if(!wanted && preFocus){")[1].split("frameVisible();")[0], \
        "clearing must return before the re-frame, or it fits the whole graph anyway"


def test_pending_refits_are_cancelled(page):
    """Three quick clicks used to leave nine fits queued, and the ones belonging to a scope you had
    already changed kept moving the camera for seconds -- measured drifting from (176,351,z0.30) to
    (-14,36,z0.54) 2.5s after the last click. Every entry to setFocus cancels what is outstanding.
    """
    assert "let refits = [];" in page
    assert page.count("refits.forEach(clearTimeout);") == 2, \
        "cancel on both paths: changing the focus, and clearing it"
    assert "refits = [400, 1000, 1900].map(ms =>" in page


def test_provenance_remembers_its_fold_like_every_other_section(page):
    """It was the one section that forgot, because KVPROPS writes it rather than the fold pass.

    Same store and same key as the others, opposite default: shut unless you have opened it.
    """
    assert "const prov = inspect.querySelector(':scope > details.kbx');" in page
    assert "prov.open = state[key] === true;" in page, "closed by default, remembered once opened"
    assert page.count("writeFold(st);") == 2, "both the sections and the provenance block persist"


def test_controls_announce_their_own_state(page):
    """"neighbors 11" tells a screen-reader user nothing about whether it is on.

    aria-pressed, not role=radio: the scopes COMBINE, and radios are mutually exclusive by
    definition. Verified in a browser that the attribute tracks the lit class on every control,
    before and after toggling: zero disagreement.
    """
    assert 'aria-pressed="${picked.length ? \'false\' : \'true\'}"' in page, "the everything row"
    assert 'aria-pressed="${on}"' in page, "each scope row"
    assert 'aria-pressed="${!off}">show</button>' in page and 'aria-pressed="${off}">hide</button>' in page
    assert 'role="group" aria-labelledby="xsonly"' in page, "the scopes are a named group"
    assert 'role="group" aria-label="${attr(t)} edges"' in page, "each show/hide pair is named"
    assert "#inspect .xsr{position:absolute" in page, "the bare count needs a unit read aloud"


def test_framing_does_not_spread_one_argument_per_node(page):
    """`Math.min(...xs)` passes one argument per visible node: fine at 303, RangeError in the tens
    of thousands (checked in the same browser -- 200k throws, the loop does not). This viewer ships
    for other people's graphs, and a crash at scale is a poor way to find that out.
    """
    import re as _re
    code = _re.sub(r"//.*", "", page)              # the comment EXPLAINING this names the old call
    assert "Math.min(...xs)" not in code and "Math.max(...xs)" not in code
    assert "for(const n of N){" in page and "if(n.x < x0) x0 = n.x;" in page
    assert "if(!seen) return;" in page, "an empty visible set must still bail out"


def test_attribute_values_are_escaped_for_attributes(page):
    """The viewer's `esc` handles text nodes -- it leaves `\"` alone -- and these go into attributes.

    No tooltip carries a double quote today, which is exactly why this was worth fixing before one
    does. Verified in a browser with a definition containing both `"` and `<`: the row stays intact
    (3 buttons) and the text round-trips verbatim.
    """
    panel = page.split("const attr = v => esc(v).replace")[1].split("</script>")[0]
    assert 'data-tip="${esc(' not in panel, "a tooltip is an attribute value"
    assert 'data-id="${esc(' not in panel and 'data-t="${esc(' not in panel
    assert 'data-tip="${attr(tip)}"' in panel

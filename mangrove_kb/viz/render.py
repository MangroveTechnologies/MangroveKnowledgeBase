"""Render ONLY the signal/indicator ontology subgraph, using the vendored jarvis viewer.

Deliberately not the whole mangrove-kg graph: this is the domain ontology under discussion
(MangroveTechnologies/MangroveAI#1012), so the view is scoped to it. Same viewer, same styling,
same interactions as the full graph surface -- we reuse `viz.data_from_rows` + `viz.render_page`
rather than reimplementing a front end.

The graph itself is NOT built here. `build_signal_indicator_ontology.py` moved into the
MangroveKnowledgeBase repository, where it emits `ontology/signal-indicator-ontology.json` as the
ontology of record -- the authored values live in those nodes and are committed. A copy of the
builder stayed behind here and rotted for two days (it imported signal modules that had been
renamed, and still expected indicators that were deliberately dropped), so it was deleted rather
than kept in sync. This renderer reads the committed file directly.

Usage:
    python -m mangrove_kb.viz > signal-indicator-ontology.html

Reads the same graph `KnowledgeGraph.load()` does -- the copy inside the installed package, or the
repository's when run from a checkout. Point `MANGROVE_KB_ONTOLOGY` at a file to render that one.
"""
from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path

from ..graph import _IN_REPO, _PACKAGED, _ENV_VAR
from . import viz


def _locate_graph() -> Path:
    """The same graph `KnowledgeGraph.load()` reads, found the same way.

    Explicit env var, then the copy inside the installed package, then the repository layout --
    so `python -m mangrove_kb.viz` renders the shipped graph after a pip install, and the working
    copy from a checkout, with no arguments either way.
    """
    for candidate in ([Path(os.environ[_ENV_VAR])] if os.environ.get(_ENV_VAR) else []) + \
                     [_PACKAGED, _IN_REPO]:
        if candidate.is_file():
            return candidate
    return _PACKAGED          # reported as missing by main(), with the path it looked for


GRAPH = _locate_graph()

# The viewer's collapse/expand is containment-reachability from a single root, which it looks up by
# a hard-coded id (`ANCHOR` in viz.py, `object:self`). Every jarvis graph is ego-centric and has one;
# without a match `recomputeHidden()` bails, nothing is ever hidden, and the dead-toggle guard
# reverts every double-click -- collapse silently no-ops in both 2D and 3D.
#
# The knowledge space carries its own root, `object:mangrove-knowledge-space`, in the graph source.
# This renderer used to invent one in memory instead, along with the edges to reach it, which put a
# claim about the model in display code where nothing could query it. The model now carries the root
# and the view is pointed at it: the viewer's hard-coded id is a display problem and is fixed here,
# in the one place display problems belong.
# The viewer draws every colour through `cssv('--bg')` and friends, read live on each frame, so
# rebranding is a matter of redefining those variables rather than touching the drawing code. The
# palette is the platform's, lifted from mangrove-platform-frontend-web `src/app/globals.css` on
# origin/dev -- the same OKLCH tokens, so the graph and the app agree without a second source.
#
# Three states, matching the platform: light, dark, and system (no attribute). Each colour is
# defined on bare `:root` first, so nothing depends only on a media query; the dark values are
# then applied under `prefers-color-scheme: dark` GUARDED by `:not([data-theme="light"])` so an
# explicit light choice wins, and again under `[data-theme="dark"]` so an explicit dark choice
# wins in a light OS. Redefining a colour in only one of those three places is how a toggle ends
# up working in one direction.
BRAND_STYLE = """
<style>
  :root{
    /* The platform authors these in OKLCH. They are written here as their exact sRGB hex, because
       the 3D view hands `--bg` straight to three.js, whose colour parser understands hex/rgb/hsl
       and NOT oklch -- an unparseable value threw inside the bundle and the entire WebGL scene
       stopped rendering while the DOM labels kept drawing, so the graph looked like floating text.
       Converted, not eyeballed: oklch(0.145 0 0) is #0a0a0a. */
    --background:#ffffff; --foreground:#0a0a0a;
    --sidebar:#fafafa; --card:#ffffff;
    --muted-fg:#737373; --border:#e5e5e5; --chip-bg:#f5f5f5;
    --dev-accent:#42a7c6; --dev-highlight:#ff9e18;
    --ok:#00a63e; --bad:#e7000b;
    --radius:0.625rem;
    /* the viewer's own names, mapped onto the above */
    --bg:var(--background); --panel:var(--sidebar); --ink:var(--foreground);
    --muted:var(--muted-fg); --line:var(--border); --act:var(--dev-accent);
    /* Deprecation is a caution, not a failure -- the signal still runs, it just has a canonical
       replacement. Red read as "broken". Yellow, and dark enough to stay legible on white. */
    --warn:#eab308;
    --chip:var(--chip-bg); --rat:var(--ok); --draft:var(--dev-highlight); --dep:var(--warn);
  }
  @media (prefers-color-scheme:dark){
    :root:not([data-theme="light"]){
      --background:#0a0a0a; --foreground:#fafafa;
      --sidebar:#171717; --card:#171717;
      --muted-fg:#a1a1a1; --border:#262626; --chip-bg:#262626;
      --ok:#00bc7d; --bad:#ff6467; --warn:#facc15;
    }
  }
  :root[data-theme="dark"]{
    --background:#0a0a0a; --foreground:#fafafa;
    --sidebar:#171717; --card:#171717;
    --muted-fg:#a1a1a1; --border:#262626; --chip-bg:#262626;
    --ok:#00bc7d; --bad:#ff6467; --warn:#facc15;
  }
  html,body{font-family:Geist,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,
            "Helvetica Neue",Arial,sans-serif}
  code,#inspect .mono,.nav{font-family:"Geist Mono",ui-monospace,SFMono-Regular,Menlo,monospace}
  #rail,#inspect{background:var(--panel)}
  #rail h1{letter-spacing:-0.01em}
  .btns button,#search-box{border-radius:calc(var(--radius) - 2px)}
  .viewsel button.on,.lblsel button.on{background:var(--act);border-color:var(--act);color:#fff}

  /* top bar */
  #brandbar{display:flex;align-items:center;gap:12px;padding:10px 16px;flex:none;
            border-bottom:1px solid var(--line);background:var(--panel)}
  #brandbar .wordmark{display:flex;align-items:center;gap:9px;font-weight:600;font-size:14px;
                      letter-spacing:-0.01em;color:var(--ink)}
  #brandbar .logo{display:block;height:22px;width:auto}
  /* Which wordmark shows follows the SAME three-state rule as the palette: a base rule, a guarded
     media query, and an explicit-attribute rule. Driving it from one media query alone would leave
     the toggle showing the wrong logo. */
  #brandbar .dark-only{display:none}
  @media (prefers-color-scheme:dark){
    :root:not([data-theme="light"]) #brandbar .light-only{display:none}
    :root:not([data-theme="light"]) #brandbar .dark-only{display:block}
  }
  :root[data-theme="dark"] #brandbar .light-only{display:none}
  :root[data-theme="dark"] #brandbar .dark-only{display:block}
  :root[data-theme="light"] #brandbar .light-only{display:block}
  :root[data-theme="light"] #brandbar .dark-only{display:none}
  #brandbar .tag{color:var(--muted);font-size:12px;font-weight:400}
  #brandbar .spacer{flex:1}
  #themesel{display:inline-flex;border:1px solid var(--line);border-radius:calc(var(--radius) - 2px);
            overflow:hidden}
  #themesel button{background:transparent;border:0;color:var(--muted);cursor:pointer;
                   padding:5px 10px;font-size:12px;line-height:1;display:flex;align-items:center}
  #themesel button:hover{color:var(--ink)}
  #themesel button[aria-pressed="true"]{background:var(--act);color:#fff}
</style>
"""

def _logo_data_uri(filename: str) -> str:
    """The shipped Mangrove wordmark, inlined as a data URI.

    A data URI rather than an inline <svg>: both variants define the same `.st0`-`.st3` class names
    internally, so inlining them together would have the second one restyle the first. And an
    external <img src> would break the page's one hard promise -- that it opens from disk with no
    network.
    """
    raw = (Path(__file__).resolve().parent / "assets" / filename).read_bytes()
    return "data:image/svg+xml;base64," + base64.b64encode(raw).decode("ascii")


LOGO_LIGHT = _logo_data_uri("Mangrove-Horiz-FullColor.svg")
LOGO_DARK = _logo_data_uri("Mangrove-Horiz-FullColor-WhiteType.svg")

#: Wordmark + theme switcher. Injected as the viewer's nav slot rather than appended, so it sits
#: above the graph instead of floating over it.
BRAND_BAR = """
<div id="brandbar">
  <span class="wordmark">
    <img class="logo light-only" src="__LOGO_LIGHT__" alt="Mangrove">
    <img class="logo dark-only" src="__LOGO_DARK__" alt="Mangrove">
    <span class="tag">signal &amp; indicator knowledge graph</span>
  </span>
  <span class="spacer"></span>
  <div id="themesel" role="group" aria-label="Colour theme">
    <button data-theme-choice="light" title="Light">&#9788;</button>
    <button data-theme-choice="dark" title="Dark">&#9789;</button>
    <button data-theme-choice="system" title="Match system">&#9673;</button>
  </div>
</div>
"""

#: The switcher. `data-theme` is stamped on <html> BEFORE first paint by an inline script in the
#: head, because setting it after the stylesheet applies gives a flash of the wrong theme on every
#: load -- the same reason the platform runs a pre-hydration script.
THEME_SCRIPT = """
<script>
(function(){
  const KEY='mangrove-kb-theme';
  function apply(pref){
    const root=document.documentElement;
    if(pref==='system'){ root.removeAttribute('data-theme'); }
    else { root.setAttribute('data-theme', pref); }
    document.querySelectorAll('#themesel button').forEach(b=>
      b.setAttribute('aria-pressed', String(b.dataset.themeChoice===pref)));
    // The 2D canvas re-reads every colour each frame, so it restyles itself. The 3D scene sets
    // its background once at init, so it has to be told -- and only if it has been initialised.
    if(typeof fg3d!=='undefined' && fg3d){
      fg3d.backgroundColor(getComputedStyle(root).getPropertyValue('--bg').trim());
    }
  }
  const stored=(function(){ try{ return localStorage.getItem(KEY); }catch(e){ return null; } })();
  apply(stored||'system');
  document.querySelectorAll('#themesel button').forEach(b=>b.addEventListener('click',()=>{
    const pref=b.dataset.themeChoice;
    try{ localStorage.setItem(KEY,pref); }catch(e){}
    apply(pref);
  }));
  // A system-following page must repaint when the OS flips, not only on reload.
  if(window.matchMedia){
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{
      const cur=(function(){ try{ return localStorage.getItem(KEY);}catch(e){return null;} })()||'system';
      if(cur==='system') apply('system');
    });
  }
})();
</script>
"""

#: Runs in <head>, before the body exists, so the first paint is already the right theme.
PREPAINT = """<script>(function(){try{var p=localStorage.getItem('mangrove-kb-theme');
if(p&&p!=='system')document.documentElement.setAttribute('data-theme',p);}catch(e){}})();</script>"""

#: This viewer is general-purpose: it names every primitive and relation category jarvis's ontology
#: defines. This graph uses five primitives and four categories, so seven facet rows render with a
#: count of 0 -- offering filters that do nothing and implying the graph is missing something. And
#: ACT-R access, a cognitive-architecture signal from the tool this viewer came from, has no meaning
#: here at all. Both are removed at load: a public product should not show its author's vocabulary.
DECLUTTER = """
<script>
(function(){
  function prune(){
    let removed=0;
    document.querySelectorAll('#prims .row, #cats .row').forEach(row=>{
      const ct=row.querySelector('.ct');
      if(ct && ct.textContent.trim()==='0'){ row.remove(); removed++; }
    });
    return removed;
  }
  // The facets are built from DATA at load, so one pass after that is enough. Counts are static --
  // filtering hides nodes, it does not renumber the facets.
  prune();

  // ACT-R has no meaning outside jarvis. Say what the ring and halo mean HERE instead.
  document.querySelectorAll('#rail p.sub').forEach(el=>{
    if(el.textContent.includes('ACT-R')){
      el.textContent='Solid arrow = ordering relation (DAG). Dashed = free / fringe. '
                    +'Ring colour = status: green ratified, red deprecated.';
    }
  });
  const ph=document.querySelector('#inspect .placeholder');
  if(ph){ ph.textContent='Click any node or edge to pin its full detail here \u2014 what it computes, '
                        +'its inputs, parameters and typed outputs, and everything it connects to.'; }
  const h1=document.querySelector('#rail h1');
  if(h1){ h1.textContent='signals & indicators'; }

  // 3D nodes are drawn at nodeRelSize(4), which is a legible dot in a graph of a few dozen. At 303
  // nodes the camera pulls back far enough that they read as specks under their own labels. The 3D
  // view initialises lazily on first toggle, so this waits for it rather than assuming it exists.
  const v3d=document.getElementById('v3d');
  if(v3d) v3d.addEventListener('click',()=>{
    let tries=0;
    (function grow(){
      if(typeof fg3d!=='undefined' && fg3d && fg3d.nodeRelSize){ fg3d.nodeRelSize(7); return; }
      if(tries++ < 40) setTimeout(grow, 100);
    })();
  });
})();
</script>
"""

def search_index() -> list[dict]:
    """The corpus and ranking `KnowledgeGraph.find()` uses, precomputed for the page.

    The viewer is one static file, so search cannot call into Python at query time. The failure
    mode that matters is not "no search" -- it is a SECOND search, hand-written in JS, that ranks
    differently from `kg.find()` and drifts. So the ranking is exported rather than reimplemented:
    `SEARCH_TIERS` decides which haystack each field belongs to, `KnowledgeGraph` builds them, and
    the page scores a query by the index of the first tier it hits, exactly as `find()` does.

    `tests/test_viz.py` asserts the two agree on real queries, so a change to one that is not
    mirrored in the other fails.
    """
    from ..graph import KnowledgeGraph, haystacks

    kg = KnowledgeGraph.load()
    rows = []
    for node in kg.nodes.values():
        source = {"name": node.name, "id": node.id, "summary": node.summary, **node.props}
        rows.append({
            "id": node.id,
            "name": node.name,
            "summary": (node.summary or "")[:140],
            # One lowercased string per tier, built by the query layer itself. Tier order
            # IS rank order.
            "t": list(haystacks(source)),
        })
    rows.sort(key=lambda r: r["id"])
    return rows


#: Search box in the top bar. Ranks by which tier matched, then by id -- the same two keys, in the
#: same order, as `KnowledgeGraph.find()`. Selecting a result pins it in the inspector and centres
#: the camera on it, because a search that only tells you a thing exists has not finished the job.
#: The rail grouped nodes by ontology primitive and edges by category, and stopped there -- so 289 of
#: 303 nodes were one undifferentiated "Procedure" row, and `about` and `has-role` were both just
#: "descriptive". Both second levels were already on every node and edge (`kind`, `relation`); the
#: viewer simply never read them. This nests them: parent stays the primitive/category, child is the
#: derived kind. Thirteen node rows and eleven edge rows, not 200 -- the sub-level is the KIND of
#: thing, never the thing itself.
#:
#: Parent and child are AND-ed rather than the parent being a bulk setter for its children. Unticking
#: `Procedure` hides every procedure whatever the child boxes say, and the children grey out to show
#: it -- so the canvas can never be empty for a reason that is not visible in the rail.
FACETS = """
<style>
  #prims .row.sub, #cats .row.sub{ padding-left:1.15rem; font-size:.94em; }
  #prims .row.sub .sw, #cats .row.sub .sw{ width:.55rem; height:.55rem; border-radius:2px; }
  #prims .row.par, #cats .row.par{ font-weight:600; margin-top:.15rem; }
  #prims .row.sub input:disabled + .sw, #cats .row.sub input:disabled + .sw{ opacity:.3; }
  #prims .row.sub input:disabled ~ span, #cats .row.sub input:disabled ~ span{ opacity:.45; }
</style>
<script>
(function(){
  const KC = DATA.kindColor || {}, RC = DATA.relationColor || {};
  window.KC = KC; window.RC = RC;          // read by the draw calls, which fall back when absent

  function tree(items, parentKey, childKey){
    const t = {};
    items.forEach(x => {
      const p = x[parentKey] || 'null', c = x[childKey] || 'null';
      (t[p] = t[p] || {})[c] = (t[p][c] || 0) + 1;
    });
    return t;
  }
  const nodeTree = tree(DATA.nodes, 'primitive', 'kind');
  const edgeTree = tree(DATA.edges, 'category', 'relation');

  function row(box, cls, label, color, checked, onchange){
    const r = document.createElement('label'); r.className = 'row ' + cls;
    const cb = document.createElement('input'); cb.type = 'checkbox'; cb.checked = checked;
    const sw = document.createElement('span'); sw.className = 'sw'; sw.style.background = color;
    const tx = document.createElement('span'); tx.textContent = label;
    const ct = document.createElement('span'); ct.className = 'ct';
    cb.onchange = () => onchange(cb.checked);
    r.append(cb, sw, tx, ct);
    box.append(r);
    return {row: r, cb: cb, ct: ct};
  }

  // A child is only reachable while its parent is on; disabling says so instead of leaving a box
  // that looks live and does nothing.
  const kids = {prim: {}, cat: {}};
  function sync(store){
    Object.entries(kids[store]).forEach(([parent, list]) => {
      const live = on[store][parent];
      list.forEach(c => { c.cb.disabled = !live; });
    });
  }

  function build(boxId, t, store, childStore, palette, parentPalette){
    const box = document.getElementById(boxId);
    box.innerHTML = '';
    Object.entries(t).sort((a, b) => sum(b[1]) - sum(a[1])).forEach(([parent, children]) => {
      const p = row(box, 'par', parent === 'null' ? '(untyped)' : parent,
                    parentPalette[parent] || parentPalette['null'], on[store][parent] !== false,
                    v => { on[store][parent] = v; sync(store); wake(0.3);
                           if (mode === '3d') refresh3d(); });
      p.ct.textContent = sum(children);
      kids[store][parent] = [];
      Object.entries(children).sort((a, b) => b[1] - a[1]).forEach(([child, n]) => {
        on[childStore][child] = true;
        const c = row(box, 'sub', child === 'null' ? '(untyped)' : child,
                      palette[child] || parentPalette[parent] || parentPalette['null'], true,
                      v => { on[childStore][child] = v; wake(0.3);
                             if (mode === '3d') refresh3d(); });
        c.ct.textContent = n;
        kids[store][parent].push(c);
      });
    });
    sync(store);
  }
  const sum = o => Object.values(o).reduce((a, b) => a + b, 0);

  on.kind = {}; on.rel = {};
  build('prims', nodeTree, 'prim', 'kind', KC, DATA.primitiveColor);
  build('cats',  edgeTree, 'cat',  'rel',  RC, DATA.categoryColor);

  // Both levels must pass. Reassigning the viewer's own predicates rather than copying the draw
  // loop, so 2D, 3D and collapse all keep using one definition of "visible".
  visN = function(n){ return on.prim[n.primitive || 'null'] && on.kind[n.kind || 'null']
                             && !hidden.has(n.id); };
  visE = function(e){ return on.cat[e.category || 'null'] && on.rel[e.relation || 'null']
                             && visN(N[e.s]) && visN(N[e.t]); };
  nodeVisById = function(id){ const n = N[idx[id]];
    return !!n && on.prim[n.primitive || 'null'] && on.kind[n.kind || 'null'] && !hidden.has(id); };
  linkVis3 = function(e){ return on.cat[e.category || 'null'] && on.rel[e.relation || 'null']
                                 && nodeVisById(e.src) && nodeVisById(e.dst); };

  // The rail's all/none buttons set the parent store only; re-sync the children's enabled state
  // after they run, or "none" leaves live-looking boxes under a dead parent.
  document.querySelectorAll('.btns button[data-g]').forEach(b => {
    b.addEventListener('click', () => { sync('prim'); sync('cat'); }, false);
  });

  document.querySelectorAll('#rail p.sub').forEach(el => {
    if (el.textContent.includes('Ring colour')) {
      el.textContent = 'Shades group with their parent: the darker teal is indicators inside '
                     + 'Procedure, the darker blue is has-role inside descriptive. '
                     + 'Solid arrow = ordering relation (DAG). Dashed = free / fringe. '
                     + 'Green ring = selected. Yellow ring = deprecated; ratified is unmarked, '
                     + 'because nearly every node is.';
    }
  });
})();
</script>
"""

SEARCH_UI = """
<style>
  #searchwrap{position:relative}
  #search{width:280px;padding:6px 10px;font-size:13px;color:var(--ink);background:var(--bg);
          border:1px solid var(--line);border-radius:calc(var(--radius) - 2px);outline:none}
  #search:focus{border-color:var(--act);box-shadow:0 0 0 3px color-mix(in oklab,var(--act) 25%,transparent)}
  #search::placeholder{color:var(--muted)}
  /* right-aligned: the box sits near the right edge, so a left-aligned 420px panel hangs off
     the viewport and clips the tier badge. */
  #results{position:absolute;top:calc(100% + 6px);right:0;width:420px;max-height:60vh;overflow:auto;
           background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);
           box-shadow:0 12px 32px rgba(0,0,0,.28);z-index:60;display:none}
  #results.open{display:block}
  #results .r{padding:7px 11px;cursor:pointer;border-bottom:1px solid var(--line)}
  #results .r:last-child{border-bottom:0}
  #results .r.sel,#results .r:hover{background:color-mix(in oklab,var(--act) 16%,transparent)}
  #results .rn{font-weight:600;font-size:13px}
  #results .rs{color:var(--muted);font-size:11.5px;margin-top:1px;
               overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  #results .why{float:right;color:var(--muted);font-size:10.5px;text-transform:uppercase;
                letter-spacing:.04em}
  #results .none{padding:10px 11px;color:var(--muted)}
</style>
<script>
(function(){
  const IDX = __INDEX__;
  const WHY = ['name','abbrev','summary','detail','other'];  // parallel to haystacks()
  const LIMIT = 40;

  const bar=document.getElementById('brandbar');
  const wrap=document.createElement('span'); wrap.id='searchwrap';
  const box=document.createElement('input');
  box.id='search'; box.type='search'; box.autocomplete='off';
  // Counted from the index rather than written down: the last hard-coded number here was
  // three chapters out of date and read as a fact about the page a reader was looking at.
  box.placeholder=`Search ${IDX.length} nodes \u2014 name, formula, outputs\u2026`;
  const out=document.createElement('div'); out.id='results';
  wrap.append(box,out); bar.insertBefore(wrap, document.getElementById('themesel'));

  let hits=[], cur=-1;

  // Terms, plural/singular variants and the AND across them -- the same rules as query_terms(),
  // _variants() and rank_of() in graph.py. The page and kg.find() must answer identically.
  // Mirrors FUNCTION_WORDS and query_terms() in graph.py; the page must rank as find() does.
  const FUNCTION = new Set('also am an any are as at be been being both but by can could did do does doing done each either every for from had has have i if in into is it its may me might must my neither no not of on or our shall should so some such than that the their them then there these they this those through to too us was we were what when where whether which while who whom why will with within would you your'.split(' '));
  function terms(q){
    const w=q.toLowerCase().split(/[^a-z0-9]+/).filter(t=>t.length>=2);
    const kept=w.filter(t=>!FUNCTION.has(t));
    return kept.length?kept:w;
  }
  function variants(t){
    if(t.length<4) return [t];
    if(t.endsWith('ies')) return [t, t.slice(0,-3)+'y'];
    if(t.endsWith('es')) return [t, t.slice(0,-2), t.slice(0,-1)];
    if(t.endsWith('s')) return [t, t.slice(0,-1)];
    return [t, t+'s', t+'es'];
  }
  const STOP_SHARE = 0.4;
  function rank(q){
    let ts=terms(q);
    if(!ts.length) return Object.assign([], {total:0});
    // Where each term hit, per node -- then the same two rules find() applies: a term most of the
    // graph carries is dropped from scoring, and when nothing carries every term the best partial
    // match answers instead of nothing at all.
    const hits=IDX.map(r=>{
      const h={};
      for(const t of ts){
        const vs=variants(t);
        const tier=r.t.findIndex(x=>vs.some(v=>x.includes(v)));
        if(tier>=0) h[t]=tier;
      }
      return {r,h};
    });
    if(ts.length>1){
      const common=ts.filter(t=>hits.filter(x=>t in x.h).length > STOP_SHARE*IDX.length);
      if(common.length && common.length<ts.length){
        ts=ts.filter(t=>!common.includes(t));
        for(const x of hits) for(const t of common) delete x.h[t];
      }
    }
    const counts=hits.map(x=>Object.keys(x.h).length);
    const want = counts.includes(ts.length) ? ts.length : Math.max(...counts, 0);
    const res=[];
    if(want) for(const x of hits){
      const got=Object.values(x.h);
      if(got.length!==want) continue;
      res.push({r:x.r, missing:ts.length-got.length, tier:Math.max(...got, 0)});
    }
    // missing, then tier, then id -- identical to find()'s sort key, so the two agree on ordering.
    res.sort((a,b)=> a.missing-b.missing || a.tier-b.tier || (a.r.id<b.r.id?-1:a.r.id>b.r.id?1:0));
    const shown=res.slice(0,LIMIT);
    shown.total=res.length;                 // the list is capped; the count must not be
    return shown;
  }

  function render(){
    if(!hits.length){ out.innerHTML='<div class="none">no match</div>'; out.classList.add('open'); return; }
    // A short list reads as "that is all there is". Result.truncated exists in the library for
    // this reason; the page owes the reader the same honesty.
    const more = hits.total>hits.length
      ? '<div class="none">showing '+hits.length+' of '+hits.total
        +' \u2014 narrow the query, or use kg.find("'+esc(box.value.trim())+'", limit=None)</div>'
      : '';
    out.innerHTML = hits.map((h,i)=>
      '<div class="r'+(i===cur?' sel':'')+'" data-i="'+i+'">'
      +'<span class="why">'+WHY[h.tier]+'</span>'
      +'<div class="rn">'+esc(h.r.name)+'</div>'
      +'<div class="rs">'+esc(h.r.summary||h.r.id)+'</div></div>').join('') + more;
    out.classList.add('open');
    out.querySelectorAll('.r').forEach(el=>el.onclick=()=>pick(+el.dataset.i));
  }

  function pick(i){
    const hit=hits[i]; if(!hit) return;
    out.classList.remove('open'); box.blur();
    // Reuse the viewer's own selection path so the inspector, highlight and camera all agree.
    const n = (typeof idx!=='undefined' && idx[hit.r.id]!=null) ? N[idx[hit.r.id]] : null;
    if(!n) return;
    if(typeof sel!=='undefined') sel=n;
    if(typeof showNode==='function') showNode(n);
    // draw() does translate(w/2 + view.x) then scale(view.z), so centring a node at (n.x, n.y)
    // means view.x = -n.x * view.z -- not view.x = n.x, which lands it off-screen by the zoom.
    if(typeof view!=='undefined' && n.x!=null){
      view.z = Math.max(view.z, 1.1);
      view.x = -n.x * view.z;
      view.y = -n.y * view.z;
    }
    if(typeof mode!=='undefined' && mode==='3d' && typeof fg3d!=='undefined' && fg3d && n.x!=null){
      const d=140, r=Math.hypot(n.x,n.y,n.z||0)||1;
      fg3d.cameraPosition({x:n.x*(1+d/r), y:n.y*(1+d/r), z:(n.z||0)*(1+d/r)}, n, 900);
    }
    if(typeof wake==='function') wake(0.35);
  }

  box.addEventListener('input',()=>{
    const q=box.value.trim().toLowerCase();
    cur=-1;
    if(q.length<2){ out.classList.remove('open'); hits=[]; return; }
    hits=rank(q); render();
  });
  box.addEventListener('keydown',e=>{
    if(!out.classList.contains('open')) return;
    if(e.key==='ArrowDown'){ cur=Math.min(cur+1,hits.length-1); render(); e.preventDefault(); }
    else if(e.key==='ArrowUp'){ cur=Math.max(cur-1,0); render(); e.preventDefault(); }
    else if(e.key==='Enter'){ pick(cur<0?0:cur); e.preventDefault(); }
    else if(e.key==='Escape'){ out.classList.remove('open'); box.blur(); }
  });
  document.addEventListener('click',e=>{ if(!wrap.contains(e.target)) out.classList.remove('open'); });
  // "/" focuses search, the convention everywhere else.
  document.addEventListener('keydown',e=>{
    if(e.key==='/' && document.activeElement!==box){ box.focus(); e.preventDefault(); }
  });
})();
</script>
"""

#: The Mangrove brand palette, taken from the logo itself (`assets/Mangrove-Horiz-FullColor.svg`
#: defines exactly these four), plus two shades derived from them so nine facets can be told apart
#: without leaving the brand.
BRAND = {
    "teal":       "#42a7c6",     # the primary mark colour
    "sky":        "#74c3d5",
    "orange":     "#ff9e18",
    "ember":      "#ff4713",
    "deep_teal":  "#2b7f99",     # shade of teal
    "sun":        "#ffc266",     # tint of orange
    "bark":       "#8c570d",     # shade of orange
}

#: The viewer ships a general-purpose categorical palette -- #4e79a7, #59a14f, #e15759 -- which is
#: nobody's brand. Node colour is the single loudest thing on the page, so leaving it made the
#: rebrand cosmetic. Assigned by weight: the bulk of the graph is `Procedure`, so it takes the
#: primary mark colour, and the rarer primitives take the accents that stand out against it.
PRIMITIVE_COLOR = {
    "Procedure": BRAND["teal"],
    "Concept":   BRAND["orange"],
    "Property":  BRAND["sky"],
    "Object":    BRAND["ember"],
    "Schema":    BRAND["deep_teal"],
    # Knowledge ABOUT the concepts rather than more concepts, so both take the concept hue: a Fact
    # states what is true of one, a Judgment what to do about it. A fifth and sixth hue would have
    # said they are unrelated to what they describe, which is the opposite of how they are read.
    "Fact":      BRAND["sun"],
    "Judgment":  BRAND["bark"],
}

CATEGORY_COLOR = {
    "structural":  BRAND["teal"],
    "descriptive": BRAND["sky"],
    "associative": BRAND["orange"],
    "meta":        BRAND["ember"],
}

def _shade(hex_color: str, amount: float) -> str:
    """Lighten (``amount`` > 0) or darken (< 0) a hex colour, toward white or black.

    Sub-kinds are shades of their parent's hue rather than new hues. The alternative -- a distinct
    colour per sub-kind -- is thirteen colours competing with a four-hue brand palette, and it loses
    the thing the grouping is for: that every one of those 289 dots is a Procedure, and the signals
    are a recognisable family within it.
    """
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    t = 255 if amount > 0 else 0
    k = abs(amount)
    return "#%02x%02x%02x" % tuple(round(c + (t - c) * k) for c in (r, g, b))


#: Node sub-kind -> colour, each a shade of the primitive it belongs to. The parent's own hue goes to
#: the sub-kind a reader thinks of as the default member of it (`signal` outnumbers `indicator` 218
#: to 71, so `indicator` is the one that takes the tint).
KIND_COLOR = {
    "signal":                PRIMITIVE_COLOR["Procedure"],
    "indicator":             _shade(PRIMITIVE_COLOR["Procedure"], -0.35),
    "formula":               _shade(PRIMITIVE_COLOR["Procedure"], 0.4),
    "class":                 PRIMITIVE_COLOR["Concept"],
    "entity type":           _shade(PRIMITIVE_COLOR["Concept"], -0.35),
    "domain":                _shade(PRIMITIVE_COLOR["Concept"], 0.35),
    "role value":            PRIMITIVE_COLOR["Property"],
    "role axis":             _shade(PRIMITIVE_COLOR["Property"], -0.35),
    "quantity":              _shade(PRIMITIVE_COLOR["Property"], 0.4),
    "root:knowledge-graph":  PRIMITIVE_COLOR["Object"],
    "schema":                PRIMITIVE_COLOR["Schema"],
    "fact":                  PRIMITIVE_COLOR["Fact"],
    "judgment":              PRIMITIVE_COLOR["Judgment"],
}

#: Relation -> colour, each a shade of its category. Deliberately NOT dash: `viz.py` already spends
#: the dash pattern on acyclic-vs-free and says so in its legend, and both descriptive relations are
#: non-acyclic, so dashing would have differentiated nothing while overloading a signal that means
#: something else.
RELATION_COLOR = {
    "instance-of": CATEGORY_COLOR["structural"],
    "kind-of":     _shade(CATEGORY_COLOR["structural"], -0.35),
    "part-of":     _shade(CATEGORY_COLOR["structural"], 0.35),
    "about":       CATEGORY_COLOR["descriptive"],
    "has-role":    _shade(CATEGORY_COLOR["descriptive"], -0.35),
    "uses":        CATEGORY_COLOR["associative"],
    "supersedes":  CATEGORY_COLOR["meta"],
}

ROOT_ID = "object:mangrove-knowledge-space"
VIEWER_ANCHOR = "const ANCHOR='object:self';"

# The inspector prints a node's edges, and an edge's endpoints, as plain text -- so the one thing
# you want to do while reading them (follow one) means finding that node again by eye in the cloud.
# Make them navigable. Appended as an overlay AFTER the viewer's own script rather than edited into
# it: `vendor/jarvis_graph/viz.py` is a verbatim copy of upstream and `vendor/sync.py` overwrites it.
# The viewer's script is a classic one, so its top-level `showNode`/`showEdge`/`N`/`L`/`idx`/`sel`/
# `esc` bindings are reachable here; we call the originals and upgrade the two blocks they emit.
INSPECTOR_LINKS = """
<style>
  #inspect .xlink{cursor:pointer;text-decoration:underline;text-decoration-style:dotted;
                  text-underline-offset:2px}
  #inspect .xlink:hover{color:var(--act);text-decoration-style:solid}
  #inspect .xgrp{font:600 10px ui-monospace,monospace;letter-spacing:.08em;text-transform:uppercase;
                 opacity:.55;margin:6px 0 2px}
  #inspect .xgrp:first-child{margin-top:0}
</style>
<script>
(function(){
  const attr = s => esc(s).replace(/"/g, '&quot;');
  const node = id => `<span class="xlink xnode" data-id="${attr(id)}" \
title="show this node">${esc(id)}</span>`;
  // the label the viewer rendered, and the value block that follows it
  const labelEl = t => [...inspect.querySelectorAll('.lbl')].find(l => l.textContent === t);
  const block = t => { const l = labelEl(t); return l && l.nextElementSibling; };

  const _showNode = showNode, _showEdge = showEdge;

  showNode = function(n){
    _showNode(n);

    // The viewer's "deep link" points at jarvis's dashboard route (`/graph?node=...`) for the ego
    // view + blast radius. This page is a standalone file with no server behind it, so the link
    // 404s. A dead affordance is worse than none -- drop it.
    const dl = labelEl('deep link');
    if(dl){ const v = dl.nextElementSibling; dl.remove(); if(v) v.remove(); }

    const b = block('edges'); if(!b) return;
    const row = (e, i, out) => (out ? '\\u2192 ' : '\\u2190 ')
      + `<span class="xlink xrel" data-i="${i}" title="show this relationship">`
      + `${esc(e.type)}</span> ` + node(out ? e.dst : e.src);
    const inn = [], outg = [];
    L.forEach((e, i) => {
      if(e.dst === n.id) inn.push(row(e, i, false));
      else if(e.src === n.id) outg.push(row(e, i, true));
    });
    const grp = (t, rs) => rs.length ? `<div class="xgrp">${t}</div>` + rs.join('<br>') : '';
    const html = grp('incoming', inn) + grp('outgoing', outg);
    if(html) b.innerHTML = html;
  };

  showEdge = function(e){
    _showEdge(e);
    const b = block('from \\u2192 to');
    if(b) b.innerHTML = node(e.src) + '<br>\\u2192 ' + node(e.dst);
  };

  inspect.addEventListener('click', ev => {
    const nd = ev.target.closest('.xnode');
    if(nd){ const n = N[idx[nd.dataset.id]]; if(n){ sel = n; showNode(n); } return; }
    const rl = ev.target.closest('.xrel');
    if(rl){ const e = L[+rl.dataset.i]; if(e){ sel = e; showEdge(e); } }
  });
})();
</script>
"""

# The inspector's property block, made readable.
#
# The viewer renders any object property with `JSON.stringify`, so `inputs`, `params` and `outputs`
# arrive as raw JSON -- BollingerBands' `outputs` alone is a ~1,400-character wall of braces. Worse,
# `JSON.stringify` is LOSSY here: the page holds `range: [0, Infinity]` as real JS numbers and
# stringify writes `null` for a non-finite one, so 161 unbounded endpoints render identically to the
# 0 that were never authored. `SKILL.md` makes that distinction load-bearing -- "unbounded is
# `[-inf, inf]`, not `null`" -- and the panel was destroying it at the last step.
#
# The property space is not arbitrary JSON. Measured across all 303 nodes: three dict-of-dict keys
# with FIXED inner shapes (`inputs` {type, description} x625, `params` {type, default, min, max,
# description} x581, `outputs` {type, units, range, canonical_name, description} x355), four plain
# strings, and two that are a list on 64 nodes and a string on 7. Three known shapes is what makes
# tables possible instead of a pretty-printer.
#
# `window.KVPROPS`/`window.KVEDGE` are read at the two `kv()` CALL SITES (patched in `main()`), not
# by redefining `kv` -- an overlay cannot rebind a `const`, and the call sites are guarded so the
# panel falls back to the viewer's own dump if this script ever fails to load. Everything is a pure
# string function over `n.props`: no DOM, no viewer bindings, so `tests/test_viz.py` runs it in node
# against the real graph rather than asserting that the source text is present.
#
# Nothing is hidden. Any key these formatters do not know about still reaches the panel through the
# generic fallback at the bottom of the details block -- the invariant the original `kv` existed for.
PROPERTY_PANEL = r"""
<style>
  /* The panel had one type size (10.5-12px) and one colour (--muted) for everything, so a
     description -- the answer to "what is this" -- read exactly like the provenance beside it.
     Now the size says what OUTRANKS what: a section heading (14.5px) is bigger than an entry name
     inside it (12.5px) is bigger than nothing. Colour is mixed against --panel rather than
     `transparent`, so every value is a real opaque colour in both themes instead of depending on
     whatever happens to be painted underneath. */
  /* WHAT FONT THIS ACTUALLY RENDERS IN. `Geist` and `Geist Mono` are named in the brand style but
     no @font-face ever loads them and this page may not fetch one -- it is a single self-contained
     file with no network. Measured in the browser: a string set in "Geist Mono" is pixel-identical
     to the same string set in "NoSuchFont12345", i.e. both fall through to the generic. So the
     brand font is aspirational here, and the only typography that is real is the size, the weight,
     the colour, and WHICH GENERIC -- sans or mono. Those are what this block sets.
     Mono is for identifiers -- names you would type: `window_dev`, `mavg`, `int`, `[0, inf]`.
     Sans is for prose -- headings, descriptions, bullets. The panel used mono, small and grey, for
     both, which is why it read as one undifferentiated block of code. */
  #inspect{--kb-sans:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
           --kb-mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,"DejaVu Sans Mono",monospace;
           --kb-2:color-mix(in oklab,var(--ink) 78%,var(--panel));
           /* --line is #262626 on a #171717 panel in dark mode: a 1.15:1 rule, which is to say no
              rule at all. Section boundaries are mixed toward --ink instead so they are visible in
              BOTH themes, and each heading gets a filled band as well -- a line you have to look
              for is not a boundary. */
           --kb-rule:color-mix(in oklab,var(--ink) 22%,var(--panel));
           --kb-edge:color-mix(in oklab,var(--ink) 42%,var(--panel));
           --kb-band:color-mix(in oklab,var(--ink) 14%,var(--panel));
           /* The brand accent is a mid teal: 6.5:1 on the dark panel and 2.66:1 on the light one,
              measured. It is the token the eye lands on first, so on light it is darkened until it
              clears 4.5:1 rather than left as decoration you cannot read. Three states, like every
              other colour here -- the default is LIGHT, so a page with no `data-theme` and no OS
              preference gets the readable one. */
           --kb-ty:#12667f}
  @media (prefers-color-scheme:dark){ :root:not([data-theme="light"]) #inspect{--kb-ty:var(--act)} }
  :root[data-theme="dark"] #inspect{--kb-ty:var(--act)}
  /* Headings were 10.5px uppercase mono in a grey mixed halfway to the background -- grey on black,
     smaller than the text under them, and in the same typeface. A heading's whole job is to be the
     thing you find when you are scanning. Now: sans, 14.5px, bold, FULL --ink, sentence case, on a
     banded row with a hard edge above it -- and it is the control that folds its own section.
     Every section folds, including the viewer's own (Description, Edges), because the transform
     runs over label/value pairs rather than over my three tables. The open/closed state is
     remembered per section name, so folding Edges once folds it for every node after it. */
  #inspect h2{font:600 14px var(--kb-mono);line-height:1.35;margin-bottom:9px;color:var(--ink)}
  #inspect details.kbs{margin:0;border-top:1px solid var(--kb-edge)}
  #inspect details.kbs:first-of-type{border-top:0}
  #inspect .lbl{font:700 14.5px var(--kb-sans);letter-spacing:0;text-transform:capitalize;
                color:var(--ink);margin:16px 0 6px}
  /* The band and the pointer belong to the ones that actually FOLD. The collapse-across panel also
     emits a `.lbl`, and dressing a non-control as a control is worse than leaving it plain. */
  #inspect summary.lbl{margin:0;padding:9px 9px 9px 8px;background:var(--kb-band);cursor:pointer;
                       list-style:none;display:flex;align-items:center;gap:7px;user-select:none}
  #inspect .lbl::-webkit-details-marker{display:none}
  #inspect summary.lbl::before{content:"\25be";font-size:11px;color:var(--kb-2);width:9px;
                               flex:none;transition:transform .12s ease}
  #inspect details.kbs:not([open])>summary.lbl::before{transform:rotate(-90deg)}
  #inspect .lbl:hover{color:var(--act)}
  #inspect details.kbs>.val{padding:10px 2px 16px}
  #inspect .val{font:13px/1.6 var(--kb-sans);color:var(--ink)}
  #inspect .val.acc{color:var(--kb-2)}
  #inspect table.kbt{border-collapse:collapse;width:100%;table-layout:fixed}
  #inspect table.kbt td{vertical-align:top;padding:7px 0}
  #inspect table.kbt tr+tr td{border-top:1px solid var(--kb-rule)}
  #inspect table.kbt td.kbn{font:600 12.5px var(--kb-mono);color:var(--ink);
                            width:38%;padding-right:10px;overflow-wrap:anywhere}
  #inspect table.kbt td.kbv{overflow-wrap:anywhere}
  /* The type is the first thing you want off an entry -- series, int, bool -- so it is the one
     token in the meta line that carries a colour of its own. */
  #inspect .kbty{color:var(--kb-ty);font-weight:700}
  #inspect .kbm{font:12px var(--kb-mono);color:var(--kb-2);line-height:1.5}
  #inspect .kbd{font:12.5px/1.55 var(--kb-sans);color:var(--ink);margin-top:4px}
  /* It belongs to the parameter table above it, not to the last row in it -- without the gap it
     read as a third line of window_dev's description. */
  #inspect .kbw{margin-top:10px}
  #inspect ul.kbl{margin:4px 0 0;padding-left:18px;font:12.5px/1.6 var(--kb-sans);color:var(--ink)}
  #inspect ul.kbl li{margin:4px 0}
  #inspect pre.kbp{margin:4px 0 0;padding:9px 11px;background:var(--chip);border:1px solid var(--line);
                   border-radius:6px;color:var(--ink);font:12px/1.6 var(--kb-mono);
                   white-space:pre-wrap;overflow-wrap:anywhere}
  /* Provenance folds like every other section, and closed by default -- it is the one section
     nobody opens to answer "what is this". */
  #inspect details.kbx{margin:0;border-top:1px solid var(--kb-edge)}
  #inspect details.kbx>summary{font:700 13px var(--kb-sans);color:var(--kb-2);cursor:pointer;
                               list-style:none;padding:9px 8px;background:var(--kb-band);
                               display:flex;align-items:center;gap:7px}
  #inspect details.kbx>summary+*{margin-top:9px}
  #inspect details.kbx>summary:hover{color:var(--act)}
  #inspect details.kbx>summary::before{content:"\25be";font-size:11px;width:9px;flex:none;
                                       transition:transform .12s ease}
  #inspect details.kbx:not([open])>summary::before{transform:rotate(-90deg)}
  #inspect details.kbx .kbm{margin:5px 0;padding:0 2px}
  #inspect details.kbx pre.kbp{margin-left:2px;margin-right:2px}
</style>
<script>
(function(){
  // Self-contained on purpose: its own escaper, no reads of the viewer's scope. That is what lets
  // the test harness eval this block in node with nothing but `window` stubbed.
  const E = s => (s==null?'':(''+s)).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');
  const sec = (label, body) => body ? `<div class="lbl">${E(label)}</div><div class="val">${body}</div>` : '';

  // 2.0 not 2, 0.5 not 0.5000000000000001, and never "Infinity" -- callers handle non-finite.
  const NUM = v => typeof v === 'number' ? (Number.isInteger(v) ? String(v)
                    : String(parseFloat(v.toPrecision(6)))) : E(v);

  // The whole point of this file. `null` means NOT AUTHORED; a non-finite bound means UNBOUNDED.
  // They are different facts about an endpoint and the panel used to print both as `null`.
  const RANGE = (r, type) => {
    if(!Array.isArray(r) || r.length !== 2) return '';
    const [lo, hi] = r;
    if(type === 'bool' && lo === 0 && hi === 1) return 'true/false';   // 218 of 355 outputs
    const nlo = lo == null, nhi = hi == null;
    if(nlo && nhi) return '<span class="kbm">not authored</span>';
    // Number.isFinite is false for null too, so test null first (above) -- order matters.
    const ulo = !Number.isFinite(lo), uhi = !Number.isFinite(hi);
    if(ulo && uhi) return 'unbounded';
    if(ulo) return '≤ ' + NUM(hi);
    if(uhi) return '≥ ' + NUM(lo);
    return NUM(lo) + ' … ' + NUM(hi);
  };

  // min/max on a param are two independent optional bounds, NOT a range pair: 142 params author a
  // min and no max. `null` there means unconstrained-because-unstated, so it is simply omitted.
  const BOUNDS = (mn, mx) => mn == null && mx == null ? ''
    : mn == null ? '≤ ' + NUM(mx)
    : mx == null ? '≥ ' + NUM(mn)
    : NUM(mn) + ' … ' + NUM(mx);

  // name in the left column; the meta line and the description stacked in the right. Holds up at
  // the 330px default width, where five real columns would wrap into porridge.
  const TABLE = (dict, row) => {
    const ks = Object.keys(dict || {});
    if(!ks.length) return '';
    return '<table class="kbt">' + ks.map(k => {
      const s = dict[k] || {}, parts = row(s).filter(Boolean);
      // The first token is always the type. It gets the accent so the eye lands on "series" /
      // "int" / "bool" first; the rest of the line is supporting detail.
      const meta = parts.length
        ? `<span class="kbty">${E(parts[0])}</span>`
          + (parts.length > 1 ? ' · ' + parts.slice(1).join(' · ') : '')
        : '';
      return `<tr><td class="kbn">${E(k)}</td><td class="kbv">`
        + (meta ? `<span class="kbm">${meta}</span>` : '')
        + (s.description ? `<div class="kbd">${E(s.description)}</div>` : '')
        + '</td></tr>';
    }).join('') + '</table>';
  };

  // 64 nodes carry these as a list and 7 as a paragraph. Same field, so it renders the same way.
  // Any value at all, rendered as rows rather than serialised. Recurses, so a property this file
  // has never seen -- `chapter_variants`, whatever comes next -- reads as nested labels instead of
  // arriving as `{"a":{"b":1}}`.
  const DEEP = v => {
    if(v == null) return '';
    if(Array.isArray(v)) return v.map(x => `<div>${DEEP(x)}</div>`).join('');
    if(typeof v === 'object') return Object.entries(v)
      .map(([k, x]) => `<div style="margin-left:8px"><b>${E(k)}</b>: ${DEEP(x)}</div>`).join('');
    return E(String(v));
  };

  const BULLETS = v => Array.isArray(v)
    ? '<ul class="kbl">' + v.map(x => `<li>${E(x)}</li>`).join('') + '</ul>'
    : (v ? `<div class="kbd">${E(v)}</div>` : '');

  const CODE = v => v ? `<pre class="kbp">${E(v)}</pre>` : '';

  const LINK = u => {
    if(!u) return '';
    let host = u; try{ host = new URL(u).hostname.replace(/^www\./,''); }catch(_){}
    return `<a href="${E(u)}" target="_blank" rel="noopener" title="${E(u)}">${E(host)} →</a>`;
  };

  // Everything the panel already showed higher up, or that is provenance rather than an answer.
  const KNOWN = ['inputs','params','outputs','formula','usage_example','warmup_bars',
                 'source_module','reference','abbreviation','interpretation','applications'];

  window.KVPROPS = function(n){
    const p = (n && n.props) || {};
    let h = '';
    h += sec('inputs',  TABLE(p.inputs,  s => [s.type]));

    // Warm-up belongs INSIDE the section it talks about. Emitted between sections it was a
    // top-level orphan on all 289 nodes that carry it -- the one thing in the panel that no
    // heading owned and no fold could hide, which is exactly how it showed up when everything
    // around it was folded away. On a node with no parameters the value is a constant, so the
    // sentence that calls it an expression in them would be a lie: it gets its own section and
    // says only what is true.
    const params = TABLE(p.params, s => [s.type,
              s.default == null ? '' : 'default ' + NUM(s.default), BOUNDS(s.min, s.max)]);
    const warm = p.warmup_bars ? E(p.warmup_bars) : '';
    if(params){
      const note = warm ? `<div class="kbm kbw">warm-up <code>${warm}</code> bars`
                          + ' — an expression in these parameters</div>' : '';
      h += sec('parameters', params + note);
    } else if(warm){
      h += sec('warm-up', `<span class="kbm"><code>${warm}</code> bars</span>`);
    }
    h += sec('outputs', TABLE(p.outputs, s => [s.type,
              s.units && s.units !== 'boolean' ? E(s.units) : '', RANGE(s.range, s.type)]));
    h += sec('interpretation', BULLETS(p.interpretation));
    h += sec('applications',   BULLETS(p.applications));
    h += sec('formula',        CODE(p.formula));
    h += sec('reference',      LINK(p.reference));

    // Provenance and the long-tail: real, occasionally wanted, never the answer to "what is this".
    let x = '';
    if(p.source_module) x += `<div class="kbm">module <code>${E(p.source_module)}</code></div>`;
    if(p.abbreviation)  x += `<div class="kbm">abbreviated <b>${E(p.abbreviation)}</b></div>`;
    // Confidence is null on every node in this graph, so it is printed only if one ever carries it.
    if(n && n.epistemic) x += `<div class="kbm">epistemic <b>${E(n.epistemic)}</b>`
      + (n.conf == null ? '' : ' · confidence ' + NUM(n.conf)) + '</div>';
    // 246 of 355 outputs say "none"; printing those is noise, and the 109 real ones are the ones a
    // reader is looking for when they ask what the literature calls this line.
    const cn = Object.entries(p.outputs || {})
      .filter(([, s]) => s && s.canonical_name && s.canonical_name !== 'none')
      .map(([k, s]) => `${E(k)} → ${E(s.canonical_name)}`);
    if(cn.length) x += `<div class="kbm">known as ${cn.join(' · ')}</div>`;
    if(p.usage_example) x += '<div class="kbm" style="margin-top:6px">usage</div>'
      + CODE(p.usage_example);
    // Anything this file has never heard of, verbatim. The panel hides nothing -- and `verbatim`
    // means readable: `JSON.stringify` on a nested value put `{"formula":"TR = max(..."}` in front
    // of a reader, which is the wall of braces this panel exists to have removed.
    for(const [k, v] of Object.entries(p)){
      if(KNOWN.includes(k) || v == null) continue;
      x += `<div class="kbm"><b>${E(k)}</b>: ${DEEP(v)}</div>`;
    }
    // ONE name for this section on every node. It used to render flat, as "epistemic status", when
    // the node had nothing else -- a special case I invented to avoid a disclosure over a single
    // line, and the only thing it achieved was that 14 nodes disagreed with the other 289 about
    // what the section is called and where the same fact lives.
    // This summary is written here rather than by the fold pass, so it needs its own `?` -- it had
    // copy and no way to reach it, which is the one section where "what even is this" is likeliest.
    const ptip = (window.KBTIPS || {})['provenance & extras'];
    if(x) h += '<details class="kbx"><summary>provenance &amp; extras'
      + (ptip ? `<button type="button" class="xtip" data-tip="${E(ptip)}" `
                + 'aria-label="what does provenance &amp; extras mean?">?</button>' : '')
      + `</summary>${x}</details>`;
    return h;
  };

  // `uses` carries WHICH outputs of the indicator flow into the signal. As raw JSON that read
  // `{"adi":{"type":"series"}}`; the type is the same on all 233 and says nothing.
  window.KVEDGE = function(e){
    const p = (e && e.props) || {};
    let h = '';
    if(p.why) h += sec('why', `<span class="kbd">${E(p.why)}</span>`);
    const io = Object.keys(p.inputs || {});
    if(io.length) h += sec('inputs used', io.map(k => `<code>${E(k)}</code>`).join(' '));
    let rest = '';
    for(const [k, v] of Object.entries(p)){
      if(['because','state','note','why','inputs'].includes(k) || v == null) continue;
      rest += `<div class="kbm"><b>${E(k)}</b>: ${DEEP(v)}</div>`;
    }
    return h + (rest ? sec('other properties', rest) : '');
  };

  // --- folding -------------------------------------------------------------------------------
  // Every section becomes a <details>, driven by the label/value pairs the panel already emits --
  // so the viewer's own blocks (Description, Edges, and the 40-edge lists that pushed everything
  // else off screen) fold on exactly the same control as mine, without either of us knowing about
  // the other. The heading keeps its `.lbl` class, so `labelEl(t).nextElementSibling` still finds
  // the value block for the two overlays that look sections up by name.
  const FOLD_KEY = 'mangrove-kb-panel-sections';
  const readFold = () => { try{ return JSON.parse(localStorage.getItem(FOLD_KEY)) || {}; }
                           catch(e){ return {}; } };
  const writeFold = s => { try{ localStorage.setItem(FOLD_KEY, JSON.stringify(s)); }catch(e){} };

  function foldSections(){
    const state = readFold();
    // Only top-level labels: the ones already inside a <details> have been folded on a previous
    // pass, and the panel is rebuilt from scratch on every click anyway.
    for(const l of [...inspect.querySelectorAll(':scope > .lbl')]){
      const v = l.nextElementSibling;
      if(!v || !v.classList.contains('val')) continue;
      const key = l.textContent.trim().toLowerCase();
      const d = document.createElement('details');
      d.className = 'kbs';
      d.open = state[key] !== false;                       // open unless folded before
      const s = document.createElement('summary');
      s.className = 'lbl';                                 // keep the class the lookups use
      s.textContent = l.textContent;
      // The section's name as DATA. Reading it back off `textContent` breaks the moment anything
      // else is appended to the heading -- adding the `?` put the Action section back above the
      // title, because the lookup for "name" was suddenly looking at "name?".
      s.dataset.k = key;
      // The help affordance rides on the heading rather than replacing it as the hover target:
      // the heading folds, the `?` explains, and neither does the other's job by accident.
      const copy = (window.KBTIPS || {})[key];
      if(copy){
        const q = document.createElement('button');
        q.type = 'button';
        q.className = 'xtip';
        q.dataset.tip = copy;
        q.setAttribute('aria-label', 'what does ' + key + ' mean?');
        q.textContent = '?';
        s.append(q);
      }
      l.replaceWith(d);
      d.append(s, v);
      d.addEventListener('toggle', () => { const st = readFold(); st[key] = d.open; writeFold(st); });
    }
    // The provenance block is written by KVPROPS as its own <details>, so the loop above never sees
    // it -- and it was the one section that forgot its state the moment you clicked another node,
    // while every other section remembered. Same store, same key, opposite default: it stays shut
    // unless you have opened it, because it is the section nobody opens to answer "what is this".
    const prov = inspect.querySelector(':scope > details.kbx');
    if(prov){
      const key = 'provenance & extras';
      prov.open = state[key] === true;
      prov.addEventListener('toggle', () => {
        const st = readFold(); st[key] = prov.open; writeFold(st);
      });
    }
  }

  // The viewer prints `epistemic · confidence` near the top, where confidence is null on every node
  // in this graph -- it rendered as the words "observed ·" with nothing after them. It now sits in
  // the details block above, so drop the original rather than show it twice.
  //
  // This wrapper is registered before the collapse panel's and the back button's, so it runs LAST
  // (each calls the one it captured) -- the panel is fully built by the time sections are folded.
  if(typeof showNode === 'function'){
    const _showNode = showNode, _showEdge = showEdge;
    showNode = function(n){
      _showNode(n);
      const l = [...inspect.querySelectorAll('.lbl')]
        .find(x => x.textContent === 'epistemic · confidence');
      if(l){ const v = l.nextElementSibling; l.remove(); if(v) v.remove(); }
      foldSections();
    };
    showEdge = function(e){ _showEdge(e); foldSections(); };
    // The action panel is inserted by a LATER wrapper, i.e. after this one has already folded
    // everything into <details>. It hands its own label/value pair back through here so there is
    // one definition of what a section is, rather than two that drift.
    window.KBFOLD = foldSections;
  }
})();
</script>
"""

# Tooltips.
#
# The panel names things the reader has no way to look up from inside it: a section called
# `provenance & extras`, an edge type called `about` that means something precise and unobvious
# (a signal is ABOUT its class; an indicator is an INSTANCE of it -- SKILL.md's distinction, and
# the copy here is taken from there rather than invented).
#
# How it behaves, and why:
#   * The trigger is a `?`, not the heading. The heading is already a control -- it folds the
#     section -- and on touch there is no hover at all, so making the heading the trigger means a
#     tap to read the tip folds the thing you were reading about. The `?` is tab-focusable, tap-
#     targetable, and dim until you approach it.
#   * 450ms in, 120ms out. Instant tooltips flicker as the pointer crosses on its way somewhere
#     else; a deliberate pause is what asks for one.
#   * Anchored to the trigger, not the cursor. A bubble that chases the mouse is noise.
#   * Rendered against the viewport, to the LEFT of the panel and over the canvas. The panel is
#     `overflow:auto` and 330px wide by default: anything inside it is either clipped at the edge
#     or covering the very content the heading introduces.
#   * `role="tooltip"` + `aria-describedby`, shows on keyboard focus, Esc dismisses, one at a time,
#     and it goes away on scroll, on click and whenever the panel is rebuilt.
# The tooltip copy, in its own block with no DOM in it, so the tests can read it in node and check
# that every section the panel renders and every relation the graph carries can explain itself.
TIP_COPY = """
<script>
// Each says what the thing is and what it is for, and never restates its label. Relation copy is
// SKILL.md's wording: those are load-bearing definitions, and a second wording of them here would
// drift from the thing it describes.
window.KBTIPS = {
  'name': 'The name this computation goes by in code -- what you import, or pass to the registry '
    + 'when you call it.',
  'action': 'Controls how much of the graph you see around this node. Use it to isolate one '
    + 'computation -- just what it touches, everything it is built from, everything built on it -- '
    + 'or to drop edge types you do not care about. Each option says how many nodes it leaves.',
  'description': 'What this computation does, in one sentence. Read it first to decide whether '
    + 'this is the one you want.',
  'subtype': 'The family this belongs to: averaging, momentum, oscillator, volatility, flow or '
    + 'pattern. Use it to find siblings that do a similar job.',
  'inputs': 'The price series this reads, and what each one is for. You supply them as columns -- '
    + 'close, high, volume.',
  'parameters': 'The settings you pass when you call it, with the default and the range each '
    + 'accepts. Tune these to your timeframe and instrument.',
  'warm-up': 'How many bars this needs before its first valid value. Feed it fewer and the leading '
    + 'rows come back empty.',
  'outputs': 'What this returns, with units and the range each value can take. Check it before you '
    + 'plot a series, threshold it, or compare two of them.',
  'interpretation': 'What the values mean in practice -- what a high reading, a low one, or a '
    + 'crossing is telling you about the market.',
  'applications': 'What this is good for in a strategy, and the conditions it suits.',
  'formula': 'The calculation itself, as stated in the source. Use it to check the implementation '
    + 'against the definition you already know.',
  'reference': 'The published description this implementation follows, for when you want the '
    + 'original rather than ours.',
  'provenance & extras': 'Where this lives in the code, a call you can copy, and how the entry '
    + 'itself was recorded.',
  'edges': 'Every relationship this node has, incoming and outgoing. Click one to jump to the node '
    + 'on the other end.',
};
// What each relation ASSERTS, and what you would follow it for. These are SKILL.md's distinctions:
// `about` versus `instance-of` is a claim the graph makes, and a second wording of it here would
// start disagreeing with the thing it describes.
window.KBRELTIPS = {
  'instance-of': 'Says this indicator measures that class -- RSI measures momentum. Follow it to '
    + 'find every indicator of a given kind.',
  'about': 'Says this signal is concerned with that class without measuring it. It is how a '
    + 'boolean signal carries a class, and it comes from the indicator the signal reads.',
  'kind-of': 'Says this is a subtype of that. Anything true of the parent is true here, so it '
    + 'carries down.',
  'part-of': 'Says this is a component of that -- how the graph groups pieces into a whole.',
  'has-role': 'The part this plays in a strategy: trigger or filter. A role is not a type -- the '
    + 'same computation can play a different part in another strategy.',
  'uses': "Says this reads the other computation, and names which of its outputs flow in. Follow "
    + "it to see what a signal is built from.",
  'supersedes': 'Says this replaces the other, which is deprecated. The old one still runs; this '
    + 'is the canonical version.',
};
</script>
"""

TOOLTIPS = """
<style>
  #inspect .xtip{margin-left:auto;flex:none;width:16px;height:16px;padding:0;border-radius:50%;
                 border:1px solid var(--kb-edge);background:transparent;color:var(--kb-2);
                 font:700 10px var(--kb-sans);line-height:14px;cursor:help;opacity:.5}
  #inspect .xtip:hover,#inspect .xtip:focus-visible{opacity:1;color:var(--act);border-color:var(--act)}
  #inspect .xtip:focus-visible{outline:2px solid var(--act);outline-offset:2px}
  #inspect .xrow .xtip{margin-left:0}
  #xtip{position:fixed;z-index:20;display:none;max-width:290px;padding:9px 11px;
        border:1px solid var(--kb-edge,var(--line));border-radius:var(--radius);
        background:var(--panel);color:var(--ink);font:12.5px/1.5 var(--kb-sans,system-ui);
        box-shadow:0 4px 16px rgba(0,0,0,.28)}
  #xtip.on{display:block}
  #xtip code{font:11.5px var(--kb-mono,ui-monospace);background:var(--chip);padding:0 4px;
             border-radius:3px}
</style>
<script>
(function(){
  const tip = document.createElement('div');
  tip.id = 'xtip';
  tip.setAttribute('role', 'tooltip');
  document.body.append(tip);

  let inT = null, outT = null, anchor = null;

  function place(el){
    tip.textContent = el.dataset.tip;
    tip.className = 'on';                       // measure only once it is laid out
    const r = el.getBoundingClientRect(), panel = inspect.getBoundingClientRect();
    tip.style.right = Math.max(8, innerWidth - panel.left + 10) + 'px';
    const top = r.top + r.height / 2 - tip.offsetHeight / 2;
    tip.style.top = Math.max(8, Math.min(innerHeight - tip.offsetHeight - 8, top)) + 'px';
    el.setAttribute('aria-describedby', 'xtip');
    anchor = el;
  }
  function hide(){
    clearTimeout(inT); clearTimeout(outT);
    tip.className = '';
    if(anchor){ anchor.removeAttribute('aria-describedby'); anchor = null; }
  }
  function schedule(el, delay){
    clearTimeout(inT); clearTimeout(outT);
    inT = setTimeout(() => place(el), delay);
  }

  inspect.addEventListener('mouseover', ev => {
    const el = ev.target.closest('[data-tip]');
    if(el && el !== anchor) schedule(el, 450);
  });
  inspect.addEventListener('mouseout', ev => {
    if(!ev.target.closest('[data-tip]')) return;
    clearTimeout(inT);
    outT = setTimeout(hide, 120);
  });
  // Keyboard and touch. A tap on the `?` inside a <summary> would fold the section, so the default
  // is cancelled here -- the button is a help affordance, not a second fold control.
  inspect.addEventListener('focusin', ev => {
    const el = ev.target.closest('[data-tip]');
    if(el) schedule(el, 0);
  });
  inspect.addEventListener('focusout', hide);
  inspect.addEventListener('click', ev => {
    const el = ev.target.closest('.xtip');
    if(!el) return;
    ev.preventDefault(); ev.stopPropagation();
    if(anchor === el) hide(); else place(el);
  }, true);
  inspect.addEventListener('scroll', hide, true);
  addEventListener('keydown', ev => { if(ev.key === 'Escape') hide(); });
  addEventListener('resize', hide);
})();
</script>
"""

# The set maths behind `show only`, kept in its own block with no reference to the viewer's scope.
#
# It takes its edges as an argument rather than reading `L`, which is the whole point: the test
# harness evaluates this script in node and runs it over the page's own DATA payload, then compares
# every answer against the same traversal written independently in Python. A count on a button that
# disagrees with what happens after the click is worse than no count at all.
FOCUS_SETS = """
<script>
// Nodes to KEEP around `id`, excluding the anchor itself, for ONE primitive scope. `null` means no
// focus at all -- which is not the same as an empty set, and the difference decides whether the
// canvas shows everything or nothing. Direction is the graph's own: a signal is `instance-of` its
// class, so classes are UP. Combinations are unions of these, see KBUNION below.
window.KBSETS = function(edges, id, types, mode){
  if(mode === 'all') return null;
  const T = types instanceof Set ? types : new Set(types);
  const inBy = {}, outBy = {};
  for(const e of edges){
    if(!T.has(e.type)) continue;
    (inBy[e.dst] = inBy[e.dst] || []).push(e.src);      // child --rel--> parent
    (outBy[e.src] = outBy[e.src] || []).push(e.dst);
  }
  const walk = adj => {
    const out = new Set(), seen = new Set([id]), q = [id];
    while(q.length){
      const u = q.shift();
      for(const v of (adj[u] || [])){
        if(seen.has(v)) continue;
        seen.add(v); out.add(v); q.push(v);
      }
    }
    return out;
  };
  if(mode === 'neighbors') return new Set([...(inBy[id] || []), ...(outBy[id] || [])]);
  if(mode === 'descendants') return walk(inBy);
  if(mode === 'ancestors') return walk(outBy);
  return null;
};

// The union of any combination -- neighbors + ancestors, all three, whatever is lit. There is no
// separate "ancestors + descendants" mode because a combination is not a fourth kind of thing; an
// empty selection is `everything`, which is no focus at all rather than an empty view.
window.KBUNION = function(edges, id, types, modes){
  if(!modes || !modes.length) return null;
  const out = new Set();
  for(const m of modes){
    const s = window.KBSETS(edges, id, types, m);
    if(s) s.forEach(x => out.add(x));
  }
  return out;
};
</script>
"""

# The Action section: how much of the graph is in view, and along which edges.
#
# Two controls, coarse first. `show only` picks how much graph is in view around this node:
# neighbors, descendants, ancestors -- combinable, so all seven combinations come out of three
# rows, and selecting none is `everything`. `show or hide` prunes edge types within that. ONE RULE
# ties them together, and it is Tim's: the walk traverses exactly the edge types currently set to
# show, so a row set to `hide` drops that branch AND drops that axis from the walk. Each row hides
# only what its own count claims -- one walk per type, never a combined one, and whatever is set to
# hide IS the answer (the root-reachability rule is skipped, as it is under focus). Every count is
# recomputed from the live type set, so the numbers always describe what the button will do.
#
# The set maths is exposed as `window.KBSETS` (one scope) and `window.KBUNION` (a combination) --
# pure, taking their edges as an argument rather than reading the viewer's `L` -- so
# `tests/test_viz.py` executes them in node against the real graph and compares every answer with
# the same traversal written independently in Python, instead of asserting that the source looks
# right.
#
# The floater rule is the hazard here. `recomputeHidden` normally ends by hiding anything that
# cannot reach the root, which is what keeps a fold from leaving orphans adrift. Under focus the
# root is usually OUT of view, so that rule would hide the entire graph -- a blank canvas with no
# error. Focus therefore REPLACES that post-condition rather than composing with it, and there is a
# test that fails on a blank canvas.
ACTION_PANEL = """
<style>
  #inspect .xintro{font:12.5px/1.55 var(--kb-sans);color:var(--kb-2);margin:0 0 7px}
  #inspect .xintro+.xintro{margin-top:16px}
  #inspect .xrow{display:flex;align-items:center;gap:9px;padding:6px 0}
  #inspect .xrow+.xrow{border-top:1px solid var(--kb-rule)}
  #inspect .xname{font:600 12.5px var(--kb-mono);color:var(--ink);overflow-wrap:anywhere}
  #inspect .xn{font:11.5px var(--kb-mono);color:var(--kb-2);margin-left:auto;flex:none}
  /* Two words, one lit. A checkbox says "ticked/unticked" and leaves you to work out which way
     round that is; show|hide says what the graph is doing right now, in the words themselves. */
  #inspect .xsw{display:inline-flex;flex:none;border:1px solid var(--kb-edge);border-radius:5px;
                overflow:hidden}
  #inspect .xsw button{font:600 11px var(--kb-sans);padding:3px 9px;border:0;cursor:pointer;
                       background:transparent;color:var(--kb-2);letter-spacing:.01em}
  #inspect .xsw button+button{border-left:1px solid var(--kb-edge)}
  #inspect .xsw button:hover{color:var(--ink)}
  /* Dark ink on the lit chip in both themes: white on this teal measures 2.6:1. */
  #inspect .xsw button.on{background:var(--act);color:#0a0a0a}
  #inspect .xsw button.on.xhide{background:var(--dev-highlight);color:#0a0a0a}
  #inspect .xnone{font:12.5px/1.55 var(--kb-sans);color:var(--kb-2)}
  /* Read aloud, never drawn: "neighbors 11" alone does not say 11 of what. */
  #inspect .xsr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);
                white-space:nowrap}
  /* The scope rows are a radio, not toggles: these views are mutually exclusive and `everything`
     is the way back. The whole row is the control -- a 5-option segmented strip wraps into
     porridge at the 330px default width, and the counts have nowhere to live. */
  #inspect button.xfrow{display:flex;align-items:center;gap:9px;width:100%;padding:6px 8px;
                        border:0;border-left:2px solid transparent;background:transparent;
                        cursor:pointer;text-align:left;font:inherit}
  #inspect button.xfrow+button.xfrow{border-top:1px solid var(--kb-rule)}
  #inspect button.xfrow:hover:not(:disabled){background:var(--kb-band)}
  #inspect button.xfrow.on{background:var(--kb-band);border-left-color:var(--act)}
  #inspect button.xfrow:disabled{cursor:default;opacity:.45}
  #inspect button.xfrow .xdot{width:9px;height:9px;flex:none;border-radius:50%;
                              border:1px solid var(--kb-edge)}
  #inspect button.xfrow.on .xdot{background:var(--act);border-color:var(--act)}
  /* Focus is a change to the whole canvas, so its indicator lives ON the canvas -- the panel can
     be scrolled away or showing a different node entirely. Without this a reduced graph has no
     visible cause and no way back. */
  #xfocus{position:absolute;left:12px;top:12px;z-index:6;display:none;align-items:center;gap:9px;
          padding:6px 10px;border:1px solid var(--kb-edge,var(--line));border-radius:var(--radius);
          background:var(--panel);color:var(--ink);font:12px var(--kb-sans,system-ui);
          box-shadow:0 2px 10px rgba(0,0,0,.18)}
  #xfocus.on{display:flex}
  #xfocus b{font:600 12px ui-monospace,monospace}
  #xfocus .xfx{border:0;background:transparent;color:var(--act);cursor:pointer;font:600 12px inherit;
               padding:0 2px}
  #xfocus .xfx:hover{text-decoration:underline}
</style>
<script>
(function(){
  const ROOT = __ROOT__;
  // Attribute-safe: the viewer's `esc` handles text nodes, not `attr="..."` values.
  const attr = v => esc(v).replace(/"/g, '&quot;');
  const scope = new Map();                       // node id -> Set of relation types set to `hide`
  let focus = {id:null, mode:'all'};             // never persisted: a page that opens showing 8 of
                                                 // 303 with no explanation is a bug report

  // relation types incident to a node, and which way they point from it
  function incident(id){
    const m = new Map();
    for(const e of L){
      if(e.dst !== id && e.src !== id) continue;
      const v = m.get(e.type) || {inn:0, out:0};
      (e.dst === id ? v.inn++ : v.out++); m.set(e.type, v);
    }
    return m;
  }
  const ALL_TYPES = [...new Set(L.map(e => e.type))];
  // Everything hidden along one edge type is everything that way FROM this node, in whichever
  // direction(s) the type is incident here -- both lineages, so a row works on a leaf too, where
  // every edge points outward and the old panel could only say "nothing hangs off this node".
  // ONE ROW AT A TIME. Walking the hidden types as a single set lets the traversal cross from one
  // to another -- out along `instance-of`, then onward down `has-role`, then `uses` -- so three
  // rows claiming one node each removed five between them. A row's count has to be what that row
  // does, so each type gets its own walk and the results are unioned.
  const awayOne = (id, t) =>
    window.KBUNION(L, id, [t], ['descendants', 'ancestors']) || new Set();
  const away = (id, types) => {
    const out = new Set();
    for(const t of types) awayOne(id, t).forEach(x => out.add(x));
    return out;
  };
  // What the walk may cross: everything except the types this node has set to hide. Tim's rule.
  const live = id => { const off = scope.get(id) || new Set();
                       return new Set(ALL_TYPES.filter(t => !off.has(t))); };

  // Two ways in, and they must not be confused:
  //   * double-click keeps UPSTREAM's rule exactly -- containment-reachability, folding only what is
  //     reachable SOLELY through the node. `Indicator` folds 75; `RSI`, `trigger` and `filter` fold
  //     nothing, because their children have a second parent. Unchanged behaviour, deliberately.
  //   * the panel hides along the chosen relation types, which is the only way to fold a
  //     cross-cutting axis. A node folded that way has an entry in `scope`.
  recomputeHidden = function(){
    const h = new Set();
    collapsed.forEach(id => {                    // panel folds: type-scoped
      const t = scope.get(id); if(t && t.size) away(id, t).forEach(x => h.add(x));
    });
    const keep = focus.id == null ? null
                 : window.KBUNION(L, focus.id, live(focus.id), focus.modes);
    // Is any row set to `hide`? Then those rows decide what is hidden, and the root-reachability
    // rule below is skipped -- for the same reason focus skips it, and it took Tim reporting a
    // node with no edges to see it. Hiding one signal's `uses` claimed 1 node and removed 21: the
    // three endpoints the rows named, plus 18 the floater rule swept up behind them, INCLUDING the
    // far end of the `about` edge that was still set to show. So a row's count lied, and a row set
    // to show did nothing, because a different row had already taken its endpoint away.
    //
    // The trade is deliberate: hiding a hub can now leave nodes on screen with no visible route to
    // the root. That is what the user asked for, and it is honest -- the alternative silently
    // deletes a fifth of the graph and reports 1.
    const scoped = [...collapsed].some(id => (scope.get(id) || new Set()).size > 0);
    if(keep){
      // Focus REPLACES the root-reachability post-condition below. Composing them would hide the
      // whole graph, because the root is normally outside the focused set.
      keep.add(focus.id);
      N.forEach(n => { if(!keep.has(n.id)) h.add(n.id); });
      collapsed.forEach(id => { if(keep.has(id)) h.delete(id); });
      h.delete(focus.id);
    } else if(scoped){
      collapsed.forEach(id => h.delete(id));     // the rows are the whole answer
    } else {
      if(idx[ROOT] != null){                     // upstream's rule, and the floater post-condition
        const seen = new Set([ROOT]), q = [ROOT];
        while(q.length){
          const u = q.shift();
          if(collapsed.has(u)) continue;         // never traverse THROUGH a collapsed node
          (cadj[u] || []).forEach(v => { if(h.has(v) || seen.has(v)) return; seen.add(v); q.push(v); });
        }
        N.forEach(n => { if(!seen.has(n.id)) h.add(n.id); });
      }
      collapsed.forEach(id => h.delete(id));     // a collapsed node is never hidden by its own fold
    }
    for(const k in hideCount) delete hideCount[k];
    collapsed.forEach(id => {                    // attribute the folded region to its node (badge)
      const t = scope.get(id);
      if(t && t.size){                           // panel fold: count along the types that folded it.
        let k = 0;                               // `cadj` is containment-only and cannot see a fold
        away(id, t).forEach(x => { if(h.has(x)) k++; });          // along `uses`, so it must not be
        hideCount[id] = k;                       // used here -- it would report 0 and the dead-toggle
        return;                                  // guard would revert every associative fold.
      }
      let k = 0; const s = new Set([id]), qq = [id];              // double-click fold: as upstream
      while(qq.length){
        const u = qq.shift();
        (cadj[u] || []).forEach(v => { if(!s.has(v) && h.has(v)){ s.add(v); k++; qq.push(v); } });
      }
      hideCount[id] = k;
    });
    hidden = h;
    paintFocusChip();
  };

  function apply(id, types){
    if(types && types.size) scope.set(id, types); else scope.delete(id);
    recomputeHidden();
    if(sel && sel.id && hidden.has(sel.id)) sel = null;
    wake(0.5);
    if(mode === '3d') refresh3d();
  }

  toggleCollapse = function(id, types){
    if(collapsed.has(id) && !types){ collapsed.delete(id); scope.delete(id); recomputeHidden(); }
    else {
      collapsed.add(id); apply(id, types);       // no types = double-click = upstream's rule
      if((hideCount[id] || 0) === 0){                        // no dead toggle, same as upstream
        collapsed.delete(id); scope.delete(id); recomputeHidden();
      }
    }
    if(sel && sel.id && hidden.has(sel.id)) sel = null;
    wake(0.5);
    if(mode === '3d') refresh3d();
    if(sel && sel.id === id) showNode(N[idx[id]]);           // reflect the new button state
  };

  // Per-edge-type show/hide, applied on the click rather than staged behind a button. The old
  // panel was tick-some-boxes-then-press-Collapse: two steps, and the boxes described a plan
  // rather than the state of the graph, so a node you had already folded came back with every box
  // ticked and a button that said Expand. Here each row says what that edge type is doing NOW.
  //
  // `scope` holds the types currently HIDDEN for a node, so "everything shown" is the empty set
  // and the node is in `collapsed` exactly when that set is non-empty.
  function setHidden(id, types){
    if(types.size){
      collapsed.add(id); apply(id, types);
      if((hideCount[id] || 0) === 0 && focus.id == null){   // folds nothing: revert rather than lie
        collapsed.delete(id); scope.delete(id); recomputeHidden(); wake(0.5);
        if(mode === '3d') refresh3d();
      }
    } else {
      collapsed.delete(id); scope.delete(id); recomputeHidden(); wake(0.5);
      if(mode === '3d') refresh3d();
    }
    if(sel && sel.id === id) showNode(N[idx[id]]);
  }

  // --- focus ------------------------------------------------------------------------------------
  // Three scopes that COMBINE -- neighbors + ancestors is a selection, not a fourth kind of thing,
  // which is why the old "ancestors + descendants" row is gone. `everything` is the ABSENCE of a
  // selection rather than a fourth choice, so it is the reset and it cannot be combined with them.
  const MODES = [['neighbors', 'neighbors'], ['descendants', 'descendants'],
                 ['ancestors', 'ancestors']];

  // Hiding 290 of 303 nodes leaves the 13 survivors wherever the layout had already scattered
  // them -- which, at the zoom you were at, is usually off screen. The first build of this showed
  // a correct focus as an EMPTY CANVAS: the data was right and the view was pointed at nothing.
  // So focus re-frames: once immediately, then three more times across the settle, because the
  // positions the first fit measured are already moving while it measures them. Clearing focus
  // does NOT re-frame -- it hands back the view you had before, which is a different question.
  function frameVisible(){
    // One pass, no spread: `Math.min(...xs)` passes one ARGUMENT per visible node, which is fine
    // for this graph's 303 and throws RangeError somewhere in the tens of thousands. This viewer
    // is shipped for other people's graphs, and a crash at scale is a poor way to find that out.
    let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity, seen = 0;
    for(const n of N){
      if(hidden.has(n.id)) continue;
      seen++;
      if(n.x < x0) x0 = n.x;
      if(n.x > x1) x1 = n.x;
      if(n.y < y0) y0 = n.y;
      if(n.y > y1) y1 = n.y;
    }
    if(!seen) return;
    const w = stage.clientWidth, h = stage.clientHeight, pad = 160;
    const z = Math.max(0.3, Math.min(3, Math.min(w / Math.max(1, x1 - x0 + pad),
                                                 h / Math.max(1, y1 - y0 + pad))));
    view.z = z;
    view.x = -((x0 + x1) / 2) * z;
    view.y = -((y0 + y1) / 2) * z;
  }

  // Where the camera was before focus took it somewhere else. Focusing re-frames -- it has to, or
  // the survivors sit off screen -- but CLEARING should hand back the view you had, not fit the
  // whole graph and drop you somewhere you never chose. You pan, you focus, you come back: you
  // should be where you left.
  let preFocus = null;
  let refits = [];                               // pending re-fit timers, cancelled on every change

  function setFocus(id, modes){
    const wanted = (!modes || !modes.length) ? null : {id, modes};
    if(wanted && focus.id == null) preFocus = {x: view.x, y: view.y, z: view.z};
    focus = wanted || {id:null, modes:[]};
    recomputeHidden();
    refits.forEach(clearTimeout);
    refits = [];
    if(!wanted && preFocus){
      view.x = preFocus.x; view.y = preFocus.y; view.z = preFocus.z;
      preFocus = null;
      wake(0.3);
      if(sel && sel.id) showNode(N[idx[sel.id]]);
      return;
    }
    frameVisible();
    wake(0.6);
    // The survivors are still being pulled together by the simulation, so one fit is a snapshot of
    // positions that are already stale. Three, spread over the settle, and the last one lands.
    //
    // Cancelled on the way in: without this, three quick clicks leave nine fits queued, and the
    // ones belonging to a scope you have already changed keep re-framing the camera for seconds
    // afterwards. Measured drifting from (176,351,z0.30) to (-14,36,z0.54) 2.5s after the last
    // click -- a view that moves on its own long after you stopped touching it.
    refits.forEach(clearTimeout);
    refits = [400, 1000, 1900].map(ms =>
      setTimeout(() => { frameVisible(); wake(0.05); }, ms));
    if(mode === '3d'){ refresh3d(); if(fg3d && fg3d.zoomToFit) fg3d.zoomToFit(600, 60); }
    if(sel && sel.id) showNode(N[idx[sel.id]]);
  }

  const chip = document.createElement('div');
  chip.id = 'xfocus';
  (document.getElementById('stage') || document.body).append(chip);
  function paintFocusChip(){
    if(focus.id == null){ chip.className = ''; chip.innerHTML = ''; return; }
    // Named in the order the rows are listed, so the chip reads the way the panel looks rather
    // than in whatever order they happened to be clicked.
    const label = MODES.filter(m => focus.modes.includes(m[0])).map(m => m[1]).join(' + ');
    chip.className = 'on';
    chip.innerHTML = `showing ${N.length - hidden.size} of ${N.length} · ${esc(label)} of `
      + `<b>${esc(focus.id)}</b>`
      + '<button class="xfx" title="show the whole graph (esc)">show everything</button>';
  }
  chip.addEventListener('click', ev => { if(ev.target.closest('.xfx')) setFocus(null, []); });
  addEventListener('keydown', ev => {
    if(ev.key === 'Escape' && focus.id != null){ setFocus(null, []); }
  });

  const _showNode = showNode;
  showNode = function(n){
    _showNode(n);
    const types = [...incident(n.id).keys()];
    const hid = scope.get(n.id) || new Set();
    const T = live(n.id);
    const lbl = document.createElement('div');
    lbl.className = 'lbl';
    lbl.textContent = 'action';
    const val = document.createElement('div');
    val.className = 'val';

    // How much graph. The scopes COMBINE, so each row carries its own size -- what `neighbors`
    // means is 11 nodes whether or not `ancestors` is also lit, and the chip on the canvas states
    // the union, which is the only number that changes as you add scopes. Counts include the
    // anchor, and a scope that would add nothing is greyed with its count still showing rather
    // than clicking through to a canvas that did not change.
    const picked = (focus.id === n.id) ? focus.modes : [];
    // State is on the element, not only in a CSS class: a screen reader reading "neighbors 11"
    // otherwise has no way to know whether it is on. aria-pressed, not role=radio -- these
    // combine, and radios are mutually exclusive by definition.
    let html = '<div class="xintro" id="xsonly">show only</div>'
      + '<div role="group" aria-labelledby="xsonly">'
      + `<button class="xfrow${picked.length ? '' : ' on'}" data-m="" data-id="${attr(n.id)}" `
      + `aria-pressed="${picked.length ? 'false' : 'true'}">`
      + `<span class="xname">everything</span><span class="xn">${N.length}</span>`
      + '<span class="xdot"></span></button>';
    for(const [m, label] of MODES){
      const k = window.KBSETS(L, n.id, T, m).size + 1;
      const on = picked.includes(m);
      html += `<button class="xfrow${on ? ' on' : ''}" data-m="${m}" `
        + `data-id="${attr(n.id)}" aria-pressed="${on}"${k <= 1 ? ' disabled' : ''}>`
        + `<span class="xname">${esc(label)}</span><span class="xn">${k}</span>`
        + `<span class="xdot"></span><span class="xsr"> nodes</span></button>`;
    }
    html += '</div>';

    // Which edges. One row per relation type incident to this node, in either direction: a signal
    // is a leaf in containment, so an incoming-only list left 249 of 303 nodes with a control that
    // could not do anything.
    if(!types.length){
      html += '<div class="xintro">show or hide nodes along the following edges</div>'
            + '<div class="xnone">this node has no edges</div>';
    } else {
      html += '<div class="xintro">show or hide nodes along the following edges</div>'
        + types.map(t => {
            const k = away(n.id, new Set([t])).size;
            const off = hid.has(t);
            const tip = (window.KBRELTIPS || {})[t];
            // `esc` escapes & and < but NOT quotes, and these go into ATTRIBUTES. No copy carries a
            // double quote today, which is exactly why this is worth fixing now rather than when
            // someone writes the first definition with a quoted term in it and the row falls apart.
            return `<div class="xrow"><span class="xname">${esc(t)}</span>`
              + (tip ? `<button type="button" class="xtip" data-tip="${attr(tip)}" `
                       + `aria-label="what does ${attr(t)} mean?">?</button>` : '')
              + `<span class="xn">${k}</span>`
              + `<span class="xsw" role="group" aria-label="${attr(t)} edges" `
              + `data-t="${attr(t)}" data-id="${attr(n.id)}">`
              + `<button class="xshow${off ? '' : ' on'}" aria-pressed="${!off}">show</button>`
              + `<button class="xhide${off ? ' on' : ''}" aria-pressed="${off}">hide</button>`
              + '</span></div>';
          }).join('');
    }
    val.innerHTML = html;

    // Below the node's name, not above its title: the first thing you read should be what the node
    // IS. Falls back to the top of the panel only if the name section is somehow absent.
    const name = [...inspect.querySelectorAll(':scope > details')]
      .find(d => d.querySelector('summary').dataset.k === 'name');
    if(name) name.after(lbl, val); else inspect.insertBefore(val, inspect.firstChild),
                                        inspect.insertBefore(lbl, inspect.firstChild);
    if(window.KBFOLD) window.KBFOLD();            // same section machinery as everything else
  };

  inspect.addEventListener('click', ev => {
    const f = ev.target.closest('.xfrow');
    if(f && !f.disabled){
      const id = f.dataset.id, m = f.dataset.m;
      // `everything` is the empty selection, so it clears rather than toggling alongside them.
      const cur = (focus.id === id) ? focus.modes : [];
      setFocus(id, !m ? [] : cur.includes(m) ? cur.filter(x => x !== m) : cur.concat(m));
      return;
    }
    const b = ev.target.closest('.xsw button'); if(!b) return;
    const sw = b.parentElement, id = sw.dataset.id, t = sw.dataset.t;
    const hid = new Set(scope.get(id) || []);
    if(b.classList.contains('xhide')) hid.add(t); else hid.delete(t);
    setHidden(id, hid);
  });

  recomputeHidden();
})();
</script>
"""

# Back, for the panel. Following a link is now the main way to move around, so a mis-click strands
# you on a node you did not want with no way back to the one you were reading.
#
# A view is pushed only when the TARGET changes, which keeps the re-renders out of the history:
# collapsing re-renders the same node to flip its button, and that must not count as navigation.
BACK_BUTTON = """
<style>
  #inspect .xback{font:11px ui-monospace,monospace;padding:2px 8px;margin-bottom:6px;cursor:pointer;
                  border:1px solid currentColor;border-radius:3px;background:transparent;color:inherit}
  #inspect .xback:hover{color:var(--act)}
</style>
<script>
(function(){
  const hist = [];
  let cur = null, restoring = false;
  const key = v => v.kind === 'node' ? 'n:' + v.id
                                     : 'e:' + v.e.src + '|' + v.e.type + '|' + v.e.dst;

  function enter(v){
    if(restoring) return;
    if(cur && key(cur) !== key(v)) hist.push(cur);       // same target = a re-render, not a move
    if(!cur || key(cur) !== key(v)) cur = v;
  }
  function chrome(){
    if(!hist.length) return;
    const b = document.createElement('button');
    b.className = 'xback'; b.textContent = '\\u2190 back';
    b.title = 'back to ' + (hist[hist.length-1].kind === 'node'
                            ? hist[hist.length-1].id : hist[hist.length-1].e.type);
    inspect.insertBefore(b, inspect.firstChild);
  }

  const _showNode = showNode, _showEdge = showEdge;
  showNode = function(n){ enter({kind:'node', id:n.id}); _showNode(n); chrome(); };
  showEdge = function(e){ enter({kind:'edge', e:e});     _showEdge(e); chrome(); };

  inspect.addEventListener('click', ev => {
    if(!ev.target.closest('.xback') || !hist.length) return;
    const v = hist.pop();
    restoring = true; cur = v;
    if(v.kind === 'node'){ const n = N[idx[v.id]]; if(n){ sel = n; showNode(n); } }
    else { sel = v.e; showEdge(v.e); }
    restoring = false;
  });
})();
</script>
"""

# id prefix -> the sub-label shown as `kind` in the inspector (the ontology primitive
# travels separately in `primitive_type`, exactly as the full graph surface does it).
KIND_BY_PREFIX = {
    "concept:": "entity type",
    "property:role-": "role value",
    "property:role": "role axis",
    # A measurable quantity a thing has -- a spread, a basis, a margin ratio. Distinct from the role
    # axis, which is the only other Property in the graph and is not a quantity at all.
    "property:": "quantity",
    "procedure:indicator-": "indicator",
    "procedure:signal-": "signal",
    # A computation the knowledge base states but the library does not implement -- a formula with
    # typed inputs and outputs and no code behind it. Distinct from `indicator` on purpose: the
    # difference between "you can call this" and "this is written down" is the whole point.
    "procedure:": "formula",
    "schema:": "schema",
    "fact:": "fact",
    "judgment:": "judgment",
    "object:": "root:knowledge-graph",
}

#: The domain the character classes divide. Its own row, because "entity type" used to hold it
#: alongside Indicator and Signal, and those are not the same thing: two are the LAYERS the domain is
#: built from, one is the domain. The sidebar should mirror the hierarchy, not flatten it.
DOMAIN_ID = "concept:technical-analysis"


def _kind(node_id: str, classes: frozenset[str] = frozenset()) -> str:
    """The sub-label shown in the inspector.

    The six character classes are identified by their EDGE -- `kind-of technical analysis` -- and not
    by their id. They used to be spelled `concept:indicator-class-momentum`, which made a prefix test
    work and also asserted, in the identifier itself, that they belonged to Indicator. The id is now
    `concept:momentum` and says only what the node is, so the classification has to come from where it
    is actually stated. Everything else is still unambiguous by prefix.
    """
    if node_id in classes:
        return "class"
    if node_id == DOMAIN_ID:
        return "domain"
    for prefix in sorted(KIND_BY_PREFIX, key=len, reverse=True):
        if node_id.startswith(prefix):
            return KIND_BY_PREFIX[prefix]
    return "node"


def main() -> int:
    if not GRAPH.exists():
        print(f"missing {GRAPH} -- run ontology/build_signal_indicator_ontology.py first",
              file=sys.stderr)
        return 1
    g = json.loads(GRAPH.read_text())

    #: The character classes, read off the edge that makes them one. See :func:`_kind`.
    _classes = frozenset(r["from_id"] for r in g["relations"]
                         if r["rel"] == "kind-of" and r["to_id"] == "concept:technical-analysis")

    nodes = [{
        "id": a["id"],
        "name": a["title"],
        "kind": _kind(a["id"], _classes),
        "primitive_type": a["kind"],
        "status": a.get("status"),
        "epistemic": a.get("epistemic"),
        "confidence": None,
        "props": {"description": a.get("summary", ""), **(a.get("props") or {})},
    } for a in g["atoms"]]

    edges = [{
        "src": r["from_id"],
        "dst": r["to_id"],
        "type": r["rel"],
        "relation": r["rel"],
        "weight": 1.0,
        # Every edge key that is not part of the edge's identity is a property OF THE RELATIONSHIP
        # and is surfaced in the inspector. `uses` carries `inputs` -- which of the indicator's
        # outputs flow into the signal -- so passing only `why` through would drop it.
        "props": {k: v for k, v in r.items()
                  if k not in ("from", "to", "rel", "from_id", "to_id")},
    } for r in g["relations"]]

    if ROOT_ID not in {n["id"] for n in nodes}:
        sys.exit(f"{GRAPH} has no {ROOT_ID}: the graph must carry its own root, and collapse "
                 f"would silently no-op without it")

    data = viz.data_from_rows(nodes, edges)
    # Recolour into the brand. Only the keys this graph actually uses are overridden; anything the
    # viewer defines and this graph does not carry keeps its default and is pruned from the rail.
    data["primitiveColor"] = {**data["primitiveColor"], **PRIMITIVE_COLOR}
    data["categoryColor"] = {**data["categoryColor"], **CATEGORY_COLOR}
    # The second level of each facet. The viewer has no key for these; FACETS reads them.
    data["kindColor"] = KIND_COLOR
    data["relationColor"] = RELATION_COLOR
    page = viz.render_page(data, title="Mangrove signal & indicator knowledge graph",
                           nav_html=BRAND_BAR.replace("__LOGO_LIGHT__", LOGO_LIGHT)
                                             .replace("__LOGO_DARK__", LOGO_DARK))
    # Before </head>, so the first paint is already the chosen theme rather than flashing to it.
    page = page.replace("</head>", PREPAINT + "</head>", 1)
    if page.count(VIEWER_ANCHOR) != 1:
        sys.exit(f"expected exactly one {VIEWER_ANCHOR!r} in the viewer script, found "
                 f"{page.count(VIEWER_ANCHOR)}; upstream viz.py changed and collapse would "
                 f"silently no-op")
    page = page.replace(VIEWER_ANCHOR, f"const ANCHOR={json.dumps(ROOT_ID)};")

    # Colour by the DERIVED kind where one is known, falling back to the primitive/category. Written
    # as a guarded inline expression rather than a helper because the viewer draws its first frame
    # during init, before any appended overlay has run -- a helper would be undefined and throw.
    # Asserted per site: if upstream viz.py rewrites one of these, the sub-kind colours would
    # silently stop applying to exactly one surface and everything would still render.
    for old, new in (
        ("ctx.strokeStyle=CC[e.category||'null']",
         "ctx.strokeStyle=(window.RC&&window.RC[e.relation])||CC[e.category||'null']"),
        ("ctx.fillStyle=CC[e.category||'null']",
         "ctx.fillStyle=(window.RC&&window.RC[e.relation])||CC[e.category||'null']"),
        ("ctx.fillStyle=PC[n.primitive||'null']",
         "ctx.fillStyle=(window.KC&&window.KC[n.kind])||PC[n.primitive||'null']"),
        (".nodeColor(n=>PC[n.primitive||'null'])",
         ".nodeColor(n=>(window.KC&&window.KC[n.kind])||PC[n.primitive||'null'])"),
        (".linkColor(e=>CC[e.category||'null'])",
         ".linkColor(e=>(window.RC&&window.RC[e.relation])||CC[e.category||'null'])"),
        # A ring on `ratified` is a ring on 301 of 303 nodes -- noise, not signal. Dropping the key
        # makes STATUS[n.status] undefined for it, so the ring is skipped entirely and only the
        # exceptions are marked. `draft` and `deprecated` keep theirs.
        ("const STATUS={ratified:'--rat',draft:'--draft',deprecated:'--dep'};",
         "const STATUS={draft:'--draft',deprecated:'--dep'};"),
        ("const sc=STATUS[n.status];if(sc){ctx.lineWidth=2;",
         "const sc=STATUS[n.status];if(sc){ctx.lineWidth=1.2;"),
        # Selection is drawn OUTSIDE the node, not on its edge. A stroke is centred on its path, so
        # stroking the fill circle at width 2 spent half that width covering the node -- the marker
        # shrank what it was marking. At r+2.2 the whole ring sits clear of the fill, so a selected
        # node is the same size as an unselected one with a halo added. At width 3.6 the band runs
        # r+0.4 to r+4.0 -- more prominent, and its inner edge still clears the fill.
        ("if(n===sel||n===hov){ctx.lineWidth=2;ctx.strokeStyle=cssv('--ink');ctx.stroke();}",
         "if(n===sel||n===hov){ctx.lineWidth=3.6;ctx.strokeStyle=cssv('--ok');"
         "ctx.beginPath();ctx.arc(n.x,n.y,r+2.2,0,6.2832);ctx.stroke();}"),
        # The focused node's own label, bigger and bold. `foc` is already `sel||hov` on that line --
        # the same condition the ring uses -- so the two states cannot drift apart.
        #
        # The x-offset moves with it: the ring's outer edge is now r+4.0 and the label started at
        # r+3, so at 14px it would have been printed across the ring it is meant to accompany.
        ("if(showLbl){ctx.fillStyle=cssv('--ink');ctx.font='11px sans-serif';\n"
         "      ctx.fillText((n.name||n.id).slice(0,26),n.x+r+3,n.y+4);}});",
         "if(showLbl){ctx.fillStyle=cssv('--ink');"
         "ctx.font=foc?'bold 14px sans-serif':'11px sans-serif';\n"
         "      ctx.fillText((n.name||n.id).slice(0,26),n.x+r+(foc?6:3),n.y+4);}});"),
    ):
        if page.count(old) != 1:
            sys.exit(f"expected exactly one {old!r} in the viewer script, found {page.count(old)}; "
                     f"upstream viz.py changed and the sub-kind colours would silently not apply")
        page = page.replace(old, new)

    # The two `kv()` call sites hand off to the readable formatters in PROPERTY_PANEL. Guarded, so a
    # page that somehow loses the overlay degrades to the viewer's own dump rather than an empty
    # block -- and asserted, so an upstream rename fails the build instead of silently reverting the
    # panel to raw JSON, which looks like nothing changed.
    for old, new in (
        # One vocabulary. The panel says show/hide, so the hint bar cannot say collapse/expand for
        # the gesture that does the same thing -- it is the only user-visible use of the word left.
        ("double-click a node to collapse/expand",
         "double-click a node to hide or show what hangs off it"),
        ("+kv('properties',n.props)",
         "+(window.KVPROPS?window.KVPROPS(n):kv('properties',n.props))"),
        ("+kv('other properties',pr,['because','state','note']);",
         "+(window.KVEDGE?window.KVEDGE(e):kv('other properties',pr,['because','state','note']));"),
    ):
        if page.count(old) != 1:
            sys.exit(f"expected exactly one {old!r} in the viewer script, found {page.count(old)}; "
                     f"upstream viz.py changed and the inspector would fall back to raw JSON")
        page = page.replace(old, new)

    overlay = (BRAND_STYLE
               + TIP_COPY
               + TOOLTIPS
               + INSPECTOR_LINKS
               + PROPERTY_PANEL
               + FOCUS_SETS
               + ACTION_PANEL.replace("__ROOT__", json.dumps(ROOT_ID))
               + BACK_BUTTON
               + THEME_SCRIPT
               + DECLUTTER
               + FACETS          # after DECLUTTER: it rebuilds the rows DECLUTTER prunes
               + SEARCH_UI.replace("__INDEX__", json.dumps(search_index(),
                                                            separators=(",", ":"))))
    print(page.replace("</body>", overlay + "</body>"))
    print(f"nodes={len(data['nodes'])} edges={len(data['edges'])}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

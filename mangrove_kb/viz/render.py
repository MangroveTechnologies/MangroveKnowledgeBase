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
    from ..graph import SEARCH_TIERS, KnowledgeGraph, _flatten

    kg = KnowledgeGraph.load()
    rows = []
    for node in kg.nodes.values():
        source = {"name": node.name, "id": node.id, "summary": node.summary, **node.props}
        rows.append({
            "id": node.id,
            "name": node.name,
            "summary": (node.summary or "")[:140],
            # One lowercased string per tier. Tier order IS rank order.
            "t": [" ".join(_flatten(source.get(f)) for f in tier).lower() for tier in SEARCH_TIERS],
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
                     + 'because 301 of 303 nodes are.';
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
  const WHY = ['name','abbrev','summary','detail'];   // parallel to SEARCH_TIERS
  const LIMIT = 40;

  const bar=document.getElementById('brandbar');
  const wrap=document.createElement('span'); wrap.id='searchwrap';
  const box=document.createElement('input');
  box.id='search'; box.type='search'; box.autocomplete='off';
  box.placeholder='Search 303 nodes \u2014 name, formula, outputs\u2026';
  const out=document.createElement('div'); out.id='results';
  wrap.append(box,out); bar.insertBefore(wrap, document.getElementById('themesel'));

  let hits=[], cur=-1;

  function rank(q){
    const res=[];
    for(const r of IDX){
      const tier=r.t.findIndex(h=>h.includes(q));
      if(tier>=0) res.push({r,tier});
    }
    // rank, then id -- identical to find()'s sort key, so the two agree on ordering.
    res.sort((a,b)=> a.tier-b.tier || (a.r.id<b.r.id?-1:a.r.id>b.r.id?1:0));
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
    "class":                 PRIMITIVE_COLOR["Concept"],
    "entity type":           _shade(PRIMITIVE_COLOR["Concept"], -0.35),
    "domain":                _shade(PRIMITIVE_COLOR["Concept"], 0.35),
    "role value":            PRIMITIVE_COLOR["Property"],
    "role axis":             _shade(PRIMITIVE_COLOR["Property"], -0.35),
    "root:knowledge-graph":  PRIMITIVE_COLOR["Object"],
    "schema":                PRIMITIVE_COLOR["Schema"],
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
  #inspect table.kbt{border-collapse:collapse;width:100%;table-layout:fixed;font-size:12px}
  #inspect table.kbt td{vertical-align:top;padding:1px 0 5px}
  #inspect table.kbt td.kbn{font:600 11.5px ui-monospace,monospace;width:34%;padding-right:8px;
                            overflow-wrap:anywhere}
  #inspect table.kbt td.kbv{overflow-wrap:anywhere}
  #inspect .kbm{font:10.5px ui-monospace,monospace;color:var(--muted);letter-spacing:.02em}
  #inspect .kbd{color:var(--muted);font-size:11.5px;line-height:1.45}
  #inspect ul.kbl{margin:2px 0 0;padding-left:16px;font-size:12px;line-height:1.5}
  #inspect pre.kbp{margin:2px 0 0;padding:6px 8px;background:rgba(128,128,128,.12);border-radius:4px;
                   font:11px ui-monospace,monospace;white-space:pre-wrap;overflow-wrap:anywhere}
  #inspect details.kbx{margin-top:14px;border-top:1px solid var(--line,rgba(128,128,128,.3));
                       padding-top:8px}
  #inspect details.kbx summary{font:10.5px ui-monospace,monospace;text-transform:uppercase;
                               letter-spacing:.06em;color:var(--muted);cursor:pointer}
  #inspect details.kbx[open] summary{margin-bottom:6px}
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
      const s = dict[k] || {}, meta = row(s).filter(Boolean).join(' · ');
      return `<tr><td class="kbn">${E(k)}</td><td class="kbv">`
        + (meta ? `<span class="kbm">${meta}</span>` : '')
        + (s.description ? `<div class="kbd">${E(s.description)}</div>` : '')
        + '</td></tr>';
    }).join('') + '</table>';
  };

  // 64 nodes carry these as a list and 7 as a paragraph. Same field, so it renders the same way.
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
    h += sec('parameters', TABLE(p.params, s => [s.type,
              s.default == null ? '' : 'default ' + NUM(s.default), BOUNDS(s.min, s.max)]));
    // An EXPRESSION over the params above ("window - 1"), not a number -- 75 nodes say exactly that.
    if(p.warmup_bars) h += `<div class="kbm" style="margin-top:4px">warm-up <code>`
      + `${E(p.warmup_bars)}</code> bars — an expression in these parameters</div>`;
    h += sec('outputs', TABLE(p.outputs, s => [s.type,
              s.units && s.units !== 'boolean' ? s.units : '', RANGE(s.range, s.type)]));
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
    // Anything this file has never heard of, verbatim. The panel hides nothing.
    for(const [k, v] of Object.entries(p)){
      if(KNOWN.includes(k) || v == null) continue;
      x += `<div class="kbm"><b>${E(k)}</b>: `
        + E(typeof v === 'object' ? JSON.stringify(v) : v) + '</div>';
    }
    // A disclosure triangle over a single line hides one word behind a click. The 14 concept nodes
    // carry no props at all, so for them the "extras" ARE the panel -- show them flat.
    if(x) h += h ? `<details class="kbx"><summary>provenance &amp; extras</summary>${x}</details>`
                 : sec('epistemic status', x);
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
      rest += `<div class="kbm"><b>${E(k)}</b>: `
        + E(typeof v === 'object' ? JSON.stringify(v) : v) + '</div>';
    }
    return h + (rest ? sec('other properties', rest) : '');
  };

  // The viewer prints `epistemic · confidence` near the top, where confidence is null on every node
  // in this graph -- it rendered as the words "observed ·" with nothing after them. It now sits in
  // the details block above, so drop the original rather than show it twice.
  if(typeof showNode === 'function'){
    const _showNode = showNode;
    showNode = function(n){
      _showNode(n);
      const l = [...inspect.querySelectorAll('.lbl')]
        .find(x => x.textContent === 'epistemic · confidence');
      if(l){ const v = l.nextElementSibling; l.remove(); if(v) v.remove(); }
    };
  }
})();
</script>
"""

# Collapse across a chosen set of relation types, driven from the node panel.
#
# The viewer's own collapse asks "what is reachable ONLY through this node", so it can never fold a
# CROSS-CUTTING AXIS: every signal has two containment parents (`instance-of` Signal and `has-role`
# its role), so collapsing `trigger` strands nobody, hideCount is 0, and the dead-toggle guard
# reverts it. Correct for what it computes, useless for "hide the signals in this role".
#
# This asks a different question -- "what hangs off this node ALONG THESE RELATIONS" -- walking
# incoming edges of the chosen types, transitively, and ignoring whether those nodes have another
# parent. Jarvis's floater-free guarantee is kept as a POST-CONDITION rather than the definition:
# after the type-scoped set is hidden, anything that can no longer reach the root is hidden too.
#
# Written against the viewer's own bindings: `hidden` is `let` so it is reassigned, `collapsed` and
# `hideCount` are `const` so they are mutated in place, and `recomputeHidden`/`toggleCollapse` are
# function declarations whose call sites (2D dblclick, 3D dblclick) resolve by name at call time.
# The vendored file is not touched.
COLLAPSE_PANEL = """
<style>
  #inspect .xcol{margin-top:4px}
  #inspect .xcol label{display:flex;align-items:center;gap:6px;font:11px ui-monospace,monospace;
                       padding:1px 0;cursor:pointer}
  #inspect .xcol label input{margin:0;cursor:pointer}
  #inspect .xcol .n{color:var(--act);margin-left:auto}
  #inspect .xcol button{margin-top:6px;font:11px ui-monospace,monospace;padding:3px 10px;
                        cursor:pointer;border:1px solid currentColor;border-radius:3px;
                        background:transparent;color:inherit}
  #inspect .xcol button:hover{color:var(--act)}
  #inspect .xcol .mut{font:11px ui-monospace,monospace}
</style>
<script>
(function(){
  const ROOT = __ROOT__;
  const scope = new Map();                       // node id -> Set of relation types to fold along

  const inBy = {};                               // dst -> incoming edges (child --rel--> parent)
  L.forEach(e => { (inBy[e.dst] = inBy[e.dst] || []).push(e); });

  // relation types incident to a node; `inn` is what a collapse could fold along
  function typesFor(id){
    const m = new Map();
    L.forEach(e => {
      const k = e.type;
      if(e.dst === id || e.src === id){
        const v = m.get(k) || {inn:0, out:0};
        (e.dst === id ? v.inn++ : v.out++); m.set(k, v);
      }
    });
    return m;
  }
  const foldable = id => [...typesFor(id)].filter(([, c]) => c.inn > 0).map(([t]) => t);
  const defaults = id => new Set(foldable(id));

  // everything that reaches `id` by incoming edges of `types`, transitively
  function descendants(id, types){
    const out = new Set(), seen = new Set([id]), q = [id];
    while(q.length){
      const u = q.shift();
      (inBy[u] || []).forEach(e => {
        if(!types.has(e.type) || seen.has(e.src)) return;
        seen.add(e.src); out.add(e.src); q.push(e.src);
      });
    }
    return out;
  }

  // Two ways in, and they must not be confused:
  //   * double-click keeps UPSTREAM's rule exactly -- containment-reachability, folding only what is
  //     reachable SOLELY through the node. `Indicator` folds 75; `RSI`, `trigger` and `filter` fold
  //     nothing, because their children have a second parent. Unchanged behaviour, deliberately.
  //   * the panel folds along the TICKED relation types, which is the only way to fold a
  //     cross-cutting axis. A node folded that way has an entry in `scope`.
  recomputeHidden = function(){
    const h = new Set();
    collapsed.forEach(id => {                    // panel folds: type-scoped
      const t = scope.get(id); if(t) descendants(id, t).forEach(x => h.add(x));
    });
    if(idx[ROOT] != null){                       // upstream's rule, and the floater post-condition
      const seen = new Set([ROOT]), q = [ROOT];
      while(q.length){
        const u = q.shift();
        if(collapsed.has(u)) continue;           // never traverse THROUGH a collapsed node
        (cadj[u] || []).forEach(v => { if(h.has(v) || seen.has(v)) return; seen.add(v); q.push(v); });
      }
      N.forEach(n => { if(!seen.has(n.id)) h.add(n.id); });
    }
    collapsed.forEach(id => h.delete(id));       // a collapsed node is never hidden by its own fold
    for(const k in hideCount) delete hideCount[k];
    collapsed.forEach(id => {                    // attribute the folded region to its node (badge)
      const t = scope.get(id);
      if(t){                                     // panel fold: count along the types that folded it.
        let k = 0;                               // `cadj` is containment-only and cannot see a fold
        descendants(id, t).forEach(x => { if(h.has(x)) k++; });   // along `uses`, so it must not be
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

  const _showNode = showNode;
  showNode = function(n){
    _showNode(n);
    const types = foldable(n.id);
    const on = scope.get(n.id) || defaults(n.id);
    const div = document.createElement('div');
    div.className = 'xcol';
    if(!types.length){
      div.innerHTML = '<div class="lbl">collapse</div>'
        + '<div class="val mut">nothing hangs off this node</div>';
    } else {
      div.innerHTML = '<div class="lbl">collapse across</div><div class="val">'
        + types.map(t => {
            const k = descendants(n.id, new Set([t])).size;
            return `<label><input type="checkbox" class="xct" data-t="${esc(t)}"`
                 + `${on.has(t) ? ' checked' : ''}>${esc(t)}<span class="n">${k}</span></label>`;
          }).join('')
        + `<button class="xcb" data-id="${esc(n.id)}">`
        + `${collapsed.has(n.id) ? 'Expand' : 'Collapse'}</button></div>`;
    }
    inspect.insertBefore(div, inspect.firstChild);   // top of the panel, not buried under the edges
  };

  inspect.addEventListener('click', ev => {
    const b = ev.target.closest('.xcb'); if(!b) return;
    const id = b.dataset.id;
    const picked = new Set([...inspect.querySelectorAll('.xct')]
      .filter(c => c.checked).map(c => c.dataset.t));
    if(collapsed.has(id)) toggleCollapse(id);                 // expand
    else if(picked.size) toggleCollapse(id, picked);          // collapse across the ticked types
    if(sel && sel.id === id) showNode(N[idx[id]]);
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
    "procedure:indicator-": "indicator",
    "procedure:signal-": "signal",
    "schema:": "schema",
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
               + INSPECTOR_LINKS
               + PROPERTY_PANEL
               + COLLAPSE_PANEL.replace("__ROOT__", json.dumps(ROOT_ID))
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

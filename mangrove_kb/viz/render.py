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
    "concept:indicator-class-": "indicator class",
    "concept:": "entity type",
    "property:role-": "role value",
    "property:role": "role axis",
    "procedure:indicator-": "indicator",
    "procedure:signal-": "signal",
}


def _kind(node_id: str) -> str:
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

    nodes = [{
        "id": a["id"],
        "name": a["title"],
        "kind": _kind(a["id"]),
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
    page = viz.render_page(data, title="Mangrove signal/indicator ontology")
    if page.count(VIEWER_ANCHOR) != 1:
        sys.exit(f"expected exactly one {VIEWER_ANCHOR!r} in the viewer script, found "
                 f"{page.count(VIEWER_ANCHOR)}; upstream viz.py changed and collapse would "
                 f"silently no-op")
    page = page.replace(VIEWER_ANCHOR, f"const ANCHOR={json.dumps(ROOT_ID)};")
    overlay = (INSPECTOR_LINKS
               + COLLAPSE_PANEL.replace("__ROOT__", json.dumps(ROOT_ID))
               + BACK_BUTTON)
    print(page.replace("</body>", overlay + "</body>"))
    print(f"nodes={len(data['nodes'])} edges={len(data['edges'])}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

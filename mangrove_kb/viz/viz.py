# VENDORED from mangrove-one/jarvis @ 3a5c27f
# Licensed CC BY-NC-SA 4.0 — Tim Darrah / Mangrove Technologies.
# Do not edit here: change it upstream in jarvis, then re-run vendor/sync.py.
# Only import paths are rewritten; the body is verbatim.
"""Knowledge-space visualizer (#185/#189) — a self-contained interactive graph (2D + 3D).

Renders any GraphStore (the sample space by default, or jarvis's real graph) as a force-directed
canvas — no CDN, no build step. Nodes are colored by their §Part-I **primitive** (or grey when
untyped, e.g. the code graph); edges by their §Part-IV relation **category**. The left rail toggles
primitives and categories — that IS the cross-cut view (untick all but "causal" for the dependency
skeleton). **Click** any node or edge to pin its full detail in the resizable right-hand inspector
(folded in from #190): status, subject, dims, description, ACT-R access events, code-graph links,
its edges, and a deep link into the dashboard ego view. Live signals (status colour, cyan ACT-R
halo, evidence-scaled radius) render when present and are simply absent on the sample space.

One implementation, two surfaces: the standalone CLI (`tools/graphviz/render.py`) calls `render_html`
for a file / HTTP server; the dashboard builds a live DATA dict with `data_from_rows` (its own
read-only reads) and serves the SAME view over `/graph-viz` via `render_page`.
"""
from __future__ import annotations

import json
import os

from . import ontology as ont
from .store import GraphStore

# 3D renderer (#233): 3d-force-graph UMD (bundles three.js + d3-force-3d), MIT, vendored in-repo and
# INLINED — no CDN, works offline, self-contained contract holds. It bundles its OWN three; we load
# NOTHING else three-related (a second global three caused a version clash — "Multiple instances of
# Three.js" / "Ak.Timer is not a constructor" — that broke the bundle). Always-on node labels are a
# three-free HTML overlay (graph2ScreenCoords → <span>), NOT SpriteText (which needs that second
# three). Fail-soft: missing file → the 3D button no-ops and 2D is unaffected.
def _read_vendor(name: str) -> str:
    try:
        with open(os.path.join(os.path.dirname(__file__), "vendor", name), encoding="utf-8") as f:
            return f.read().replace("</script", "<\\/script")
    except Exception:
        return ""

_LIB3D = _read_vendor("3d-force-graph.min.js")

# Colors are assigned by *iterating the ontology* — the KEYS derive from ontology.PRIMITIVE_TYPES /
# ontology.CATEGORIES (single source), only the palette values are local. Add a primitive/category to
# the ontology and it gets a color automatically; nothing here to hand-sync.
_UNTYPED = "#9aa0a6"                                   # code-graph / NULL fallback
_PRIMITIVE_PALETTE = ("#4e79a7", "#59a14f", "#e15759", "#f28e2b", "#b07aa1",
                      "#76b7b2", "#edc948", "#ff9da7", "#9c755f", "#b6992d")
_CATEGORY_PALETTE = ("#4e79a7", "#e15759", "#59a14f", "#af7aa1", "#f28e2b", "#b07aa1")

PRIMITIVE_COLOR = {p: _PRIMITIVE_PALETTE[i % len(_PRIMITIVE_PALETTE)]
                   for i, p in enumerate(sorted(ont.PRIMITIVE_TYPES))}
PRIMITIVE_COLOR[None] = _UNTYPED
CATEGORY_COLOR = {c: _CATEGORY_PALETTE[i % len(_CATEGORY_PALETTE)]
                  for i, c in enumerate(ont.CATEGORIES)}
CATEGORY_COLOR[ont.ROOT_RELATION] = "#e6a817"          # the generic root ("fringe")
CATEGORY_COLOR[None] = _UNTYPED
FILTER_CATEGORIES = list(ont.CATEGORIES) + [ont.ROOT_RELATION]


def _props(p) -> dict:
    if isinstance(p, str):
        return json.loads(p) if p else {}
    return p or {}


def data_from_rows(nodes, edges, *, generation: int | None = None) -> dict:
    """Build the view DATA from raw row dicts — the shared builder for BOTH surfaces.

    node rows: id, name, kind, primitive_type, props (JSON str|dict), status, epistemic, confidence,
      and OPTIONAL live signals used / retrieved / code_links (the dashboard supplies them from its
      own read-only DB reads; the sample space leaves them 0).
    edge rows: src, dst, type, relation, weight, props. Edges to a node outside the set are dropped."""
    out_nodes = []
    for n in nodes:
        p = _props(n.get("props"))
        out_nodes.append({
            "id": n["id"], "name": n["name"], "kind": n.get("kind"),
            "primitive": n.get("primitive_type"), "classification": p.get("classification", {}),
            "status": n.get("status"), "epistemic": n.get("epistemic"),
            "conf": n.get("confidence"), "desc": (p.get("description") or p.get("note") or "")[:400],
            "evidence": len(p.get("evidence") or []),
            "gen": n.get("generation"), "created": n.get("created_at"),
            # every other prop key passes through so the inspector surfaces ALL of it (nothing hidden)
            "props": {k: v for k, v in p.items()
                      if k not in ("classification", "description", "note", "evidence")},
            "used": n.get("used", 0), "retrieved": n.get("retrieved", 0),
            "code_links": n.get("code_links", 0),
        })
    ids = {n["id"] for n in out_nodes}
    out_edges = []
    for e in edges:
        if e["src"] not in ids or e["dst"] not in ids:
            continue
        rel = e.get("relation")
        cat = None if rel is None else (ont.ROOT_RELATION if rel == ont.ROOT_RELATION
                                        else ont.relation_category(rel))
        out_edges.append({
            "src": e["src"], "dst": e["dst"], "type": e["type"], "relation": rel,
            "category": cat, "acyclic": bool(rel and ont.is_acyclic(rel)),
            "weight": e.get("weight", 1.0), "props": _props(e.get("props")),
        })
    return _wrap(out_nodes, out_edges, generation)


def _graph_json(store: GraphStore) -> dict:
    """Build the view DATA from a GraphStore (standalone/sample path; live signals are 0)."""
    return data_from_rows([dict(n) for n in store.nodes()], [dict(e) for e in store.edges()],
                          generation=store.live_generation())


def _wrap(nodes: list[dict], edges: list[dict], generation: int | None = None) -> dict:
    return {"nodes": nodes, "edges": edges, "generation": generation,
            "primitives": [p for p in PRIMITIVE_COLOR if p], "categories": FILTER_CATEGORIES,
            "primitiveColor": PRIMITIVE_COLOR, "categoryColor": CATEGORY_COLOR}


def page_body(data: dict, *, nav_html: str = "") -> str:
    """The page CONTENT (style + markup + script) — embeddable as a dashboard route body.
    `nav_html` (optional) is injected as a top bar so the dashboard nav appears above the graph."""
    body = _BODY.replace("__NAV__", nav_html)
    lib3d = f"<script>\n{_LIB3D}\n</script>" if _LIB3D else ""   # vendored 3d-force-graph, inlined (#233)
    return (f"<style>{_STYLE}</style>{body}{lib3d}"
            f"<script>\nconst DATA = {json.dumps(data)};\n{_SCRIPT}</script>")


def render_page(data: dict, *, title: str = "jarvis knowledge space", nav_html: str = "") -> str:
    """Full standalone HTML document from a prebuilt DATA dict (dashboard/live path)."""
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{title}</title></head><body>{page_body(data, nav_html=nav_html)}</body></html>')


def render_html(store: GraphStore, *, title: str = "jarvis knowledge space") -> str:
    """Full standalone HTML document from a GraphStore (opens offline; no external assets)."""
    return render_page(_graph_json(store), title=title)


def render_body(store: GraphStore) -> str:
    """Page content only, from a GraphStore."""
    return page_body(_graph_json(store))


_STYLE = r"""
  :root{--bg:#0f1115;--panel:#171a21;--ink:#e6e6e6;--muted:#9aa0a6;--line:#2a2f3a;--act:#3fb6c9;
        --rat:#2e9e6b;--draft:#d9962e;--dep:#b04a4a;--chip:#212630}
  @media (prefers-color-scheme:light){:root{--bg:#f6f7f9;--panel:#fff;--ink:#1a1a1a;--muted:#666;
        --line:#e2e5ea;--chip:#eef0f3}}
  *{box-sizing:border-box} html,body{margin:0;height:100%;background:var(--bg);color:var(--ink);
    font:13px/1.45 -apple-system,Segoe UI,Roboto,sans-serif}
  #viewport{display:flex;flex-direction:column;height:100vh}
  .nav{padding:8px 16px;border-bottom:1px solid var(--line);font:13px ui-monospace,monospace;flex:none}
  .nav a{color:var(--muted);text-decoration:none;margin-right:12px}
  .nav .here{color:var(--ink);margin-right:12px} .nav .brand{font-weight:700;margin-right:16px}
  #app{display:flex;flex:1;min-height:0}
  #rail{width:224px;flex:none;overflow:auto;padding:13px;background:var(--panel);border-right:1px solid var(--line)}
  #rail h1{font-size:14px;margin:0 0 2px} #rail .sub{color:var(--muted);margin:0 0 10px;font-size:11px}
  #rail h2{font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);margin:15px 0 5px}
  .row{display:flex;align-items:center;gap:7px;padding:2px 0;cursor:pointer;user-select:none}
  .row input{margin:0} .sw{width:11px;height:11px;border-radius:3px;flex:none}
  .row .ct{margin-left:auto;color:var(--muted);font-variant-numeric:tabular-nums}
  .btns{display:flex;gap:6px;margin-top:7px} .btns button{flex:1;padding:4px;font-size:11px;
    background:transparent;color:var(--ink);border:1px solid var(--line);border-radius:5px;cursor:pointer}
  #stage{flex:1;position:relative;min-width:0} canvas{display:block;width:100%;height:100%}
  #stage3d{position:absolute;inset:0;display:none}
  #density{width:100%;margin-top:4px;accent-color:var(--act)}
  .viewsel button.on,.lblsel button.on{background:var(--act);color:#fff;border-color:var(--act);font-weight:600}
  #hint{position:absolute;left:12px;bottom:10px;color:var(--muted);font-size:11px}
  #divider{width:6px;flex:none;cursor:col-resize;background:var(--line)} #divider:hover{background:var(--act)}
  #inspect{width:var(--paw,330px);min-width:250px;max-width:70vw;flex:none;overflow:auto;
    padding:15px;background:var(--panel);border-left:1px solid var(--line)}
  #inspect h2{font:600 13px ui-monospace,monospace;margin:0 0 6px;overflow-wrap:anywhere}
  .lbl{font:10.5px ui-monospace,monospace;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin:12px 0 3px}
  .val{font-size:12.5px;overflow-wrap:anywhere} .mut{color:var(--muted)}
  .acc{font:12px ui-monospace,monospace;font-variant-numeric:tabular-nums}
  .pill{display:inline-block;font:11px ui-monospace,monospace;border-radius:3px;padding:2px 7px;color:#fff;margin:0 4px 4px 0}
  .placeholder{color:var(--muted);font-size:12.5px;max-width:38ch}
  #inspect a{color:var(--act)} code{background:rgba(128,128,128,.18);padding:0 4px;border-radius:3px}
"""

_BODY = r"""
<div id="viewport">__NAV__
<div id="app">
  <div id="rail">
    <h1>knowledge space</h1>
    <p class="sub" id="counts"></p>
    <h2>View</h2>
    <div class="btns viewsel"><button id="v2d" class="on">2D</button><button id="v3d">3D</button></div>
    <h2>Density</h2>
    <input id="density" type="range" min="1" max="14" value="4" title="graph spread (left = tighter, right = looser)">
    <h2>Labels</h2>
    <div class="btns lblsel"><button data-l="on" class="on">on</button><button data-l="off">off</button><button data-l="hover">hover</button><button data-l="zoom">zoom</button></div>
    <h2>Node primitives</h2><div id="prims"></div>
    <div class="btns"><button data-g="prims" data-v="1">all</button><button data-g="prims" data-v="0">none</button></div>
    <h2>Relation categories</h2><div id="cats"></div>
    <div class="btns"><button data-g="cats" data-v="1">all</button><button data-g="cats" data-v="0">none</button></div>
    <h2>Legend</h2>
    <p class="sub">Solid arrow = ordering relation (DAG). Dashed = free / fringe.
    Cyan halo = ACT-R access. Ring = status.</p>
  </div>
  <div id="stage"><canvas id="cv"></canvas><div id="stage3d"></div>
    <div id="hint">click to inspect · <b>double-click a node to collapse/expand</b> (2D &amp; 3D) · <b>3D:</b> drag to rotate, scroll to zoom, right-drag to pan</div></div>
  <div id="divider" title="drag to resize"></div>
  <aside id="inspect"><div class="placeholder">Click any node or edge to pin its full detail here —
    primitive, status, dimensions, description, ACT-R access events, and its relationships.</div></aside>
</div>
</div>
"""

_SCRIPT = r"""
const PC=DATA.primitiveColor, CC=DATA.categoryColor;
const cv=document.getElementById('cv'), ctx=cv.getContext('2d'), stage=document.getElementById('stage');
const inspect=document.getElementById('inspect');
const on={prim:{},cat:{}};
DATA.primitives.forEach(p=>on.prim[p]=true); on.prim['null']=true;
DATA.categories.forEach(c=>on.cat[c]=true); on.cat['null']=true;
const esc=s=>(s==null?'':(''+s)).replace(/&/g,'&amp;').replace(/</g,'&lt;');
// generic key→value dump: renders EVERY entry of an object so no prop is ever hidden in the inspector
const kv=(label,obj,skip)=>{const es=Object.entries(obj||{}).filter(([k])=>!(skip||[]).includes(k));
  return es.length?`<div class="lbl">${esc(label)}</div><div class="val acc">`+es.map(([k,v])=>
    '<b>'+esc(k)+'</b>: '+esc(typeof v==='object'?JSON.stringify(v):v)).join('<br>')+'</div>':'';};

// --- filter chips -----------------------------------------------------------
function countBy(kind){const m={};(kind==='prim'?DATA.nodes.map(n=>n.primitive)
  :DATA.edges.map(e=>e.category)).forEach(k=>{k=k||'null';m[k]=(m[k]||0)+1});return m;}
function chip(box,label,color,key,store){const c=countBy(store);const row=document.createElement('label');
  row.className='row';const cb=document.createElement('input');cb.type='checkbox';cb.checked=true;
  cb.onchange=()=>{on[store][key]=cb.checked;wake(0.3);if(mode==='3d')refresh3d();};const sw=document.createElement('span');sw.className='sw';
  sw.style.background=color;const tx=document.createElement('span');tx.textContent=label;
  const ct=document.createElement('span');ct.className='ct';ct.textContent=c[key]||0;
  row.append(cb,sw,tx,ct);box.append(row);}
DATA.primitives.forEach(p=>chip(document.getElementById('prims'),p,PC[p],p,'prim'));
chip(document.getElementById('prims'),'(untyped)',PC['null'],'null','prim');
DATA.categories.forEach(c=>chip(document.getElementById('cats'),c,CC[c],c,'cat'));
chip(document.getElementById('cats'),'(untyped)',CC['null'],'null','cat');
document.getElementById('counts').textContent =
  DATA.nodes.length+' atoms · '+DATA.edges.length+' relationships'+(DATA.generation!=null?' · gen '+DATA.generation:'');
document.querySelectorAll('.btns button').forEach(b=>b.onclick=()=>{
  const g=b.dataset.g,v=b.dataset.v==='1',store=g==='prims'?'prim':'cat';
  Object.keys(on[store]).forEach(k=>on[store][k]=v);
  document.querySelectorAll('#'+g+' .row input').forEach(i=>i.checked=v);
  wake(0.3);if(mode==='3d')refresh3d();});

// --- layout -----------------------------------------------------------------
const N=DATA.nodes, idx={};N.forEach((n,i)=>{idx[n.id]=i;
  n.x=Math.cos(i*2.4)*(120+i*5); n.y=Math.sin(i*2.4)*(120+i*5); n.vx=0; n.vy=0;});
const L=DATA.edges.filter(e=>idx[e.src]!=null&&idx[e.dst]!=null).map(e=>({...e,s:idx[e.src],t:idx[e.dst]}));
let view={x:0,y:0,z:1}, drag=null, hov=null, sel=null, down=null;
let mode='2d', fg3d=null;                              // #233: 2D canvas default; 3D lazy-inits on toggle
let labelMode='on', density=4; const densF=()=>density/4;   // #233: labels on/off/hover/zoom + spread slider
let baseCam3d=0;                                            // #233: zoomed-out baseline camera distance (for zoom-mode labels)
let pivot3d={x:0,y:0,z:0};                                  // #233: 3D orbit center — set to the clicked node
let _lastNC={id:null,t:0};                                  // #233: 3D double-click detector (collapse/expand)
const STATUS={ratified:'--rat',draft:'--draft',deprecated:'--dep'};
const cssv=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();

// --- collapse / expand (#202, semantics fixed after the policies-hub change) -------------------
// CONTAINMENT-REACHABILITY collapse. hidden = every node NOT reachable from object:self over the
// CONTAINMENT graph without passing THROUGH a collapsed node (the collapsed node itself stays drawn
// as a dot but blocks traversal). This is floater-free BY CONSTRUCTION: a node is visible iff it has
// a path to self over visible nodes, so nothing can ever be left disconnected.
//   Containment edges = structural (part-of/instance-of/kind-of/is-a) + descriptive (has-property/
//   has-state) — "belongs to". Associative/causal/temporal/meta edges are EXCLUDED, so a policy's
//   enforced-in link to the code graph can't keep it visible when concept:rules collapses (that
//   alternate route was the old all-edges bug — the hub no-op). Fallback: a node with NO containment
//   edge (a loosely-attached fact/context) rides along ALL its edges so it stays connected at rest.
const ANCHOR='object:self';
const CONTAIN=e=>e.category==='structural'||e.category==='descriptive';
const hasContain={};DATA.edges.forEach(e=>{if(CONTAIN(e)){hasContain[e.src]=true;hasContain[e.dst]=true;}});
const cadj={};const addC=(a,b)=>{(cadj[a]=cadj[a]||[]).push(b);};
DATA.edges.forEach(e=>{ // include an edge if it's containment, OR either endpoint is loosely-attached
  if(CONTAIN(e)||!hasContain[e.src]||!hasContain[e.dst]){addC(e.src,e.dst);addC(e.dst,e.src);}});
const collapsed=new Set(); let hidden=new Set(); const hideCount={};
function recomputeHidden(){
  hidden=new Set(); for(const k in hideCount) delete hideCount[k];
  if(idx[ANCHOR]==null) return;
  const seen=new Set([ANCHOR]), q=[ANCHOR];
  while(q.length){const u=q.shift(); if(collapsed.has(u)) continue;   // don't traverse THROUGH a collapsed node
    (cadj[u]||[]).forEach(v=>{if(!seen.has(v)){seen.add(v);q.push(v);}});}
  N.forEach(n=>{if(!seen.has(n.id))hidden.add(n.id);});
  collapsed.forEach(c=>{let k=0;const s=new Set([c]),qq=[c];  // hidden region attributed to c (badge)
    while(qq.length){const u=qq.shift();(cadj[u]||[]).forEach(v=>{if(!s.has(v)&&hidden.has(v)){s.add(v);k++;qq.push(v);}});}
    hideCount[c]=k;});
}
recomputeHidden();

// Cooling (fix for the perpetual jostle): forces scale by a decaying alpha, and integration stops
// entirely once settled — interaction (drag / collapse / filter) re-warms it. High-degree hubs also
// get degree-scaled spring rest lengths so 40+ spokes have room instead of oscillating forever.
let alpha=1; const wake=v=>{alpha=Math.max(alpha,v);};
const deg={};L.forEach(e=>{deg[e.src]=(deg[e.src]||0)+1;deg[e.dst]=(deg[e.dst]||0)+1;});
function step(){
  if(alpha<0.02) return;            // settled — no integration until something wakes it
  alpha*=0.995;
  for(let i=0;i<N.length;i++){if(hidden.has(N[i].id))continue;
    for(let j=i+1;j<N.length;j++){if(hidden.has(N[j].id))continue;const a=N[i],b=N[j];
    let dx=a.x-b.x,dy=a.y-b.y,d2=dx*dx+dy*dy+.01,d=Math.sqrt(d2),f=2600*densF()/d2*alpha;dx/=d;dy/=d;
    a.vx+=dx*f;a.vy+=dy*f;b.vx-=dx*f;b.vy-=dy*f;}}
  L.forEach(e=>{if(hidden.has(N[e.s].id)||hidden.has(N[e.t].id))return;const a=N[e.s],b=N[e.t];
    const rest=80+10*Math.sqrt((deg[e.src]||1)+(deg[e.dst]||1));
    let dx=b.x-a.x,dy=b.y-a.y,d=Math.sqrt(dx*dx+dy*dy)+.01,f=(d-rest)*0.02*alpha;
    dx/=d;dy/=d;a.vx+=dx*f;a.vy+=dy*f;b.vx-=dx*f;b.vy-=dy*f;});
  N.forEach(n=>{if(hidden.has(n.id))return;n.vx-=n.x*0.002*alpha;n.vy-=n.y*0.002*alpha;if(n!==drag){n.x+=n.vx*=.86;n.y+=n.vy*=.86;}});
}
const rOf=n=>{let r=7+Math.min(6,n.evidence||0);
  if(collapsed.has(n.id))r+=Math.min(16,Math.round(Math.log2(1+(hideCount[n.id]||0))*4));return r;};
function visN(n){return on.prim[n.primitive||'null']&&!hidden.has(n.id);}
function visE(e){return on.cat[e.category||'null']&&visN(N[e.s])&&visN(N[e.t]);}
function draw(){
  const w=stage.clientWidth,h=stage.clientHeight;
  cv.width=w*devicePixelRatio;cv.height=h*devicePixelRatio;
  ctx.setTransform(devicePixelRatio,0,0,devicePixelRatio,0,0);ctx.clearRect(0,0,w,h);
  ctx.save();ctx.translate(w/2+view.x,h/2+view.y);ctx.scale(view.z,view.z);
  L.forEach(e=>{if(!visE(e))return;const a=N[e.s],b=N[e.t];
    ctx.strokeStyle=CC[e.category||'null'];ctx.lineWidth=Math.max(.7,e.weight*1.6);
    ctx.setLineDash(e.acyclic?[]:[4,3]);ctx.globalAlpha=e===sel?1:(e===hov?.9:.5);
    ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();
    if(e.acyclic){const g=Math.atan2(b.y-a.y,b.x-a.x),mx=(a.x+b.x)/2,my=(a.y+b.y)/2;ctx.setLineDash([]);
      ctx.beginPath();ctx.moveTo(mx,my);ctx.lineTo(mx-8*Math.cos(g-.4),my-8*Math.sin(g-.4));
      ctx.lineTo(mx-8*Math.cos(g+.4),my-8*Math.sin(g+.4));ctx.closePath();ctx.fillStyle=CC[e.category||'null'];ctx.fill();}});
  ctx.globalAlpha=1;ctx.setLineDash([]);
  N.forEach(n=>{if(!visN(n))return;const r=rOf(n),act=(n.used||0)+(n.retrieved||0);
    if(act>0){ctx.beginPath();ctx.arc(n.x,n.y,r+5,0,6.2832);ctx.strokeStyle=cssv('--act');ctx.lineWidth=2.4;ctx.stroke();}
    ctx.beginPath();ctx.arc(n.x,n.y,r,0,6.2832);ctx.fillStyle=PC[n.primitive||'null'];ctx.fill();
    const sc=STATUS[n.status];if(sc){ctx.lineWidth=2;ctx.strokeStyle=cssv(sc);ctx.stroke();}
    if(n===sel||n===hov){ctx.lineWidth=2;ctx.strokeStyle=cssv('--ink');ctx.stroke();}
    if(collapsed.has(n.id)){ctx.setLineDash([3,3]);ctx.lineWidth=2;ctx.strokeStyle=cssv('--ink');
      ctx.beginPath();ctx.arc(n.x,n.y,r+3,0,6.2832);ctx.stroke();ctx.setLineDash([]);
      const k=hideCount[n.id]||0;if(k){ctx.fillStyle=cssv('--ink');ctx.font='bold 11px sans-serif';
        ctx.fillText('+'+k,n.x+r+4,n.y-r);}}
    const foc=(n===sel||n===hov);                      // #233: 2D labels honor the labels switch
    const showLbl = labelMode==='on' ? true : labelMode==='off' ? false
                  : labelMode==='hover' ? foc : (view.z>0.65||foc);   // zoom
    if(showLbl){ctx.fillStyle=cssv('--ink');ctx.font='11px sans-serif';
      ctx.fillText((n.name||n.id).slice(0,26),n.x+r+3,n.y+4);}});
  ctx.restore();
}
(function loop(){step();draw();requestAnimationFrame(loop);})();

// --- interaction ------------------------------------------------------------
function toWorld(px,py){const w=stage.clientWidth,h=stage.clientHeight;
  return {x:(px-w/2-view.x)/view.z,y:(py-h/2-view.y)/view.z};}
function pickNode(px,py){const p=toWorld(px,py);let best=null,bd=256;
  N.forEach(n=>{if(!visN(n))return;const d=(n.x-p.x)**2+(n.y-p.y)**2;if(d<bd){bd=d;best=n;}});return best;}
function pickEdge(px,py){const p=toWorld(px,py);let best=null,bd=36;
  L.forEach(e=>{if(!visE(e))return;const a=N[e.s],b=N[e.t];const dx=b.x-a.x,dy=b.y-a.y,len=dx*dx+dy*dy||1;
    let t=((p.x-a.x)*dx+(p.y-a.y)*dy)/len;t=Math.max(0,Math.min(1,t));
    const cx=a.x+t*dx,cy=a.y+t*dy,d=(p.x-cx)**2+(p.y-cy)**2;if(d<bd){bd=d;best=e;}});return best;}
cv.onmousedown=e=>{down={x:e.offsetX,y:e.offsetY};const n=pickNode(e.offsetX,e.offsetY);
  drag=n||{pan:true,sx:e.offsetX-view.x,sy:e.offsetY-view.y};if(n)wake(0.4);};
cv.onmousemove=e=>{if(drag&&drag.pan){view.x=e.offsetX-drag.sx;view.y=e.offsetY-drag.sy;return;}
  if(drag){const p=toWorld(e.offsetX,e.offsetY);drag.x=p.x;drag.y=p.y;drag.vx=drag.vy=0;wake(0.3);return;}
  hov=pickNode(e.offsetX,e.offsetY)||pickEdge(e.offsetX,e.offsetY);cv.style.cursor=hov?'pointer':'grab';};
window.onmouseup=e=>{
  if(down&&Math.hypot(e.offsetX-down.x,e.offsetY-down.y)<4){       // a click, not a drag
    const n=pickNode(e.offsetX,e.offsetY);
    if(n){sel=n;showNode(n);} else {const ed=pickEdge(e.offsetX,e.offsetY);if(ed){sel=ed;showEdge(ed);}}}
  drag=null;down=null;};
cv.onwheel=e=>{e.preventDefault();view.z=Math.max(.3,Math.min(3,view.z*(e.deltaY<0?1.1:0.9)));};
function toggleCollapse(id){                             // shared by 2D dblclick + 3D dblclick (#233)
  if(collapsed.has(id)){collapsed.delete(id);recomputeHidden();}
  else{collapsed.add(id);recomputeHidden();                          // no dead toggle: revert if it folds nothing
    if((hideCount[id]||0)===0){collapsed.delete(id);recomputeHidden();}}
  wake(0.5);
  if(sel&&hidden.has(sel.id))sel=null;
  if(mode==='3d')refresh3d();                           // re-apply nodeVisibility/linkVisibility — no relayout
}
cv.ondblclick=e=>{const n=pickNode(e.offsetX,e.offsetY);if(n)toggleCollapse(n.id);};

function showNode(n){const c=n.classification||{};
  const dims=Object.entries(c).filter(([k])=>k!=='subject'&&k!=='subtype');
  // match edges by ID, not object identity — the 3D view passes a shallow-cloned node (#233), so
  // identity (N[e.s]===n) would find none; id works for both the 2D original and the 3D clone.
  const edges=L.filter(e=>e.src===n.id||e.dst===n.id).map(e=>{const out=e.src===n.id;
    return (out?'→ ':'← ')+esc(e.type)+' <span class=mut>'+esc(out?e.dst:e.src)+'</span>';}).join('<br>');
  const sc=STATUS[n.status]||'--muted';const act=(n.used||0)+(n.retrieved||0);
  inspect.innerHTML=`<h2>${esc(n.id)}</h2>
    <span class="pill" style="background:${PC[n.primitive||'null']}">${esc(n.primitive||'untyped')}</span>`
    +(n.status?`<span class="pill" style="background:var(${sc})">${esc(n.status)}</span>`:'')
    +(c.subject?`<span class="pill" style="background:#5b6b80">${esc(c.subject)}</span>`:'')
    +`<div class="lbl">name</div><div class="val">${esc(n.name)}</div>`
    +(n.desc?`<div class="lbl">description</div><div class="val">${esc(n.desc)}</div>`:'')
    +(dims.length?`<div class="lbl">dimensions</div><div class="val acc">${dims.map(([k,v])=>esc(k)+'='+esc(v)).join(' · ')}</div>`:'')
    +(n.epistemic?`<div class="lbl">epistemic · confidence</div><div class="val acc">${esc(n.epistemic)} · ${esc(n.conf)}</div>`:'')
    +(n.code_links?`<div class="lbl">code-graph links</div><div class="val acc">${n.code_links}</div>`:'')
    +(act>0?`<div class="lbl">ACT-R access</div><div class="val acc" style="color:var(--act)">used ${n.used} · retrieved ${n.retrieved}</div>`:'')
    +(n.kind?`<div class="lbl">subtype</div><div class="val acc">${esc(n.kind)}</div>`:'')
    +kv('properties',n.props)
    +((n.gen!=null||n.created)?`<div class="lbl">generation · created</div><div class="val acc">${esc(n.gen)}${n.created?' · '+esc(n.created):''}</div>`:'')
    +`<div class="lbl">edges</div><div class="val acc">${edges||'<span class=mut>none</span>'}</div>`
    +`<div class="lbl">deep link</div><div class="val"><a href="/graph?node=${encodeURIComponent(n.id)}">ego view + impact →</a></div>`;
}
function showEdge(e){const pr=e.props||{};
  inspect.innerHTML=`<h2>${esc(e.type)}</h2>
    <span class="pill" style="background:${CC[e.category||'null']}">${esc(e.relation||'untyped')}</span>`
    +(e.category?`<span class="pill" style="background:#5b6b80">${esc(e.category)}</span>`:'')
    +`<div class="lbl">from → to</div><div class="val acc">${esc(e.src)}<br>→ ${esc(e.dst)}</div>`
    +(pr.because?`<div class="lbl">because</div><div class="val">${esc(pr.because)}</div>`:'')
    +(pr.state?`<div class="lbl">state</div><div class="val">${esc(pr.state)}${pr.note?' — '+esc(pr.note):''}</div>`:'')
    +`<div class="lbl">weight · topology</div><div class="val acc">${esc(e.weight)} · ${e.acyclic?'ordering (DAG-enforced)':'free'}</div>`
    +kv('other properties',pr,['because','state','note']);   // surface any remaining edge prop
}

// --- resizable inspector (folded from #190) ---------------------------------
const root=document.documentElement, saved=localStorage.getItem('kviz-pane');
if(saved)root.style.setProperty('--paw',saved+'px');
const divider=document.getElementById('divider');let rz=null;
divider.onpointerdown=e=>{rz=e.clientX;divider.setPointerCapture(e.pointerId);};
divider.onpointermove=e=>{if(rz===null)return;
  const cur=parseInt(getComputedStyle(inspect).width);const w=Math.max(250,Math.min(innerWidth*0.7,cur+(rz-e.clientX)));
  root.style.setProperty('--paw',w+'px');localStorage.setItem('kviz-pane',Math.round(w));rz=e.clientX;};
divider.onpointerup=()=>{rz=null;};

// --- 3D mode (#233: vendored/inlined 3d-force-graph; additive toggle, 2D stays default) ---------
// Reuses the same visibility (filters + collapse hidden-set) and inspector as 2D. d3-force-3d (bundled
// in 3d-force-graph) does the layout; the 2D sim is untouched. Nodes/links are shallow-cloned so the
// 3D engine's x/y/z mutations never corrupt the 2D node objects. Node names show as a hover tooltip
// (built-in nodeLabel — no extra lib, so no multiple-three conflict).
const stage3d=document.getElementById('stage3d');
const node3d=new Map();   // ALL nodes fed ONCE as stable objects; filters toggle VISIBILITY (below), never
function build3dData(){    // graphData — so the force layout never re-runs and the graph never jumps on a filter.
  const nodes=[]; N.forEach(n=>{let o=node3d.get(n.id); if(!o){o={...n};node3d.set(n.id,o);} nodes.push(o);});
  return {nodes, links:L.map(e=>({...e,source:e.src,target:e.dst}))};
}
function nodeVisById(id){const n=N[idx[id]];return !!n&&on.prim[n.primitive||'null']&&!hidden.has(id);}
function nodeVis3(n){return nodeVisById(n.id);}
function linkVis3(e){return on.cat[e.category||'null']&&nodeVisById(e.src)&&nodeVisById(e.dst);}
function nodeVal3(n){const b=1+Math.min(6,n.evidence||0);   // #233: a collapsed node grows clearly with how many it hides.
  if(!collapsed.has(n.id))return b;                        // sphere radius ∝ cbrt(val), so size val by radiusMult^3:
  const rm=1+Math.min(2.5,0.5+(hideCount[n.id]||0)/10);   // ≥1.5× radius when collapsed, up to 3.5× for big subtrees
  return b*rm*rm*rm;}
// custom arcball: rotate point Q around pivot P — yaw about world-Y, pitch about the camera-right axis.
function _rotY(q,P,a){const s=Math.sin(a),c=Math.cos(a),x=q.x-P.x,z=q.z-P.z;return {x:P.x+x*c+z*s,y:q.y,z:P.z-x*s+z*c};}
function _rotAxis(q,P,u,a){const s=Math.sin(a),c=Math.cos(a),x=q.x-P.x,y=q.y-P.y,z=q.z-P.z;
  const d=x*u.x+y*u.y+z*u.z, cx=u.y*z-u.z*y, cy=u.z*x-u.x*z, cz=u.x*y-u.y*x;   // Rodrigues
  return {x:P.x+x*c+cx*s+u.x*d*(1-c), y:P.y+y*c+cy*s+u.y*d*(1-c), z:P.z+z*c+cz*s+u.z*d*(1-c)};}
// Always-on labels: a three-free HTML overlay. Each frame we project every node's 3D position to
// screen via 3d-force-graph's graph2ScreenCoords and place a <span>. (SpriteText would need a second
// global three, which clashes with 3d-force-graph's bundled three and crashes the whole thing.)
let lbox=null; const lmap=new Map();
function clearLabels(){lmap.forEach(el=>el.remove());lmap.clear();}
function updateLabels(){
  if(mode==='3d'&&fg3d&&lbox){
    const w=stage.clientWidth,h=stage.clientHeight;
    const overlayOn=(labelMode==='on'||labelMode==='zoom');   // off/hover → no overlay (hover uses the tooltip)
    let zoomOk=true;                                   // zoom mode: reveal labels once zoomed in past 70% of the
    if(labelMode==='zoom'){const cp=fg3d.cameraPosition();const d=Math.hypot(cp.x,cp.y,cp.z);  // zoomed-out baseline
      if(d>baseCam3d)baseCam3d=d; zoomOk=d < baseCam3d*0.7;}
    (fg3d.graphData().nodes||[]).forEach(n=>{
      let el=lmap.get(n.id);
      if(!el){el=document.createElement('span');
        el.style.cssText='position:absolute;font:10px sans-serif;white-space:nowrap;pointer-events:none;'
          +'transform:translate(-50%,-150%);color:'+cssv('--ink')
          +';text-shadow:0 0 3px '+cssv('--bg')+',0 0 3px '+cssv('--bg')+',0 0 3px '+cssv('--bg');
        el.textContent=(n.name||n.id).slice(0,24);lbox.appendChild(el);lmap.set(n.id,el);}
      if(!overlayOn||!zoomOk||n.x==null||!nodeVis3(n)){el.style.display='none';return;}   // hide filtered-out
      const c=fg3d.graph2ScreenCoords(n.x,n.y,n.z);
      if(!c||c.x<-40||c.y<-20||c.x>w+40||c.y>h+20){el.style.display='none';return;}  // off-screen / behind
      el.style.display='';el.style.left=c.x+'px';el.style.top=c.y+'px';});
  }
  requestAnimationFrame(updateLabels);
}
function refresh3d(){if(fg3d)fg3d.nodeVisibility(nodeVis3).linkVisibility(linkVis3).nodeVal(nodeVal3);}   // filters + collapsed-size; NO reheat/jump
function init3d(){                                     // called only when #stage3d is already VISIBLE
  if(typeof ForceGraph3D==='undefined')return false;   // vendored lib absent/failed → stay 2D
  fg3d=ForceGraph3D({controlType:'orbit'})(stage3d)     // orbit: left=rotate, right-drag=PAN, scroll=zoom
    .width(stage.clientWidth).height(stage.clientHeight)
    .backgroundColor(cssv('--bg'))
    .nodeRelSize(4).nodeLabel(n=>labelMode==='off'?'':(n.name||n.id))   // hover tooltip (unless labels off)
    .nodeColor(n=>PC[n.primitive||'null'])
    .nodeVal(nodeVal3)                                  // size grows when collapsed (by hideCount)
    .linkColor(e=>CC[e.category||'null']).linkOpacity(0.55)
    .linkWidth(e=>Math.max(0.4,(e.weight||1)*0.8))
    .linkDirectionalArrowLength(e=>e.acyclic?3.5:0).linkDirectionalArrowRelPos(0.6)
    .onNodeClick(n=>{sel=n;showNode(n);                 // set the orbit pivot; NO camera move → no jump (#233)
      if(n.x!=null)pivot3d={x:n.x,y:n.y,z:n.z};         // custom arcball (below) rotates around this
      const t=Date.now();                               // double-click a node → collapse/expand (like 2D)
      if(_lastNC.id===n.id&&t-_lastNC.t<350){toggleCollapse(n.id);_lastNC={id:null,t:0};}else _lastNC={id:n.id,t:t};})
    .onLinkClick(e=>{sel=e;showEdge(e);})
    .nodeVisibility(nodeVis3).linkVisibility(linkVis3); // filter via visibility, not graphData → no jump
  fg3d.graphData(build3dData());                        // feed ALL nodes/links ONCE (stable objects)
  fg3d.d3Force('charge').strength(-30*densF()*2.5);    // #233: density slider controls 3D spread
  lbox=document.createElement('div');
  lbox.style.cssText='position:absolute;inset:0;overflow:hidden;pointer-events:none';
  stage3d.appendChild(lbox);
  // custom arcball: OrbitControls always re-centers its target (that was the "jump to center"), so we
  // disable ITS rotation and orbit camera+target around pivot3d ourselves — the pivot stays put on screen.
  const ctl=fg3d.controls(); if(ctl)ctl.enableRotate=false;    // keep OrbitControls pan (right-drag) + zoom (wheel)
  let arc=null;
  stage3d.addEventListener('pointerdown',e=>{if(e.button===0)arc={x:e.clientX,y:e.clientY};});
  addEventListener('pointerup',()=>{arc=null;});
  addEventListener('pointermove',e=>{if(!arc||mode!=='3d'||!fg3d)return;
    const dx=e.clientX-arc.x,dy=e.clientY-arc.y;arc={x:e.clientX,y:e.clientY};
    const c=fg3d.controls(),cam=fg3d.camera();if(!c||!cam)return;
    const fx=c.target.x-cam.position.x,fz=c.target.z-cam.position.z;   // right = cross(forward, worldUp) = (-fz,0,fx)
    let ax=-fz,az=fx;const al=Math.hypot(ax,az)||1;ax/=al;az/=al;
    const yaw=-dx*0.005,pitch=-dy*0.005,U={x:ax,y:0,z:az},P=pivot3d;   // orbit both cam & target around the pivot
    const np=_rotAxis(_rotY(cam.position,P,yaw),P,U,pitch), nt=_rotAxis(_rotY(c.target,P,yaw),P,U,pitch);
    cam.position.set(np.x,np.y,np.z);c.target.set(nt.x,nt.y,nt.z);c.update();});
  refresh3d();
  updateLabels();
  return true;
}
function setMode(m){
  if(m===mode)return;
  mode=m;
  // Show the target surface FIRST, then init/size the 3D graph — 3d-force-graph's WebGL renderer +
  // orbit controls must attach to a VISIBLE, sized container or drag/zoom is dead.
  cv.style.display=m==='2d'?'block':'none';
  stage3d.style.display=m==='3d'?'block':'none';
  document.getElementById('v2d').classList.toggle('on',m==='2d');
  document.getElementById('v3d').classList.toggle('on',m==='3d');
  if(m==='3d'){
    if(!fg3d&&!init3d()){                              // init failed → revert to 2D
      mode='2d';cv.style.display='block';stage3d.style.display='none';
      document.getElementById('v2d').classList.add('on');document.getElementById('v3d').classList.remove('on');return;}
    fg3d.width(stage.clientWidth).height(stage.clientHeight);refresh3d();
  }
}
document.getElementById('v2d').onclick=()=>setMode('2d');
document.getElementById('v3d').onclick=()=>setMode('3d');
addEventListener('resize',()=>{if(mode==='3d'&&fg3d)fg3d.width(stage.clientWidth).height(stage.clientHeight);});
// density slider: spreads/tightens the layout (2D repulsion + 3D charge). #233
const dsl=document.getElementById('density');
dsl.oninput=()=>{density=+dsl.value;wake(0.7);
  if(fg3d){fg3d.d3Force('charge').strength(-30*densF()*2.5);fg3d.d3ReheatSimulation();}};
// labels switch: on / off / hover / zoom. #233 (2D honored in draw(); 3D via updateLabels + nodeLabel)
document.querySelectorAll('.lblsel button').forEach(b=>b.onclick=()=>{
  labelMode=b.dataset.l;
  document.querySelectorAll('.lblsel button').forEach(x=>x.classList.toggle('on',x===b));
  wake(0.2);});
"""



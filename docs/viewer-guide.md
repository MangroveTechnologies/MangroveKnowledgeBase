# A guide to the graph viewer

The viewer draws the whole signal library as a map you can click through: what each computation
does, what it reads, and what reads it.

```bash
python -m mangrove_kb.viz > graph.html
```

That writes one self-contained page. No server, no build step, no network.

---

## The three panes

| Pane | Where | What it holds |
| --- | --- | --- |
| Rail | left | filters, by kind of node and kind of edge |
| Map | middle | 303 nodes, 1049 edges, in 2D or 3D |
| Panel | right | everything the library records about whatever you clicked |

Nodes are indicators, signals, and the concepts that classify them. Edges are the claims that link
them — which signal reads which indicator, what family each belongs to, what part each plays in a
strategy.

## Search

The box at the top searches every authored field, not just names: formulas, interpretations,
applications, and the names and descriptions of inputs, params and outputs.

Results rank by where the match landed, and each carries a tag saying which — `NAME`, `ABBREV`,
`SUMMARY`, `DETAIL`. So `divergence` returns the things called that before the things that merely
mention it.

## Reading a node

Click a node. The panel fills with what the library records about it, in sections you can fold. Your
choices stick: fold **Edges** once and it stays folded on every node after it.

- **Inputs** — the series it reads
- **Parameters** — each with its type, default, and the range it accepts
- **Outputs** — each with units and the range its values can take
- **Formula**, **Interpretation**, **Applications**, **Reference** — as authored
- **Edges** — every link, grouped incoming and outgoing
- **Provenance & extras** — module, a call you can copy, how the entry was recorded

Every heading carries a **?** that says what that section holds. So does every edge type.

### Ranges say more than they look like

| Shown | Means |
| --- | --- |
| `0 … 100` | bounded both ways |
| `≥ 0` | floored, no ceiling |
| `unbounded` | `[-inf, inf]` — stated, not missing |
| `true/false` | boolean, not a `[0,1]` interval |
| `not authored` | nobody has written the range down |

The last two rows are the ones worth knowing apart. `unbounded` is a fact about the output;
`not authored` is a gap in the notes.

### Warm-up is an expression

**Warm-up** is how many bars the computation needs before its output means anything, and it is
usually written in terms of the node's own parameters — `window - 1`, `window_slow + window_sign - 1`.
Evaluate it against the parameters you intend to use.

## Following the graph

Every name under **Edges** is a link: click it and the panel moves there, with a **back** button to
return. What each edge type asserts:

| Edge | Claim |
| --- | --- |
| `instance-of` | this indicator measures that family — RSI measures momentum |
| `about` | this signal is concerned with that family without measuring it |
| `uses` | this reads that one, and carries which of its outputs flow in |
| `has-role` | the part it plays in a strategy: trigger or filter |
| `part-of` | a component of the other |
| `kind-of` | a subtype of the other |

`instance-of` and `about` are the pair to keep straight. An indicator produces the quantity, so it
is an instance of the family. A signal emits a boolean, so it is *about* the family instead — and
the `uses` edge beside it is the reason.

## Trimming the graph

303 nodes at once is a picture, not an answer. The **Action** section on any node cuts it down.

**show only** — pick any combination:

| | Keeps |
| --- | --- |
| everything | no trim |
| neighbors | one hop, in or out |
| descendants | everything built on this node |
| ancestors | everything this node is built from |

They combine: neighbors + ancestors gives you both. The count beside each says how many nodes you
would be left with before you commit, and a choice that would leave a single node is disabled.

**show or hide** — one row per edge type on this node, with its own count. Hiding a type removes
what hangs off it. The number is exact: hide `uses` on RSI and the eight signals that read it go,
and nothing else does.

The two halves compose. An edge type set to hide is also dropped from the lineage walk above, so the
counts change to match.

While a trim is active a bar sits over the map — *showing 13 of 303 · neighbors + ancestors of RSI*
— with a way out. **Esc** also clears it, and clearing returns you to the view you had, not to a
fitted whole graph.

Hiding a hub can leave a few nodes floating with nothing visibly joining them. That is honest: the
thing that connected them is the thing you hid.

## Getting around the map

- drag to pan, scroll to zoom
- double-click a node to hide or show what hangs off it
- **3D** is the same graph, same filters, same panel — drag to rotate, right-drag to pan
- **Labels** switches names on / off / on hover / on zoom. At 303 nodes, off is often clearer
- **Density** spreads or tightens the layout

## The rail

Nodes group by primitive, edges by relation category, and each opens into the derived kind beneath
it — `signal` and `indicator` inside `Procedure`, `about` and `has-role` inside `descriptive`.

Sub-kinds are shades of their parent's hue rather than new colours, so a darker teal is always a
subset of the teal above it. Parent and child are AND-ed: untick `Procedure` and every procedure
goes, with the children greyed to show why.

## Rings and themes

A **green ring** marks the selected node. A **yellow ring** marks a deprecated one — it still runs,
it just has a canonical replacement. Nothing else is ringed: 301 of 303 nodes are `ratified`, so
marking that would be decoration.

Light, dark and follow-the-system are top right, and the choice is remembered.

---

Everything here is also a query. See the [agent guide](../skills/knowledge-graph/GUIDE.md) and the
[skill](../skills/knowledge-graph/SKILL.md) for the same graph from Python.

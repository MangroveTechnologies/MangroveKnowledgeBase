# Agent guide: using the knowledge graph

Fifteen tasks an agent actually gets asked to do with this library, and how to do each one with
`mangrove_kb.graph`. Every call here was executed against the committed graph; the outputs are real.

The skill (`SKILL.md`, beside this file) is the reference for *which call*. This is the
reference for *what a whole job looks like*, including the traps.

```python
from mangrove_kb.graph import KnowledgeGraph
kg = KnowledgeGraph.load()
```

---

## Contents

Fifteen jobs. Each is self-contained — jump to the one you have, and follow the links at its end
when the answer needs a second call.

| | job | |
|---|---|---|
| 1 | [Orient yourself in a library you have never seen](#1-orient-yourself-in-a-library-you-have-never-seen) | Start from the graph's own summary rather than the file tree. |
| 2 | [Check whether something already exists](#2-check-whether-something-already-exists-before-building-it) | The duplicate you are about to write is one hop from the indicator it would read. |
| 3 | [Work out what a change breaks](#3-work-out-what-a-change-breaks) | Who reads this, and which specific output each of them takes. |
| 4 | [Compose a strategy from both axes](#4-compose-a-strategy-from-both-axes) | Intersect what a thing measures with the part it plays. |
| 5 | [Find out what a signal needs to run](#5-find-out-what-a-signal-needs-to-run) | Params, warm-up and the indicators beneath it, before you call anything. |
| 6 | [Decide whether two outputs are comparable](#6-decide-whether-two-outputs-are-comparable) | Bounded does not mean same-scale; units and range say which. |
| 7 | [Check whether something is deprecated](#7-check-whether-something-is-deprecated-and-what-replaced-it) | And what supersedes it, from the edge rather than a naming convention. |
| 8 | [Explain why something is classified as it is](#8-explain-why-something-is-classified-the-way-it-is) | The claim and the derivation behind it are different routes through the graph. |
| 9 | [Ask about the values, not the nodes](#9-ask-about-the-values-not-the-nodes) | The output index answers questions `get()` cannot reach one node at a time. |
| 10 | [Filter by what something needs, and whether it is current](#10-filter-by-what-something-needs-and-whether-it-is-still-current) | Two enumerable vocabularies that reject a guess instead of returning nothing. |
| 11 | [Turn what the user said into a node](#11-turn-what-the-user-said-into-a-node) | Resolving a spoken name to an id, and what to do when it does not resolve. |
| 12 | [Go from the graph to an answer about live data](#12-go-from-the-graph-to-an-answer-about-live-data) | Using the graph to choose what to compute, then computing it. |
| 13 | [Compute an indicator the graph told you about](#13-compute-an-indicator-the-graph-told-you-about) | The node's `name` is the registered name — that is the join to runnable code. |
| 14 | [Pull what the knowledge base says about a subject](#14-pull-what-the-knowledge-base-says-about-a-subject) | Everything under a subject, whatever kind of node it is, by walking containment. |
| 15 | [Find the reasoning behind a piece of advice](#15-find-the-reasoning-behind-a-piece-of-advice) | The Judgment holds what to do, the Fact holds why, and folds hold where the two sources disagree. |
| — | [What this guide does not tell you](#what-this-guide-does-not-tell-you) | The graph's limits, and the questions it is the wrong tool for. |

## 1. Orient yourself in a library you have never seen

**Task:** "Have a look at mangrove-kb and tell me what's in it."

Do not start by listing files. Start with the graph's own summary:

```python
s = kg.stats()
s["nodes"], s["edges"]          # 427, 1267
s["primitives"]                 # {'Procedure': 295, 'Concept': 55, 'Property': 15, ...}
s["relations"]                  # {'instance-of': 364, 'uses': 234, 'about': 275, ...}
s["classes"]                    # the seven character classes -- what find(kind=) is for
s["roles"]                      # ['property:role-filter', 'property:role-trigger']
kg.schema()                     # the (subject, relation, object) shapes that actually occur
```

```
nodes, edges  427 1267
primitives    {'Procedure': 295, 'Concept': 55, 'Property': 15, 'Object': 1,
               'Schema': 1, 'Fact': 2, 'Judgment': 1}
relations     {'instance-of': 364, 'uses': 234, 'about': 275, 'has-role': 218,
               'kind-of': 32, 'part-of': 31, 'supersedes': 2}
classes       ['concept:averaging', 'concept:chart-pattern', 'concept:flow',
               'concept:momentum', 'concept:oscillator', 'concept:pattern',
               'concept:volatility']
roles         ['property:role-filter', 'property:role-trigger']
schema        [{'subject': 'Procedure', 'relation': 'instance-of', 'object': 'Concept'},
               {'subject': 'Procedure', 'relation': 'about',       'object': 'Concept'},
               {'subject': 'Procedure', 'relation': 'has-role',    'object': 'Property'},
               ... 23 shapes in total]
```

`schema()` is the one to read carefully. It tells you what questions are answerable *before* you ask
one and get an empty result you might misread as "there are none".

**Trap:** `stats()["classes"]` returns full node ids (`concept:momentum`), but every filter
also accepts the short name (`"momentum"`). Both work; the ids are what you get back.

`classes` is deliberately the six and not every class-like node. `find(kind=...)` *also* accepts
`"indicator"` (71), `"signal"` (218) and `"technical-analysis"` (299 of 427) — legal, occasionally
useful, and not classes. A filter that returns almost everything reads like a query and acts like a
no-op, so they are documented here rather than advertised as vocabulary.

**See also:** [§2 does it exist](GUIDE.md#2-check-whether-something-already-exists-before-building-it) · [SKILL · which call](SKILL.md#which-call) · [§14 the knowledge layer](GUIDE.md#14-pull-what-the-knowledge-base-says-about-a-subject)

---

## 2. Check whether something already exists before building it

**Task:** "Add a signal that fires when RSI diverges from price."

The expensive failure is writing a duplicate. They named two things — a word (*divergence*) and an
indicator (*RSI*) — so ask about both. Three searches, cheap:

```python
kg.neighbors(kg.resolve("RSI"), relation="uses", direction="in", limit=None)  # what is built on RSI
kg.find("divergence")                                                        # the word they used
kg.find(kind="oscillator", role="trigger")                                   # what it is + how it is used
```

**Start with the indicator.** Everything built on RSI is one hop away, and the hop is exact — nothing
ranked, nothing guessed:

```
8 signals read RSI
  procedure:signal-rsi-bearish-divergence          <- the four divergences
  procedure:signal-rsi-bullish-divergence
  procedure:signal-rsi-hidden-bearish-divergence
  procedure:signal-rsi-hidden-bullish-divergence
  procedure:signal-rsi-cross-down                  procedure:signal-rsi-overbought
  procedure:signal-rsi-cross-up                    procedure:signal-rsi-oversold
```

That already answers it: four RSI divergence signals exist. Do not write a fifth.

Text search is the wider net, for when they did *not* name an indicator, or named one you do not
have:

```
find("divergence") -> 38 matches, name matches first
  procedure:signal-rsi-bearish-divergence
  procedure:signal-rsi-bullish-divergence
  procedure:signal-rsi-hidden-bearish-divergence
  procedure:signal-rsi-hidden-bullish-divergence
  procedure:indicator-klingervolumeoscillator      <- from here down, matched in prose only
  procedure:indicator-kvo
  procedure:indicator-roc
  procedure:indicator-swingdelta
```

Results are ranked by *where* the query matched: name, then abbreviation, then summary, then the
authored detail (formula, interpretation, applications, and the names and descriptions of inputs,
params and outputs). The thing actually called "divergence" comes before things that merely mention
it, so the long tail costs you nothing — read down until the matches stop being about your term.

**The rule worth carrying:** text search finds things that *mention* a word; `neighbors` finds things
that *use* the computation. When the request names an indicator, the second one is the answer and the
first one is the sanity check.

**Trap:** results are capped at 10 by default. `Result.truncated` and `Result.note` tell you when
there are more. Pass `limit=None` when the count itself is the answer — here the default would have
shown you 10 of 38.

**See also:** [§3 what breaks](GUIDE.md#3-work-out-what-a-change-breaks) · [§11 name to id](GUIDE.md#11-turn-what-the-user-said-into-a-node) · [§14 what the knowledge base says](GUIDE.md#14-pull-what-the-knowledge-base-says-about-a-subject)

---

## 3. Work out what a change breaks

**Task:** "I want to change RSI's output range. What depends on it?"

```python
readers = kg.neighbors("procedure:indicator-rsi", relation="uses",
                       direction="in", limit=None)
for r in readers:
    print(r["id"], r["inputs"])      # which output each reader actually reads
```

```
8 readers
  procedure:signal-rsi-bearish-divergence  {'rsi': {'type': 'series'}}
  procedure:signal-rsi-bullish-divergence  {'rsi': {'type': 'series'}}
  procedure:signal-rsi-cross-down          {'rsi': {'type': 'series'}}
  procedure:signal-rsi-cross-up            {'rsi': {'type': 'series'}}
  ...
```

All eight read the same single output, so a change to `rsi` touches all of them and a change to
anything else touches none.

The `inputs` on the edge is the point: a reader that only takes `rsi` is unaffected by a change to a
second output, and the graph tells you which is which without opening a file.

Widen to the neighbourhood when you need the shape rather than the list:

```python
kg.subgraph("procedure:indicator-rsi", radius=1)
```

**See also:** [§12 graph to live data](GUIDE.md#12-go-from-the-graph-to-an-answer-about-live-data) · [SKILL · edges carry data](SKILL.md#the-typed-detail-is-the-point)

---

## 4. Compose a strategy from both axes

**Task:** "Build a strategy with a momentum trigger and a volatility filter."

This is the query the two axes exist for:

```python
triggers = kg.find(kind="momentum",   role="trigger", limit=None)
filters  = kg.find(kind="volatility", role="filter",  limit=None)
```

```
momentum triggers   25      volatility filters  16
  procedure:signal-adosc-cross-down       procedure:signal-atr-high-volatility
  procedure:signal-adosc-cross-up         procedure:signal-bb-above-upper
  procedure:signal-ao-zero-cross          procedure:signal-bb-below-lower
```

`kind` is the character a computation is concerned with; `role` is the part it *plays*. They are
independent — a signal can be momentum-class and used as either a trigger or a filter.

**`kind` means something different on each layer, and the graph says which.** An indicator
`instance-of` momentum *measures* rate of change. A signal is `about` momentum — it emits a boolean,
so it measures nothing; it is concerned with momentum because of the indicator it reads. `find(kind=)`
returns both, because "everything to do with momentum" is the useful question, but the two edges stay
distinguishable so you can always ask *why* (use case 8).

**Trap:** a signal can be about **two** classes. The RSI divergence signals read both an oscillator
and a momentum indicator, so they appear under both. Do not assume the sets are disjoint.

**See also:** [SKILL · the two axes](SKILL.md#the-two-axes-the-thing-to-understand) · [§8 why it is classified that way](GUIDE.md#8-explain-why-something-is-classified-the-way-it-is) · [§5 what it needs to run](GUIDE.md#5-find-out-what-a-signal-needs-to-run)

---

## 5. Find out what a signal needs to run

**Task:** "Can I use `rsi_oversold` on 50 bars of 1-minute data?"

```python
sig = kg.get("rsi_oversold")       # get() resolves a name; you do not need the id
sig["params"]        # every knob, with its range and default
sig["warmup_bars"]   # an EXPRESSION in those params -- e.g. 'window'
sig["inputs"]        # which OHLCV columns it needs
kg.neighbors(sig["id"], relation="uses", direction="out")   # the indicators beneath it
```

```
params       {'window':    {'type': 'int',   'default': 14,   'min': 2,   'max': 100},
              'threshold': {'type': 'float', 'default': 30.0, 'min': 0.0, 'max': 50.0}}
warmup_bars  'window'
inputs       {'close': {'type': 'series', 'description': 'closing price'}}
uses         ['procedure:indicator-rsi']
```

So with the default `window=14` it needs 14 bars, and 50 is plenty. With `window=100` it is not.

**Trap:** `warmup_bars` is a formula, not a number — `window * 3 - 1`, and worse. To answer "is 50
bars enough", substitute the params you intend to use. Comparing the string numerically is
meaningless.

**See also:** [§13 run it](GUIDE.md#13-compute-an-indicator-the-graph-told-you-about) · [SKILL · the typed detail](SKILL.md#the-typed-detail-is-the-point)

---

## 6. Decide whether two outputs are comparable

**Task:** "Can I put RSI and ADX on the same axis?"

```python
for ind in ("procedure:indicator-rsi", "procedure:indicator-adx", "procedure:indicator-obv"):
    for name, spec in kg.get(ind)["outputs"].items():
        print(ind, name, spec["units"], spec["range"])
```

```
rsi      rsi       units=dimensionless  range=[0, 100]
adx      adx       units=dimensionless  range=[0, 100]
adx      adx_pos   units=dimensionless  range=[0, 100]
adx      adx_neg   units=dimensionless  range=[0, 100]
obv      obv       units=dimensionless  range=[-inf, inf]     <- NOT comparable with the above
```

RSI and ADX share units and bounds, so they belong on one axis. OBV shares the units but is
unbounded, so it does not.

Same units and a shared bounded range means comparable; anything unbounded does not belong on a
shared scale with anything bounded.

**Trap:** unbounded is written `[-inf, inf]`, not `null`. A naive "does it have a range" check passes
for unbounded outputs. Test the endpoints for infinity — or let `outputs(bounded=…)` do it, which is
the next use case.

**See also:** [§9 the value index](GUIDE.md#9-ask-about-the-values-not-the-nodes) · [SKILL · units and range](SKILL.md#the-typed-detail-is-the-point)

## 7. Check whether something is deprecated, and what replaced it

**Task:** "Should I use `hanging_man_trigger`?"

```python
sig = kg.get("hanging_man_trigger")                          # the name they gave you resolves
sig["status"]                                                # 'deprecated'
kg.neighbors(sig["id"], relation="supersedes", direction="in")   # what replaced it, and why
```

```
status         'deprecated'
replaced by    procedure:signal-hammer-trigger
why            'computes the same thing under the canonical name'
```

The `why` on the edge carries the reason — here, *"computes the same thing under the canonical
name"*. That is the difference between "renamed" and "replaced because it was wrong", and you should
report which.

**Trap:** `status` is on the node, not the edge, and only 2 of 427 nodes are deprecated. Check it
explicitly; nothing else surfaces it.


**See also:** [§10 filter by status](GUIDE.md#10-filter-by-what-something-needs-and-whether-it-is-still-current) · [§2 before building](GUIDE.md#2-check-whether-something-already-exists-before-building-it)

---

## 8. Explain why something is classified the way it is

**Task:** "Why does `adosc_bearish` come back when I ask for momentum signals?"

**Answer it with `uses`.** The question is *what does this signal read*, and that is one call — no
search, no shortest-path behaviour to depend on:

```python
sig = kg.neighbors("adosc_bearish", relation="uses", direction="out")   # -> indicator-adosc
kg.get("adosc_bearish")            # and its own `about` edge names the class
```

```
adosc_bearish --uses--> ADOSC,  and ADOSC --instance-of--> momentum
```

It is about momentum because it reads ADOSC, and ADOSC measures momentum. Every `about` edge has a
`uses` edge behind it — the builder aborts if one does not — so this always terminates in an answer.

**When you do not already know the shape**, ask for every route rather than one:

```python
kg.all_paths("adosc_bearish", "momentum")
```

```
2 paths
  adosc_bearish --about--> momentum                                  the claim
  adosc_bearish --uses--> indicator-adosc --instance-of--> momentum  the reason
```

Both, in one call, shortest first. That is the difference between `all_paths` and `path`: `path`
returns the first of these and never mentions the second.

**Trap:** `path` returns the **shortest** connection, which is rarely the *explanatory* one — here
the one-hop `about` edge wins and the derivation disappears. This is not hypothetical: the guide
used to show a three-step `path` here, and adding the `about` edge silently turned it into one step.
If you use `path` for an explanation, constrain it — `relations=["uses", "instance-of"]` — or use
`all_paths` and read them all.

**Trap:** `all_paths` excludes routes through a shared parent by default. `adosc_bearish
--instance-of--> Signal <--instance-of-- adosc_bullish` says "they are both signals", and with
`concept:signal` at degree 218 those detours outnumber the real answers 9,638 to 2 at
`max_depth=5`. Pass `sibling_hops=True` when the shared parent *is* the answer — *"how are these two
related?" "they both read RSI"*.

**See also:** [SKILL · the two axes](SKILL.md#the-two-axes-the-thing-to-understand) · [§15 reasoning behind advice](GUIDE.md#15-find-the-reasoning-behind-a-piece-of-advice) · [§4 compose](GUIDE.md#4-compose-a-strategy-from-both-axes)

---

## 9. Ask about the values, not the nodes

**Task:** "Give me every bounded oscillator output I could put on a shared 0-100 panel."

`get()` answers this one node at a time, which means knowing the nodes first. `outputs()` indexes the
values themselves, so you can ask by what they *are*:

```python
rows = kg.outputs(bounded=True, kind="oscillator", limit=None)
rows.total                       # 48
```

**48 is not the answer**, and this is the trap worth internalising: `bounded=True` means *has two
finite endpoints*, not *on the same scale*. Those 48 span five different ranges — 37 of them are
`[0, 1]`, two are `[-1, 1]`, two `[-100, 100]`, one `[-100, 0]`. Putting them on one panel would be
wrong. The range is on every row, so filter it:

```python
panel = [r for r in rows if r["range"] == [0, 100]]
```

```
6 of 48 are actually on [0, 100]
  mfi                   mfi                  dimensionless  [0, 100]
  rsi                   rsi                  dimensionless  [0, 100]
  stc                   stc                  dimensionless  [0, 100]
  stochasticoscillator  stoch_d              dimensionless  [0, 100]
  stochasticoscillator  stoch_k              dimensionless  [0, 100]
  ultimateoscillator    ultimate_oscillator  dimensionless  [0, 100]
```

A row is an **output**, not a node — MACD contributes three — because comparability is a property of
one output, not of its producer. Every row names its producer, so `get()` and `neighbors()` are the
obvious next call.

It also runs the reverse lookup, which `resolve()` cannot: `resolve("histogram")` raises, because
`histogram` is nobody's node name.

```python
kg.outputs("histogram", limit=None)
# procedure:indicator-macd  histogram  price  [-inf, inf]
#   'macd minus signal. Crosses zero exactly when macd crosses it'
```

The other filters are `units=` (`kg.stats()["units"]` enumerates them; `percent` matches 28) and
`bounded=False` for the unbounded tail.

**Trap:** `units=` is an exact match against a deliberately heterogeneous vocabulary — a unit is a
statement about what a computation measures, so a percentage change, a price, a quotient and an
index number are labelled differently on purpose. SwingDelta goes further: its deltas are labelled
`indicator units` because they carry whatever unit the companion indicator it reads has, which is
not knowable until you supply one. Read `stats()["units"]` and filter on what is there.

**See also:** [§6 comparability](GUIDE.md#6-decide-whether-two-outputs-are-comparable) · [SKILL · the typed detail](SKILL.md#the-typed-detail-is-the-point)

---

## 10. Filter by what something needs, and whether it is still current

**Task:** "Give me trigger signals I can run on a feed with no volume column — and nothing retired."

```python
kg.find(requires="volume", role="trigger", limit=None)   # the ones to EXCLUDE
kg.find(status="deprecated", limit=None)                 # everything superseded, in one call
```

```
volume triggers   8    adosc-cross-down, adosc-cross-up, kvo-bearish-cross, kvo-bullish-cross,
                       pvo-bearish-cross, ...
deprecated        2    procedure:signal-hanging-man-trigger
                       procedure:signal-shooting-star-trigger
```

Both vocabularies are enumerable — `stats()["input_columns"]` runs from the implemented
indicators' columns (`close, high, low, open, volume`) to the terms the chapter formulas declare
(`bid`, `ask`, `adv`, `order_size`, …), and `stats()["statuses"]` is `draft, deprecated, ratified`. Use case 7 checks deprecation on
a node you already suspect; this is the sweep that finds the ones you did not.

**Trap:** a guessed value raises rather than returning an empty result. `find(requires="vwap")` is a
`GraphError` naming the real columns, not a quiet zero you would read as "nothing needs it".

**See also:** [§7 deprecation](GUIDE.md#7-check-whether-something-is-deprecated-and-what-replaced-it) · [§5 what it needs](GUIDE.md#5-find-out-what-a-signal-needs-to-run)

---

---

---

## 11. Turn what the user said into a node

**Someone says:** *"is there an rsi oversold signal?"*

They gave you a name, not a node id. Every use case above starts from an id like
`procedure:signal-rsi-oversold`, and nothing hands you one — you have to get there first.

```python
kg.resolve("rsi_oversold")     # exact function name
kg.resolve("RSI")              # or an indicator name
kg.resolve("bollinger")        # or an unambiguous fragment
```

```
procedure:signal-rsi-oversold
procedure:indicator-rsi
procedure:indicator-bollingerbands
```

`resolve` takes an id, a name, or any fragment that matches exactly one node. When the fragment
matches several, it does not pick one — it raises and hands you the candidates:

```python
from mangrove_kb.graph import NodeNotFound

try:
    kg.resolve("rsi_over")
except NodeNotFound as e:
    print(e.suggestions)
```

```
['procedure:signal-rsi-overbought', 'procedure:signal-rsi-oversold',
 'procedure:signal-stochrsi-overbought', 'procedure:signal-stochrsi-oversold']
```

**That message is the next step, not a failure.** Catch it and either pick from `e.suggestions` or
show them to the user. The one case it cannot help with is a phrase — `resolve("rsi oversold")` with
a space matches nothing, because no node is named that. Fall back to search:

```python
def lookup(words):
    """Whatever the user typed -> a node, or a shortlist to ask them about."""
    try:
        return kg.get(words)
    except NodeNotFound as e:
        if e.suggestions:
            return kg.get(e.suggestions[0])
        return kg.find(words)               # phrases, typos, descriptions

lookup("rsi_oversold")["id"]                # 'procedure:signal-rsi-oversold'
lookup("rsi_over")["id"]                    # 'procedure:signal-rsi-overbought' -- first suggestion
[r["id"] for r in lookup("rsi oversold")]   # a phrase falls through to find()
```

**Trap:** `find("oversold")` ranks by *where* the term matched, and `cci_oversold` sorts before
`rsi_oversold` because rank ties break on id alphabetically. If the user named an indicator too,
filter on it — `kg.find("oversold", kind="oscillator")` — or resolve the indicator first and look at
what reads it. Do not assume the first hit is the one they meant.

**See also:** [§2 does it exist](GUIDE.md#2-check-whether-something-already-exists-before-building-it) · [SKILL · which call](SKILL.md#which-call)

---

## 12. Go from the graph to an answer about live data

**Someone says:** *"set me up a momentum entry with a volatility filter, and tell me whether it fires
right now."*

Every use case up to here stops at a query result. This is the one that closes the loop: the graph
names a function, and the same package runs it.

```python
trigger = kg.find(kind="momentum",   role="trigger", limit=None).items[0]
filt    = kg.find(kind="volatility", role="filter",  limit=None).items[0]

t, f = kg.get(trigger["id"]), kg.get(filt["id"])
sorted(set(t["inputs"]) | set(f["inputs"]))     # the columns your data must have
t["warmup_bars"], f["warmup_bars"]              # expressions in each one's own params
```

```
trigger  procedure:signal-adosc-cross-down     filter  procedure:signal-atr-high-volatility
inputs   ['close', 'high', 'low', 'volume']
warmup   'slow + 1'  /  'window - 1'
```

Check they are not the same bet wearing two hats — two signals reading one indicator are not
independent confirmation:

```python
set(n["id"] for n in kg.neighbors(t["id"], relation="uses", direction="out")) \
    & set(n["id"] for n in kg.neighbors(f["id"], relation="uses", direction="out"))
# set()  -- adosc and atr, genuinely independent
```

Now run them. **The node\'s `name` is the registered signal name** — that is the join between the
graph and the code:

```python
from mangrove_kb import RuleRegistry, sample_ohlcv

df = sample_ohlcv()          # or your own frame with those columns
fired = RuleRegistry.evaluate({"name": t["name"], "params": {"fast": 3, "slow": 10}}, df)
gated = RuleRegistry.evaluate({"name": f["name"], "params": {"window": 14, "threshold_pct": 3.0}}, df)
fired and gated
```

```
adosc_cross_down     True
atr_high_volatility  True
composed             True
```

So the answer to the user is: *yes — `adosc_cross_down` fired and `atr_high_volatility` confirms the
regime, on 200 bars where both needed at most 13.*

Want the shape rather than the list, to explain the setup? `subgraph` returns the neighbourhood and
every edge inside it:

```python
kg.subgraph(t["id"], radius=1)
# 5 nodes, 5 edges:
#   concept:momentum, concept:signal, procedure:indicator-adosc,
#   procedure:signal-adosc-cross-down, property:role-trigger
#
# The class is IN the neighbourhood -- the signal's `about` edge reaches it in one hop, and
# `indicator-adosc --instance-of--> momentum` comes along because subgraph returns every edge
# BETWEEN the nodes it returns, so the derivation is visible in the fragment itself.
```

**Trap:** `RuleRegistry.evaluate` needs the signal\'s module imported before the name is registered.
`from mangrove_kb.signals import momentum, volatility` (or whichever class the graph gave you — the
module is named for it) before evaluating, or you get `Unknown rule name`.

**See also:** [§3 what breaks](GUIDE.md#3-work-out-what-a-change-breaks) · [§13 compute it](GUIDE.md#13-compute-an-indicator-the-graph-told-you-about)

---

## 13. Compute an indicator the graph told you about

**Someone says:** *"can I plot RSI and ADX on one panel? show me the current values."*

Use case 6 answered the first half from `units` and `range`. The second half needs the indicator
actually run, and the node carries a copy-pasteable call:

```python
kg.get("procedure:indicator-rsi")["usage_example"]
kg.get("procedure:indicator-adx")["usage_example"]
```

```
RSI.compute(data={'close': df['close']}, params={'window': value})
ADX.compute(data={'high': df['high'], 'low': df['low'], 'close': df['close']}, params={'window': value})
```

Substitute your params and run it:

```python
from mangrove_kb.indicators import RSI, ADX

rsi = RSI.compute(data={"close": df["close"]}, params={"window": 14})["rsi"]
adx = ADX.compute(data={"high": df["high"], "low": df["low"], "close": df["close"]},
                  params={"window": 14})["adx"]
rsi.iloc[-1], adx.iloc[-1]
```

```
rsi  25.72      adx  63.05
both dimensionless on [0, 100]  ->  one panel is fine
```

**Trap:** `usage_example` writes `params={'window': value}` — `value` is a placeholder, not a
default. The real defaults are in `kg.get(id)["params"]`, with `min` and `max` beside them.

**See also:** [§5 what it needs](GUIDE.md#5-find-out-what-a-signal-needs-to-run) · [§12 graph to live data](GUIDE.md#12-go-from-the-graph-to-an-answer-about-live-data)

---

## 14. Pull what the knowledge base says about a subject

**Task:** "What do we actually know about liquidity?"

The graph holds two kinds of thing and one call spans both. Start with the node, then widen:

```python
kg.get("concept:liquidity")
kg.find(under="concept:liquidity", limit=None)          # everything beneath it, any primitive
kg.neighbors("concept:liquidity", limit=None)           # what quantifies it, what it is part of
```

```
summary       The ease with which an asset can be bought or sold without materially moving
              its price.
source_wording
              The chapter's own phrasing, kept when it differs materially from the
              authored summary -- an outer join, so neither statement is lost.
applications  Estimating realistic execution costs for strategy backtesting
              Determining optimal order sizing based on available liquidity
neighbors  in   about    property:participation-rate
           out  about    fact:market-foundations-core-principles
           out  about    judgment:market-foundations-best-practices
           out  part-of  concept:market-foundations
```

Direction carries meaning. **Incoming** `about` is what quantifies liquidity — participation rate,
a number an execution has. **Outgoing** `about` is what is known about it: the principles that hold
and the practices that follow, each statement on its edge.

Note the primitive. `property:` is a **quantity** something has, the way `atr` is a number a bar
has; `procedure:` is a method you run. Neither has code behind it here — `get()` gives you the
formula and there is no `RuleRegistry` name to call. Reading every stated formula as a Procedure is
the easy mistake, and it hides the other two: `Put-Call Parity` is a `Fact`, an identity that holds,
and breaking it is an arbitrage rather than a failed function call.

Widen by subject rather than by node when the question is broader. `find(under=…)` walks containment
— `part-of` as well as `kind-of` and `instance-of` — and is primitive-blind:

```python
kg.find(under="market foundations", limit=None)                 # 100 nodes
kg.find(under="market foundations", primitive="Procedure")      # just its computations
kg.find("spread", under="market foundations")                   # scoped text search
```

**Trap:** do not reach for `reference_chapter`. It is provenance on nodes that predate a chapter
node, not the retrieval mechanism — the edges are, and they are what `under=` walks.

**See also:** [SKILL · two halves, one surface](SKILL.md#two-halves-one-retrieval-surface) · [§15 the reasoning](GUIDE.md#15-find-the-reasoning-behind-a-piece-of-advice) · [§2 does it exist](GUIDE.md#2-check-whether-something-already-exists-before-building-it)

---

## 15. Find the reasoning behind a piece of advice

**Task:** "Why does executing a large order slowly cost less?"

Each subject carries two nodes beside its concepts: a `Fact` holding what is true of it, and a
`Judgment` holding what to do about it. They are separate primitives because they answer to
different standards — a Fact is settled by measurement, a Judgment by argument.

**Ask the concept, not the lists.** A statement that concerns a node hangs off that node, and the
edge carries the statement itself:

```python
kg.neighbors("concept:market-impact", relation="about", direction="out")
```

```
fact:…-core-principles      Impact is Non-Linear: market impact grows faster than linearly with
                            order size · Urgency-Cost Tradeoff: faster execution incurs higher
                            market impact; slower execution risks adverse price movement
judgment:…-best-practices   Consider total cost of execution including fees, spread, and market
                            impact
```

Two hops from the node to the reason, and the reason is on the edge rather than buried in a
thirty-line property. `concept:dark-pool` answers the same way, and so does every concept the
chapter says anything about.

**A statement lives in exactly one place.** Until it concerns a node it sits in the list; once it
does, it moves onto the edge. So what remains in `["principles"]` and `["practices"]` is precisely
what has not been connected yet — a backlog, not an index. Read the lists to see what is missing;
read the edges to see what is known.

**Where the book and the code disagree.** When a chapter defines something the library already
implements, the node folds and the two statements are kept side by side rather than one overwriting
the other:

```python
kg.get("procedure:indicator-atr")["chapter_variants"]
# {'formula': 'TR = max(High - Low, |High - Previous Close|, |Low - Previous Close|)\n
#              ATR = EMA(TR, n periods)'}
```

The node's own `formula` is the implementation's; `chapter_variants` is the chapter's wording of the
same computation, unreconciled. A key in there means nobody has decided yet — not that either is
wrong.

**Trap:** a Judgment is not a fact and must not be reported as one. It is argued from practice and
is context-dependent — "use limit orders" is advice to a liquidity taker and meaningless to a market
maker. Quote it as guidance, with the principle behind it.

**See also:** [§14 the whole subject](GUIDE.md#14-pull-what-the-knowledge-base-says-about-a-subject) · [SKILL · two halves, one surface](SKILL.md#two-halves-one-retrieval-surface) · [§8 classification](GUIDE.md#8-explain-why-something-is-classified-the-way-it-is)

---

## What this guide does not tell you

The graph describes what the library *does*, never whether it is a good idea. A signal existing, or
carrying the `trigger` role, says nothing about whether it works on your data, your timeframe, or
your instrument. Backtest before you believe anything.

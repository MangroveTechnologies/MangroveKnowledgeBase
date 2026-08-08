"""Emit the signal/indicator class ontology as graph atoms + relations.

STAGE 1 of a two-stage pipeline. This script only LIFTS -- it never authors:

    build_signal_indicator_ontology.py  >  ontology/signal-indicator-ontology.json
    author the null fields IN THE NODES                                    (by hand)

The emitted JSON is the ontology of record and is committed to this repository. Authored values
live in the nodes, so this builder must never destroy them: it reads the existing file and carries
every authored value forward (see the carry-forward block near the end). Running it twice is a
no-op -- the output is a fixed point.

Rendering the graph to an interactive page is deliberately NOT part of this repository; the viewer
is a separate, differently-licensed component that consumes the JSON emitted here.

Design decisions live in `ontology/signal-indicator-ontology.md`; the literature research behind
the authored values is in `ontology/research/`.

What gets lifted, and from where:
  - class attributes (`_data` / `_params` / `_outputs`)  -> inputs, params, outputs keys
  - indicator docstring                                   -> summary prose, reference URL, param types
  - the docstrings of SIGNALS that wrap each indicator    -> param default / min / max / description,
                                                             resolved by AST call-graph
  - `min_periods` in `_compute`                           -> warmup_bars, where unambiguous
  - knowledge-base markdown (`knowledge-base/*.md`)       -> definition (feeds `summary`), formula,
                                                             interpretation, applications, abbreviation
  - generated from the class attributes                   -> usage_example

Everything else is emitted as `null` and must be authored by reading `_compute`: per-output `units`,
`range`, `canonical_name` and `description`, and per-input `description`. Those nulls ARE the
worklist -- see the invariant enforced at the bottom of this file.

Two fail-loud contracts, both deliberate: the class assignments abort on any indicator that is
unknown, unassigned or double-assigned, and the build aborts on any output carrying a `description`
without `units`/`range` (the signature of prose authored without the machine-readable fields).
"""
import importlib
import inspect
import pathlib
import json, re, glob, sys, textwrap
import os

# Read THIS repository, not whatever `mangrove_kb` happens to be installed.
#
# An installed `mangrove_kb` is typically a plain site-packages directory rather than an editable
# install, so `import mangrove_kb` can resolve to a release snapshot instead of the tree being
# edited. Everything this builder lifts -- docstring prose, param metadata from the signals, the
# knowledge-base markdown -- must come from the working tree, so the repo root is put ahead of
# site-packages explicitly. `MANGROVE_KB_REPO` overrides it for the unusual case of building the
# ontology against a different checkout.
KB_REPO = pathlib.Path(os.environ.get(
    "MANGROVE_KB_REPO", pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(KB_REPO))
KB = str(KB_REPO / "mangrove_kb" / "indicators")

CLASSES_DEF = {
 'averaging': "Emits a reference level in price units, produced by averaging over a window.",
 'momentum': "Measures rate of change -- how fast, and in which direction, the input is moving.",
 'oscillator': "Bounded output where absolute thresholds are meaningful (overbought/oversold).",
 'volatility': "Measures observed dispersion -- distance, width, or range.",
 'flow': "Running accumulation whose level is arbitrary but whose direction carries meaning.",
 'pattern': "Shape of one or a few bars (candlestick geometry).",
 'unclassed': "No class determined yet. Deliberately named so the gap stays visible.",
}
ASSIGN = {
 'averaging': "SMA EMA WMA DEMA TEMA TRIMA SMMA HMA ALMA T3 KAMA VWMA VWAP MAMA WilliamsAlligator",
 'momentum': "ROC MOM TRIX MACD PPO KST AwesomeOscillator DPO PVO ForceIndex EaseOfMovement "
             "ADOSC KVO KlingerVolumeOscillator DailyReturn DailyLogReturn MassIndex ADX Aroon "
             "Vortex MultiTFTrend",
 'oscillator': "RSI StochasticOscillator StochRSI WilliamsR MFI UltimateOscillator CMO TSI BOP STC CCI CMF",
 'volatility': "ATR TrueRange NATR UlcerIndex BollingerBands KeltnerChannel DonchianChannel STARCBands "
               "ChandelierLevels",
 'flow': "OBV ADI VPT NVI CumulativeReturn",
 'unclassed': "EPMA Ichimoku HeikinAshi TTMSqueeze Divergence",
}
# Not indicators: their outputs are VERDICTS, not measurements. SuperTrend emits `direction`
# (+1 long / -1 short) and NaNs its bands according to it; PSAR emits flip flags; ATRTrailingStop
# and VolatilityStop carry a position state forward. An indicator states what it measured, and
# deciding what that means is the signal layer's job.
#
# ChandelierExit was on this list and should not have been: it emits two price levels, both defined
# every bar, both plain functions of the window. It was excluded for being a "stateful policy rule"
# when its own docstring says it is not a state machine. It is now `ChandelierLevels`, class
# volatility. See `signal-indicator-ontology.md`.
REMOVED = "ATRTrailingStop VolatilityStop SuperTrend PSAR".split()

# --- ground truth from the installed package
present, mod_of = set(), {}
for f in glob.glob(f'{KB}/*_indicators.py'):
    m = f.split('/')[-1].replace('_indicators.py', '')
    for c in re.findall(r'^class (\w+)', open(f).read(), re.M):
        present.add(c); mod_of[c] = m
patterns = sorted(c for c in present if mod_of[c] == 'pattern')
ASSIGN['pattern'] = ' '.join(patterns)

assigned = {i: cls for cls, s in ASSIGN.items() for i in s.split()}
# --- integrity checks: fail loudly rather than emit a wrong graph
unknown = sorted(set(assigned) - present)
missing = sorted(present - set(assigned) - set(REMOVED))
dupes = [i for i in assigned if sum(i in s.split() for s in ASSIGN.values()) > 1]
if unknown or missing or dupes:
    print(f"ABORT unknown={unknown} unassigned={missing} duplicated={dupes}"); sys.exit(1)


# --- everything below is LIFTED from the class or its docstring. Nothing is guessed here; where a
# value is authored, it was authored INTO the docstring and is lifted from there like any other.
_SECTION = (r"\n\s*(?:Args|Returns|Formula|Formulas|Reference|References|Note|Notes|"
            r"Implementation|Outputs|Weights|Equivalently|Lookahead-free):")

# --- the authored per-output grammar, written into the docstring's Returns: block.
#
#     Returns:
#         mavg (series, price): rolling mean of close over window -- the center band.
#         wband (series, percent): band separation as a percent of the center band,
#             (hband - lband) / mavg * 100. Range: 0-inf.
#
# `name (type, units): description`, continuation lines indented further, and an optional
# `Range: lo-hi` clause anywhere in the description with `inf`/`-inf` for an unbounded side.
# This is the same shape `Args:` already uses for parameters, so it introduces no new convention.
# Indicators not yet authored keep the legacy dict-literal block and still yield their types.
_RET_LINE = re.compile(r"^(\s*)(\w+)\s*\(([^)]*)\)\s*:\s*(.*)$")
_RET_RANGE = re.compile(r"Range:\s*(-?inf|-?[\d.]+)\s*-\s*(-?inf|-?[\d.]+)", re.I)
# The name the literature uses for this series, where it differs from the output key -- BollingerBands
# emits `wband` and `pband` for what every text and our own Formula block call Bandwidth and %B.
# Without it the node contains a formula referring to names found nowhere else in the node.
_RET_CANON = re.compile(r"Canonical:\s*([^.\n]+)")


def _bound(tok):
    """`inf` / `-inf` mean unbounded on that side, which the schema spells as None."""
    return None if tok.lower().lstrip("-") == "inf" else _num(tok)


def _parse_returns(doc):
    """Parse an authored `Returns:` block into {output: {type, units, range, canonical_name, description}}.

    Grammar (see the module-level comment for a worked example):
        name (type, units): description text, wrapping onto further-indented lines.
            Range: lo-hi. Canonical: LiteratureName.

    `Range:` accepts `inf` / `-inf` for an unbounded side and is stripped out of the description;
    same for `Canonical:`. Returns {} for the legacy dict-literal form, so the caller falls back to
    type-only lifting and every un-migrated indicator still builds.

    Currently no indicator docstring uses this grammar -- authored values live in the graph nodes,
    not in `mangrove_kb` source. This parser exists so the option stays open without a rewrite.
    """
    blk = re.search(r"Returns:\n(.*?)(?:\n\s*\n|\Z)", doc, re.S)
    if not blk or blk.group(1).lstrip().startswith("{"):
        return {}

    out, current, indent = {}, None, None
    for line in blk.group(1).splitlines():
        if not line.strip():
            continue
        m = _RET_LINE.match(line)
        # A deeper-indented line with no `name (...)` header continues the previous description.
        if m and (indent is None or len(m.group(1)) <= indent):
            indent = len(m.group(1))
            name, spec, rest = m.group(2), m.group(3), m.group(4)
            parts = [p.strip() for p in spec.split(",")]
            current = out[name] = {
                "type": parts[0] or None,
                "units": parts[1] if len(parts) > 1 else None,
                "range": None,
                "canonical_name": None,
                "description": rest.strip(),
            }
        elif current is not None:
            current["description"] += " " + line.strip()

    for spec in out.values():
        text = spec["description"]
        rng = _RET_RANGE.search(text)
        if rng:
            spec["range"] = [_bound(rng.group(1)), _bound(rng.group(2))]
            text = _RET_RANGE.sub("", text)
        canon = _RET_CANON.search(text)
        if canon:
            spec["canonical_name"] = canon.group(1).strip()
            text = _RET_CANON.sub("", text)
        # Removing the Range: clause can leave a dangling separator, so trim trailing
        # whitespace and full stops together rather than in one fixed order.
        spec["description"] = re.sub(r"[\s.]+$", "", re.sub(r"\s+", " ", text)).strip() or None
    return out


_DOC_SECTION = re.compile(
    r"^(Formula|Interpretation|Applications):\s*\n(.*?)(?=^\w+:|\Z)", re.M | re.S)


def _doc_sections(doc):
    """{formula, interpretation, applications} written in the indicator's own docstring.

    The knowledge-base markdown covers only 41 of the 94 indicators, and nothing at all for
    indicators defined after it was written. An indicator documenting itself is the more natural
    home anyway, so a `Formula:` / `Interpretation:` / `Applications:` section here is lifted the
    same way -- and takes second place to the knowledge base, which is the curated source where
    both exist.

    `Formula` is kept as a block of text; the other two are split into bullets, matching the shape
    the knowledge-base lift produces so consumers see one format regardless of origin.
    """
    out = {}
    for m in _DOC_SECTION.finditer(doc or ""):
        name, body = m.group(1).lower(), textwrap.dedent(m.group(2)).strip("\n")
        if not body.strip():
            continue
        if name == "formula":
            out[name] = body.rstrip()
        else:
            out[name] = _bullets(body)
    return out


# Docstring-derived prose, stashed per class and applied only after carry-forward -- see the
# precedence note in `_lift`.
DOC_SECTIONS = {}


def _lift(cls):
    """Machine-derivable properties for one indicator.

    Returns the props dict for the atom. Anything no source states is returned as None, so the gap
    is queryable in the graph itself rather than merely described in a doc -- those nulls are the
    authoring worklist.

    Emitted as None here, to be authored by reading `_compute`:
      - `inputs.<name>.description`
      - `outputs.<name>.units` / `.range` / `.canonical_name` / `.description`

    Emitted from the docstring when it uses the authored `Returns:` grammar (see `_parse_returns`),
    otherwise from the legacy dict-literal block, which yields type only.

    NOTE the indicator description is NOT returned here. It belongs in the atom's native `summary`,
    which is its only home; carrying it in props as well would store one fact twice. The renderer
    maps summary -> props.description at render time.
    """
    doc = inspect.getdoc(cls) or ""
    head = re.split(_SECTION, doc)[0]
    lines = [l.strip() for l in head.splitlines() if l.strip() and not l.strip().startswith("http")]
    description = " ".join(lines[1:]) or None          # line 0 is the title; prose follows it

    url = re.search(r"https?://\S+", doc)

    # param TYPES are the one structural fact absent from the class attributes (_params holds
    # names only), so they come from the docstring params block -- verified to agree with
    # _params for all 99 indicators.
    ptypes = {}
    blk = re.search(r"params:\s*\{(.*?)\}", doc, re.S)
    if blk:
        ptypes = dict(re.findall(r"'(\w+)':\s*(\w+)", blk.group(1)))

    otypes = {}
    rblk = re.search(r"Returns:\s*\{(.*?)\}", doc, re.S)
    if rblk:
        otypes = {k: ("series" if v.endswith("Series") else v)
                  for k, v in re.findall(r"'(\w+)':\s*([\w.]+)", rblk.group(1))}

    # Authored per-output units/range/description, when the Returns: block uses the prose grammar.
    authored = _parse_returns(doc)

    # Per-input description, authored in the Args: block as `close (series): closing price`.
    idescs = {}
    ablk = re.search(r"Args:\n(.*?)(?:\n\s*\n|\Z)", doc, re.S)
    if ablk:
        for line in ablk.group(1).splitlines():
            m = _RET_LINE.match(line)
            if m and m.group(2) in cls._data:
                idescs[m.group(2)] = re.sub(r"\s+", " ", m.group(4)).strip().rstrip(".") or None

    DOC_SECTIONS[cls.__name__] = _doc_sections(doc)

    # warmup: min_periods is the only machine-readable hint, and only when unambiguous. It is a
    # GUESS, not a reading -- it assumes the rolling result is published on the bar it was computed
    # for. A `.shift(` breaks that assumption and makes the guess wrong by exactly the shift, so the
    # guess is withheld and the authored value stands. DonchianChannel is the case that exposed
    # this: excluding the current bar costs one extra warmup bar, and `min_periods=window` alone
    # cannot see it.
    src = inspect.getsource(cls)
    warm = sorted({m for m in re.findall(r"min_periods\s*=\s*([A-Za-z_]\w*|\d+)", src)})
    if ".shift(" in src:
        warm = []
    return {
        # NOTE: the indicator description is NOT returned here. It belongs in the atom's native
        # `summary` field -- the only place it is stored. `viz.data_from_rows` reads
        # props["description"], so the renderer maps summary -> props.description at render time;
        # carrying it in props as well would store one fact twice.
        "reference": url.group(0) if url else None,
        "warmup_bars": (f"{warm[0]} - 1" if len(warm) == 1 else None),
        "abbreviation": GLOSSARY_ABBR.get(cls.__name__),
        "usage_example": _usage_example(cls),
        # Lifted from the knowledge-base markdown; null on the indicators with no section there,
        # which puts them on the authoring queue like any other null.
        #
        # NOTE the KB `definition` is deliberately NOT a property. It is the same fact as the
        # atom's `summary`, and the schema rule is one fact, one home -- carrying both put two
        # descriptions on 34 of 94 nodes. It feeds `summary` instead, at the atom() call below.
        # Precedence for these three: knowledge base -> previously authored -> docstring. The KB is
        # the curated source where it has an entry. The docstring is only a BOOTSTRAP for
        # indicators nobody has authored yet, so it is applied after carry-forward, not here --
        # applying it here let a docstring that restates the code overwrite a researched formula
        # (it cost CMO its contested-default note and T3 the GD recursion + Tillson's factor).
        **{k: KB_SECTIONS.get(cls.__name__, {}).get(k)
           for k in ("formula", "interpretation", "applications")},
        "inputs": {d: {"type": "series", "description": idescs.get(d)} for d in cls._data},
        "params": {q: {"type": ptypes.get(q),
                       **{k: SIGNAL_PARAM_DOCS.get(cls.__name__, {}).get(q, {}).get(k)
                          for k in ("default", "min", "max", "description")}}
                   for q in cls._params},
        # Output TYPE is declared in the docstring Returns: block. Every one of the 136 typed
        # outputs is a pd.Series; the 27 pattern indicators carry no Returns: block at all but
        # were confirmed by execution to return Series too, so "series" is uniform and safe.
        # The informative distinction between outputs is the element dtype and value domain,
        # which `units` and `range` carry -- not this container type.
        "outputs": {o: {"type": (authored.get(o, {}).get("type") or otypes.get(o) or "series"),
                        "units": authored.get(o, {}).get("units"),
                        "range": authored.get(o, {}).get("range"),
                        "canonical_name": authored.get(o, {}).get("canonical_name"),
                        "description": authored.get(o, {}).get("description")}
                    for o in cls._outputs},
    }



# --- parameter metadata lifted from the SIGNALS that wrap each indicator.
# The indicator docstrings declare param names and types only; the prose, ranges and defaults
# live in the docstrings of the signals built on them (243/243 signals carry per-param prose).
# Recorded with provenance so a lifted value is auditable back to its source signal.
_PARAM_LINE = re.compile(r"^\s*(\w+)\s*\(([^)]*)\)\s*:\s*(.+)$")
_RANGE = re.compile(r"Range:\s*(-?[\d.]+)\s*-\s*(-?[\d.]+)")
# NOTE the lazy token plus lookahead. The obvious `([^.\s]+)` is WRONG: it stops at the first dot,
# so `Default: 0.05.` lifts as `0`. That silently corrupted 53 parameter defaults across the corpus --
# CCI's 0.015 scaling constant became 0 (which would make CCI infinite), PiercingLine's 0.5 minimum
# penetration became 0 (fires on anything), MAMA's 0.05 slow limit became 0. The trailing sentence
# period or comma is consumed by the optional class, and the lookahead requires whitespace or
# end-of-string after it, so an internal decimal point is kept while sentence punctuation is not.
_DEFAULT = re.compile(r"Default:\s*(\S+?)[.,]?(?=\s|$)")


def _num(x):
    """Parse a docstring literal into a value, or None if it is not one.

    Booleans are handled explicitly: a bool param writes `Default: false`, which `float()` rejects,
    so every boolean default lifted as None and looked unauthored. `require_gap` and
    `original_version` are the ones this hid.
    """
    if isinstance(x, str) and x.strip().lower().rstrip(".") in ("true", "false"):
        return x.strip().lower().rstrip(".") == "true"
    try:
        f = float(x)
        return int(f) if f == int(f) else f
    except ValueError:
        return None


def _sibling_functions(path, sigs_dir):
    """Top-level functions this file imports from another signal module, as {name: ast node}.

    Helper resolution used to be per-file, which was correct only while every helper lived beside
    the signals that call it. Splitting the files onto the ontology class moved `_ma_crossover` and
    `_ma_is_above` into `_common.py` -- both are called from `averaging.py` AND from the EPMA
    signals still in `trend.py`, so a helper used by two classes belongs to neither. Fifteen signals
    silently lost their `uses` edge, and with it their class, because the call went to a name this
    scan could no longer see.

    Resolved through the file's own imports rather than by pooling every function name in the
    package, so two modules may define the same private helper without shadowing each other.
    """
    import ast
    out = {}
    for node in ast.parse(path.read_text()).body:
        if not (isinstance(node, ast.ImportFrom) and (node.module or "").startswith("mangrove_kb.signals.")):
            continue
        sib = sigs_dir / (node.module.rsplit(".", 1)[-1] + ".py")
        if not sib.exists():
            continue
        sib_fns = {n.name: n for n in ast.walk(ast.parse(sib.read_text()))
                   if isinstance(n, ast.FunctionDef)}
        for alias in node.names:
            if alias.name in sib_fns:
                out[alias.asname or alias.name] = sib_fns[alias.name]
    return out


def _signal_param_docs():
    """{indicator name: {param: {description, min, max, default}}}"""
    import ast
    from mangrove_kb.registry import RuleRegistry
    # Importing the package registers every signal module, so this does not need updating each
    # time a file is split or renamed -- which it did, twice.
    import mangrove_kb.signals  # noqa: F401

    kbs = pathlib.Path(inspect.getfile(mangrove_kb.signals.trend)).parent
    out = {}
    for path in sorted(kbs.glob("*.py")):
        if path.name in ("__init__.py", "onchain.py", "defi_pro.py"):
            continue
        tree = ast.parse(path.read_text())
        sibling = _sibling_functions(path, kbs)
        local = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)} | set(sibling)
        info, reg = {}, {}
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)] + list(sibling.values()):
            inds, calls = set(), set()
            for nd in ast.walk(fn):
                if isinstance(nd, ast.Call):
                    f = nd.func
                    if isinstance(f, ast.Attribute) and f.attr == "compute" and isinstance(f.value, ast.Name):
                        inds.add(f.value.id)
                    elif isinstance(f, ast.Name) and f.id in local:
                        calls.add(f.id)
            info[fn.name] = (inds, calls)
            for d in fn.decorator_list:
                if (isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                        and d.func.attr == "register" and d.args):
                    reg[d.args[0].value] = fn.name

        def resolve(fname, seen=None):
            seen = seen or set()
            if fname in seen or fname not in info:
                return set()
            seen.add(fname)
            direct, calls = info[fname]
            got = set(direct)
            for c in calls:
                got |= resolve(c, seen)
            return got

        for signame, fname in reg.items():
            targets = resolve(fname)
            fn = RuleRegistry._registry.get(signame)
            if not fn or not targets:
                continue
            doc = inspect.getdoc(fn) or ""
            blk = re.search(r"Args:(.*?)(?:Returns:|\Z)", doc, re.S)
            if not blk:
                continue
            for line in blk.group(1).splitlines():
                m = _PARAM_LINE.match(line)
                if not m or m.group(1) == "df":
                    continue
                pname, ptype, rest = m.group(1), m.group(2).strip(), m.group(3).strip()
                desc = re.split(r"\s*(?:Range|Default):", rest)[0].strip().rstrip(".")
                rng, dflt = _RANGE.search(rest), _DEFAULT.search(rest)
                spec = {"description": desc or None,
                        "min": _num(rng.group(1)) if rng else None,
                        "max": _num(rng.group(2)) if rng else None,
                        "default": _num(dflt.group(1)) if dflt else None}
                for t in targets:
                    out.setdefault(t, {}).setdefault(pname, spec)
    return out


SIGNAL_PARAM_DOCS = _signal_param_docs()


# --- prose lifted from the knowledge-base markdown, which is authored independently of the code.
# Coverage is partial by construction: 50 `###` sections against 94 indicators, so most nodes get
# nulls here and land on the authoring queue. Matching is by the generated `**Indicator Class**`
# block where present, else by normalised title ("Keltner Channels" -> KeltnerChannel). Titles that
# match nothing are reported rather than silently dropped -- several are indicators we deliberately
# excluded (Parabolic SAR, VIX, Standard Deviation), and the rest would be a matching bug.
KB_DOC = KB_REPO / "knowledge-base" / "06-indicators.md"
GLOSSARY = KB_REPO / "knowledge-base" / "09-glossary.md"

# Doc titles whose name genuinely differs from the class name. Explicit data rather than a looser
# regex, because a fuzzy rule broad enough to catch these also produces false matches -- and a wrong
# join here silently attaches one indicator's prose to another.
KB_TITLE_ALIASES = {
    "Accumulation/Distribution Line (ADL)": "ADI",   # same measure, different expansion
    # The KB section states the Volume Force / dm-cm construction, which is Klinger's ORIGINAL --
    # not the simplified signed-volume form that `KVO` implements. It used to be joined to `KVO`,
    # attaching one variant's prose to the other on the one indicator in the corpus where the two
    # variants are ~145x apart in scale.
    "Klinger Volume Oscillator": "KlingerVolumeOscillator",
    "Vortex Indicator": "Vortex",
}
# Sections that legitimately match nothing: indicators we deliberately excluded, or breadth/market
# measures with no class at all. Listed so the unmatched report stays a signal rather than noise.
KB_TITLES_NOT_INDICATORS = {
    "Parabolic SAR",                 # removed from the indicator layer: stateful policy rule
    "Standard Deviation", "Volatility Index (VIX)", "Advance-Decline Line",
    "Arms Index (TRIN)", "McClellan Oscillator", "McClellan Summation Index",
    "Daily and Cumulative Returns",  # one section covering DailyReturn AND CumulativeReturn
}


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _variants(title):
    """Normalised forms a doc title might take: full, sans-parenthetical, each parenthetical,
    and the singular of each -- the doc pluralises ("Keltner Channels" -> KeltnerChannel)."""
    raw = [title, re.sub(r"\s*\(.*?\)", "", title)] + re.findall(r"\(([^)]+)\)", title)
    forms = {_norm(r) for r in raw if r.strip()}
    return forms | {f[:-1] for f in forms if f.endswith("s")}


def _bullets(body):
    got = [re.sub(r"\s+", " ", l.strip()[1:]).strip() for l in body.splitlines()
           if l.strip().startswith("- ")]
    return got or None


def _kb_sections():
    """Lift per-indicator prose from `knowledge-base/06-indicators.md`.

    Returns ({indicator: {definition, formula, interpretation, applications}}, [unmatched titles]).

    Coverage is partial BY CONSTRUCTION -- 50 doc sections against 94 indicators, and `Trading
    Applications` appears in only 14 of them. Most nodes get nulls here and land on the authoring
    queue; do not read a null as "the doc says nothing interesting", read it as "nobody has written
    it yet".

    Matching, in order: the generated `**Indicator Class**` block; then KB_TITLE_ALIASES; then the
    normalised title with singular/plural variants. Titles matching nothing are returned as
    unmatched UNLESS declared in KB_TITLES_NOT_INDICATORS, which keeps that report a signal rather
    than noise. A wrong join here silently attaches one indicator's prose to another, which is why
    the fuzzy step is deliberately narrow and the exceptions are explicit data.

    `definition` is lifted but does NOT become a property -- it feeds the atom's `summary` at the
    atom() call, because it is the same fact and the schema rule is one fact, one home.
    """
    if not KB_DOC.exists():
        return {}, []
    text = KB_DOC.read_text()
    parts = re.split(r"\n### (?:\d+\.\d+\.\d+) (.+)\n", text)
    by_norm = {_norm(c): c for c in present}
    out, unmatched = {}, []
    for i in range(1, len(parts) - 1, 2):
        title, body = parts[i], parts[i + 1]
        declared = re.search(r"\*\*Indicator Class\*\*:\s*`(\w+)`", body)
        if declared and declared.group(1) in present:
            ind = declared.group(1)
        elif title in KB_TITLE_ALIASES:
            ind = KB_TITLE_ALIASES[title]
        else:
            ind = next((by_norm[c] for c in _variants(title) if c in by_norm), None)
        if ind is None:
            if title not in KB_TITLES_NOT_INDICATORS:
                unmatched.append(title)
            continue
        sect = {m.group(1).strip(): m.group(2) for m in
                re.finditer(r"^#### (.+?)$\n(.*?)(?=^#### |\Z)", body, re.M | re.S)}
        fence = re.search(r"```\n(.*?)```", sect.get("Formula", ""), re.S)
        out[ind] = {
            "definition": re.sub(r"\s+", " ", sect.get("Definition", "")).strip() or None,
            "formula": fence.group(1).strip() if fence else None,
            "interpretation": _bullets(sect.get("Interpretation", "")),
            "applications": _bullets(sect.get("Trading Applications", "")),
        }
    return out, unmatched


def _glossary():
    """{indicator: abbreviation} from the `09-glossary.md` table.

    Matches on the spelled-out term AND on the abbreviation column, because the class name is as
    often the abbreviation (ATR, ADX, CCI) as the full term. Rows with no abbreviation are skipped.
    Coverage is thin -- roughly 12 of 94 -- so most abbreviations are authored.
    """
    if not GLOSSARY.exists():
        return {}
    by_norm = {_norm(c): c for c in present}
    out = {}
    for row in re.findall(r"^\|([^|]+)\|([^|]+)\|([^|]+)\|", GLOSSARY.read_text(), re.M):
        term, _defn, abbr = (c.strip() for c in row)
        if abbr in ("-", "", "Abbreviation"):
            continue
        # the class name is as often the abbreviation (ATR, ADX, CCI) as the spelled-out term
        ind = next((by_norm[c] for c in (_variants(term) | {_norm(abbr)}) if c in by_norm), None)
        if ind:
            out[ind] = abbr
    return out


KB_SECTIONS, KB_UNMATCHED = _kb_sections()
GLOSSARY_ABBR = _glossary()


def _usage_example(cls):
    """A copy-pasteable `compute()` call, generated from the class attributes.

    Deliberately GENERATED rather than parsed out of the knowledge-base markdown: the doc's version
    is itself generated from these same attributes by MangroveAI's generate_kb_docs.py, so parsing
    it back would make a derived artifact the source. This is the one node field that is always
    populated, for all 94.
    """
    data = ", ".join(f"'{d}': df['{d.title()}']" for d in cls._data)
    params = ", ".join(f"'{p}': value" for p in cls._params)
    return f"{cls.__name__}.compute(data={{{data}}}, params={{{params}}})"


def _describe(cls):
    """The docstring's leading prose, which becomes the atom's `summary`."""
    doc = inspect.getdoc(cls) or ""
    head = re.split(_SECTION, doc)[0]
    lines = [l.strip() for l in head.splitlines() if l.strip() and not l.strip().startswith("http")]
    return " ".join(lines[1:]) or None


def _load_classes():
    """{indicator name: class} for every registered indicator."""
    found = {}
    for mn in ("momentum_indicators", "trend_indicators", "volatility_indicators",
               "volume_indicators", "return_indicators", "pattern_indicators"):
        mod = importlib.import_module(f"mangrove_kb.indicators.{mn}")
        for nm, c in vars(mod).items():
            if isinstance(c, type) and hasattr(c, "_outputs") and c.__module__ == mod.__name__:
                found[nm] = c
    return found


# =============================================================================
# SIGNAL LAYER
#
# Same two-stage rule as the indicator layer: lift everything machine-readable, emit `null` for
# anything a human must author. Shape settled in `example-bollinger-signals-subgraph.md`, which is
# the review artifact for everything below.
#
# A signal node reuses the indicator node's fields wherever the field means the same thing --
# `inputs` in particular is raw input series at BOTH layers, so the two are comparable -- plus one
# addition, `consumes`, naming which of an indicator's outputs the signal actually reads.
#
# Only `reference` and `formula` come out null. `interpretation`, `applications` and the class are
# deliberately NOT fields: they are reached by following the `uses` edge to the indicator, which is
# the same rule that makes an indicator's class its `instance-of` edge rather than a property.
# =============================================================================

def _guard_to_warmup(expr, strict=True):
    """Convert a `len(df) < EXPR` guard into `warmup_bars`, which is a DIFFERENT quantity.

    The guard is the minimum frame length the signal needs. `warmup_bars` -- established by the
    indicator layer -- is the number of leading bars DISCARDED before the first valid output, which
    is one less. BollingerBands(window=20) is authored `window - 1` and has exactly 19 leading NaNs;
    a signal reading it needs a frame of 20 to produce its first answer, so it discards 19 too.

    Lifting the guard verbatim published every signal's warmup one too high, and hid a relationship
    that is obvious once the numbers are right: a state signal inherits its indicator's warmup
    unchanged, and a crossing costs exactly one bar more.

    `strict` is whether the guard used `<` or `<=`, and it changes the answer by one:
    `len(df) < N` needs N bars and so discards N-1, while `len(df) <= N` needs N+1 and discards N.
    Assuming `<` everywhere published mom_cross_up as `window` when its guard is
    `len(closes) <= window + 1`, i.e. `window + 1`.

    Folds the common `X + 1` case so the result reads as a bound rather than as arithmetic.
    """
    import ast

    if not strict:
        return expr

    try:
        node = ast.parse(expr, mode="eval").body
    except SyntaxError:
        return f"({expr}) - 1"
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return str(node.value - 1)
    if (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add)
            and isinstance(node.right, ast.Constant) and isinstance(node.right.value, int)):
        k = node.right.value - 1
        return ast.unparse(node.left) if k == 0 else f"{ast.unparse(node.left)} + {k}"
    return f"{expr} - 1"


# A signal that duplicates another announces it in its own docstring, and both the node `status` and
# the `supersedes` edge are lifted from that one declaration -- so the code stays the single source
# and the graph cannot drift from it.
#
# `deprecated` is not invented: the vendored ontology defines
# STATUS = {"draft", "ratified", "deprecated"}, and `supersedes` (meta, acyclic) is its relation for
# "this replaces that".
_SIG_DEPRECATED = re.compile(r"^\s*DEPRECATED:\s*identical to `(\w+)`", re.M)

_SIG_TYPE = re.compile(r"^\s*Type:\s*(.+)$", re.M)
_SIG_REQUIRES = re.compile(r"^\s*Requires:\s*(.+)$", re.M)
_SIG_RETURNS = re.compile(r"Returns:\s*\n\s*bool:\s*(.+)")


def _signal_facts():
    """Per-signal facts only the AST can supply: which indicator outputs are read, and the warmup.

    Both are read from the registered function's own body, following local helpers, because a signal
    that delegates to a shared helper (`_ma_cross`, `_macd_line`) reads its indicator there rather
    than at the decorated function.

    Returns {registered name: {"consumes": {Indicator: [output, ...]}, "warmup_bars": str|None}}.
    """
    import ast

    sigs_dir = pathlib.Path(inspect.getfile(importlib.import_module("mangrove_kb.signals.trend"))).parent
    out = {}
    for path in sorted(sigs_dir.glob("*.py")):
        if path.name == "__init__.py":
            continue
        tree = ast.parse(path.read_text())
        local = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        local.update({k: v for k, v in _sibling_functions(path, sigs_dir).items() if k not in local})

        def scan(fn, binding=None):
            """(consumes, calls, guards) for one function body, no recursion.

            `binding` maps this function's parameter names to what the caller passed, so a generic
            helper resolves to the concrete indicator and output. Without it the MA signals recorded
            `indicator_cls` -- a parameter name -- as their indicator.
            """
            binding = binding or {}

            def val(node):
                """The literal behind a node, following the call-site binding through a parameter."""
                if isinstance(node, ast.Constant):
                    return node.value
                if isinstance(node, ast.Name):
                    return binding.get(node.id, node.id)
                return None

            consumes, calls, guards, assigned = {}, set(), [], {}
            for nd in ast.walk(fn):
                if isinstance(nd, ast.Call):
                    f = nd.func
                    if isinstance(f, ast.Name) and f.id in local:
                        # Record the call WITH the indicator classes passed into it. The MA signals
                        # never write `DEMA.compute(...)`; they write
                        # `_ma_is_above(df, DEMA, 'dema', window)` and the helper calls
                        # `indicator_cls.compute(...)`. Scanning the helper alone yields the
                        # PARAMETER name, so 18 signals resolved to a variable and got no `uses`
                        # edge, and DEMA/TEMA/TRIMA/SMMA/HMA looked like indicators nothing used.
                        # Bind the helper's PARAMETERS to what this call site passes, so a helper
                        # written generically resolves to the indicator it was handed. Names and
                        # string literals both matter: `_ma_is_above(df, DEMA, 'dema', window)`
                        # supplies the indicator AND the output key, and the helper body names
                        # neither -- it says `indicator_cls.compute(...)[output_key]`.
                        params = [a.arg for a in local[f.id].args.args]
                        binding = {}
                        for pname, arg in zip(params, nd.args):
                            if isinstance(arg, ast.Name) and arg.id in present:
                                binding[pname] = arg.id
                            elif isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                                binding[pname] = arg.value
                        calls.add((f.id, tuple(sorted(binding.items()))))
                # X.compute(...)['key']
                if isinstance(nd, ast.Subscript) and isinstance(nd.value, ast.Call):
                    f = nd.value.func
                    if isinstance(f, ast.Attribute) and f.attr == "compute" and isinstance(f.value, ast.Name):
                        ind, key = val(f.value), val(nd.slice)
                        if ind in present and isinstance(key, str):
                            consumes.setdefault(ind, set()).add(key)
                # var = X.compute(...)   then   var['key']
                if isinstance(nd, ast.Assign) and isinstance(nd.value, ast.Call):
                    f = nd.value.func
                    if isinstance(f, ast.Attribute) and f.attr == "compute" and isinstance(f.value, ast.Name):
                        ind = val(f.value)
                        if ind in present:
                            for t in nd.targets:
                                if isinstance(t, ast.Name):
                                    assigned[t.id] = ind
                # the `if len(x) < N: return False` warmup guard
                if isinstance(nd, ast.If) and isinstance(nd.test, ast.Compare):
                    c = nd.test
                    if (isinstance(c.left, ast.Call) and getattr(c.left.func, "id", None) == "len"
                            and c.comparators):
                        # `<` and `<=` mean different warmups -- see _guard_to_warmup
                        guards.append((ast.unparse(c.comparators[0]),
                                       isinstance(c.ops[0], ast.Lt)))
            for nd in ast.walk(fn):
                if (isinstance(nd, ast.Subscript) and isinstance(nd.value, ast.Name)
                        and nd.value.id in assigned):
                    key = val(nd.slice)
                    if isinstance(key, str):
                        consumes.setdefault(assigned[nd.value.id], set()).add(key)
            return consumes, calls, guards

        def resolve(fname, seen=None, binding=()):
            """Resolve one function, with its parameters bound to what the caller passed."""
            seen = seen or set()
            if fname in seen or fname not in local:
                return {}, []
            seen.add(fname)
            consumes, calls, guards = scan(local[fname], dict(binding))
            for cname, passed in calls:
                sub_c, sub_g = resolve(cname, seen, passed)
                for k, v in sub_c.items():
                    consumes.setdefault(k, set()).update(v)
                guards += sub_g
            return consumes, guards

        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            for d in fn.decorator_list:
                if (isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                        and d.func.attr == "register" and d.args):
                    consumes, guards = resolve(fn.name)
                    out[d.args[0].value] = {
                        # Sorted for a stable diff; `set` above only deduplicates.
                        "consumes": {k: sorted(v) for k, v in sorted(consumes.items())},
                        # Only when unambiguous. Several guards with different expressions means the
                        # minimum is a judgement rather than a reading, so it goes to the queue.
                        "warmup_bars": (_guard_to_warmup(*guards[0])
                                        if len(set(guards)) == 1 else None),
                        "module": path.stem,
                    }
    return out


SIGNAL_FACTS = _signal_facts()


def _signal_input_descriptions():
    """{series name: description}, lifted from what is already authored on the indicator nodes.

    `close` means the same thing wherever it appears, so a signal's input descriptions are taken
    from the indicator layer rather than authored a second time. Derivation, not authoring -- and it
    keeps one description per series instead of 247 copies that can drift.
    """
    out = {}
    for cls in CLASSES.values():
        for name, spec in (_lift(cls).get("inputs") or {}).items():
            if spec.get("description") and name not in out:
                out[name] = spec["description"]
    return out


def _signal_summary(doc):
    """The docstring's leading prose, which becomes the atom's `summary`.

    The signal counterpart of `_describe`. The `Reference:` line sits above the first section, so it
    is stripped here rather than ending up inside the description -- the URL is lifted separately
    into its own field, and one fact in two places is one too many.
    """
    head = re.split(r"\n\s*(?:Type|Requires|Args|Returns):", doc)[0]
    # Strip the reference clause WHEREVER it sits. Anchoring this to the start of a line was wrong:
    # most pattern docstrings append `Reference: <url>` to the end of a prose sentence rather than
    # putting it on its own line, so 29 summaries carried the URL as well as the `reference` field --
    # one fact in two places, which is the thing this strip exists to prevent.
    head = re.sub(r"References?:\s*\S+", "", head)
    return re.sub(r"\s+", " ", head).strip().rstrip() or None


def _signal_lift(name, fn, facts):
    """Everything liftable for one signal. `reference` and `formula` are the only nulls."""
    doc = inspect.getdoc(fn) or ""

    # inputs: the raw series the signal declares it needs in the frame. Same meaning as an
    # indicator's `inputs`. NOT the indicator outputs it reads -- those are `consumes`.
    req = _SIG_REQUIRES.search(doc)
    inputs = {}
    for tok in (re.split(r"[,/]", req.group(1)) if req else []):
        tok = tok.strip()
        if not tok:
            continue
        # OHLCV is declared capitalised (`Close`) because that is the DataFrame column; the series
        # itself is lowercase everywhere else in this graph. Non-price series keep their own casing.
        key = tok.lower() if tok.lower() in ("open", "high", "low", "close", "volume") else tok
        inputs[key] = {"type": "series", "description": SIGNAL_INPUT_DESC.get(key)}

    params = {}
    blk = re.search(r"Args:(.*?)(?:Returns:|\Z)", doc, re.S)
    for line in (blk.group(1).splitlines() if blk else []):
        m = _PARAM_LINE.match(line)
        if not m or m.group(1) == "df":
            continue
        pname, ptype, rest = m.group(1), m.group(2).strip(), m.group(3).strip()
        desc = re.split(r"\s*(?:Range|Default):", rest)[0].strip().rstrip(".")
        rng, dflt = _RANGE.search(rest), _DEFAULT.search(rest)

        # `_num` narrows an integral value to int, which is right for an int param and wrong for a
        # float one: `threshold` is declared float with default 5.0 and Range 1-20, and came out
        # `{"type": "float", "default": 5, "min": 1, "max": 20}` -- every bound an int. A consumer
        # generating a sweep from that gets integer steps on a continuous parameter.
        cast = (lambda v: None if v is None else float(v)) if ptype == "float" else (lambda v: v)
        params[pname] = {"type": ptype,
                         "default": cast(_num(dflt.group(1))) if dflt else None,
                         "min": cast(_num(rng.group(1))) if rng else None,
                         "max": cast(_num(rng.group(2))) if rng else None,
                         "description": desc or None}

    ret = _SIG_RETURNS.search(doc)
    sig_params = ", ".join(f"'{p}': value" for p in params)

    # The first URL in the docstring, exactly as the indicator layer does it. Absent on most
    # signals, and absent is fine: it stays null and lands on the authoring queue like any other
    # null. The pattern signals cited sources as bracket keys (`References: [NISON], [KB-07]`)
    # against a legend that defined three of the ten keys in use, so nothing resolved and the field
    # could not be lifted at all; they now carry a URL directly.
    url = re.search(r"https?://\S+", doc)

    return {
        "source_module": facts["module"],
        "reference": url.group(0).rstrip(".,") if url else None,
        "warmup_bars": facts["warmup_bars"],
        # Signals have no abbreviation. Held at null for consistency with the indicator layer, which
        # already uses null for inapplicable rather than a real value -- see the worked example.
        "abbreviation": None,
        "usage_example": f"RuleRegistry.evaluate({{'name': '{name}', 'params': {{{sig_params}}}}}, df)",
        "formula": None,
        # NOTE there is no `consumes` here. Which indicator outputs a signal reads is a property of
        # the `uses` EDGE, not of the signal -- see `rel()`. `inputs` below is the same word for the
        # same concept: series the signal consumes. The two differ only by provenance, which is
        # exactly what an edge expresses. A signal's full input set is this dict plus the `inputs` on
        # each of its `uses` edges.
        "inputs": inputs,
        "params": params,
        # One boolean. A signal returns a bare bool with no name to lift, so the key is invented --
        # named rather than anonymous so it carries the same sub-schema as every indicator output.
        "outputs": {"fired": {"type": "bool", "units": "boolean", "range": [0, 1],
                              "canonical_name": "none",
                              "description": ret.group(1).strip().rstrip(".") if ret else None}},
    }


CLASSES = _load_classes()
SIGNAL_INPUT_DESC = _signal_input_descriptions()



atoms, rels = [], []
def atom(i, t, k, s, status="ratified", **p):
    """`epistemic` and `status` are two different questions, and this emitted a status value for
    both until 2026-08-08.

    Per the vendored ontology: `epistemic` = how the belief was arrived at
    (observed | inferred | hypothesized | assumed); `status` = admission state
    (draft | ratified | deprecated). `ratified` was never a legal `epistemic` value, so that field
    conveyed nothing on all 127 atoms.

    Everything in this graph is `observed`: the lifted fields are read directly from the code, and
    the authored ones are read from `_compute` and verified by executing it. Nothing here is an
    interpretation of prose, because the indicators and signals whose behaviour is genuinely
    unsettled are being held out of scope rather than guessed at. If that ever stops being true --
    an atom whose content is inferred rather than read -- it takes `inferred`, and the difference
    is the point of the field.
    """
    atoms.append({"id": i, "title": t, "kind": k, "summary": s,
                  "epistemic": "observed", "status": status, "props": p})
def rel(a, r, b, why, ai, bi, **props):
    """`props` are properties of the RELATIONSHIP, not of either endpoint.

    `uses` carries `inputs` this way: which of the indicator's outputs flow into the signal is a
    fact about the connection, and storing it on either node would be storing it in the wrong place.
    It also cannot be ambiguous here -- one edge per indicator -- whereas a node property had to
    repeat the indicator name to disambiguate the signals that read two.
    """
    rels.append({"from": a, "rel": r, "to": b, "why": why, "from_id": ai, "to_id": bi, **props})

# The knowledge space's root.
#
# NOT "the ontology": the ontology is jarvis's nine primitives and its relation hierarchy, and it was
# decided before any of this. What we are building is the KNOWLEDGE SPACE -- the populated instance
# graph that the ontology types. Signals and indicators are only its first region; strategies,
# markets and the rest of the knowledge base land under this same root.
#
# `Object`, not `Concept`. Per the primitive definitions, a Concept is a CATEGORY with graded
# membership -- things are `instance-of` it. Nothing is an instance of this; Indicator, Signal and
# Strategy are `part-of` it. It is a single individuated artifact that persists and has identity,
# which is a DOLCE endurant, i.e. an Object -- the same kind of thing as "MangroveTrader" in the
# ontology doc's own examples.
#
# Without a root the graph has four disconnected tops -- Indicator, Signal, Strategy and Role -- and
# nothing states that they belong to the same space. A viewer that walks containment from one root
# can then only ever see part of the graph, and the missing part was Role.
#
# It exists here, in the source, for the same reason every other node does: it is part of the model.
# A renderer that invents it in memory is asserting a fact about the ontology in display code, where
# nothing can query it and the next rebuild does not know about it.
ROOT = "object:mangrove-knowledge-space"
ROOT_TITLE = "Mangrove Knowledge Space"
atom(ROOT, ROOT_TITLE, "Object",
     "Root of the Mangrove knowledge space -- the populated graph the jarvis ontology types. Its "
     "first region is signals and indicators: the entity types (Indicator, Signal, Strategy), the "
     "role axis, and everything classified under them. Strategies, markets and the rest of the "
     "knowledge base attach here too.")

# entity types
atom("concept:indicator", "Indicator", "Procedure",
     "A computation over one or more input series producing one or more numeric output series.")
atom("concept:signal", "Signal", "Procedure",
     "A boolean predicate over indicator output, evaluated per bar. Composed of (indicator, predicate, params).")
atom("concept:strategy", "Strategy", "Schema",
     "A structured template composing signals into entry/exit rules plus configuration.")
for _t, _tid in (("Indicator", "concept:indicator"), ("Signal", "concept:signal"),
                 ("Strategy", "concept:strategy")):
    rel(_t, "part-of", ROOT_TITLE, "entity type defined by the knowledge space", _tid, ROOT)

# role axis
#
# `part-of` Signal, not the root: every one of the has-role edges this builder emits starts at a
# signal and none at an indicator, so role is a facet of Signal rather than a peer of it. `kind-of`
# would be wrong -- a role is not a kind of signal, it is an axis along which signals are placed.
atom("property:role", "Role", "Property",
     "The position a signal occupies within a strategy. Contextual, not intrinsic.")
rel("Role", "part-of", "Signal", "axis along which signals are placed", "property:role", "concept:signal")
for r in ("trigger", "filter", "arm"):
    atom(f"property:role-{r}", r, "Property", f"Signal role: {r}.")
    rel(r, "kind-of", "Role", "role value", f"property:role-{r}", "property:role")

# class axis + members
for cls, desc in CLASSES_DEF.items():
    atom(f"concept:indicator-class-{cls}", cls, "Concept", desc)
    rel(cls, "kind-of", "Indicator", "indicator class", f"concept:indicator-class-{cls}", "concept:indicator")
for ind, cls in sorted(assigned.items()):
    lifted = _lift(CLASSES[ind])
    # Description precedence, best source first: the docstring's own prose (closest to the code),
    # then the knowledge-base definition, then the placeholder that puts it on the authoring queue.
    # The KB definition covers indicators whose docstring is a bare title line, so lifting it here
    # removes them from the hand-authoring list rather than duplicating what is already written.
    atom(f"procedure:indicator-{ind.lower()}", ind, "Procedure",
         (_describe(CLASSES[ind])
          or KB_SECTIONS.get(ind, {}).get("definition")
          or f"Indicator `{ind}` -- no description in source."),
         # class is the instance-of edge below -- NEVER also a property, or there are two
         # representations of one fact.
         source_module=f"{mod_of[ind]}_indicators", **lifted)
    rel(ind, "instance-of", cls, "class membership",
        f"procedure:indicator-{ind.lower()}", f"concept:indicator-class-{cls}")

# --- signals.
#
# Three edges each, and no new relation vocabulary: `instance-of` (structural) to the Signal entity
# type, `uses` (associative) to the indicator it invokes, `has-role` (descriptive) to its role.
#
# `uses` rather than `derived-from`: the vendored ontology glosses it as "runtime
# invocation/orchestration (skill->tool, procedure->tool)", and a signal is a Procedure that calls
# `Indicator.compute()` when evaluated. `derived-from` is provenance of knowledge, not dataflow, and
# `requires` is the KST surmise relation, which this would distort. Reasoning in full in
# `example-bollinger-signals-subgraph.md`.
#
# The class is NOT emitted: it is reached by following `uses` to the indicator and then that
# indicator's `instance-of`. Same rule as the indicator layer, one level out.
import mangrove_kb.signals  # noqa: E402,F401  -- registers every signal
from mangrove_kb.registry import RuleRegistry  # noqa: E402

# Which signals get nodes. The signal layer is being brought in deliberately, one group at a time,
# the same way the indicator layer was: settle the shape on a specimen, review it, then widen.
#
# This is a scope list, NOT a filter over something already decided -- emitting all 247 before the
# shape is agreed would put 247 nodes in the graph on a schema nobody has looked at, and the point
# of the worked example (`example-bollinger-signals-subgraph.md`) is that that does not happen.
#
# `None` means every registered signal. Widen by adding names, or set to None when the shape is
# settled for all of them.
SIGNAL_SCOPE = {
    # NOT here, deliberately: atr_trailing_stop_{long,short,flip_up,flip_down} and
    # volatility_stop_{upper,lower}. They are built on ATRTrailingStop and VolatilityStop, two of
    # the five stateful policy rules that `signal-indicator-ontology.md` excludes -- "not
    # indicators ... policy, not measurement. Excluded from this ontology AND FROM THE GRAPH."
    # Adding them put six signals in the graph that the design excludes, and produced six signals
    # with no class as a symptom.
    # Volatility -- the five Bollinger signals were the worked example that settled the
    # node shape; the rest of the module follows.
    "cl_above_low_offset", "cl_below_high_offset",
    "atr_high_volatility", 
    "bb_above_upper",
    "bb_below_lower", "bb_lower_breakout", "bb_squeeze",
    "bb_upper_breakout", "dc_lower_breakout", "dc_upper_breakout",
    "kc_above_upper", "kc_below_lower", "kc_lower_breakout",
    "kc_upper_breakout", "natr_high_volatility", "natr_low_volatility",
    "starc_lower_breakout", "starc_upper_breakout", "ulcer_high_risk",
    "ulcer_low_risk", 
    # Momentum.
    "ao_bearish", "ao_bullish", "ao_zero_cross",
    "bop_bearish", "bop_bullish", "bop_cross_down",
    "bop_cross_up", "cmo_cross_down", "cmo_cross_up",
    "cmo_overbought", "cmo_oversold", "kama_cross_down",
    "kama_cross_up", "macd_line_cross_down", "macd_line_cross_up",
    "macd_line_negative", "macd_line_positive", "mom_bearish",
    "mom_bullish", "mom_cross_down", "mom_cross_up",
    "ppo_bearish_cross", "ppo_bullish_cross", "pvo_bearish_cross",
    "pvo_bullish_cross", "roc_momentum_shift", "roc_negative",
    "roc_positive", "rsi_cross_down", "rsi_cross_up",
    "rsi_overbought", "rsi_oversold", "stoch_overbought",
    "stoch_oversold", "stochrsi_overbought", "stochrsi_oversold",
    "tsi_bearish", "tsi_bullish", "uo_overbought",
    "uo_oversold", "williams_r_overbought", "williams_r_oversold",
    # Volume.
    "adi_bearish", "adi_bullish", "adosc_bearish",
    "adosc_bullish", "adosc_cross_down", "adosc_cross_up",
    "cmf_bearish", "cmf_bullish", "cumulative_return_positive",
    "cumulative_return_target", "daily_return_negative", "daily_return_positive",
    "eom_bearish", "eom_bullish", "force_bearish",
    "force_bullish", "is_above_vwma", "kvo_bearish",
    "kvo_bearish_cross", "kvo_bullish", "kvo_bullish_cross",
    "mfi_overbought", "mfi_oversold", "nvi_bearish",
    "nvi_bullish", "obv_bearish", "obv_bullish",
    "vpt_bearish", "vpt_bullish", "vwap_above",
    "vwap_below", "vwma_cross_down", "vwma_cross_up",
    # Chart patterns.
    "bearish_engulfing_trigger", "bearish_harami_trigger", "bearish_pattern_recent",
    "bearish_pin_bar_trigger", "bullish_engulfing_trigger", "bullish_harami_trigger",
    "bullish_pattern_recent", "bullish_pin_bar_trigger", "continuation_pattern_bearish",
    "continuation_pattern_bullish", "dark_cloud_cover_trigger", "doji_trigger",
    "dragonfly_doji_trigger", "evening_star_trigger", "gravestone_doji_trigger",
    "hammer_trigger", "hanging_man_trigger", "indecision_pattern_recent",
    "inside_bar_trigger", "inverted_hammer_trigger", "long_legged_doji_trigger",
    "marubozu_bearish_trigger", "marubozu_bullish_trigger", "morning_star_trigger",
    "nr7_trigger", "outside_bar_trigger", "piercing_line_trigger",
    "reversal_pattern_bearish", "reversal_pattern_bullish", "shooting_star_trigger",
    "spinning_top_trigger", "strong_body_recent", "three_black_crows_trigger",
    "three_inside_down_trigger", "three_inside_up_trigger", "three_white_soldiers_trigger",
    "tweezer_bottoms_trigger", "tweezer_tops_trigger", "two_bar_reversal_bearish_trigger",
    "two_bar_reversal_bullish_trigger",

    # Trend -- 64 of the file's 88 (86 after the two chandelier signals moved to volatility). The other 24 are held out for two different reasons.
    #
    # Seven read an indicator whose output is a VERDICT rather than a measurement, and must never
    # enter the graph: psar_bearish, psar_bullish, psar_reversal (PSAR's flip flags);
    # supertrend_flip_down, supertrend_flip_up, supertrend_long, supertrend_short (SuperTrend's
    # +1/-1 `direction`). The guard below fails the build if one slips in. The two chandelier
    # signals were on this list until ChandelierExit was found to emit plain levels; they are now
    # cl_below_high_offset / cl_above_low_offset, in scope above.
    #
    # Fifteen read an indicator still in the `unclassed` class, whose classification is an open
    # decision: heikin_ashi_{bullish,bearish} (HeikinAshi); ichimoku_{bullish,bearish},
    # ichimoku_tk_cross (Ichimoku); rsi_{,hidden_}{bullish,bearish}_divergence (Divergence);
    # ttm_squeeze_active, ttm_squeeze_fired_{bullish,bearish} (TTMSqueeze); epma_cross_up,
    # epma_cross_down, is_above_epma (EPMA -- reached through the shared MA helper, so only the
    # builder's parameter binding resolves it; a direct read of the call graph misses them). Their
    # class is
    # transitive, so it changes when those five are classed -- and the file a signal lives in is
    # transitive, so it changes when those five are classed -- and the file a signal lives in is
    # its class, so authoring them now would place them on a guess.
    "adx_bullish_di", "adx_strong_trend", "alligator_bearish", "alligator_bullish",
    "alligator_sleeping", "alma_cross_down", "alma_cross_up", "aroon_crossover",
    "aroon_down_trend", "aroon_up_trend", "cci_overbought", "cci_oversold", "dema_cross_down",
    "dema_cross_up", "dpo_negative", "dpo_positive", "ema_cross_down", "ema_cross_up",
    "ema_crossover", "hma_cross_down", "hma_cross_up",
    "is_above_alma", "is_above_dema", "is_above_hma", "is_above_mama",
    "is_above_sma", "is_above_smma", "is_above_t3", "is_above_tema", "is_above_trima",
    "kst_bearish_cross", "kst_bullish_cross", "ma_ribbon_bearish", "ma_ribbon_bullish",
    "ma_ribbon_tangled", "macd_bearish_cross", "macd_bullish_cross", "macd_positive",
    "mama_cross_down", "mama_cross_up", "mass_reversal_signal", "multi_tf_trend_bearish",
    "multi_tf_trend_bullish", "price_above_ema", "sma_cross_down", "sma_cross_up",
    "sma_crossover", "smma_cross_down", "smma_cross_up", "stc_overbought", "stc_oversold",
    "t3_cross_down", "t3_cross_up", "tema_cross_down", "tema_cross_up", "trima_cross_down",
    "trima_cross_up", "trix_bearish", "trix_bullish", "vortex_bearish", "vortex_bullish",
    "vortex_crossover", "wma_cross_down", "wma_cross_up",
}

# A signal built on one of the five excluded policy rules must not enter the graph. The design is
# explicit -- "Excluded from this ontology AND FROM THE GRAPH" -- but excluding the indicator alone
# does not exclude the signals standing on it, and six of them were added before this check existed.
# They arrive looking like an ordinary signal with no class, which is indistinguishable from the
# pattern signals that legitimately read raw OHLC, so it fails the build rather than being reported.
_on_removed = sorted(
    n for n in (RuleRegistry.names() if SIGNAL_SCOPE is None else SIGNAL_SCOPE)
    if set(SIGNAL_FACTS.get(n, {}).get("consumes", {})) & set(REMOVED))
if _on_removed:
    print(f"ABORT {len(_on_removed)} in-scope signals are built on indicators excluded from the "
          f"graph ({', '.join(sorted(set(REMOVED)))}):\n  " + "\n  ".join(_on_removed),
          file=sys.stderr)
    sys.exit(1)

signal_no_indicator, signal_unknown_role, deprecated_signals = [], [], []
for sname in sorted(RuleRegistry.names() if SIGNAL_SCOPE is None else SIGNAL_SCOPE):
    facts = SIGNAL_FACTS.get(sname)
    if not facts:
        # Registered but not found by the AST pass -- a real inconsistency, not something to paper
        # over, since it means the source shape changed underneath the resolver.
        print(f"ABORT signal {sname!r} is registered but was not found in the source", file=sys.stderr)
        sys.exit(1)
    sid = f"procedure:signal-{sname.replace('_', '-')}"
    fn = RuleRegistry._registry[sname]
    doc = inspect.getdoc(fn) or ""
    lifted = _signal_lift(sname, fn, facts)
    dep = _SIG_DEPRECATED.search(doc)
    atom(sid, sname, "Procedure",
         _signal_summary(doc) or f"Signal `{sname}` -- no description in source.",
         status="deprecated" if dep else "ratified", **lifted)
    rel(sname, "instance-of", "Signal", "entity type", sid, "concept:signal")
    if dep:
        # The canonical signal supersedes the duplicate. Emitted from the DUPLICATE's docstring so
        # one declaration produces both the status and the edge; recorded on the replacement's side
        # because `supersedes` reads "newer replaces older".
        canon = dep.group(1)
        deprecated_signals.append((canon, sname))

    m = _SIG_TYPE.search(doc)
    role = m.group(1).strip().lower() if m else None
    if role in ("trigger", "filter", "arm"):
        rel(sname, "has-role", role, "role", sid, f"property:role-{role}")
    else:
        signal_unknown_role.append(sname)

    # One `uses` edge per indicator read. A signal reading two indicators gets two edges; a signal
    # reading none gets no edge and lands on the report below rather than being silently classless.
    #
    # Membership is tested against `assigned` -- the indicators that HAVE a node -- not against
    # `CLASSES`, which is every class importable from the indicator modules. The two differ by the
    # five stateful policy rules (SuperTrend, PSAR, ChandelierExit, ATRTrailingStop, VolatilityStop)
    # that the ontology deliberately excludes as not-indicators. They are still importable, so
    # testing against CLASSES produced 15 edges pointing at nodes that do not exist. The 15 signals
    # built on them genuinely have no class, and belong on the report rather than in a dangling edge.
    known = [i for i in facts["consumes"] if i in assigned]
    for ind in known:
        # Same nested-dict shape as a node's `inputs`, because it is the same concept: series the
        # signal consumes.
        #
        # NO `description` here. The edge's job is to say WHICH output flows across it; what that
        # output means is authored once, on the indicator node that emits it, and following the edge
        # is how you get there. Copying the prose onto the edge duplicated it and carried a
        # description written for one context into another -- BollingerBands' `lband` reads
        # "Population stdev, as above", which is true where it sits under `hband` on the indicator
        # node and dangles on an edge that carries only `lband`.
        ind_outputs = (_lift(CLASSES[ind]).get("outputs") or {})
        edge_inputs = {out: {"type": ind_outputs.get(out, {}).get("type") or "series"}
                       for out in facts["consumes"][ind]}
        rel(sname, "uses", ind, "reads indicator output",
            sid, f"procedure:indicator-{ind.lower()}", inputs=edge_inputs)
    if not known:
        signal_no_indicator.append(sname)

# `supersedes` edges for the duplicate signals. Emitted after the loop so both endpoints exist --
# a replacement may be declared before or after the signal that names it.
_sig_ids = {a["title"]: a["id"] for a in atoms if a["id"].startswith("procedure:signal-")}
for canon, dup in deprecated_signals:
    if canon not in _sig_ids:
        # The replacement is out of scope, so the edge would dangle. Report rather than drop.
        print(f"NOTE {dup} is deprecated in favour of {canon}, which is not in SIGNAL_SCOPE -- "
              f"no supersedes edge emitted", file=sys.stderr)
        continue
    rel(canon, "supersedes", dup, "computes the same thing under the canonical name",
        _sig_ids[canon], _sig_ids[dup])


# --- carry forward authored values. Authored values live in the nodes, and this builder is the
# thing that rewrites the nodes -- so every run must preserve what was authored into the last one,
# or a rebuild silently erases hours of hand-authoring. Rule: a lift always wins (source changes
# are supposed to propagate), but wherever THIS run produced `null` and the previous build had a
# value, the previous value is kept. Keys absent from this run are NOT resurrected, so a field
# deliberately removed from the schema stays removed.
NODE_FILE = pathlib.Path(__file__).resolve().parent / "signal-indicator-ontology.json"


def _carry(new, old):
    """Fill nulls in `new` from `old`, recursing into nested dicts. Returns the number filled."""
    n = 0
    for k, ov in (old or {}).items():
        if k not in new:
            continue
        nv = new[k]
        if isinstance(nv, dict) and isinstance(ov, dict):
            n += _carry(nv, ov)
        elif nv is None and ov is not None:
            new[k] = ov
            n += 1
    return n


carried = 0
if NODE_FILE.exists():
    _prev = {a["id"]: a for a in json.loads(NODE_FILE.read_text()).get("atoms", [])}
    for a in atoms:
        p = _prev.get(a["id"])
        if not p:
            continue
        carried += _carry(a["props"], p.get("props") or {})
        if not a.get("summary") and p.get("summary"):
            a["summary"] = p["summary"]
            carried += 1

# Last resort for the three prose fields: the indicator's own docstring, for anything neither the
# knowledge base nor a previous authoring pass has reached.
bootstrapped = 0
for a in atoms:
    sec = DOC_SECTIONS.get(a["title"])
    if not sec:
        continue
    for k in ("formula", "interpretation", "applications"):
        if a["props"].get(k) is None and sec.get(k) is not None:
            a["props"][k] = sec[k]
            bootstrapped += 1

# --- invariant: `null` means "not yet authored", everywhere. A field that is deliberately not
# applicable must carry a real value instead, or it is indistinguishable from an unfilled one and
# the nulls stop being a usable worklist. The signature of the mistake is prose authored without the
# machine-readable fields beside it, so fail loudly on exactly that.
half_authored = [f"{a['title']}.{o}: description present but "
                 + " and ".join(f for f in ("units", "range") if s.get(f) is None) + " is null"
                 for a in atoms for o, s in (a["props"].get("outputs") or {}).items()
                 if s.get("description") is not None and (s.get("units") is None
                                                          or s.get("range") is None)]
if half_authored:
    print("ABORT half-authored outputs:\n  " + "\n  ".join(half_authored), file=sys.stderr)
    sys.exit(1)

# --- invariant: every edge lands on a node that exists. A dangling edge is a graph that lies -- a
# consumer walking `uses` to find a signal's class follows it to nothing and gets no answer, which
# is indistinguishable from a signal that reads no indicator at all. Caught here because it was
# introduced once already: testing indicator membership against every importable class rather than
# against the ones with nodes attached 15 signals to the five excluded policy rules.
_ids = {a["id"] for a in atoms}
dangling = [f"{r['from']} --{r['rel']}--> {r['to']}"
            for r in rels if r["from_id"] not in _ids or r["to_id"] not in _ids]
if dangling:
    print(f"ABORT {len(dangling)} dangling edges:\n  " + "\n  ".join(dangling), file=sys.stderr)
    sys.exit(1)

# --- invariant: every `uses` edge declares what it carries. An edge saying only "this signal reads
# this indicator" is a question, not an answer -- the whole reason the output list lives on the edge
# is so a consumer can tell `bb_squeeze` (wband) from `bb_upper_breakout` (hband) without reading
# source. A `uses` with no `inputs` is a silent gap, so it fails the build like every other one.
uses_without_inputs = [f"{r['from']} --uses--> {r['to']}"
                       for r in rels if r["rel"] == "uses" and not r.get("inputs")]
if uses_without_inputs:
    print(f"ABORT {len(uses_without_inputs)} `uses` edges declare no inputs:\n  "
          + "\n  ".join(uses_without_inputs), file=sys.stderr)
    sys.exit(1)

out = {"atoms": atoms, "relations": rels,
       "meta": {"scope": "indicator class ontology", "indicators": len(assigned),
                "classes": len(CLASSES_DEF), "removed_not_indicators": sorted(REMOVED),
                "carried_forward_from_previous_build": carried,
                "bootstrapped_from_docstring": bootstrapped,
                "kb_doc_sections_matched": len(KB_SECTIONS),
                "kb_doc_sections_unmatched": sorted(KB_UNMATCHED),
                "signals": len(atoms) - len([a for a in atoms if not a["id"].startswith("procedure:signal-")]),
                "signals_registered": len(RuleRegistry.names()),
                "signals_out_of_scope": (0 if SIGNAL_SCOPE is None
                                         else len(RuleRegistry.names() - SIGNAL_SCOPE)),
                # Reported, never silently defaulted. A signal with no `uses` edge has no class,
                # because class is reached through that edge -- so this list IS the classless set.
                "signals_with_no_indicator": sorted(signal_no_indicator),
                "signals_with_unknown_role": sorted(signal_unknown_role),
                "signals_missing_warmup": sorted(
                    a["title"] for a in atoms
                    if a["id"].startswith("procedure:signal-") and a["props"]["warmup_bars"] is None),
                "indicators_missing_description":
                    sorted(i for i in assigned if not _describe(CLASSES[i]))}}
print(json.dumps(out, indent=1))
print(f"\n// atoms={len(atoms)} relations={len(rels)} indicators={len(assigned)}", file=sys.stderr)

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
 'averaging': "SMA EMA WMA DEMA TEMA TRIMA SMMA HMA ALMA T3 KAMA VWMA VWAP MAMA WilliamsAlligator MARibbon",
 'momentum': "ROC MOM TRIX MACD PPO APO KST AwesomeOscillator DPO PVO ForceIndex EaseOfMovement "
             "ADOSC KVO DailyReturn DailyLogReturn MassIndex ADX Aroon Vortex MultiTFTrend",
 'oscillator': "RSI StochasticOscillator StochRSI WilliamsR MFI UltimateOscillator CMO TSI BOP STC CCI CMF",
 'volatility': "ATR TrueRange NATR UlcerIndex BollingerBands KeltnerChannel DonchianChannel STARCBands",
 'flow': "OBV ADI VPT NVI CumulativeReturn",
 'unclassed': "EPMA Ichimoku HeikinAshi TTMSqueeze Divergence",
}
REMOVED = "ATRTrailingStop VolatilityStop ChandelierExit SuperTrend PSAR".split()

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

    # warmup: min_periods is the only machine-readable hint, and only when unambiguous.
    warm = sorted({m for m in re.findall(r"min_periods\s*=\s*([A-Za-z_]\w*|\d+)",
                                         inspect.getsource(cls))})
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
    try:
        f = float(x)
        return int(f) if f == int(f) else f
    except ValueError:
        return None


def _signal_param_docs():
    """{indicator name: {param: {description, min, max, default}}}"""
    import ast
    from mangrove_kb.registry import RuleRegistry
    import mangrove_kb.signals.momentum, mangrove_kb.signals.trend, mangrove_kb.signals.volume  # noqa
    import mangrove_kb.signals.volatility, mangrove_kb.signals.patterns                          # noqa

    kbs = pathlib.Path(inspect.getfile(mangrove_kb.signals.trend)).parent
    out = {}
    for path in sorted(kbs.glob("*.py")):
        if path.name in ("__init__.py", "onchain.py", "defi_pro.py"):
            continue
        tree = ast.parse(path.read_text())
        local = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        info, reg = {}, {}
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
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
    "Klinger Volume Oscillator": "KVO",
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


CLASSES = _load_classes()



atoms, rels = [], []
def atom(i, t, k, s, **p):
    atoms.append({"id": i, "title": t, "kind": k, "summary": s,
                  "epistemic": "ratified", "status": "ratified", "props": p})
def rel(a, r, b, why, ai, bi):
    rels.append({"from": a, "rel": r, "to": b, "why": why, "from_id": ai, "to_id": bi})

# entity types
atom("concept:indicator", "Indicator", "Procedure",
     "A computation over one or more input series producing one or more numeric output series.")
atom("concept:signal", "Signal", "Procedure",
     "A boolean predicate over indicator output, evaluated per bar. Composed of (indicator, predicate, params).")
atom("concept:strategy", "Strategy", "Schema",
     "A structured template composing signals into entry/exit rules plus configuration.")

# role axis
atom("property:role", "Role", "Property",
     "The position a signal occupies within a strategy. Contextual, not intrinsic.")
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

out = {"atoms": atoms, "relations": rels,
       "meta": {"scope": "indicator class ontology", "indicators": len(assigned),
                "classes": len(CLASSES_DEF), "removed_not_indicators": sorted(REMOVED),
                "carried_forward_from_previous_build": carried,
                "bootstrapped_from_docstring": bootstrapped,
                "kb_doc_sections_matched": len(KB_SECTIONS),
                "kb_doc_sections_unmatched": sorted(KB_UNMATCHED),
                "indicators_missing_description":
                    sorted(i for i in assigned if not _describe(CLASSES[i]))}}
print(json.dumps(out, indent=1))
print(f"\n// atoms={len(atoms)} relations={len(rels)} indicators={len(assigned)}", file=sys.stderr)

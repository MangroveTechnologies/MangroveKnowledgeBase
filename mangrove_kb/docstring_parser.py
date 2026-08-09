"""
Docstring parser for MangroveAI signal functions.

Extracts structured metadata from enriched docstrings on signal functions
decorated with @RuleRegistry.register("signal_name"), producing output that
matches the schema of signals_metadata.json.

Structured docstring tags parsed:
    Type:             TRIGGER or FILTER
    Requires:         Comma-separated column names, or "None"
    Disabled:         True (only present when the signal is disabled)
    Disabled-Reason:  Explanation text (only present when Disabled: True)
    Args:             Parameter block in Google-style format with Range/Default

Each parameter line in the Args block follows this format:
    name (type): Description. Range: min-max. Default: value.

The `df` parameter is always excluded from the output since it is an
implementation detail (always pd.DataFrame) and is not part of the
public metadata schema.
"""

import inspect
import re
import textwrap
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Regex patterns for docstring parsing
# ---------------------------------------------------------------------------

# Matches "Type: TRIGGER" or "Type: FILTER"
_TYPE_RE = re.compile(r"^\s*Type:\s*(TRIGGER|FILTER)\s*$", re.MULTILINE)

# Matches "Requires: Close" or "Requires: High, Low, Close" or "Requires: None"
_REQUIRES_RE = re.compile(r"^\s*Requires:\s*(.+)$", re.MULTILINE)

# Matches "Disabled: True"
_DISABLED_RE = re.compile(r"^\s*Disabled:\s*(True|False)\s*$", re.MULTILINE)

# Matches "Disabled-Reason: some text here"
_DISABLED_REASON_RE = re.compile(r"^\s*Disabled-Reason:\s*(.+)$", re.MULTILINE)

# Matches the Args: section header
_ARGS_HEADER_RE = re.compile(r"^\s*Args:\s*$", re.MULTILINE)

# --- authored-metadata sections (the docstring-as-SSOT format) --------------------------------
# Every authored value lives in the docstring of the thing it describes; the code supplies
# everything derivable. See docs/backfill-authored-values-into-docstrings.md.

#: Opens every indicator and signal docstring: the KIND and the CODE name, so the builder can
#: assert the docstring is attached to the object it claims to document. A docstring copy-pasted
#: onto the wrong class then fails the build instead of silently mislabelling a node.
_DECL_RE = re.compile(r"^\s*(Indicator|Signal):\s*(\S+)\s*$")

#: Sections carrying a single inline value.
_INLINE_SECTIONS = ("Abbreviation", "Reference")
#: Sections carrying an indented block.
_BLOCK_SECTIONS = ("Formula", "Inputs", "Outputs", "Interpretation", "Applications")
#: Sections the pre-existing parser already owns; listed so the description stops at them too.
_LEGACY_SECTIONS = ("Type", "Requires", "Disabled", "Disabled-Reason", "Args", "Returns")

_ALL_SECTIONS = _INLINE_SECTIONS + _BLOCK_SECTIONS + _LEGACY_SECTIONS
_SECTION_START_RE = re.compile(r"^(" + "|".join(_ALL_SECTIONS) + r"):")

#: Which sections each kind may carry. Enforced, not documented -- an `Interpretation:` on a signal
#: is an authoring mistake, and the graph has no field to receive it.
PERMITTED = {
    "Indicator": set(_INLINE_SECTIONS) | set(_BLOCK_SECTIONS) | {"Args", "Returns"},
    "Signal": {"Reference", "Formula", "Inputs", "Outputs", "Type", "Requires",
               "Disabled", "Disabled-Reason", "Args", "Returns"},
}

#: `name [units, lo..hi]` with an optional `"canonical name"`. Omitting the quoted name parses back
#: to the literal string "none", which is what the graph holds for an output that has none.
_OUTPUT_RE = re.compile(r"^(\w+)\s*\[([^,\]]+),\s*([^\]]+)\]\s*(?:\"([^\"]+)\")?\s*:\s*$")

# Matches a parameter line:  "name (type): Description text. Range: X-Y. Default: V."
# Captures: name, type, description_and_rest
# After inspect.getdoc() strips common indentation, params are at 4-space indent.
_PARAM_LINE_RE = re.compile(
    r"^\s{4,}(\w+)\s*\(([^)]+)\)\s*:\s*(.+)$"
)

# Extracts Range from a description string: "Range: min-max" or "Range: min-max."
# Handles negative numbers like "Range: -200--50" or "Range: -100--70"
# The separator is a single '-' with NO surrounding whitespace so that a
# negative max value (e.g. "-50") is not confused with the separator.
_RANGE_RE = re.compile(
    r"Range:\s*(-?[\d.]+)-(-?[\d.]+)"
)

# Extracts Default from a description string: "Default: value." or "Default: value"
_DEFAULT_RE = re.compile(
    r"Default:\s*(.+?)\.?\s*$"
)


# ---------------------------------------------------------------------------
# Value conversion helpers
# ---------------------------------------------------------------------------

def _convert_value(raw: str, type_str: str) -> Any:
    """Convert a raw string value to the appropriate Python type.

    Args:
        raw: The raw string value extracted from the docstring.
        type_str: The type name string (e.g. "int", "float", "str", "bool").

    Returns:
        The converted value, or the raw string if the type is unrecognized.
    """
    raw = raw.strip().rstrip(".")
    type_str = type_str.strip()

    if type_str == "int":
        # Handle floats written as "14" or "14.0"
        return int(float(raw))
    elif type_str == "float":
        return float(raw)
    elif type_str == "bool":
        return raw.lower() in ("true", "1", "yes")
    elif type_str == "str":
        # Strip surrounding quotes if present
        return raw.strip("'\"")
    else:
        return raw


def _convert_range_value(raw: str, type_str: str) -> Any:
    """Convert a range boundary value to a numeric type.

    Range values are always numeric (int or float). We infer the target
    type from the parameter's declared type.

    Args:
        raw: The raw string value for min or max.
        type_str: The parameter's declared type string.

    Returns:
        int or float value.
    """
    raw = raw.strip()
    type_str = type_str.strip()
    if type_str == "int":
        return int(float(raw))
    else:
        return float(raw)


# ---------------------------------------------------------------------------
# Core parsing functions
# ---------------------------------------------------------------------------

def _extract_description(docstring: str) -> str:
    """Extract the description text from a docstring.

    The description is everything from the start of the docstring up to (but
    not including) the first structured tag line (Type:, Requires:, Disabled:,
    Args:, Returns:).

    Multi-line descriptions are joined with a single space. Extra blank lines
    and leading/trailing whitespace are stripped.

    Args:
        docstring: The raw docstring text.

    Returns:
        A cleaned single-line description string.
    """
    lines = docstring.split("\n")
    desc_lines = []
    for line in lines:
        stripped = line.strip()
        # Stop at the first structured tag
        if _SECTION_START_RE.match(stripped):
            break
        desc_lines.append(stripped)

    # Join, collapse whitespace, strip
    desc = " ".join(desc_lines).strip()
    # Collapse multiple spaces
    desc = re.sub(r"\s+", " ", desc)
    return desc


def _parse_params_section(docstring: str) -> dict:
    """Parse the Args section of a docstring into a parameter metadata dict.

    Each parameter entry is extracted with its name, type, description,
    optional Range (min/max), and optional Default value. The special
    `df` parameter is always excluded.

    Args:
        docstring: The raw docstring text.

    Returns:
        A dict mapping parameter names to their metadata dicts.
    """
    params = {}

    # Find the Args: section
    args_match = _ARGS_HEADER_RE.search(docstring)
    if not args_match:
        return params

    # Get text after "Args:" up to next section header (Returns:, etc.) or end
    after_args = docstring[args_match.end():]

    # Split into lines and parse each parameter
    lines = after_args.split("\n")

    # Collect parameter blocks (a param line may be followed by continuation lines)
    current_param_text = None
    param_texts = []

    for line in lines:
        stripped = line.strip()

        # Stop at the next section header
        if re.match(r"^(Returns|Raises|Notes|Examples|Type|Requires|Disabled):", stripped):
            break

        # Check if this is a new parameter line
        param_match = _PARAM_LINE_RE.match(line)
        if param_match:
            # Save previous parameter text
            if current_param_text is not None:
                param_texts.append(current_param_text)
            current_param_text = line
        elif current_param_text is not None and stripped:
            # Continuation of previous parameter description
            current_param_text += " " + stripped
        elif not stripped and current_param_text is not None:
            # Blank line ends the current parameter
            param_texts.append(current_param_text)
            current_param_text = None

    # Don't forget the last parameter
    if current_param_text is not None:
        param_texts.append(current_param_text)

    # Now parse each parameter text
    for text in param_texts:
        match = _PARAM_LINE_RE.match(text)
        if not match:
            continue

        name = match.group(1).strip()
        ptype = match.group(2).strip()
        rest = match.group(3).strip()

        # If there's continuation text appended, include it
        full_text = text[match.end():].strip()
        if full_text:
            rest = rest + " " + full_text

        # Skip the `df` parameter -- it's always present and not in the metadata
        if name == "df":
            continue

        # Clean the type: "pd.DataFrame" -> skip, "int" -> "int", etc.
        # Normalize common type annotations
        clean_type = ptype.split(".")[-1] if "." in ptype else ptype

        # Build the param metadata dict
        param_meta = {
            "type": clean_type,
        }

        # Extract description (everything before "Range:" or "Default:")
        desc_text = rest
        # Remove Range and Default portions to get clean description
        desc_clean = re.sub(r"\s*Range:.*$", "", desc_text)
        desc_clean = re.sub(r"\s*Default:.*$", "", desc_clean)
        desc_clean = desc_clean.strip().rstrip(".")
        param_meta["description"] = desc_clean

        # Extract Range
        range_match = _RANGE_RE.search(rest)
        if range_match:
            min_val = _convert_range_value(range_match.group(1).rstrip('.'), clean_type)
            max_val = _convert_range_value(range_match.group(2).rstrip('.'), clean_type)
            param_meta["min"] = min_val
            param_meta["max"] = max_val

        # Extract Default
        default_match = _DEFAULT_RE.search(rest)
        if default_match:
            default_raw = default_match.group(1).strip().rstrip(".")
            param_meta["optional"] = True
            # "Default: None" means the param is optional with no default value
            # (it maps to Python None, which is omitted from the JSON schema)
            if default_raw.lower() != "none":
                param_meta["default"] = _convert_value(default_raw, clean_type)
        else:
            # No default means the parameter is required
            param_meta["optional"] = False

        params[name] = param_meta

    return params


def _get_rule_name_from_registry(func) -> Optional[str]:
    """Look up the rule name for a function in the RuleRegistry.

    Searches the RuleRegistry._registry dict for a function object that
    matches the given function. Returns the registered name if found.

    This approach handles the common case where the function is registered
    via @RuleRegistry.register("name").

    Args:
        func: The function object to look up.

    Returns:
        The registered rule name string, or None if not found.
    """
    try:
        from mangrove_kb.registry import RuleRegistry
        for name, registered_func in RuleRegistry._registry.items():
            if registered_func is func:
                return name
    except ImportError:
        pass
    return None


def _get_rule_name_from_source(func) -> Optional[str]:
    """Extract rule name from function source code by finding the decorator.

    Falls back to inspecting the source code for the
    @RuleRegistry.register("name") decorator pattern when the registry
    is not available.

    Args:
        func: The function object to inspect.

    Returns:
        The rule name string from the decorator, or None if not found.
    """
    try:
        source = inspect.getsource(func)
        match = re.search(
            r'@RuleRegistry\.register\(["\']([^"\']+)["\']\)',
            source
        )
        if match:
            return match.group(1)
    except (OSError, TypeError):
        pass
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_signal_docstring(func) -> dict:
    """Parse a signal function's docstring into structured metadata.

    Takes a function object (typically decorated with @RuleRegistry.register)
    and extracts metadata from its docstring that matches the
    signals_metadata.json schema.

    The returned dict has the following structure::

        {
            "rule_name": "rsi_overbought",
            "description": "Check if RSI is above the overbought threshold...",
            "type": "FILTER",
            "requires": ["Close"],
            "params": {
                "window": {
                    "type": "int",
                    "description": "RSI calculation window",
                    "min": 2,
                    "max": 100,
                    "optional": true,
                    "default": 14
                }
            }
        }

    If the signal is disabled, the dict will also contain::

        "disabled": True,
        "disabled_reason": "Social signals integration not yet available"

    Args:
        func: A Python function object with a structured docstring.

    Returns:
        A dict containing the parsed metadata.

    Raises:
        ValueError: If the function has no docstring or is missing
            required fields (Type, Requires).
    """
    docstring = inspect.getdoc(func)
    if not docstring:
        raise ValueError(f"Function {func.__name__} has no docstring")

    # Determine rule name
    rule_name = _get_rule_name_from_registry(func)
    if not rule_name:
        rule_name = _get_rule_name_from_source(func)
    if not rule_name:
        rule_name = func.__name__

    # Extract Type
    type_match = _TYPE_RE.search(docstring)
    if not type_match:
        raise ValueError(
            f"Function {func.__name__} docstring missing 'Type:' tag"
        )
    signal_type = type_match.group(1)

    # Extract Requires
    requires_match = _REQUIRES_RE.search(docstring)
    if not requires_match:
        raise ValueError(
            f"Function {func.__name__} docstring missing 'Requires:' tag"
        )
    requires_raw = requires_match.group(1).strip()
    if requires_raw.lower() == "none":
        requires = []
    else:
        requires = [r.strip() for r in requires_raw.split(",")]

    # Extract description
    description = _extract_description(docstring)

    # Extract params
    params = _parse_params_section(docstring)

    # Build result
    result = {
        "rule_name": rule_name,
        "description": description,
        "type": signal_type,
        "requires": requires,
        "params": params,
    }

    # Extract Disabled flag
    disabled_match = _DISABLED_RE.search(docstring)
    if disabled_match and disabled_match.group(1).lower() == "true":
        result["disabled"] = True

        # Extract Disabled-Reason
        reason_match = _DISABLED_REASON_RE.search(docstring)
        if reason_match:
            result["disabled_reason"] = reason_match.group(1).strip()

    return result


def parse_all_signals(signal_modules: list) -> dict:
    """Parse all registered signal functions from a list of modules.

    Iterates over each module, finds all functions decorated with
    @RuleRegistry.register, and parses their docstrings into structured
    metadata.

    Signal functions are identified by looking them up in the
    RuleRegistry._registry. For each registered function, the module
    that defines it is checked against the provided module list.

    Args:
        signal_modules: A list of Python module objects containing
            signal functions (e.g. momentum.signals, trend.signals).

    Returns:
        A dict mapping signal names to their metadata dicts, e.g.::

            {
                "rsi_overbought": { ... },
                "sma_cross_up": { ... },
                ...
            }
    """
    from mangrove_kb.registry import RuleRegistry
    registry = RuleRegistry._registry

    # Build a set of module names for fast lookup
    module_names = set()
    for mod in signal_modules:
        module_names.add(mod.__name__)
        # Also include parent package names (e.g. for "momentum.signals"
        # we might need to match against "MangroveAI.domains.signals.momentum.signals")

    all_signals = {}

    # Snapshot the registry to avoid "dictionary changed size during iteration"
    # when signal module imports trigger late registrations.
    for name, func in dict(registry).items():
        # Check if this function belongs to one of the provided modules
        func_module = getattr(func, "__module__", None)
        if func_module is None:
            continue

        # Match if the function's module is in our set, or if any of our
        # module names is a suffix of the function's module
        belongs = False
        if func_module in module_names:
            belongs = True
        else:
            for mod_name in module_names:
                if func_module.endswith(mod_name.split(".")[-1]):
                    belongs = True
                    break
                # Also check if the module objects match
            for mod in signal_modules:
                if func_module == mod.__name__:
                    belongs = True
                    break

        if not belongs:
            # If we can't match by module name, try to see if the function
            # is actually defined in one of the modules
            for mod in signal_modules:
                if hasattr(mod, func.__name__):
                    mod_func = getattr(mod, func.__name__)
                    if mod_func is func:
                        belongs = True
                        break

        if not belongs:
            continue

        try:
            metadata = parse_signal_docstring(func)
            all_signals[name] = metadata
        except (ValueError, OSError) as e:
            # Log but don't fail for individual parse errors
            print(f"Warning: Could not parse docstring for '{name}': {e}")

    return all_signals


# --- the docstring-as-SSOT reader ----------------------------------------------------------------

class DocstringFormatError(ValueError):
    """The docstring does not conform to the authored-metadata format."""


def _num(raw: str) -> Any:
    """A range bound. `inf`/`-inf` are real values here, never a stand-in for null."""
    raw = raw.strip()
    if raw in ("inf", "+inf"):
        return float("inf")
    if raw == "-inf":
        return float("-inf")
    return float(raw) if "." in raw else int(raw)


def _split_sections(body: list[str]) -> "OrderedDictType[str, list[str]]":
    """Split docstring lines into `{section: lines}` plus a `_prose` bucket for the preamble."""
    from collections import OrderedDict
    out: "OrderedDictType[str, list[str]]" = OrderedDict()
    out["_prose"] = []
    current = "_prose"
    for line in body:
        stripped = line.strip()
        if _SECTION_START_RE.match(stripped):
            name, _, inline = stripped.partition(":")
            current = name
            out[current] = [inline.strip()] if inline.strip() else []
        else:
            out[current].append(line)
    return out


def parse_authored(docstring: str) -> dict:
    """Read every AUTHORED value out of an indicator or signal docstring.

    Returns the kind, the declared code name, and only the fields a human wrote. Nothing derivable
    from the code is read here -- param types, defaults, `usage_example`, `source_module`, warmup and
    the graph's edges all come from the code itself, and a docstring that restated them could
    contradict it.

    Raises:
        DocstringFormatError: if the declaration line is missing or malformed, or if a section is
            used on a kind that may not carry it.
    """
    if not docstring or not docstring.strip():
        raise DocstringFormatError("empty docstring")
    raw = textwrap.dedent("    " + docstring.strip("\n")).split("\n")
    decl = _DECL_RE.match(raw[0].strip())
    if not decl:
        raise DocstringFormatError(
            f"first line must be 'Indicator: <Name>' or 'Signal: <name>', got {raw[0].strip()!r}")
    kind, name = decl.group(1), decl.group(2)

    secs = _split_sections(textwrap.dedent("\n".join(raw[1:])).split("\n"))
    used = {k for k in secs if k != "_prose"}
    if forbidden := used - PERMITTED[kind]:
        raise DocstringFormatError(
            f"{kind} {name!r} carries section(s) it may not have: {', '.join(sorted(forbidden))}")

    res: dict = {"kind": kind, "name": name}

    prose = textwrap.dedent("\n".join(secs["_prose"])).strip("\n")
    paragraphs = [re.sub(r"\s+", " ", p.strip()) for p in prose.split("\n\n") if p.strip()]
    # The SUMMARY is the first paragraph only. Everything after it is preserved prose -- design
    # rationale, caveats -- which belongs in the docstring but is not a graph field. Collapsing all
    # of it into the summary was the bug this split exists to prevent.
    if paragraphs:
        res["summary"] = paragraphs[0]

    for sec in _INLINE_SECTIONS:
        if sec in secs and secs[sec]:
            res[sec.lower()] = secs[sec][0].strip()

    if "Formula" in secs:
        res["formula"] = textwrap.dedent("\n".join(secs["Formula"])).strip("\n").strip()

    for sec in ("Interpretation", "Applications"):
        if sec in secs:
            res[sec.lower()] = [l.strip()[2:].strip() for l in secs[sec] if l.strip().startswith("- ")]

    if "Inputs" in secs:
        res["inputs"] = {}
        for line in secs["Inputs"]:
            if line.strip() and ":" in line:
                key, _, desc = line.strip().partition(":")
                res["inputs"][key.strip()] = desc.strip()

    if "Outputs" in secs:
        res["outputs"] = {}
        current = None
        for line in secs["Outputs"]:
            if not line.strip():
                continue
            m = _OUTPUT_RE.match(line.strip())
            if m:
                current = m.group(1)
                lo, _, hi = m.group(3).partition("..")
                res["outputs"][current] = {
                    "units": m.group(2).strip(),
                    "range": [_num(lo), _num(hi)],
                    "canonical_name": m.group(4) or "none",
                    "description": [],
                }
            elif current is None:
                raise DocstringFormatError(
                    f"{kind} {name!r}: text under Outputs before any output line: {line.strip()!r}")
            else:
                res["outputs"][current]["description"].append(line.strip())
        for spec in res["outputs"].values():
            spec["description"] = " ".join(spec["description"]).strip()

    return res

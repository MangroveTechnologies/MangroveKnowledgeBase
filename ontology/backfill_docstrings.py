"""Write the graph's authored values into the docstrings they came from.

One-time migration. Reads the committed graph, renders each node's authored values in the
authored-metadata format, and replaces the docstring of the class or function in place.

Only AUTHORED values are written. Everything the code already states -- param types and defaults,
usage examples, source module, warmup, the edges -- is left to be derived, because a docstring that
restated it could contradict it.

The existing `Args:` / `Returns:` / `Type:` / `Requires:` sections are preserved verbatim: they are
read by the pre-existing parser and are not this migration's business.

    python3 ontology/backfill_docstrings.py --dry-run     # report, touch nothing
    python3 ontology/backfill_docstrings.py               # rewrite in place
"""
from __future__ import annotations

import argparse
import inspect
import json
import re
import sys
import textwrap
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from mangrove_kb import indicators                      # noqa: E402
from mangrove_kb.registry import RuleRegistry           # noqa: E402

GRAPH = REPO / "ontology" / "signal-indicator-ontology.json"

#: Sections owned by the pre-existing parser. Kept exactly as they are.
_KEEP = re.compile(r"^\s*(Type|Requires|Disabled|Disabled-Reason|Args|Returns):")


def _fmt_range(bounds) -> str:
    def one(v):
        if v == float("inf"):
            return "inf"
        if v == float("-inf"):
            return "-inf"
        return str(v)
    return f"{one(bounds[0])}..{one(bounds[1])}"


def _wrap(text: str, width: int = 96, indent: str = "") -> list[str]:
    # Text that aligns columns with runs of spaces cannot survive re-wrapping -- rejoining would
    # need to guess where the runs were. Emit it verbatim on one line instead; long, but lossless.
    if re.search(r"\S  +\S", text):
        return [indent + text]
    # break_on_hyphens is the trap: it splits "Non-negative" across lines, and re-joining on parse
    # yields "Non- negative". break_long_words would do the same to a reference URL.
    return textwrap.wrap(text, width=width, initial_indent=indent, subsequent_indent=indent,
                         break_on_hyphens=False, break_long_words=False) or [""]


def render(node: dict, kind: str) -> str:
    """The authored half of a node, as a docstring body. Inverse of `parse_authored`."""
    p = node.get("props") or {}
    out: list[str] = [f"{kind}: {node['title']}", ""]
    out += _wrap(node["summary"])

    # Warmup is AUTHORED, not derived. The old builder guessed it from `min_periods` only where
    # unambiguous and otherwise let the carried-forward authored value stand -- 53 indicators
    # disagree with any such guess, so the guess cannot be the source.
    inline = [("Abbreviation", p.get("abbreviation")), ("Reference", p.get("reference")),
              ("Warmup", p.get("warmup_bars"))]
    # `is not None`, not truthiness: CandleRaw's warmup is the integer 0, which a falsy
    # check silently drops.
    inline = [(k, v) for k, v in inline if v is not None and v != ""]
    if inline:
        out.append("")
        out += [f"{k}: {v}" for k, v in inline]

    if p.get("formula"):
        out += ["", "Formula:"]
        out += [("    " + l if l.strip() else "") for l in p["formula"].split("\n")]

    if p.get("inputs"):
        out += ["", "Inputs:"]
        for name, spec in p["inputs"].items():
            out += _wrap(f"{name}: {spec['description']}", indent="    ")

    if p.get("params"):
        # Only the DESCRIPTION is authored. type/default/min/max are read from the signature and
        # the wrapping signals' Args blocks, and restating them here would let the two disagree.
        rows = []
        for name, spec in p["params"].items():
            bits = [f"{k}={spec[k]!r}" for k in ("default", "min", "max") if spec.get(k) is not None]
            head = f"{name} [{', '.join(bits)}]" if bits else name
            rows.append(f"{head}: {spec.get('description') or ''}".rstrip())
        if rows:
            out += ["", "Params:"]
            for r in rows:
                out += _wrap(r, indent="    ")

    if p.get("outputs"):
        out += ["", "Outputs:"]
        for name, spec in p["outputs"].items():
            canon = f' "{spec["canonical_name"]}"' if spec.get("canonical_name") not in (None, "none") else ""
            out.append(f"    {name} [{spec['units']}, {_fmt_range(spec['range'])}]{canon}:")
            out += _wrap(spec["description"], indent="        ")

    for label, key in (("Interpretation", "interpretation"), ("Applications", "applications")):
        value = p.get(key)
        if value:
            out += ["", f"{label}:"]
            # 64 nodes hold a LIST here and 7 hold a plain string. Both shapes must survive, so a
            # list renders as bullets and a string renders as prose; the parser reads the shape back
            # off the presence of bullets rather than being told.
            if isinstance(value, str):
                out += _wrap(value, indent="    ")
            else:
                for item in value:
                    out += _wrap(f"- {item}", indent="    ")

    return "\n".join(out)


def _preserved_tail(doc: str) -> list[str]:
    """The `Args:`/`Returns:`/`Type:`/`Requires:` block, verbatim, from the current docstring."""
    lines = doc.split("\n")
    for i, line in enumerate(lines):
        if _KEEP.match(line):
            return lines[i:]
    return []


def new_docstring(node: dict, kind: str, current: str) -> str:
    body = render(node, kind)
    tail = _preserved_tail(current)
    return body + ("\n\n" + "\n".join(l.rstrip() for l in tail).strip("\n") if tail else "")


def _docstring_span(lines: list[str], def_line: int) -> tuple[int, int] | None:
    """(start, end) line indices of the docstring belonging to the def/class at `def_line`.

    Located by AST-free scanning from the signature, which may span several lines.
    """
    i = def_line
    while i < len(lines) and '"""' not in lines[i]:
        i += 1
        if i - def_line > 40:
            return None
    if i >= len(lines):
        return None
    if lines[i].count('"""') >= 2:
        return (i, i)
    for j in range(i + 1, len(lines)):
        if '"""' in lines[j]:
            return (i, j)
    return None


def rewrite_file(path: Path, jobs: list[tuple[int, str]], indent: str = "    ") -> int:
    """Replace several docstrings in one file, BOTTOM-UP so earlier edits cannot shift later spans.

    Rewriting top-down and re-reading line numbers from `inspect` between edits is what corrupted
    the tree on the first attempt: every replacement moved the lines beneath it, `inspect` served
    cached positions, and docstrings landed on the wrong functions -- `stochrsi_overbought` ended up
    holding `williams_r_overbought`'s text. One read, one write, descending line order.
    """
    lines = path.read_text().split("\n")
    done = 0
    for def_line, body in sorted(jobs, key=lambda j: -j[0]):
        span = _docstring_span(lines, def_line)
        if span is None:
            continue
        rendered = [indent + l if l.strip() else "" for l in body.split("\n")]
        block = [indent + '"""' + rendered[0].strip()] + rendered[1:] + [indent + '"""']
        lines[span[0]:span[1] + 1] = block
        done += 1
    path.write_text("\n".join(lines))
    return done


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", help="restrict to one node title")
    args = ap.parse_args()

    graph = json.loads(GRAPH.read_text())
    atoms = {a["id"]: a for a in graph["atoms"]}
    registry = RuleRegistry._registry

    targets = []
    for a in graph["atoms"]:
        if a["id"].startswith("procedure:indicator-"):
            targets.append((a, "Indicator", getattr(indicators, a["title"], None)))
        elif a["id"].startswith("procedure:signal-"):
            targets.append((a, "Signal", registry.get(a["title"])))
    if args.only:
        targets = [t for t in targets if t[0]["title"] == args.only]

    # Collect every edit FIRST, against pristine line numbers, then apply per file bottom-up.
    by_file: dict[Path, list[tuple[int, str]]] = {}
    failed = 0
    for node, kind, obj in targets:
        if obj is None:
            print(f"  UNRESOLVED {node['title']}"); failed += 1; continue
        target = inspect.unwrap(obj)
        path = Path(inspect.getsourcefile(target))
        _, lineno = inspect.getsourcelines(target)
        body = new_docstring(node, kind, inspect.getdoc(obj) or "")
        by_file.setdefault(path, []).append((lineno, body))

    done = sum(len(v) for v in by_file.values())
    if args.dry_run:
        print(f"would rewrite {done} docstrings across {len(by_file)} files; unresolved {failed}")
        return 1 if failed else 0
    written = sum(rewrite_file(path, jobs) for path, jobs in by_file.items())
    print(f"rewrote {written} of {done} docstrings across {len(by_file)} files; unresolved {failed}")
    failed += done - written
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

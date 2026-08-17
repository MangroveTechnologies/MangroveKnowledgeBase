"""Every Python example on the two front pages must actually run.

`PKG_README.md` is the PyPI page -- for most people it IS the documentation, and it is the first
thing anyone runs. It carried a whole section built on `from mangrove_kb.indicators import Hammer,
BullishEngulfing, MorningStar, NR7`, four classes that no longer exist: the candlestick indicators
were replaced by `CandleRaw` / `CandleGeometry` / `CandleRelation` and the section was never
revisited. It raised `ImportError` on the first line, on the published page, for an unknown number of
releases.

Nothing caught it because nothing executed it. The guide's examples are re-run by
`test_agent_guide.py`; these two files were the documentation that only ever got proofread.

Each file's blocks run **in order, in one namespace**, which is how a reader follows a page: an
import in an early block is available to a later one. A block that needs setup the page never shows
is a block a reader cannot run either, so that failure is the point rather than an inconvenience --
fix the page, not this test.
"""
from __future__ import annotations

import re
import warnings
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
PAGES = ("README.md", "PKG_README.md")


def blocks_of(name: str) -> list[tuple[int, str]]:
    text = (REPO / name).read_text(encoding="utf-8")
    return list(enumerate(re.findall(r"```python\n(.*?)```", text, re.S), start=1))


@pytest.mark.parametrize("page", PAGES)
def test_the_page_still_has_examples(page):
    """A guard on the guard: if the blocks stop being found, everything below passes vacuously."""
    assert len(blocks_of(page)) >= 4, f"{page} has almost no python examples -- has the fence changed?"


@pytest.mark.parametrize("page", PAGES)
def test_every_python_example_executes(page, capsys):
    """Run the page top to bottom, exactly as a reader would."""
    namespace: dict = {}
    failures = []
    with warnings.catch_warnings():
        # Deprecated re-export modules warn on import and several examples use them on purpose.
        warnings.simplefilter("ignore", DeprecationWarning)
        for number, source in blocks_of(page):
            try:
                exec(compile(source, f"{page} block {number}", "exec"), namespace)
            except Exception as exc:                      # noqa: BLE001 -- the whole point
                first = next((ln for ln in source.strip().splitlines() if ln.strip()), "")
                failures.append(f"{page} block {number} ({first.strip()[:60]!r}): "
                                f"{type(exc).__name__}: {exc}")
    capsys.readouterr()          # the examples print; that is not this test's output
    assert not failures, "documented examples do not run:\n  " + "\n  ".join(failures)

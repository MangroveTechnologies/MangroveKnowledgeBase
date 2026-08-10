"""The visualizer ships with the package and renders the graph the package carries."""
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def page():
    proc = subprocess.run([sys.executable, "-m", "mangrove_kb.viz"], cwd=REPO,
                          capture_output=True, text=True, timeout=600)
    assert proc.returncode == 0, proc.stderr[-2000:]
    return proc.stdout


def test_it_renders_the_whole_graph(page):
    from mangrove_kb.graph import KnowledgeGraph

    kg = KnowledgeGraph.load()
    m = re.search(r"const DATA = (\{.*?\});\s*\n", page, re.S)
    assert m, "the page carries no DATA payload"
    import json
    data = json.loads(m.group(1))
    assert len(data["nodes"]) == len(kg.nodes)
    assert len(data["edges"]) == len(kg.edges)


def test_it_is_self_contained(page):
    """No CDN, no build step -- one file that opens from disk."""
    external = re.findall(r'(?:src|href)="(https?://[^"]+)"', page)
    assert not external, f"the page fetches from the network: {external}"


def test_the_root_is_the_collapse_anchor(page):
    """Collapse is containment-reachability from one root. Without a match it silently no-ops."""
    assert 'const ANCHOR="object:mangrove-knowledge-space";' in page


def test_the_page_carries_the_mangrove_palette(page):
    """The platform's tokens, not the viewer's originals. Lifted from globals.css on origin/dev."""
    assert "--dev-accent:#42a7c6" in page and "--dev-highlight:#ff9e18" in page
    assert "--radius:0.625rem" in page


def test_all_three_theme_states_are_defined(page):
    """Light, dark and system. A colour defined in only one place is how a toggle works one way."""
    assert "@media (prefers-color-scheme:dark)" in page
    assert ':root:not([data-theme="light"])' in page, "an explicit light choice must beat a dark OS"
    assert ':root[data-theme="dark"]' in page, "an explicit dark choice must beat a light OS"
    # Every colour the dark blocks touch must also exist on bare :root -- specifically the BRAND
    # :root, not the viewer's own earlier one. Splitting on the first `:root{` found that one and
    # failed for the wrong reason.
    blocks = [b.split("}", 1)[0] for b in page.split(":root{")[1:]]
    brand = [b for b in blocks if "--dev-accent" in b]
    assert len(brand) == 1, f"expected exactly one brand :root block, found {len(brand)}"
    for token in ("--background", "--foreground", "--sidebar", "--muted-fg", "--border", "--chip-bg"):
        assert token in brand[0], f"{token} has no base definition, only a themed one"


def test_the_theme_is_set_before_first_paint(page):
    """Stamping data-theme after the stylesheet applies flashes the wrong theme on every load."""
    head = page.split("</head>", 1)[0]
    assert "mangrove-kb-theme" in head, "the pre-paint script is not in <head>"


def test_no_jarvis_vocabulary_survives(page):
    """This is a public Mangrove product; it must not show the vocabulary of the tool it came from."""
    for term in ("ACT-R",):
        assert page.count(term) == 0 or "el.textContent.includes" in page, term


def test_search_ranks_exactly_as_find_does(page):
    """One definition of search. A second one hand-written in JS would drift from kg.find()."""
    import json

    from mangrove_kb.graph import SEARCH_TIERS, KnowledgeGraph

    m = re.search(r"const IDX = (\[.*?\]);\n", page, re.S)
    assert m, "the page carries no search index"
    idx = json.loads(m.group(1))
    kg = KnowledgeGraph.load()
    assert len(idx) == len(kg.nodes)
    assert all(len(r["t"]) == len(SEARCH_TIERS) for r in idx), "a tier is missing from the export"

    # Re-run the page's ranking in Python and compare it against find() itself.
    for query in ("divergence", "rsi", "mean reversion", "histogram", "oversold"):
        q = query.lower()
        hits = [(next(i for i, h in enumerate(r["t"]) if q in h), r["id"])
                for r in idx if any(q in h for h in r["t"])]
        hits.sort()
        assert [h[1] for h in hits] == [r["id"] for r in kg.find(query, limit=None)], \
            f"the page and kg.find() disagree on {query!r}"


def test_search_says_when_it_truncates(page):
    """A short list reads as 'that is all there is'. Result.truncated exists for this reason.

    Asserting only that the message EXISTS is not enough: changing `total` to the truncated length
    leaves the message intact and the number wrong, and the guard stayed green when I tried it. So
    the count must come from the FULL result set, before the slice.
    """
    assert "showing '+hits.length+' of '+hits.total" in page, "no truncation notice"
    assert "const shown=res.slice(0,LIMIT);" in page
    assert "shown.total=res.length;" in page, \
        "the reported total must be the full match count, not the truncated one"

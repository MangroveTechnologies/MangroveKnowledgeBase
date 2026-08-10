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

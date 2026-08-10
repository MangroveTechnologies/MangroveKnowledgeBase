"""The published wheel must contain the graph and the skills, not just the Python modules.

This is a regression test for a defect that shipped: `pip install mangrove-kb` produced a package
whose `KnowledgeGraph.load()` raised, because the wheel carried `mangrove_kb/` and nothing else --
the graph sat in `ontology/` outside the package, and `mangrove_kb/data/` did not exist. Nothing in
the suite noticed, because every other test runs from a source checkout where the repo-relative
fallback path resolves.

So the check has to be made against a REAL BUILT ARTIFACT. Reading `pyproject.toml` and reasoning
about what setuptools would include is what produced the bug.
"""
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from mangrove_kb.graph import _PACKAGED

REPO = Path(__file__).resolve().parent.parent
PKG = "mangrove_kb"


#: Never copied into the hermetic build tree. `build/` is the important one: setuptools stages into
#: `build/lib/` and does not remove files it no longer produces, so a leftover copy of the graph from
#: an earlier build satisfies these assertions even when the build hook has been deleted outright.
#: That was observed, not theorised -- removing the hook left three of these tests green.
_NOT_SOURCE = shutil.ignore_patterns(".git", "build", "dist", "*.egg-info", "__pycache__",
                                     ".pytest_cache", ".ruff_cache", "venv", ".venv")


@pytest.fixture(scope="module")
def wheel(tmp_path_factory):
    """A wheel built from a pristine copy of this checkout, as the release workflow builds it.

    Hermetic on purpose. Building in place reuses `build/`, and `--no-cache-dir` alone does not save
    you -- pip's wheel cache is only one of the two things that can hand back a stale artifact.
    """
    src = tmp_path_factory.mktemp("src") / "repo"
    shutil.copytree(REPO, src, ignore=_NOT_SOURCE)

    out = tmp_path_factory.mktemp("wheel")
    env = {**os.environ, "SETUPTOOLS_SCM_PRETEND_VERSION": "0.0.0"}   # the copy has no .git
    proc = subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-deps", "--no-cache-dir",
                           "-w", str(out), str(src)],
                          capture_output=True, text=True, timeout=900, env=env)
    assert proc.returncode == 0, f"wheel build failed:\n{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}"
    built = list(out.glob("*.whl"))
    assert len(built) == 1, f"expected one wheel, got {built}"
    return zipfile.ZipFile(built[0])


def test_the_graph_is_in_the_wheel(wheel):
    """And at exactly the path the library looks for it -- not merely somewhere in the archive."""
    want = f"{PKG}/{_PACKAGED.relative_to(_PACKAGED.parent.parent)}".replace("\\", "/")
    assert want in wheel.namelist(), (
        f"{want} is not in the wheel. `pip install mangrove-kb` would give a package whose "
        f"KnowledgeGraph.load() raises. Present json files: "
        f"{[n for n in wheel.namelist() if n.endswith('.json')] or 'none'}")


def test_the_packaged_graph_is_the_committed_graph(wheel):
    """One canonical graph. A stale copy inside the wheel is worse than none -- it answers wrong."""
    want = f"{PKG}/{_PACKAGED.relative_to(_PACKAGED.parent.parent)}".replace("\\", "/")
    committed = (REPO / "ontology" / "signal-indicator-ontology.json").read_bytes()
    assert wheel.read(want) == committed, "the wheel's graph differs from the committed one"


def test_the_skills_are_in_the_wheel(wheel):
    """An agent that installs the package should get the instructions for using it."""
    for name in ("SKILL.md", "GUIDE.md"):
        want = f"{PKG}/skills/knowledge-graph/{name}"
        assert want in wheel.namelist(), (
            f"{want} is not in the wheel; present markdown: "
            f"{[n for n in wheel.namelist() if n.endswith('.md')] or 'none'}")


def test_every_bundled_source_exists():
    """Fast guard on the setup.py <-> graph.py contract, independent of a build.

    `setup.py` names the files it copies into the wheel by path. If one is renamed or moved and the
    hook is not updated, the build raises -- but only at release time. This fails immediately.
    """
    sys.path.insert(0, str(REPO))
    try:
        import setup as build_hook              # noqa: PLC0415 -- deliberately imported late
    finally:
        sys.path.pop(0)

    for src, rel in build_hook.BUNDLED:
        assert src.is_file(), f"setup.py bundles {src}, which does not exist"

    destinations = {rel for _, rel in build_hook.BUNDLED}
    expected = str(_PACKAGED.relative_to(_PACKAGED.parent.parent)).replace("\\", "/")
    assert expected in destinations, (
        f"graph.py loads {expected} from inside the package, but setup.py does not put it there; "
        f"it copies {sorted(destinations)}")

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


def test_the_semantic_index_is_in_the_wheel(wheel):
    """Without it `ask()` silently drops to the word search -- twelve of twenty rather than sixteen,
    with nothing in the answer saying which one the caller got."""
    want = f"{PKG}/data/semantic-index.npz"
    assert want in wheel.namelist(), (
        f"{want} is not in the wheel; present data files: "
        f"{[n for n in wheel.namelist() if '/data/' in n] or 'none'}")


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


#: Files inside the package that are not `.py`. setuptools ships only Python modules unless they are
#: declared, and the failure is invisible from a source checkout: every test passes, and the viewer
#: dies on `pip install` with `FileNotFoundError` on its own logo.
NON_PY_PACKAGE_DATA = (
    "mangrove_kb/viz/assets/Mangrove-Horiz-FullColor.svg",
    "mangrove_kb/viz/assets/Mangrove-Horiz-FullColor-WhiteType.svg",
    "mangrove_kb/viz/vendor/3d-force-graph.min.js",
    "mangrove_kb/viz/schema.sql",
)


def test_the_viewers_own_files_are_in_the_wheel(wheel):
    """The 3D view is dead without the vendored library, and the page will not render without the
    wordmark. Both were absent for the first four builds of this package."""
    names = set(wheel.namelist())
    missing = [f for f in NON_PY_PACKAGE_DATA if f not in names]
    assert not missing, (f"the wheel ships no {missing}.\n"
                         f"  Declare them in [tool.setuptools.package-data]; setuptools includes "
                         f"only *.py otherwise, and nothing running from the source tree notices.")


def test_the_viewer_runs_from_the_wheel_alone(wheel, tmp_path):
    """The consumer's check, not ours: install the built artifact into a clean venv OUTSIDE the
    repo and run the documented command. Reading the file list proves the bytes are present; only
    running it proves they are the ones the code reaches for."""
    venv = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True, capture_output=True)
    py = venv / "bin" / "python"
    # `wheel` is an open ZipFile; the artifact's path is on it.
    subprocess.run([str(py), "-m", "pip", "-q", "install", "--no-cache-dir", wheel.filename],
                   check=True, capture_output=True, timeout=900)
    proc = subprocess.run([str(py), "-m", "mangrove_kb.viz"], capture_output=True, text=True,
                          cwd=str(tmp_path), timeout=900)
    assert proc.returncode == 0, f"the viewer does not run from a wheel install:\n{proc.stderr[-1500:]}"
    assert "data:image/svg" in proc.stdout, "the wordmark did not embed -- the SVG is missing"
    assert len(proc.stdout) > 1_000_000, "the page is too small to contain the vendored 3D library"

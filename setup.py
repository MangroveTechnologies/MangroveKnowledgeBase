"""Build hook: put the knowledge graph and the agent skills inside the installed package.

Everything else about this build is declared in ``pyproject.toml``; this file exists only because
setuptools can package data that lives *inside* the package directory, and these two assets are
authored outside it:

* ``ontology/signal-indicator-ontology.json`` -- the graph. It is authored beside the builder that
  writes it and the design notes that explain it, and it is the artifact reviewed in a diff. Moving
  it under ``mangrove_kb/`` to satisfy packaging would drag a dozen references and the two authoring
  skills along with it.
* ``skills/knowledge-graph/`` -- the skill and agent guide. Same reasoning: they are documentation
  first and package data second.

So the source tree keeps one canonical copy of each, and the build copies them into the wheel. There
is never a second committed copy to drift.

Without this, ``pip install mangrove-kb`` yields a package whose ``KnowledgeGraph.load()`` raises:
the wheel carries ``mangrove_kb/`` and nothing else, and the graph is not in it.
``tests/test_wheel_contents.py`` builds a real wheel and asserts otherwise, so this cannot regress
into a silent packaging failure -- which is how it shipped in the first place.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py

HERE = Path(__file__).resolve().parent

#: (source in the repo, destination relative to the installed ``mangrove_kb/``).
BUNDLED = [
    (HERE / "ontology" / "signal-indicator-ontology.json", "data/signal-indicator-ontology.json"),
    (HERE / "skills" / "knowledge-graph" / "SKILL.md", "skills/knowledge-graph/SKILL.md"),
    (HERE / "skills" / "knowledge-graph" / "GUIDE.md", "skills/knowledge-graph/GUIDE.md"),
]


class build_py(_build_py):
    """Copy the bundled assets into the build tree after the Python modules are staged."""

    def run(self) -> None:
        super().run()
        if self.editable_mode:          # an editable install reads the repo directly
            return
        pkg_root = Path(self.build_lib) / "mangrove_kb"
        for src, rel in BUNDLED:
            if not src.is_file():
                # Fail the build rather than ship a package that raises on first use. A wheel
                # missing the graph is indistinguishable from a working one until someone installs it.
                raise FileNotFoundError(
                    f"cannot build mangrove-kb: {src} is missing. It is bundled into the wheel; "
                    f"build the graph first (python ontology/build_signal_indicator_ontology.py) "
                    f"or check the sdist includes it.")
            dst = pkg_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)


# Guarded so a test can import BUNDLED without triggering a build. setuptools' PEP 517 backend
# execs this file with __name__ == "__main__", so the guard does not change how it is built --
# `tests/test_wheel_contents.py` builds a real wheel and would catch it if it did.
if __name__ == "__main__":
    setup(cmdclass={"build_py": build_py})

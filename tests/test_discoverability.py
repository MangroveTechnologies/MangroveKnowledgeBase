"""A consumer who finds this package must be able to find the graph, and the guide to using it.

Both were true of the code and false of the front door: the graph shipped in the wheel and every use
case in `GUIDE.md` ran, but `PKG_README.md` -- the page PyPI renders, and the only thing most
consumers ever read -- did not mention `KnowledgeGraph` at all. Working and discoverable are
different properties and only one of them had a test.
"""
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SKILL = "skills/knowledge-graph/SKILL.md"
GUIDE = "skills/knowledge-graph/GUIDE.md"

#: PyPI renders PKG_README with no repository context, so a relative link 404s there. GitHub renders
#: README in context, where a relative link is correct and survives forks and branches.
PYPI_BASE = "https://github.com/MangroveTechnologies/MangroveKnowledgeBase/blob/main"


@pytest.fixture(scope="module")
def pkg_readme():
    return (REPO / "PKG_README.md").read_text()


@pytest.fixture(scope="module")
def readme():
    return (REPO / "README.md").read_text()


def test_the_pypi_page_tells_you_the_graph_exists(pkg_readme):
    for token in ("KnowledgeGraph", "kg.find(", "knowledge graph"):
        assert token in pkg_readme, f"PKG_README never mentions {token!r}"


def test_the_pypi_page_links_the_skill_and_guide_absolutely(pkg_readme):
    """A relative link on PyPI is a 404, so these two must be full URLs."""
    for rel in (SKILL, GUIDE):
        assert f"{PYPI_BASE}/{rel}" in pkg_readme, f"PKG_README is missing an absolute link to {rel}"


def test_the_github_readme_links_the_skill_and_guide(readme):
    for rel in (SKILL, GUIDE):
        assert f"]({rel})" in readme, f"README is missing a link to {rel}"


@pytest.mark.parametrize("doc", ["README.md", "PKG_README.md"])
def test_every_linked_path_exists(doc):
    """A link to a renamed file is worse than no link -- it looks like documentation."""
    text = (REPO / doc).read_text()
    targets = set(re.findall(r"\]\((?!https?:)([^)#]+)\)", text))
    targets |= {m for m in re.findall(rf"{re.escape(PYPI_BASE)}/([^)\s]+)", text)}
    missing = sorted(t for t in targets if not (REPO / t).exists())
    assert not missing, f"{doc} links to paths that do not exist: {missing}"


def test_the_pypi_graph_snippet_runs(pkg_readme):
    """Every call advertised on the front page has to work, or the first thing a user tries fails."""
    block = next(b for b in re.findall(r"```python\n(.*?)```", pkg_readme, re.S)
                 if "KnowledgeGraph" in b)
    exec(compile(block, "PKG_README.md", "exec"), {})


DOCS = ("README.md", "PKG_README.md", SKILL, GUIDE)


def test_the_four_documents_reference_each_other():
    """SKILL.md linked nothing, so an agent that loaded only the skill never learned the guide
    existed. Each document must point at the others a reader would need next."""
    text = {d: (REPO / d).read_text() for d in DOCS}
    expected = {
        "README.md":     [SKILL, GUIDE],
        "PKG_README.md": [SKILL, GUIDE],
        SKILL:           [GUIDE],
        GUIDE:           [SKILL],
    }
    for doc, targets in expected.items():
        for t in targets:
            name = Path(t).name
            assert t in text[doc] or name in text[doc], f"{doc} does not reference {name}"


def _prose_only(text: str) -> str:
    """Documents with the fences stripped.

    A worked example prints its own numbers -- `# 4 nodes, 3 edges` for a radius-1 subgraph -- and
    those are not claims about the graph's size. Only prose is.
    """
    return re.sub(r"```.*?```", "", text, flags=re.S)


def test_the_documents_do_not_contradict_each_other_on_the_graph_size():
    """Three documents once gave three different signal counts. Whatever they quote must agree."""
    sizes = {}
    for d in DOCS:
        found = set(re.findall(r"(\d+) nodes(?:,| and) [\d,]+ edges", _prose_only((REPO / d).read_text())))
        if found:
            sizes[d] = found
    assert len(sizes) >= 3, f"only {sorted(sizes)} state the graph size"
    everything = set().union(*sizes.values())
    assert len(everything) == 1, f"documents disagree on node count: {sizes}"

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


def test_the_licence_is_stated_consistently_everywhere():
    """One repo, one licence. The terms are a promise to users, so they must not disagree.

    The repo was MIT; it is now PolyForm Noncommercial 1.0.0 -- free for noncommercial use, paid for
    commercial. Nothing may still describe it as MIT except a dated record of when it was.
    """
    licence = (REPO / "LICENSE").read_text()
    assert "PolyForm Noncommercial License 1.0.0" in licence
    assert "Commercial use requires a paid license" in licence
    assert "Required Notice: Copyright Mangrove Technologies Inc." in licence
    # The grant itself must be present verbatim, not paraphrased in our preamble.
    assert "Any noncommercial purpose is a permitted purpose." in licence

    pyproject = (REPO / "pyproject.toml").read_text()
    assert 'license = {text = "PolyForm-Noncommercial-1.0.0"}' in pyproject
    assert "OSI Approved" not in pyproject, "PolyForm is not an OSI-approved licence"

    for doc in ("README.md", "PKG_README.md", "LICENSE"):
        text = (REPO / doc).read_text()
        assert "PolyForm Noncommercial License 1.0.0" in text, f"{doc} does not state the licence"
        assert "Commercial use requires a paid license" in text, f"{doc} omits the commercial terms"
        # A licensing contact that silently rots leaves a buyer with nowhere to go.
        assert "support@mangrove.ai" in text, f"{doc} does not say where to buy a commercial licence"
        assert "team@mangrovetechnologies.ai" not in text, f"{doc} keeps the old licensing contact"


def test_nothing_still_claims_the_repo_is_mit():
    """Except the dated records: a changelog entry and the licence itself say when."""
    dated = {"CHANGELOG.md", "LICENSE"}
    offenders = []
    for path in REPO.rglob("*"):
        if not path.is_file() or path.suffix not in {".md", ".toml", ".py", ".json"}:
            continue
        rel = path.relative_to(REPO)
        if ".git" in rel.parts or "build" in rel.parts or str(rel) in dated:
            continue
        if re.search(r"\bMIT[- ](?:licen[cs]ed|License)\b", path.read_text()):
            offenders.append(str(rel))
    assert not offenders, f"these still describe the repo as MIT: {offenders}"


@pytest.mark.parametrize("doc", ["README.md", "PKG_README.md"])
def test_every_image_exists(doc):
    """A broken image renders as a broken icon on the page a reader lands on first.

    `test_every_linked_path_exists` only sees markdown `](path)` links. The README's screenshots are
    HTML `<img src=...>` -- in a `<p align="center">` block, because markdown has no way to centre or
    float one -- so they were invisible to it.
    """
    text = (REPO / doc).read_text()
    srcs = set(re.findall(r'<img\s[^>]*src="(?!https?:)([^"]+)"', text))
    missing = sorted(s for s in srcs if not (REPO / s).exists())
    assert not missing, f"{doc} shows images that do not exist: {missing}"


def test_the_readme_shows_the_viewer():
    """The graph is the reason this package is interesting, and it is a visual thing.

    A reader deciding whether to `pip install` looks at the pictures. If the hero ever goes missing
    the README still reads fine, which is why this is asserted rather than left to review.
    """
    text = (REPO / "README.md").read_text()
    assert "assets/graph-viewer.png" in text, "the README must show the viewer"
    for shot in ("viewer-facets", "viewer-search", "viewer-inspector", "viewer-3d"):
        assert f"assets/{shot}.png" in text, f"the interface guide is missing {shot}"


def test_the_readme_keeps_the_community_links():
    """Discord, downloads, the ecosystem line and the star ask.

    A README rewrite is a rewrite of the growth surface too, and these are easy to lose because they
    are not *about* the software -- exactly what happened: a restructure dropped all four without
    anyone asking for it, and it was caught by eye, not by a test.
    """
    text = (REPO / "README.md").read_text()
    for token, what in (("discord.gg/Yycbw6P93B", "the Discord invite"),
                        ("pepy.tech/projects/mangrove-kb", "the downloads badge"),
                        ("please star the repo", "the star ask"),
                        ("github.com/MangroveTechnologies)", "the ecosystem link")):
        assert token in text, f"the README lost {what}"


def test_no_session_or_handoff_docs_are_committed():
    """This repo keeps no summaries, handoffs or next-steps docs.

    They are written to describe a moment and then read as if they describe now. The one that was
    here opened with the words "Not committed. Working note only." -- and was committed.

    Asks git what is TRACKED rather than globbing the filesystem. An uncommitted working note in
    someone's checkout is fine -- that is the whole point of keeping them out of the repo -- and
    globbing failed the build for one, which is the opposite of what this guards.
    """
    import subprocess
    try:
        proc = subprocess.run(["git", "ls-files", "*.md", "**/*.md"], cwd=REPO,
                              capture_output=True, text=True)
    except FileNotFoundError:  # no git binary
        pytest.skip("git unavailable -- nothing to ask about what is tracked")
    if proc.returncode != 0:  # an unpacked sdist, not a checkout
        pytest.skip("not a git checkout")
    banned = [f for f in proc.stdout.split()
              if any(w in Path(f).name.lower()
                     for w in ("session-summary", "handoff", "next-steps", "status"))]
    assert not banned, f"summary/handoff docs must not be committed: {banned}"


def _github_slug(text: str) -> str:
    """GitHub's heading anchor: lowercase, drop punctuation, spaces to hyphens.

    `&` and `—` are dropped rather than replaced, so "Skill & graph tools" becomes
    `skill--graph-tools` -- two hyphens, from the two spaces the ampersand left behind. Guessing
    that rule is exactly how a table of contents ends up with links that scroll nowhere.
    """
    return re.sub(r"[^\w\- ]", "", text.strip().lower()).replace(" ", "-")


def _headings(text: str) -> list[tuple[int, str]]:
    """`##`/`###` headings, ignoring anything inside a fenced code block."""
    out, fence = [], False
    for line in text.splitlines():
        if line.startswith("```"):
            fence = not fence
        elif not fence:
            m = re.match(r"^(#{2,3}) (.+)$", line)
            if m:
                out.append((len(m.group(1)), m.group(2).strip()))
    return out


def test_the_readme_has_a_table_of_contents_that_links_every_section():
    """A TOC is only worth having if its links land. Anchors are derived, never hand-typed."""
    text = (REPO / "README.md").read_text()
    assert "## Contents" in text, "the README has no table of contents"

    heads = _headings(text)
    valid = {_github_slug(t) for _, t in heads}

    # EVERY in-page anchor, not just the list items. The hero caption links `#the-viewer` too, and
    # scoping this to the table of contents left that one unguarded -- found by breaking it and
    # watching the test stay green.
    all_anchors = set(re.findall(r"\]\(#([^)]+)\)", text))
    dangling = sorted(all_anchors - valid)
    assert not dangling, f"in-page links that match no heading: {dangling}"

    linked = set(re.findall(r"^\s*- \[[^\]]+\]\(#([^)]+)\)", text, re.M))

    top = {t for lvl, t in heads if lvl == 2 and t != "Contents"}
    missing = sorted(t for t in top if _github_slug(t) not in linked)
    assert not missing, f"sections missing from the table of contents: {missing}"


def test_the_skill_and_tools_have_their_own_section():
    """The query surface and the two agent documents are the point of the package, and they were
    a single sentence inside Install."""
    text = (REPO / "README.md").read_text()
    assert "## Skill & graph tools" in text
    section = text.split("## Skill & graph tools", 1)[1].split("\n## ", 1)[0]
    for call in ("stats()", "schema()", "find(", "get(id)", "outputs(", "neighbors(",
                 "subgraph(", "path(a, b)", "all_paths(a, b)"):
        assert call in section, f"the tools section does not mention {call}"
    for doc in ("SKILL.md", "GUIDE.md"):
        assert doc in section, f"the tools section does not link {doc}"


def test_no_committed_file_carries_a_local_absolute_path():
    """This is a public repository. A developer's home directory is not documentation.

    `scripts/audit/gap_analysis.py` defaulted a reference-library path to
    `/home/<user>/mangrove/MangroveResearch/...`, which leaked a username and a local layout and was
    wrong for every other machine anyway. Environment variables, or nothing.
    """
    import subprocess
    files = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True,
                           check=True).stdout.split()
    offenders = []
    for rel in files:
        path = REPO / rel
        if not path.is_file() or path.suffix in {".png", ".svg", ".db", ".csv", ".ipynb"}:
            continue
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        for pattern in (r"/home/[a-z]", r"/Users/[a-z]"):
            if re.search(pattern, text):
                offenders.append(rel)
                break
    assert not offenders, f"committed files carry a local absolute path: {sorted(set(offenders))}"


def test_no_agent_definitions_are_committed():
    """Agent specs and repo memory live in the private workspace. CLAUDE.md used to point at
    `.claude/agents/product-owner.md`, which is not in this repo -- a dead pointer in the file an
    agent reads first. The authoring skills stay; they document the values this repo carries."""
    import subprocess
    committed = subprocess.run(["git", "ls-files", ".claude"], cwd=REPO,
                               capture_output=True, text=True, check=True).stdout.split()
    stray = [f for f in committed if not f.startswith(".claude/skills/")]
    assert not stray, f"only authoring skills belong under .claude here: {stray}"
    assert "agents/product-owner.md" not in (REPO / "CLAUDE.md").read_text(), \
        "CLAUDE.md points at an agent spec this repo does not contain"


DOCS_WITH_IMAGES = ("README.md", "PKG_README.md", "docs/viewer-guide.md")


def test_every_screenshot_is_shown_somewhere_and_every_shown_one_exists():
    """Both directions, because both have bitten.

    A missing file renders as a broken icon on the page a reader lands on first. An orphan is the
    quieter one: `viewer-tooltip.png` was committed, weighed 233KB, and appeared nowhere -- the
    section that would have shown it had been moved out from under it.
    """
    shown = set()
    for doc in DOCS_WITH_IMAGES:
        text = (REPO / doc).read_text()
        shown |= {m for m in re.findall(r'src="(?:\.\./)?(assets/[^"]+)"', text)}
        shown |= {m for m in re.findall(r"\]\((?:\.\./)?(assets/[^)]+)\)", text)}
    on_disk = {f"assets/{p.name}" for p in (REPO / "assets").glob("*.png")}
    assert not (shown - on_disk), f"shown but not in the repo: {sorted(shown - on_disk)}"
    assert not (on_disk - shown), f"in the repo but shown nowhere: {sorted(on_disk - shown)}"


def test_no_screenshot_is_a_canyon():
    """A tall image floated beside a short paragraph leaves a column of nothing next to the text.

    `viewer-facets.png` was 340x1441 -- a ratio of 4.24 -- floated at 300px wide, so it stood 1270px
    tall next to ten lines of prose. Nobody notices while writing the markdown; everybody notices on
    the rendered page.
    """
    from PIL import Image

    tall = []
    for path in sorted((REPO / "assets").glob("*.png")):
        w, h = Image.open(path).size
        if h / w > 2.0:
            tall.append(f"{path.name} {w}x{h} (ratio {h / w:.2f})")
    assert not tall, f"too tall to sit beside text: {tall}"

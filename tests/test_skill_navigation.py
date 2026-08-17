"""The skill and guide can be navigated without reading them end to end.

Both files are long enough that an agent should be able to find the one section it needs, read that,
and follow a link when the answer needs a second call. That only works if the contents table is
complete, every entry says what its section is for, and every link actually resolves — a dead
anchor is worse than no link, because it reads as a promise the file cannot keep.

Anchors are computed the way GitHub computes them: lowercase, punctuation stripped, spaces to
hyphens. Getting that wrong is silent in a renderer, so it is asserted here rather than eyeballed.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SKILLS = REPO / "skills" / "knowledge-graph"
FILES = ("SKILL.md", "GUIDE.md")

#: Every skill file that must be navigable, as (directory, filename). The ingest skill is held to
#: the same bar: it is read by an agent looking for one section, not end to end.
NAVIGABLE = [("knowledge-graph", "SKILL.md"), ("knowledge-graph", "GUIDE.md"),
             ("knowledge-ingest", "SKILL.md")]


def anchor(heading: str) -> str:
    a = re.sub(r"[^\w\s-]", "", heading.strip().lower())
    return re.sub(r"\s+", "-", a)


def sections(text: str) -> list[str]:
    """Headings, ignoring anything fenced -- `## N.M <Section title>` inside a code block shows the
    shape of a source document and is not a section of the file."""
    outside = re.sub(r"^```.*?^```", "", text, flags=re.S | re.M)
    return re.findall(r"^## (.+)$", outside, re.M)


@pytest.fixture(scope="module")
def docs() -> dict[str, str]:
    return {name: (SKILLS / name).read_text() for name in FILES}


@pytest.mark.parametrize("name", FILES)
def test_every_section_is_in_the_contents_table(docs, name):
    text = docs[name]
    assert "## Contents" in text, f"{name} has no contents table"
    body = text.split("## Contents", 1)[1]
    toc = body.split("\n## ", 1)[0]

    for heading in sections(text):
        if heading == "Contents":
            continue
        assert f"#{anchor(heading)})" in toc, f"{name}: '{heading}' is not listed in the contents"


@pytest.mark.parametrize("name", FILES)
def test_every_contents_entry_describes_its_section(docs, name):
    """A link with no sentence beside it makes the reader open the section to find out if it is the
    one they want, which is the cost the table exists to remove."""
    body = docs[name].split("## Contents", 1)[1].split("\n## ", 1)[0]
    rows = [r for r in body.split("\n") if r.startswith("|") and "](#" in r]
    assert rows, f"{name}: the contents table has no linked rows"
    for row in rows:
        cells = [c.strip() for c in row.strip("|").split("|")]
        description = cells[-1]
        assert len(description) > 30, f"{name}: no description for row {row.strip()!r}"
        assert description.endswith("."), f"{name}: description is not a sentence: {description!r}"


@pytest.mark.parametrize("name", FILES)
def test_every_section_links_onward(docs, name):
    """Progressive discovery needs an exit from each section, not just an entrance."""
    text = docs[name]
    parts = re.split(r"^## ", text, flags=re.M)[1:]
    for part in parts:
        heading = part.split("\n", 1)[0].strip()
        if heading in ("Contents", "What this guide does not tell you", "Worked examples"):
            continue
        assert "**See also:**" in part, f"{name}: '{heading}' links nowhere"


def test_every_internal_link_resolves(docs):
    """Including across the two files -- a cross-file anchor is the easiest one to get wrong."""
    anchors = {name: {anchor(h) for h in sections(text)} for name, text in docs.items()}
    broken = []
    for name, text in docs.items():
        for target, frag in re.findall(r"\]\((SKILL\.md|GUIDE\.md)?#([\w-]+)\)", text):
            where = target or name
            if frag not in anchors[where]:
                broken.append(f"{name} -> {where}#{frag}")
    assert not broken, "dead anchors: " + ", ".join(broken)


@pytest.mark.parametrize("skill,name", NAVIGABLE)
def test_every_navigable_file_has_a_described_contents_table(skill, name):
    """The same three rules as above, applied to every skill file rather than to one pair."""
    text = (REPO / "skills" / skill / name).read_text()
    assert "## Contents" in text, f"{skill}/{name} has no contents table"
    toc = text.split("## Contents", 1)[1].split("\n## ", 1)[0]
    for heading in sections(text):
        if heading == "Contents":
            continue
        assert f"#{anchor(heading)})" in toc, f"{skill}/{name}: '{heading}' is not in the contents"
    rows = [r for r in toc.split("\n") if r.startswith("|") and "](#" in r]
    assert rows, f"{skill}/{name}: the contents table has no linked rows"
    for row in rows:
        description = [c.strip() for c in row.strip("|").split("|")][-1]
        assert len(description) > 30 and description.endswith("."), \
            f"{skill}/{name}: row does not describe its section: {row.strip()!r}"


def test_the_ingest_skill_points_at_files_that_exist():
    """A reference a skill promises and does not ship is worse than one it never mentions."""
    root = REPO / "skills" / "knowledge-ingest"
    text = (root / "SKILL.md").read_text()
    targets = {t for t in re.findall(r"\]\(([\w./-]+\.md)[^)]*\)", text)}
    missing = [t for t in targets if not (root / t).resolve().is_file()]
    assert not missing, f"the ingest skill links to files that do not exist: {missing}"
    assert targets >= {"references/declarations.md", "references/lessons.md"}, \
        "the skill must point at both references, or their content is unreachable"


def test_the_two_files_still_say_different_things(docs):
    """SKILL is the reference for WHICH CALL, GUIDE for a whole job. When the skill restated the
    guide's jobs the pair was 847 lines with five duplicated, and neither was the place to look."""
    skill = docs["SKILL.md"]
    assert "reference for **which call**" in skill
    worked = skill.split("## Worked examples", 1)[1]
    assert "GUIDE" in worked, "the skill's worked examples must index the guide, not restate it"
    assert "```python" not in worked, \
        "a code block under Worked examples means the skill is re-teaching a job the guide owns"

"""The architecture diagrams must render, and must describe this repository.

A broken mermaid block does not fail loudly -- GitHub renders an error box where the diagram should
be, and the page still looks like documentation. `graph` as a node id was enough to do it.

Two levels of checking. The structural ones always run. The real parse runs only where the mermaid
package is installed, which is a local `npm install mermaid jsdom` away and is how these were
checked when written:

    node tests/mermaid-parse.mjs docs/architecture/README.md
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
DOC = REPO / "docs" / "architecture" / "README.md"

#: Reserved in mermaid's flowchart grammar: using one as a node id is a parse error, and the diagram
#: silently becomes an error box on the rendered page.
RESERVED = {"graph", "end", "subgraph", "click", "class", "style", "linkStyle", "flowchart"}


@pytest.fixture(scope="module")
def doc() -> str:
    assert DOC.is_file(), f"{DOC.relative_to(REPO)} is missing"
    return DOC.read_text(encoding="utf-8")


def blocks(text: str) -> list[str]:
    return re.findall(r"```mermaid\n(.*?)```", text, re.S)


def test_every_block_declares_a_diagram_type(doc):
    found = blocks(doc)
    assert len(found) >= 7, f"expected the documented set of diagrams, found {len(found)}"
    for i, block in enumerate(found, 1):
        first = block.strip().splitlines()[0].strip()
        assert re.match(r"^(flowchart|graph|classDiagram|sequenceDiagram|erDiagram|stateDiagram)",
                        first), f"block {i} declares no diagram type: {first!r}"


def test_no_reserved_word_is_used_as_a_node_id(doc):
    """The defect that motivated this file: `ids --> graph[[...]]` parses as a nested diagram."""
    offenders = []
    for i, block in enumerate(blocks(doc), 1):
        for line in block.splitlines():
            for node_id in re.findall(r"(?:^|\s|>)([A-Za-z_][\w-]*)\s*[\[\(\{]", line):
                if node_id in RESERVED:
                    offenders.append(f"block {i}: {node_id!r} in {line.strip()!r}")
    assert not offenders, offenders


def test_the_contents_table_lists_every_diagram_section(doc):
    sections = [h for h in re.findall(r"^## (.+)$", doc, re.M) if h[0].isdigit()]
    table = doc.split("## 1.", 1)[0]
    for heading in sections:
        anchor = re.sub(r"[^\w\s-]", "", heading.lower().replace(" ", "-"))
        assert f"(#{anchor})" in table, f"'{heading}' is not in the contents table"
    assert len(sections) >= 7


def test_it_points_at_files_and_tests_that_exist(doc):
    """A diagram claiming a guard that no longer exists is worse than no claim."""
    for path in set(re.findall(r"`((?:tests|ontology|mangrove_kb|skills)/[\w./*-]+)`", doc)):
        if "*" in path:
            assert list(REPO.glob(path)), f"{path} matches nothing"
        else:
            assert (REPO / path).exists(), f"the doc points at {path}, which does not exist"


def test_the_diagrams_carry_no_counts(doc):
    """A number in a diagram label goes stale silently -- no test can read prose out of a diagram,
    which is why `test_documented_counts.py` pins numbers in text and diagrams state none.

    A measurement is the thing being refused, not every digit: a tier is called "tier 0" and the
    document weights are "3·2·2·1·1", and neither goes stale when a chapter lands.
    """
    counted = re.compile(r"\b\d[\d,]*\s*(?:nodes?|edges?|terms?|components?|%|kib|mib|ms|of)\b",
                         re.I)
    for i, block in enumerate(blocks(doc), 1):
        for line in block.splitlines():
            label = " ".join(re.findall(r"[\[\(\{]+\"?(.*?)\"?[\]\)\}]+", line))
            stale = counted.findall(label) + [n for n in re.findall(r"\b\d{2,}\b", label)]
            assert not stale, f"block {i} states a count that will go stale: {line.strip()!r}"


@pytest.mark.skipif(not (REPO / "node_modules" / "mermaid").is_dir(),
                    reason="npm install mermaid jsdom to check the diagrams actually parse")
def test_every_block_parses_as_mermaid():
    node = shutil.which("node")
    assert node, "node is required for the real parse"
    proc = subprocess.run([node, str(REPO / "tests" / "mermaid-parse.mjs"), str(DOC)],
                          capture_output=True, text=True, timeout=300, cwd=REPO)
    assert proc.returncode == 0, proc.stdout + proc.stderr

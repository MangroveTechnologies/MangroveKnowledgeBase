"""Tests for the authored-metadata docstring format.

The format is the SSOT for every value a human wrote. These tests pin two properties:

1. **Lossless** -- what the parser reads back equals what the graph holds. Verified against the real
   committed graph, not a fixture, because a fixture would agree with a format that had drifted from
   the data it is supposed to carry.
2. **Enforced** -- malformed docstrings raise rather than parse to a plausible wrong value. That is
   the failure mode that matters here: across 22 files, a silent mis-parse produces a graph that
   looks fine and is wrong.
"""
import re
from pathlib import Path

import pytest

from mangrove_kb.docstring_parser import DocstringFormatError, PERMITTED, parse_authored
from mangrove_kb.graph import KnowledgeGraph

REPO = Path(__file__).resolve().parent.parent
PROPOSAL = REPO / "DOCSTRING-FORMAT-PROPOSAL.md"


@pytest.fixture(scope="module")
def kg():
    return KnowledgeGraph.load()


def _examples():
    """The worked examples, read from the proposal while it exists.

    Once phase 3 lands they come from the source tree instead and this fixture goes away.
    """
    if not PROPOSAL.is_file():
        pytest.skip("proposal file removed -- examples now live in the source tree")
    return re.findall(r'```python\n"""(.*?)"""\n```', PROPOSAL.read_text(), re.S)


@pytest.mark.parametrize("idx,node_id", [(0, "procedure:indicator-bollingerbands"),
                                         (1, "procedure:signal-bb-above-upper")])
def test_authored_values_round_trip_exactly(idx, node_id, kg):
    """Every authored field the graph holds must come back out of the docstring unchanged."""
    got = parse_authored(_examples()[idx])
    node = kg.get(node_id)

    assert got["name"] == node["name"], "the declared name must match the graph's node name"
    assert got.get("summary") == node["summary"]
    for field in ("formula", "abbreviation", "reference", "interpretation", "applications"):
        assert got.get(field) == node.get(field), field
    assert got.get("inputs") == {k: v["description"] for k, v in node["inputs"].items()}

    for name, spec in node["outputs"].items():
        parsed = got["outputs"][name]
        for field in ("units", "range", "canonical_name", "description"):
            assert parsed[field] == spec[field], f"output {name}.{field}"


def test_summary_is_the_first_paragraph_only(kg):
    """Not all the prose. BollingerBands has a rationale paragraph that is NOT its summary.

    Regression: collapsing every prose line into one string -- what the legacy description extractor
    does -- silently merges the rationale into the summary and the round-trip fails.
    """
    got = parse_authored(_examples()[0])
    assert got["summary"] == kg.get("procedure:indicator-bollingerbands")["summary"]
    assert "hband_indicator" not in got["summary"], "rationale prose leaked into the summary"


def test_unbounded_ranges_are_infinities_not_null(kg):
    got = parse_authored(_examples()[0])
    assert got["outputs"]["pband"]["range"] == [float("-inf"), float("inf")]
    assert got["outputs"]["mavg"]["range"] == [0, float("inf")]


def test_absent_canonical_name_parses_to_the_string_none(kg):
    """The graph holds the literal string "none", not null, so the parser must produce that."""
    got = parse_authored(_examples()[0])
    assert got["outputs"]["mavg"]["canonical_name"] == "none"
    assert got["outputs"]["pband"]["canonical_name"] == "%B"


# --- enforcement -----------------------------------------------------------------------------

def test_missing_declaration_is_rejected():
    with pytest.raises(DocstringFormatError, match="first line must be"):
        parse_authored("Volatility bands placed above a moving average.\n\nInputs:\n    close: x\n")


def test_declaration_must_name_the_kind():
    with pytest.raises(DocstringFormatError):
        parse_authored("Thing: BollingerBands\n\ndesc\n")


@pytest.mark.parametrize("section", ["Interpretation", "Applications", "Abbreviation"])
def test_indicator_only_sections_are_rejected_on_signals(section):
    """A signal has no graph field to receive these. Silently ignoring them loses authored text."""
    body = f"    - x" if section != "Abbreviation" else "BB"
    doc = f"Signal: s\n\ndesc\n\n{section}: {body}\n" if section == "Abbreviation" else \
          f"Signal: s\n\ndesc\n\n{section}:\n    - x\n"
    with pytest.raises(DocstringFormatError, match="may not have"):
        parse_authored(doc)


def test_indicator_may_carry_them():
    doc = "Indicator: X\n\ndesc\n\nAbbreviation: X\n\nInterpretation:\n    - a\n\nApplications:\n    - b\n"
    got = parse_authored(doc)
    assert got["abbreviation"] == "X" and got["interpretation"] == ["a"] and got["applications"] == ["b"]


def test_stray_text_under_outputs_is_rejected():
    """Text before any output line would otherwise be silently dropped."""
    with pytest.raises(DocstringFormatError, match="before any output line"):
        parse_authored("Indicator: I\n\ndesc\n\nOutputs:\n    loose prose\n")


def test_empty_docstring_is_rejected():
    for empty in ("", "   \n  "):
        with pytest.raises(DocstringFormatError, match="empty"):
            parse_authored(empty)


def test_permitted_sets_are_disjoint_where_they_should_be():
    """Guards the table in the proposal: three sections are indicator-only."""
    assert PERMITTED["Indicator"] - PERMITTED["Signal"] == {"Interpretation", "Applications",
                                                            "Abbreviation"}


def test_declaration_does_not_leak_into_the_legacy_description():
    """`parse_signal_docstring` feeds signal metadata consumed well outside the graph.

    Regression: adding the `Signal: <name>` line prefixed every description with the rule name
    ("Signal: bb_above_upper Check if price is..."), which no test caught because none asserted the
    description's opening.
    """
    from mangrove_kb.docstring_parser import parse_signal_docstring
    from mangrove_kb.signals.volatility import bb_above_upper
    desc = parse_signal_docstring(bb_above_upper)["description"]
    assert not desc.startswith("Signal:")
    assert desc.startswith("Check if price is currently above the upper Bollinger Band.")


def test_real_source_objects_round_trip(kg):
    """The two converted objects, read from the live classes rather than the proposal file."""
    from mangrove_kb.indicators import BollingerBands
    from mangrove_kb.signals.volatility import bb_above_upper
    for obj, node_id in ((BollingerBands, "procedure:indicator-bollingerbands"),
                         (bb_above_upper, "procedure:signal-bb-above-upper")):
        got, node = parse_authored(obj.__doc__), kg.get(node_id)
        assert got["name"] == node["name"]
        assert got.get("summary") == node["summary"]
        for name, spec in node["outputs"].items():
            for field in ("units", "range", "canonical_name", "description"):
                assert got["outputs"][name][field] == spec[field], f"{node_id} {name}.{field}"

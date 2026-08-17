"""Does the graph ANSWER, not merely contain.

Every other check in this suite verifies fidelity -- that what the chapters say reached the record.
None of them ask whether a question gets the right node back, which is the only thing the graph is
for. This one does, three ways, and each measures something different:

1. **Its own headings.** For every `###` a chapter states, can `find` return the node that heading
   produced? Generated from the raw files rather than chosen, so it cannot be cherry-picked. This is
   the easy direction -- the query IS the corpus's wording -- and it should stay near perfect.

2. **Questions in someone else's words.** Twenty-five questions phrased the way a trader asks them,
   deliberately avoiding the node's own vocabulary: "what are the odds I wipe out the account"
   rather than "risk of ruin". This is the honest measure and it is much lower. An earlier set
   scored 16/20 and was worthless: it was written after reading the chapters, so it used their
   words back at them.

3. **Structure.** Questions answered by walking rather than matching -- what reads this indicator,
   what is this class made of, how do these two connect.

The numbers here are FLOORS recorded from a measurement, not targets. Raise them when retrieval
improves; never lower one to make a change pass.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from mangrove_kb.graph import KnowledgeGraph

RAW = Path(__file__).resolve().parent.parent / "ontology" / "raw"

#: Headings whose text names something other than the node they made -- both are an abbreviation
#: with its expansion in brackets, where the signals that read the indicator outrank the indicator.
KNOWN_HEADING_MISSES = 2

#: Measured 2026-08-17, over the 25 paraphrased questions below, with `ask(hops=1)`.
PARAPHRASE_FLOOR = 11

#: A trader's phrasing, and any node that would be a fair answer. Written to avoid the node's own
#: words wherever the question can be asked without them.
QUESTIONS: list[tuple[str, set[str]]] = [
    ("how much should I put on a single trade",
     {"concept:position-sizing", "property:max-risk-per-trade", "property:position-size"}),
    ("if I lose half my account how much do I need to make it back",
     {"fact:recovery-mathematics"}),
    ("my system wins most of the time so it must be safe", {"fact:win-rate-is-not-risk"}),
    ("when should I stop trading for the day",
     {"procedure:daily-loss-limit", "property:max-daily-loss", "property:cool-down-period"}),
    ("price keeps bouncing off the same level",
     {"concept:support-and-resistance", "concept:horizontal-level"}),
    ("the market is going sideways what works here",
     {"concept:mean-reversion", "concept:ranging-market"}),
    ("how do I know a break is real and not a fake",
     {"procedure:breakout-confirmation-filter", "concept:false-breakout"}),
    ("things have gone very quiet, what usually follows", {"concept:compression"}),
    ("is this trend strong enough to bother trading",
     {"procedure:adx-trend-strength", "concept:trending-market"}),
    ("how far away from my entry should the stop go",
     {"procedure:atr-based-stop", "concept:stop-and-target-engineering"}),
    ("my backtest looks too good to be true",
     {"concept:overfitting", "concept:strategy-validation"}),
    ("how do I tell whether my results are just luck",
     {"procedure:returns-t-test", "procedure:multiple-testing-correction"}),
    ("what are the odds I wipe out the account", {"concept:risk-of-ruin"}),
    ("two names that usually move together have drifted apart", {"procedure:pairs-trading"}),
    ("the bar has a long tail underneath it",
     {"procedure:signal-hammer-trigger", "concept:pin-bar"}),
    ("three peaks and the middle one is the highest", {"concept:head-and-shoulders"}),
    ("everything I own started moving together in the crash",
     {"procedure:correlation-stress-testing", "concept:correlation-risk"}),
    ("how much can I borrow against what I have", {"concept:leverage", "concept:margin"}),
    ("does the hour of the day change anything",
     {"concept:seasonality", "procedure:session-filter", "property:trading-hour"}),
    ("big moves seem to come in bunches", {"concept:volatility-clustering"}),
    ("what tells me whether buyers or sellers are winning, using volume",
     {"concept:flow", "procedure:indicator-obv"}),
    ("some of these fire once and some stay true, what is that",
     {"property:role-trigger", "property:role-filter"}),
    ("the asset is twice as jumpy as usual, how do I size it",
     {"procedure:volatility-adjusted-position-sizing"}),
    ("when do I move the stop up so I cannot lose", {"procedure:break-even-stop"}),
    ("the setup failed, is that useful",
     {"judgment:trading-failed-pattern", "concept:false-breakout"}),
]

_SCAFFOLD = ("Definition", "Core Principles", "Common Use Cases", "Best Practices", "Formula",
             "Interpretation", "Trading Applications", "Examples", "MangroveAI API",
             "Related Trading", "Mathematical", "Structure")


@pytest.fixture(scope="module")
def kg() -> KnowledgeGraph:
    return KnowledgeGraph.load()


def _headings_that_name_a_node(kg: KnowledgeGraph) -> list[tuple[str, str]]:
    by_title: dict[str, str] = {}
    for nid, n in kg.nodes.items():
        by_title.setdefault((n.name or "").strip().lower(), nid)
    out = []
    for f in sorted(RAW.glob("*.md")):
        for h in re.findall(r"^#{3,4} (.+)$", f.read_text(encoding="utf-8"), re.M):
            h = re.sub(r"^\d+(?:\.\d+)*\s+", "", h).strip()
            if h.startswith(_SCAFFOLD):
                continue
            nid = by_title.get(h.lower()) or by_title.get(re.sub(r"\s*\(.*?\)", "", h).lower())
            if nid:
                out.append((h, nid))
    return out


def test_a_chapter_can_find_the_things_it_names(kg):
    """The easy direction, and the one that must not rot: ask for a heading, get its node."""
    cases = _headings_that_name_a_node(kg)
    assert len(cases) > 90, "the heading-to-node match itself has broken"
    missed = [(h, nid) for h, nid in cases
              if nid not in {r["id"] for r in kg.find(h, limit=5)}]
    assert len(missed) <= KNOWN_HEADING_MISSES, \
        f"{len(missed)} headings no longer find their node: {missed[:5]}"


def test_it_answers_questions_asked_in_someone_elses_words(kg):
    """The honest measure. Low, and recorded so it cannot quietly get lower."""
    hit = [q for q, want in QUESTIONS if want & {r["id"] for r in kg.ask(q, hops=1, limit=5)}]
    assert len(hit) >= PARAPHRASE_FLOOR, (
        f"{len(hit)}/{len(QUESTIONS)} answered, floor is {PARAPHRASE_FLOOR}. Missing: "
        f"{[q for q, _ in QUESTIONS if q not in hit][:6]}")


def test_meaning_beats_words_on_a_question(kg):
    """`ask` must stay worth having over `find`: the whole point of the semantic index."""
    words = sum(1 for q, want in QUESTIONS if want & {r["id"] for r in kg.find(q, limit=5)})
    meaning = sum(1 for q, want in QUESTIONS if want & {r["id"] for r in kg.ask(q, hops=1, limit=5)})
    assert meaning > words * 2, f"words {words}, meaning {meaning} -- the index stopped earning its place"


def test_a_wired_statement_can_still_be_found(kg):
    """Wiring moves a statement onto the edge it explains, which took ~100k characters of the
    knowledge base out of the search corpus until the reasons were folded back in."""
    hits = {r["id"] for r in kg.find("keep risk per trade below", limit=5)}
    assert "property:max-risk-per-trade" in hits, \
        "a statement that lives on an edge is invisible to search again"


# --- questions answered by walking rather than matching ------------------------------------------

def test_what_reads_this_indicator(kg):
    readers = {r["id"] for r in kg.neighbors("procedure:indicator-atr", relation="uses",
                                             direction="in", limit=None)}
    assert {"procedure:atr-based-stop", "procedure:atr-trailing-stop"} <= readers, \
        "the exit rules chapters 4 and 5 state read ATR, and the graph should say so"


def test_what_a_class_is_made_of(kg):
    """The class the graph was built to hold, and the chapter that finally filled it."""
    assert len(kg.descendants("concept:chart-pattern")) == 9
    assert "concept:head-and-shoulders" in kg.descendants("concept:chart-pattern")


def test_how_two_things_connect(kg):
    """A question no single node answers: what does a stop rule have to do with a market state?"""
    route = kg.path("procedure:atr-based-stop", "concept:trending-market", max_depth=4)
    assert route, "no route from an ATR stop to a trending market"


def test_a_subject_area_holds_its_chapter(kg):
    """`under` is what a chapter's scope means, and every chapter should have one."""
    for anchor, floor in (("concept:market-foundations", 100), ("concept:risk-management", 50),
                          ("concept:strategy-design", 60), ("concept:price-action", 70)):
        assert len(kg.under(anchor)) >= floor, f"{anchor} holds less than its chapter"


def test_both_axes_still_answer_together(kg):
    """Class and role are separate questions, and the graph answers them jointly."""
    r = kg.find(kind="oscillator", role="trigger", limit=None)
    assert r.total > 0
    assert all("procedure:signal-" in row["id"] for row in r)

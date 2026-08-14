#!/usr/bin/env python3
"""Derive atoms and relations from a knowledge-base chapter.

The 289 procedure nodes are parsed out of the library's docstrings. These chapters are the same
kind of source -- structured text with a fixed scaffold -- so they are parsed the same way rather
than transcribed by hand. Every chapter section carries the same six headings:

    ## 1.N <Section>
    ### Definition                    -> the Concept(s) the section is about
    ### Core Principles               -> claims about them          (one Fact node per chapter)
    ### Common Use Cases              -> `applications` on the section concept
    ### Examples                      -> a taxonomy, or an illustration (see CHAPTERS)
    ### Best Practices for Traders    -> what to do about them      (one Judgment node per chapter)
    ### Mathematical Rules/Formulas   -> Procedure nodes

What is NOT a node: a heading, a worked example with figures in it, and any claim about a thing --
"Liquidity is Dynamic" is something true of liquidity, not a second thing beside it.

Core Principles and Best Practices are each ONE node carrying the whole list, not one node per
bullet. A bullet has no name to slug, and naming 50 of them means inventing 50 interpretations.

Everything emitted is `status: draft`. Promotion is a human act.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

H2 = re.compile(r"^## (?:(\d+\.\d+)\s+)?(.+?)\s*$")
H3 = re.compile(r"^### (.+?)\s*$")
BULLET = re.compile(r"^\s*-\s+\*\*(.+?)\*\*\s*[::]\s*(.+?)\s*$")
PLAIN_BULLET = re.compile(r"^\s*-\s+(.+?)\s*$")
BLOCK_LABEL = re.compile(r"^\*\*(.+?)\*\*\s*[::]?\s*$")

#: Per-chapter declarations: the two things that cannot be read off the text.
#:
#: `taxonomy` -- an `### Examples` block is either the section's real taxonomy, whose members become
#: Concepts, or a worked illustration, which becomes none. "Market Makers" is a kind of participant;
#: "Slippage Example" is arithmetic. Nothing in the markup separates them.
#:
#: `wired` -- a stated line and the node it concerns. The line MOVES: out of the principles or
#: practices list and onto an `about` edge from that node, as the edge's `why`. Never in both, so
#: the copies cannot drift; what remains in a list is exactly what is not yet connected.
#:
#: Keyed by SECTION TITLE, never by section number. A number says where a thing sits in a file, not
#: what it is -- and keying on it made every declaration silently inert on any other chapter, since
#: chapter 2's sections are 2.x and none of chapter 1's numbers matched. The result was a clean
#: build with no taxonomies at all, which is invisible unless you already know what is missing.
#:
#: A chapter absent from here raises rather than building with nothing.
CHAPTERS: dict[str, dict] = {
    "market-foundations": {
        "taxonomy": {"Order Types", "Market Participants", "Volatility, Regimes & Regime Shifts",
                     "Trading Venues & Execution Models", "Price Discovery Mechanisms"},
        # `### <heading>` blocks that are a table of things rather than prose. Declared, because a
        # table is as often a summary of nodes that already exist (the Order Type Summary Table
        # restates the six order types) as it is a source of new ones.
        "tables": {"Execution Algorithm Selection Guide":
                   ("concept:execution-model", "instance-of")},
        # Edges nothing in the text states, authored here. The chapter's VWAP is an execution
        # SCHEDULE -- trade in proportion to volume -- and the library's VWAP is the price series it
        # targets. Different things with the same name, so neither folds into the other; the edge is
        # what stops them sitting side by side looking like a duplicate.
        "edges": [("procedure:vwap", "uses", "procedure:indicator-vwap",
                   "executes against the price series this computes")],
        "wired": {
            # --- order types -------------------------------------------------------------------
            "Use market orders sparingly": "concept:market-order",
            "Understand that stop orders become market orders": "concept:market-order",
            "Place limit orders at realistic prices": "concept:limit-order",
            "Use limit orders to control execution prices": "concept:limit-order",
            "Use limit orders to avoid paying the full spread": "concept:limit-order",
            "Conditional Execution: Stop orders become active": "concept:stop-order",
            "Set stop-losses based on technical levels": "concept:stop-order",
            "Consider using stop-limit orders": "concept:stop-limit-order",
            "Use iceberg orders for large positions": "concept:iceberg-order",
            # Wired to the iceberg order rather than to `order-type`, where the sentence points:
            # the node's own definition invokes information leakage, so this is the principle that
            # accounts for what that node does.
            "Information Leakage: Some order types reveal": "concept:iceberg-order",
            "Immediacy vs. Price Control": "concept:order-type",
            "Execution Certainty: Different order types": "concept:order-type",
            "Be aware of venue-specific order types": "concept:order-type",
            # --- participants ------------------------------------------------------------------
            "Understand your position in the market participant": "concept:market-participant",
            "Heterogeneous Motivations": "concept:market-participant",
            "Information Hierarchy": "concept:market-participant",
            "Time Horizon Diversity": "concept:market-participant",
            "Adversarial Dynamics": "concept:market-participant",
            "Recognize that market makers adjust spreads": "concept:market-maker",
            "Liquidity Ecosystem: Market makers": "concept:market-maker",
            "Spread as Compensation": "concept:market-maker",
            "Monitor institutional activity": "concept:institutional-investor",
            "Be aware that HFT can front-run": "concept:high-frequency-trader",
            # --- liquidity, slippage, impact ---------------------------------------------------
            "Monitor order book depth continuously": "concept:liquidity",
            "Trade during high liquidity periods": "concept:liquidity",
            "Evaluate liquidity before sizing positions": "concept:liquidity",
            "Liquidity is Dynamic": "concept:liquidity",
            "Liquidity Illusion": "concept:liquidity",
            "Build slippage assumptions into backtest": "concept:slippage",
            "Impact is Non-Linear": "concept:market-impact",
            "Urgency-Cost Tradeoff": "concept:market-impact",
            "Consider total cost of execution": "concept:market-impact",
            "Use volume-weighted average price (VWAP) orders": "procedure:vwap",
            # --- volatility and regimes --------------------------------------------------------
            "Volatility Clustering": "concept:volatility",
            "Mean Reversion of Volatility": "concept:volatility",
            "Asymmetric Volatility": "concept:volatility",
            "Monitor volatility indicators": "concept:volatility",
            "Regime Persistence": "concept:market-regime",
            "Correlation Breakdown": "concept:market-regime",
            "Reduce position sizes and leverage during high volatility": "concept:high-volatility-regime",
            "Consider that regime shifts often occur faster": "concept:regime-shift",
            # --- venues and execution ----------------------------------------------------------
            "Fragmentation: Modern markets are fragmented": "concept:trading-venue",
            "Transparency Spectrum": "concept:trading-venue",
            "Latency Competition": "concept:trading-venue",
            "Regulatory Frameworks": "concept:trading-venue",
            "Use smart order routers": "concept:trading-venue",
            "Best Execution Obligation": "concept:execution-model",
            "Consider using dark pools for large orders": "concept:dark-pool",
            "Use dark pools strategically": "concept:dark-pool",
            # --- spread ------------------------------------------------------------------------
            "Always check the current spread": "concept:bid-ask-spread",
            "Avoid trading when spreads are abnormally wide": "concept:bid-ask-spread",
            "Information Asymmetry Cost": "concept:bid-ask-spread",
            "Inventory Risk: Spreads reflect": "concept:bid-ask-spread",
            "Competition Effect": "concept:bid-ask-spread",
            "Volatility Relationship: Spreads typically widen": "concept:bid-ask-spread",
            # --- price discovery ---------------------------------------------------------------
            "Information Aggregation": "concept:price-discovery",
            "Continuous Process": "concept:price-discovery",
            "Order Flow Information": "concept:price-discovery",
            "Multiple Venues": "concept:price-discovery",
            "Speed of Incorporation": "concept:price-discovery",
            "Study auction dynamics": "concept:auction-based-discovery",
        },
    },
}

#: Blocks inside a taxonomy section that are still NOT kinds: "Regime Shift Triggers" lists causes
#: of a shift and "Information Events" lists occasions for discovery. Both read like members and
#: are not, which no rule about the text can tell apart from the ones that are.
NOT_A_KIND = {"Regime Shift Triggers", "Information Events",
              # The execution-algorithm table lists Iceberg beside TWAP and VWAP. It is the same
              # thing as the order type of that name, which is already a node; a second one under a
              # different primitive would be a duplicate wearing a different hat.
              "Iceberg"}

#: Chapter term -> the node in the graph that IS that thing under a different id. A collision the
#: slug cannot see: the chapter calls it "Average True Range", the library registers the class as
#: `ATR`. Terms that collide on the id itself (the chapter's "Volatility" and `concept:volatility`)
#: need no entry -- `--ontology` catches those.
#:
#: Merging is folding, not replacing: the existing node stands, the chapter's edges retarget onto
#: it, and it gains `reference_chapter` so the prose that explains it can be found. Nothing
#: code-derived is overwritten.
MERGE_INTO = {
    "procedure:average-true-range": "procedure:indicator-atr",
}

#: Authored definitions for terms the chapter names but never defines. Every one here is a place
#: where the parser would otherwise put an *instance* where a *definition* belongs: §1.2 explains
#: each order type only through a worked example, so `market-order` read "Buy 100 shares at the
#: best available price" -- true of one order, and not what a market order IS. The example is kept
#: as `examples`; this is the summary beside it.
DEFINITION = {
    "concept:market-order":
        "An instruction to trade immediately at the best price currently available. Execution is "
        "certain, the price is not.",
    "concept:limit-order":
        "An instruction to trade only at a stated price or better. The price is certain, execution "
        "is not; the order rests in the book supplying liquidity until it fills or is cancelled.",
    "concept:stop-order":
        "A resting instruction that becomes a market order once price reaches a trigger level. The "
        "trigger is certain, the fill price is not.",
    "concept:stop-limit-order":
        "A stop order that becomes a limit order rather than a market order when triggered, "
        "bounding the fill price at the risk of not filling at all in a fast market.",
    "concept:trailing-stop":
        "A stop whose trigger follows price at a fixed distance in the favourable direction only, "
        "locking in gain while leaving the position room to run.",
    "concept:iceberg-order":
        "A large order that displays only part of its size at a time, refreshing as each slice "
        "fills, to reduce the information leakage and impact of showing full size.",
    # The chapter defines the FIELD ("the study of the processes and mechanisms..."). A discipline
    # is not the thing it studies, and the graph holds market things.
    "concept:market-microstructure":
        "The mechanics by which orders become trades and trades become prices: the matching rules, "
        "order flow, transaction costs and information asymmetries specific to a market's design.",
}

#: Typed I/O for the chapter's computations, in the shape the 71 code-derived indicators use. The
#: formula is in the text; what it consumes and emits is not, and without it nothing can connect
#: `quoted spread` to the bid and ask it reads. `range` uses None for an open end -- Infinity does
#: not survive a JSON round trip in every consumer, and null means "unbounded" throughout.
#: Existing nodes whose definition has already been reconciled by hand against this chapter's.
#: `chapter_variants` means "two wordings, nobody has decided" -- once someone has, recording the
#: chapter's phrasing as a conflict reports work that is finished as work outstanding.
RECONCILED = {"concept:volatility"}

#: A stated line, and the node it concerns. A principle or a practice lives in its list until it
#: earns an edge; then it MOVES -- out of the list, onto the edge as that edge's `why`. It is never
#: in both places, so the two copies cannot drift apart, and what remains in a list is exactly what
#: has not been wired yet. An empty list means the chapter is fully connected.
#:
#: Keyed by a distinctive fragment of the line rather than the whole sentence: the match must fail
#: loudly if the source is reworded, and it does -- an unmatched key raises rather than quietly
#: drawing no edge.
#: What these two nodes ARE, said without reference to anything the reader cannot see. The first
#: drafts described the file they came from -- "as advised across 01-market-foundations" -- which
#: tells a reader nothing about why the node is worth opening.
FACT_SUMMARY = (
    "Things that are true of this market whether or not anyone acts on them. A strategy does not "
    "get to disagree with one: it either accounts for it or pays for it.")
JUDGMENT_SUMMARY = (
    "Things we follow because someone has already paid to learn them. Each is a default rather "
    "than a rule -- departing from one is often right, but it should be a decision with a reason.")

PRICE = {"type": "series", "units": "price"}
PROCEDURE_IO = {
    "procedure:quoted-spread": (
        {"bid": "highest price a buyer will pay", "ask": "lowest price a seller will accept"},
        {"quoted_spread": {**PRICE, "range": [0, None], "canonical_name": "Quoted Spread"}}),
    "procedure:relative-spread": (
        {"bid": "highest price a buyer will pay", "ask": "lowest price a seller will accept"},
        {"relative_spread": {"type": "series", "units": "percent", "range": [0, None],
                             "canonical_name": "Relative Spread"}}),
    "procedure:effective-spread": (
        {"trade_price": "price actually paid or received", "midpoint": "(bid + ask) / 2 at the time"},
        {"effective_spread": {**PRICE, "range": [0, None], "canonical_name": "Effective Spread"}}),
    "procedure:realized-spread": (
        {"trade_price": "price actually paid or received",
         "midpoint_after": "midpoint a fixed interval after the trade",
         "direction": "+1 buyer-initiated, -1 seller-initiated"},
        {"realized_spread": {**PRICE, "range": [None, None],
                             "canonical_name": "Realized Spread"}}),
    "procedure:simple-slippage": (
        {"execution_price": "average price actually filled", "expected_price": "price expected"},
        {"slippage": {**PRICE, "range": [None, None], "canonical_name": "Slippage"},
         "slippage_pct": {"type": "series", "units": "percent", "range": [None, None]}}),
    "procedure:price-impact": (
        {"order_flow": "signed order flow over the interval",
         "lam": "market price sensitivity to order flow (Kyle lambda)"},
        {"delta_p": {**PRICE, "range": [None, None], "canonical_name": "Price Impact"}}),
    "procedure:almgren-chriss-market-impact-model": (
        {"order_size": "shares or contracts to execute", "adv": "average daily volume",
         "sigma": "daily volatility", "eta": "temporary-impact coefficient",
         "gamma": "permanent-impact coefficient"},
        {"temporary_impact": {**PRICE, "range": [0, None]},
         "permanent_impact": {**PRICE, "range": [0, None]}}),
    "procedure:square-root-market-impact-rule": (
        {"order_size": "shares or contracts to execute", "adv": "average daily volume",
         "sigma": "daily volatility"},
        {"impact": {**PRICE, "range": [0, None], "canonical_name": "Square-Root Impact"}}),
    "procedure:participation-rate": (
        {"order_size": "shares or contracts to execute", "adv": "average daily volume",
         "duration_days": "execution horizon in days"},
        {"participation_rate": {"type": "series", "units": "fraction", "range": [0, 1],
                                "canonical_name": "Participation Rate"}}),
    "procedure:historical-volatility": (
        {"returns": "periodic returns series", "periods": "periods per year for annualisation"},
        {"sigma": {"type": "series", "units": "fraction", "range": [0, None],
                   "canonical_name": "Historical Volatility"}}),
    "procedure:garch-model": (
        {"returns": "periodic returns series", "omega": "long-run variance weight",
         "alpha": "reaction to recent shocks", "beta": "persistence of volatility"},
        {"sigma2": {"type": "series", "units": "variance", "range": [0, None],
                    "canonical_name": "Conditional Variance"}}),
    "procedure:volatility-ratio": (
        {"short_vol": "short-window volatility", "long_vol": "long-window volatility"},
        {"vol_ratio": {"type": "series", "units": "ratio", "range": [0, None],
                       "canonical_name": "Volatility Ratio"}}),
    "procedure:information-share": (
        {"variance_contribution": "variance of this market's contribution to the efficient price",
         "variance_total": "variance of the total efficient price"},
        {"information_share": {"type": "series", "units": "fraction", "range": [0, 1],
                               "canonical_name": "Information Share"}}),
    "procedure:component-share": (
        {"permanent_impact_market": "permanent price impact from this market",
         "permanent_impact_total": "total permanent price impact"},
        {"component_share": {"type": "series", "units": "fraction", "range": [0, 1],
                             "canonical_name": "Component Share"}}),
    "procedure:price-efficiency-ratio": (
        {"var_long": "return variance over the long horizon",
         "var_short": "return variance over the short horizon", "n": "horizon ratio"},
        {"efficiency": {"type": "series", "units": "ratio", "range": [0, None],
                        "canonical_name": "Price Efficiency Ratio"}}),
}

#: Sections whose `### Definition` is prose about ONE thing; the rest define several things as
#: bolded bullets and have no single subject of their own.
SCAFFOLD = ("Definition", "Core Principles", "Common Use Cases", "Examples",
            "Best Practices for Traders", "Mathematical Rules/Formulas")

#: Dropped from an id so a section heading and the thing it names collide onto ONE node:
#: "1.7 Bid-Ask Spread Dynamics" and "1.8 Price Discovery Mechanisms" are chapter headings for
#: `bid-ask-spread` and `price-discovery`. Kept out of the middle of a name -- "over-the-counter"
#: must not become "over-counter" -- so only leading and trailing words are removed.
EDGE_STOPWORDS = {"the", "a", "an", "of", "and", "or", "in", "to", "for",
                  "dynamics", "mechanisms"}

#: A category node is singular: one `market maker`, not `market makers`. The chapter titles its
#: sections and example blocks in the plural because they head a list.
IRREGULAR = {"mechanics": "mechanics", "analysis": "analysis", "series": "series",
             "venues": "venue", "networks": "network"}


#: Trailing words that name the FORM of a thing rather than the thing: "Almgren-Chriss Market
#: Impact Model" is about market impact, "Volatility Ratio" about volatility. Stripped from the end
#: of a label before matching it to a subject.
FORM_WORDS = {"model", "rule", "ratio", "guide", "example", "formula", "method", "empirical"}


def head_noun(label: str) -> str:
    """The last meaningful word of a label -- what it is actually about.

    `Simple Slippage` -> slippage. `Square Root Market Impact Rule` -> impact. English puts the head
    of a noun phrase last, so the final word after the form words are dropped names the subject.
    """
    parts = [p for p in slug(re.sub(r"\(.*?\)", " ", label)).split("-") if p]
    while parts and parts[-1] in FORM_WORDS:
        parts.pop()
    return parts[-1] if parts else ""


def singular(word: str) -> str:
    if word in IRREGULAR:
        return IRREGULAR[word]
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("ses") or word.endswith("xes") or word.endswith("ches"):
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        return word[:-1]
    return word


def slug(text: str) -> str:
    text = re.sub(r"\(.*?\)", " ", text)
    parts = [p for p in re.sub(r"[^a-z0-9]+", "-", text.lower()).split("-") if p]
    while parts and parts[0] in EDGE_STOPWORDS:
        parts.pop(0)
    while parts and parts[-1] in EDGE_STOPWORDS:
        parts.pop()
    if parts:
        parts[-1] = singular(parts[-1])
    return "-".join(parts) or "untitled"


def parse(path: Path) -> dict:
    """Split the chapter into {section_number: {"title": .., "blocks": {heading: [lines]}}}."""
    sections: dict[str, dict] = {}
    num = head = None
    for raw in path.read_text(encoding="utf-8").split("\n"):
        if m := H2.match(raw):
            n, title = m.group(1), m.group(2)
            if n is None:                      # "## Summary" and friends: not a numbered section
                num = None
                continue
            num, head = n, None
            sections[num] = {"title": title, "blocks": {}}
        elif num and (m := H3.match(raw)):
            head = m.group(1)
            sections[num]["blocks"].setdefault(head, [])
        elif num and head is not None:
            sections[num]["blocks"][head].append(raw)
    return sections


def bullets(lines: list[str]) -> list[tuple[str, str]]:
    """`- **Name**: text` pairs. A bullet with no bold lead-in yields ("", text)."""
    out = []
    for line in lines:
        if m := BULLET.match(line):
            out.append((m.group(1).strip(), m.group(2).strip()))
        elif m := PLAIN_BULLET.match(line):
            out.append(("", m.group(1).strip()))
    return out


def labelled_blocks(lines: list[str]) -> list[tuple[str, list[str]]]:
    """`**Label:**` followed by its bullets -- the shape of Examples and Formulas sub-blocks."""
    out, label, body = [], None, []
    for line in lines:
        if m := BLOCK_LABEL.match(line.strip()):
            if label:
                out.append((label, body))
            label, body = m.group(1).strip().rstrip(":"), []
        elif label is not None:
            body.append(line)
    if label:
        out.append((label, body))
    return out


#: Bullet prefixes that mark the two halves of an Examples block. "Instruction:" states what the
#: thing IS; "Result:" walks through what happens. Both are wanted -- the definition as the summary,
#: the walkthrough as `examples` -- rather than one standing in for the other.
ILLUSTRATIVE = ("result:", "indication:", "interpretation:")
DEFINITIONAL = ("instruction:",)


def split_block(body: list[str]) -> tuple[str, str]:
    """Return (definition, illustration) for one Examples sub-block.

    Blocks that draw the distinction explicitly (the order types) are split on the prefix. Blocks
    that do not (the participant and venue taxonomies) are wholly definitional -- every bullet says
    what the thing is -- so the illustration is empty rather than guessed at."""
    define, show = [], []
    for line in body:
        s = line.strip()
        if not s.startswith("-"):
            continue
        s = s.lstrip("- ").strip()
        low = s.lower()
        if low.startswith(ILLUSTRATIVE):
            show.append(s)
        elif low.startswith(DEFINITIONAL):
            define.append(s.split(":", 1)[1].strip().strip('"'))
        else:
            define.append(s)
    return " ".join(define), " ".join(show)


def table_rows(lines: list[str]) -> list[tuple[str, str]]:
    """`| name | ... |` rows as (name, the rest joined). Header and rule rows are skipped."""
    out = []
    for line in lines:
        s = line.strip()
        if not s.startswith("|") or set(s) <= set("|- :"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 2 or cells[0].lower() in ("algorithm", "order type", "name", "term"):
            continue
        out.append((cells[0], ". ".join(c for c in cells[1:] if c)))
    return out


def code_of(lines: list[str]) -> str:
    inside, out = False, []
    for line in lines:
        if line.strip().startswith("```"):
            inside = not inside
            continue
        if inside:
            out.append(line)
    return "\n".join(out).strip()


def build(path: Path, chapter: str, parent: str,
          existing: dict[str, dict] | None = None) -> tuple[list[dict], list[dict], list[dict]]:
    """Returns (new atoms, relations, enrichments).

    `enrichments` are the props to add to nodes that ALREADY exist -- the third return value rather
    than a silent mutation, because a caller merging into the record must be able to see every
    change this makes to the code-derived half before applying it.
    """
    if chapter not in CHAPTERS:
        raise ValueError(
            f"no declarations for chapter {chapter!r}. Add an entry to CHAPTERS naming which of its "
            "`### Examples` sections are taxonomies -- building without it emits a graph with no "
            "taxonomy at all, and nothing about the output says so.")
    decl = CHAPTERS[chapter]
    sections = parse(path)
    existing = existing or {}
    atoms: dict[str, dict] = {}
    rels: list[dict] = []
    folded: dict[str, str] = {}          # chapter id -> the existing id it folded into
    extra: dict[str, dict] = {}          # existing id -> props the chapter adds to it

    def atom(kind: str, title: str, summary: str, **props) -> str:
        """Create or MERGE. A term defined twice in one chapter (price discovery in 1.1 and 1.8) is
        one node: the longer definition wins and the props union, rather than a second node or a
        build error. Deconfliction of the two wordings is a review step, not a parse-time decision."""
        nid = f"{kind.lower()}:{slug(title)}"
        target = MERGE_INTO.get(nid, nid)
        if target in existing:
            # Already in the graph: FULL OUTER MERGE. The existing node keeps its identity and its
            # edges, every edge this chapter draws retargets onto it, and everything the chapter
            # says about it is unioned in. Returning early with only a chapter tag -- which this
            # did -- silently discards the chapter's own formula and definition.
            folded[nid] = target
            add = extra.setdefault(target, {})
            for k, v in props.items():
                if k.startswith("_") or not v:
                    continue
                add[k] = v
            if summary and not props.get("_generated"):
                add["_summary"] = " ".join(summary.split())
            return target
        cur = atoms.get(nid)
        if cur is None:
            atoms[nid] = {"id": nid, "title": title.lower(), "kind": kind,
                          "summary": " ".join(summary.split()), "epistemic": "observed",
                          "status": "draft",
                          "props": {"reference_chapter": [chapter],
                                    **{k: v for k, v in props.items() if v}}}
            return nid
        if len(summary) > len(cur["summary"]):
            cur["summary"] = " ".join(summary.split())
        for k, v in props.items():
            if v and k not in cur["props"]:
                cur["props"][k] = v
        cur["props"].setdefault("merged_from", []).append(props.get("_section", ""))
        return nid

    def subject_for(label: str, subjects: list[str]) -> str:
        """Which of a section's subjects a label belongs to.

        A section often defines several things -- §1.4 defines liquidity, slippage and market impact
        -- and every formula and every taxonomy member used to attach to whichever came first. So
        `simple slippage` was declared to be about LIQUIDITY, and `low volatility regime` was made a
        kind of VOLATILITY rather than of market regime. Match on the label's head noun, and fall
        back to the first subject only when nothing matches, which is the single-subject case anyway.
        """
        if len(subjects) == 1:
            return subjects[0]
        head = head_noun(label)
        if head:
            for sid in subjects:
                if head in sid.split(":", 1)[1].split("-"):
                    return sid
        return subjects[0]

    def name_of(nid: str) -> str:
        """The display name, for an id anywhere: authored in this chapter, folded into the existing
        graph, or the chapter's parent. Reading it out of `atoms` alone breaks the moment a term
        folds -- `concept:volatility` is in the record, not in this parse."""
        if nid in atoms:
            return atoms[nid]["title"]
        if nid in existing:
            return existing[nid]["title"]
        return nid.split(":", 1)[1].replace("-", " ")

    def rel(src: str, relation: str, dst: str, why: str) -> None:
        if not any(r["from_id"] == src and r["rel"] == relation and r["to_id"] == dst for r in rels):
            rels.append({"from": name_of(src), "rel": relation, "to": name_of(dst),
                         "why": why, "from_id": src, "to_id": dst})

    principles, practices = [], []

    for num, sec in sorted(sections.items()):
        blocks = sec["blocks"]
        definition = blocks.get("Definition", [])
        defined = bullets([l for l in definition if BULLET.match(l)])
        prose = " ".join(l.strip() for l in definition if l.strip() and not l.strip().startswith("-"))
        uses = [t for _, t in bullets(blocks.get("Common Use Cases", []))]

        # The section's subject(s). Bolded bullets mean the section defines several things and has
        # no single subject; prose means the section IS about one thing, named by its own heading.
        if defined:
            subjects = [atom("Concept", name, text, _section=num) for name, text in defined]
        else:
            subjects = [atom("Concept", sec["title"], prose, applications=uses, _section=num)]
        for s in subjects:
            # The section's NAME, not its number. `§1.1` records a position in a file; the graph
            # holds what a thing is and where it is defined, and "market microstructure" says that.
            rel(s, "part-of", parent, f"defined under {sec['title'].lower()}")
        if defined and uses:
            # The section's subject may have folded into a node already in the graph, in which case
            # its use cases are an enrichment rather than a property of something new. Dropping them
            # would lose the section's Common Use Cases without saying so.
            if subjects[0] in atoms:
                atoms[subjects[0]]["props"].setdefault("applications", uses)
            else:
                extra.setdefault(subjects[0], {}).setdefault("applications", uses)

        for name, text in bullets(blocks.get("Core Principles", [])):
            principles.append(f"{name}: {text}" if name else text)
        for _, text in bullets(blocks.get("Best Practices for Traders", [])):
            practices.append(text)

        if sec["title"] in decl["taxonomy"]:
            for label, body in labelled_blocks(blocks.get("Examples", [])):
                if label in NOT_A_KIND:
                    continue
                definition, illustration = split_block(body)
                if not definition:
                    continue
                kid = atom("Concept", label, definition,
                           examples=[illustration] if illustration else None, _section=num)
                parent_sub = subject_for(label, subjects)
                rel(kid, "kind-of", parent_sub, f"a kind of {name_of(parent_sub)}")
        else:
            # Not a taxonomy: the Examples are worked illustrations of the section's own subjects
            # ("Slippage Example", "Tight Spread"). They are not nodes, but they are not rubbish
            # either -- attach each to the subject it illustrates, by name.
            for label, body in labelled_blocks(blocks.get("Examples", [])):
                # The WHOLE block, not the prefixed lines: an illustration is the walkthrough,
                # and splitting it kept "Indication: highly liquid" while dropping the bid, ask and
                # spread figures that make the point.
                text = " ".join(b.strip().lstrip("- ").strip()
                                for b in body if b.strip().startswith("-"))
                if not text:
                    continue
                key = slug(re.sub(r"\bexample\b", "", label, flags=re.I))
                target = next((s for s in subjects if s.endswith(f":{key}")), subjects[0])
                if target in atoms:
                    atoms[target]["props"].setdefault("examples", []).append(f"{label}: {text}")
                else:
                    extra.setdefault(target, {}).setdefault("examples", []).append(
                        f"{label}: {text}")

        for heading, (target, relation) in decl.get("tables", {}).items():
            for name, rest in table_rows(blocks.get(heading, [])):
                if name in NOT_A_KIND:
                    continue
                nid = atom("Procedure", name, rest, _generated=True, _section=num)
                rel(nid, relation, target, f"listed under {heading.lower()}")

        for label, body in labelled_blocks(blocks.get("Mathematical Rules/Formulas", [])):
            formula = code_of(body)
            if not formula:
                continue
            # `_generated` marks a summary this builder wrote rather than read. It is a filler
            # until the node is reviewed, and must never be recorded as a "chapter variant" of a
            # real authored summary -- that is noise presented as a conflict.
            pid = atom("Procedure", label, f"Computes {label.lower()}.",
                       formula=formula, _generated=True, _section=num)
            quantified = subject_for(label, subjects)
            rel(pid, "about", quantified, f"quantifies {name_of(quantified)}")

    # Named for the SUBJECT, not the chapter file: `01-market-foundations-core-principles` carried
    # a sort key and a file extension into an identifier. The title is just "core principles" --
    # the node hangs off market foundations, so the edge already says which principles these are.
    # The id keeps the subject because eight chapters each have a set and they must not collide.
    subject = parent.split(":", 1)[1]
    fid = f"fact:{subject}-core-principles"
    jid = f"judgment:{subject}-best-practices"
    atoms[fid] = {"id": fid, "title": "core principles", "kind": "Fact",
                  "summary": f"How the market behaves: {len(principles)} principles stated "
                             f"across {subject.replace('-', ' ')}.",
                  "epistemic": "observed", "status": "draft",
                  "props": {"reference_chapter": [chapter], "principles": principles}}
    atoms[jid] = {"id": jid, "title": "best practices", "kind": "Judgment",
                  "summary": f"What to do about it: {len(practices)} practices advised "
                             f"across {subject.replace('-', ' ')}.",
                  # Argued from accumulated practice rather than measured, which is the difference
                  # between this node and the Fact beside it.
                  "epistemic": "inferred", "status": "draft",
                  "props": {"reference_chapter": [chapter], "practices": practices}}
    def wire(list_id: str, lines: list[str]) -> list[str]:
        """Move every wired line out of the list and onto an `about` edge carrying it as the why."""
        kept = []
        for line in lines:
            target = next((v for k, v in decl["wired"].items() if k in line), None)
            if target is None:
                kept.append(line)
                continue
            if target not in atoms and target not in existing:
                raise ValueError(f"`wired` points at {target!r}, which is not a node")
            # FROM the node, TO the list it draws on. A reader arrives at a concept and asks what
            # is known about it, and outgoing edges are the answer to that question -- so the
            # concept points at the principles and practices that govern it, not the reverse. It
            # also keeps the two list nodes from accumulating 87 outgoing edges apiece while every
            # concept sits there with none.
            prior = next((r for r in rels if r["from_id"] == target and r["rel"] == "about"
                          and r["to_id"] == list_id), None)
            if prior:
                prior["why"] += " · " + line
            else:
                rels.append({"from": name_of(target), "rel": "about", "to": atoms[list_id]["title"],
                             "why": line, "from_id": target, "to_id": list_id})

        return kept

    for src, relation, dst, why in decl.get("edges", []):
        for end in (src, dst):
            if end not in atoms and end not in existing:
                raise ValueError(f"authored edge endpoint {end!r} is not a node")
        rel(src, relation, dst, why)

    unused = {k for k in decl["wired"] if not any(k in l for l in principles + practices)}
    if unused:
        raise ValueError(f"`wired` keys match no line in {chapter} -- reworded? {sorted(unused)}")
    atoms[fid]["props"]["principles"] = wire(fid, principles)
    atoms[jid]["props"]["practices"] = wire(jid, practices)
    atoms[fid]["summary"] = FACT_SUMMARY
    atoms[jid]["summary"] = JUDGMENT_SUMMARY

    for i in (fid, jid):
        rels.append({"from": atoms[i]["title"], "rel": "part-of", "to": parent.split(":", 1)[1].replace("-", " "),
                     "why": f"stated across {chapter}", "from_id": i, "to_id": parent})

    for nid, a in atoms.items():
        a["props"].pop("_section", None)
        a["props"].pop("_generated", None)
        a["props"].pop("merged_from", None)
        if nid in DEFINITION:
            # The parsed text was an instance, not a definition: keep it as the illustration.
            if a["summary"] and a["summary"] not in (a["props"].get("examples") or []):
                a["props"].setdefault("examples", []).insert(0, a["summary"])
            a["summary"] = DEFINITION[nid]
        if nid in PROCEDURE_IO:
            ins, outs = PROCEDURE_IO[nid]
            a["props"]["inputs"] = {k: {"type": "series", "description": v} for k, v in ins.items()}
            a["props"]["outputs"] = outs

    enrich = []
    for tid in sorted(set(folded.values()) | set(extra)):
        add, variants = {"reference_chapter": [chapter]}, {}
        node = existing.get(tid, {})
        held = node.get("props", {})
        for k, v in extra.get(tid, {}).items():
            if k == "_summary":
                # The chapter's wording of something the graph already defines. The existing
                # summary stands -- it is code-derived -- and this is kept beside it so the two
                # can be deconflicted by a reader rather than one of them vanishing.
                if v and v != node.get("summary") and tid not in RECONCILED:
                    variants["summary"] = v
                continue
            if k not in held:
                add[k] = v
            elif held[k] != v:
                variants[k] = v
        if variants:
            add["chapter_variants"] = variants
        enrich.append({"id": tid, "props": add,
                       "folded_from": sorted(c for c, x in folded.items() if x == tid)})
    return list(atoms.values()), rels, enrich


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("chapter", type=Path)
    ap.add_argument("--chapter-id", required=True)
    ap.add_argument("--parent", required=True, help="the chapter's node, e.g. concept:market-foundations")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--table", action="store_true", help="print the node table instead of JSON")
    ap.add_argument("--ontology", type=Path,
                    help="the record; a chapter term whose id is already in it folds into that node")
    ap.add_argument("--merge", action="store_true",
                    help="write the whole record with this chapter merged in, not just its delta")
    args = ap.parse_args()

    existing = {}
    if args.ontology:
        existing = {a["id"]: a for a in json.loads(args.ontology.read_text())["atoms"]}
    atoms, rels, enrich = build(args.chapter, args.chapter_id, args.parent, existing)

    if args.table:
        import collections
        by = collections.Counter(a["kind"] for a in atoms)
        for kind in ("Concept", "Procedure", "Property", "Schema", "Fact", "Judgment"):
            rows = [a for a in atoms if a["kind"] == kind]
            if not rows:
                continue
            print(f"\n=== {kind} ({len(rows)}) ===")
            for a in sorted(rows, key=lambda x: x["id"]):
                print(f"  {a['id']:52} {a['summary'][:88]}")
        if enrich:
            print(f"\n=== folded into the existing graph ({len(enrich)}) ===")
            for e in enrich:
                print(f"  {e['id']:52} <- {', '.join(e['folded_from'])}")
        print(f"\nnodes {len(atoms)}  {dict(by)}")
        print(f"edges {len(rels)}  "
              f"{dict(collections.Counter(r['rel'] for r in rels))}")
    if args.merge:
        if not args.ontology or not args.out:
            raise SystemExit("--merge needs --ontology and --out")
        if args.out.resolve() == args.ontology.resolve():
            raise SystemExit("refusing to write over the input record; use a build path for --out")
        rec = json.loads(args.ontology.read_text())
        by_id = {a["id"]: a for a in rec["atoms"]}
        for e in enrich:                     # the folds, applied where they belong
            held = by_id[e["id"]]["props"]
            for k, v in e["props"].items():
                # A list-valued prop UNIONS. `reference_chapter` is the one that matters: replacing
                # it made chapter 01 erase chapter 06's claim on `concept:volatility`, so the node
                # stopped answering for the chapter that defines it as a character class.
                if isinstance(v, list) and isinstance(held.get(k), list):
                    held[k] = held[k] + [x for x in v if x not in held[k]]
                else:
                    held[k] = v
        seen = {(r["from_id"], r["rel"], r["to_id"]) for r in rec["relations"]}
        added = [r for r in rels if (r["from_id"], r["rel"], r["to_id"]) not in seen]
        rec["atoms"] += atoms
        rec["relations"] += added
        rec["meta"] = {**rec["meta"],
                       "derived_atom_ids": sorted(set(rec["meta"].get("derived_atom_ids", ()))
                                                  | {a["id"] for a in atoms}),
                       "derived_relations": sorted(
                           {tuple(x) for x in rec["meta"].get("derived_relations", ())}
                           | {(r["from_id"], r["rel"], r["to_id"]) for r in added}),
                       f"chapter_{args.chapter_id}_atoms": len(atoms),
                       f"chapter_{args.chapter_id}_relations": len(added),
                       f"chapter_{args.chapter_id}_folded": [e["id"] for e in enrich],
                       # Code-derived atoms that a later stage added props to. They are still the
                       # builder's output and must still be reproduced -- but as a SUBSET, since
                       # the fold is additive. One key, so the test needs no per-chapter knowledge.
                       "folded_atom_ids": sorted(set(rec["meta"].get("folded_atom_ids", ()))
                                                 | {e["id"] for e in enrich})}
        # indent=1 matches the code builder: the record is reviewed as a diff, and indent=2 would
        # rewrite all 27,000 lines around the additions.
        args.out.write_text(json.dumps(rec, indent=1) + "\n")
        print(f"merged: +{len(atoms)} atoms, +{len(added)} relations, "
              f"{len(enrich)} folded -> {len(rec['atoms'])} atoms, {len(rec['relations'])} relations")
        print(f"wrote {args.out}")
        return 0
    if args.out:
        args.out.write_text(json.dumps(
            {"atoms": atoms, "relations": rels, "enrich": enrich}, indent=1) + "\n")
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

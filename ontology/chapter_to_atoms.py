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
    "core-trading-concepts": {
        # §3.0 has no Definition and no subject: it states four things about how trading behaves,
        # each under its own heading, and they are the chapter's most load-bearing claims. The first
        # is advice with reasons; the other three are assertions a strategy is judged against.
        "blocks_as_nodes": {"Core Market Wisdom": {
            "The Trend Is Your Friend": "Judgment",
            "Win Rate Is Not Risk": "Fact",
            "Risk Is Multi-Dimensional": "Fact",
            "Regime Determines Archetype Effectiveness": "Fact"}},
        # §3.4 states five real concepts as principles -- a stop hunt is a thing that happens, not a
        # claim about a thing -- exactly as §1.1 did.
        "principle_concepts": {
            "Liquidity Pools": "concept", "Stop Hunts": "concept", "Liquidity Grab": "concept",
            "Smart Money Concept": "concept", "Equal Highs/Lows": "concept",
            "Break of Structure (BOS)": "concept", "Change of Character (CHoCH)": "concept",
        },
        # §3.11's Key Definitions table is five terms of the volume profile, not five procedures.
        "tables": {"Key Definitions": ("concept:volume-profile", "part-of", "Concept")},
        # A section heading names a section. Where the thing it defines is already in the graph the
        # id folds onto it -- §3.1 defines price action, which is this chapter's own parent, and
        # §3.3's three market states are §1.5's regimes under another name.
        "rename": {"Price Action Theory": "concept:price-action",
                   "Trend, Range, Compression/Expansion": "concept:market-regime",
                   "Liquidity Theory": "concept:liquidity",
                   "Volume & Order Flow": "concept:volume",
                   "Support & Resistance": "concept:support-and-resistance",
                   "Volume Profile & Market Auction Theory": "concept:volume-profile",
                   "Equal Highs/Lows": "concept:equal-highs-and-lows",
                   "Trending Market Characteristics": "concept:trending-market",
                   "Ranging Market Characteristics": "concept:ranging-market",
                   "Compression Phase": "concept:compression",
                   "Expansion Phase": "concept:expansion",
                   "Demand Zone Formation": "concept:demand-zone",
                   "Supply Zone Formation": "concept:supply-zone",
                   "Horizontal Support/Resistance": "concept:horizontal-level",
                   "Dynamic Support/Resistance": "concept:dynamic-level",
                   "Bullish Fair Value Gap": "concept:bullish-fair-value-gap",
                   # Chapter 2's delta is an option's sensitivity to the underlying. This one is
                   # buy volume minus sell volume, which shares the name and nothing else.
                   "Delta (Order Flow)": "property:order-flow-delta",
                   "Bearish Fair Value Gap": "concept:bearish-fair-value-gap",
                   "On-Balance Volume (OBV)": "procedure:on-balance-volume",
                   "Volume Weighted Average Price (VWAP)": "procedure:volume-weighted-average-price"},
        "retitle": {"Trending Market Characteristics": "trending market",
                    "Ranging Market Characteristics": "ranging market",
                    "Compression Phase": "compression",
                    "Expansion Phase": "expansion",
                    "Demand Zone Formation": "demand zone",
                    "Supply Zone Formation": "supply zone",
                    "Horizontal Support/Resistance": "horizontal level",
                    "Dynamic Support/Resistance": "dynamic level",
                    "Equal Highs/Lows": "equal highs and lows",
                    "Volume Profile & Market Auction Theory": "volume profile",
                    "Support & Resistance": "support and resistance",
                    "Trend, Range, Compression/Expansion": "market regime",
                    "Liquidity Theory": "liquidity", "Price Action Theory": "price action",
                    "Volume & Order Flow": "volume"},
        # Read one at a time. A rule you evaluate over bars is a Procedure -- detection,
        # classification, the value-area walk. A level or a score a chart has is a Property. The
        # timeframe ratio is neither: it is a convention this chapter states as holding.
        "formula_primitive": {
            "Swing Point Identification": "Procedure",
            "Trend Classification": "Procedure",
            "Structure Break Detection": "Procedure",
            "ADX Trend Strength": "Procedure",
            "Equal Level Detection": "Procedure",
            "On-Balance Volume (OBV)": "Procedure",
            "Volume Weighted Average Price (VWAP)": "Procedure",
            "Volume Profile": "Procedure",
            "Zone Identification": "Procedure",
            "Bullish FVG Detection": "Procedure",
            "Bearish FVG Detection": "Procedure",
            "FVG Validity (Significance Filter)": "Procedure",
            "FVG Fill Status": "Procedure",
            "Value Area Calculation": "Procedure",
            "Liquidity Zone Identification": "Procedure",
            "Timeframe Ratio": "Fact",
        },
        "formula_subject": {"Liquidity Zone Identification": "concept:liquidity-pool",
                            "Equal Level Detection": "concept:equal-highs-and-lows",
                            "Volume Profile": "concept:volume",
                            "Delta (Order Flow)": "concept:order-flow",
                            "Zone Identification": "concept:supply-demand-zone",
                            "Zone Freshness": "concept:supply-demand-zone"},
        "taxonomy": {"Trend, Range, Compression/Expansion", "Liquidity Theory",
                     "Volume & Order Flow", "Support & Resistance", "Supply & Demand Zones",
                     "Fair Value Gaps"},
        # This chapter names computations the library already ships -- ATR, ADX, Bollinger bands,
        # OBV, VWAP -- and states rules on top of them without ever saying they depend on one. It
        # also defines a thing in one section and the rule that detects it in another.
        "edges": [
            ("property:atr-percentage", "uses", "procedure:indicator-atr",
             "the range it scales against price"),
            ("property:bollinger-band-width", "uses", "procedure:indicator-bollingerbands",
             "the bands whose distance it measures"),
            ("procedure:adx-trend-strength", "uses", "procedure:indicator-adx",
             "the strength reading it thresholds"),
            ("procedure:liquidity-zone-identification", "uses", "procedure:indicator-atr",
             "the buffer it places the pool beyond the swing by"),
            ("procedure:fvg-validity", "uses", "procedure:indicator-atr",
             "the size a gap must exceed to be worth marking"),
            ("procedure:zone-identification", "uses", "procedure:indicator-atr",
             "the departure size that makes a base a zone"),
            ("property:support-resistance-zone-width", "uses", "procedure:indicator-atr",
             "how wide a level is drawn"),
            ("procedure:trend-classification", "uses", "procedure:swing-point-identification",
             "the swings it compares"),
            ("procedure:structure-break-detection", "uses", "procedure:swing-point-identification",
             "the swing a close is tested against"),
            ("procedure:value-area-calculation", "uses", "procedure:volume-profile",
             "the profile it walks outward from"),
            # the thing, and the rule that finds it
            ("procedure:swing-point-identification", "about", "concept:market-structure",
             "the swings structure is defined over"),
            ("procedure:adx-trend-strength", "about", "concept:trending-market",
             "above twenty-five is what it calls one"),
            ("procedure:adx-trend-strength", "about", "concept:ranging-market",
             "below twenty is what it calls one"),
            ("procedure:structure-break-detection", "about", "concept:break-of-structure",
             "how one is detected"),
            ("procedure:structure-break-detection", "about", "concept:change-of-character",
             "the same test, applied against the prevailing trend"),
            ("procedure:bullish-fvg-detection", "about", "concept:bullish-fair-value-gap",
             "how one is found"),
            ("procedure:bearish-fvg-detection", "about", "concept:bearish-fair-value-gap",
             "how one is found"),
            ("procedure:equal-level-detection", "about", "concept:equal-highs-and-lows",
             "how they are found"),
            ("procedure:zone-identification", "about", "concept:demand-zone",
             "the base a rally left, marked"),
            ("procedure:zone-identification", "about", "concept:supply-zone",
             "the base a decline left, marked"),
            ("procedure:volume-profile", "about", "concept:point-of-control",
             "the level it returns as the busiest"),
            ("property:relative-volume", "about", "concept:volume-confirmation",
             "the objective form of above average"),
            ("property:bollinger-band-width", "about", "concept:compression",
             "low and falling is what one looks like"),
            ("property:atr-percentage", "about", "concept:expansion",
             "rising is what one looks like"),
            ("property:pivot-point", "about", "concept:horizontal-level",
             "levels everyone computes from the same bar, which is what makes them levels"),
            ("procedure:indicator-obv", "about", "concept:accumulation-pattern",
             "rising while price stays flat is what identifies one"),
            ("procedure:indicator-obv", "about", "concept:distribution-pattern",
             "falling while price holds up is what identifies one"),
            ("procedure:indicator-vwap", "about", "concept:dynamic-level",
             "a level that moves with price rather than sitting at one"),
            ("concept:high-volume-node", "about", "concept:support-and-resistance",
             "business done at a price is why it holds"),
            # and back into chapters one and two
            ("concept:volume", "about", "concept:order-flow",
             "volume says how much traded; flow says which side was the aggressor"),
            ("concept:liquidity-pool", "about", "concept:stop-order",
             "the resting orders that make one are mostly stops"),
            ("concept:stop-hunt", "about", "concept:liquidity-pool",
             "the pool it runs"),
            ("concept:liquidity-grab", "about", "concept:liquidity-pool",
             "the same sweep, named for the fill it achieves"),
            ("judgment:trend-is-your-friend", "about", "concept:trending-market",
             "the state it advises trading with"),
            ("fact:regime-determines-archetype-effectiveness", "about", "concept:market-regime",
             "the regime it says selects the archetype"),
            ("fact:win-rate-is-not-risk", "about", "fact:risk-is-multi-dimensional",
             "skew is one of the dimensions it lists"),
            # leaves: a thing the chapter states once and never connects to anything else
            ("property:candle-body-size", "uses", "procedure:indicator-candlegeometry",
             "the same anatomy, already computed"),
            ("procedure:fvg-fill-status", "uses", "procedure:bullish-fvg-detection",
             "the zone whose fill it tracks"),
            ("concept:value-area-high", "about", "concept:support-and-resistance",
             "the edge of value acts as a level in the session after it"),
            ("concept:value-area-low", "about", "concept:support-and-resistance",
             "the edge of value acts as a level in the session after it"),
            ("concept:low-volume-node", "about", "concept:fair-value-gap",
             "both mark price the market passed through rather than traded in"),
            ("property:volume-profile-metric", "about", "concept:ranging-market",
             "a value area wide against the session range is a rotational day"),
            ("property:range-ratio", "about", "concept:compression",
             "below half the average range is what one measures as"),
            ("concept:smart-money-concept", "about", "concept:institutional-investor",
             "the participants whose size is the whole of the argument"),
            ("concept:buy-side-liquidity", "about", "concept:equal-highs-and-lows",
             "it gathers above them"),
            ("concept:sell-side-liquidity", "about", "concept:equal-highs-and-lows",
             "it gathers below them"),
            ("procedure:equal-level-detection", "uses", "procedure:swing-point-identification",
             "the highs and lows it compares"),
            ("procedure:indicator-obv", "about", "concept:volume-divergence",
             "it rising while price does not is the classic form of one"),
            ("property:relative-volume", "about", "concept:climactic-volume",
             "several times normal is what makes it climactic"),
            ("property:order-flow-delta", "about", "concept:volume",
             "the same activity with a side attached to it"),
            ("property:level-strength-score", "about", "concept:confluence",
             "counting agreeing factors, applied to a single level"),
            ("property:zone-freshness", "about", "concept:demand-zone",
             "untested is the whole of its claim"),
            ("property:zone-freshness", "about", "concept:supply-zone",
             "untested is the whole of its claim"),
            ("fact:timeframe-ratio", "about", "concept:market-structure",
             "structure repeats at every scale, which is what makes two timeframes say different "
             "things about the same market"),
            ("property:trend-alignment-score", "uses", "procedure:trend-classification",
             "the direction it scores on each timeframe"),
            ("property:confluence-score", "uses", "property:level-strength-score",
             "the weight each factor carries into the sum"),
            ("property:zone-overlap", "uses", "property:support-resistance-zone-width",
             "the widths it intersects"),
        ],
        # All 114 stated lines name something the graph holds. Two reach outside this chapter: the
        # claim that price discounts everything is chapter one's market efficiency, and the advice
        # never to trade against the higher timeframe is §3.0's own judgment restated.
        "wired": {
            # --- price action --------------------------------------------------------------------
            "Price Discounts Everything": "concept:market-efficiency",
            "Raw Data Superiority": "concept:price-action",
            "Repetitive Patterns": "concept:price-action",
            "Context Dependency": "concept:price-action",
            "Simplicity: Fewer indicators": "concept:price-action",
            "Practice reading charts without any indicators": "concept:price-action",
            "Document recurring patterns": "concept:price-action",
            "Combine with price action for higher probability": "concept:price-action",
            "Always analyze volume alongside price action": "concept:volume",
            "Study candle anatomy": "property:candle-body-size",
            # --- structure -----------------------------------------------------------------------
            "Higher Highs, Higher Lows": "concept:trending-market",
            "Lower Highs, Lower Lows": "concept:trending-market",
            "Trend Persistence": "concept:trending-market",
            "Structure is Fractal": "concept:market-structure",
            "Nested Structure": "concept:market-structure",
            "Always analyze price action in context of market structure": "concept:market-structure",
            "Always identify structure on higher timeframe first": "concept:market-structure",
            "Mark significant swing points": "procedure:swing-point-identification",
            "Wait for structural breaks rather than anticipating": "concept:break-of-structure",
            "Use CHoCH as a warning": "concept:change-of-character",
            "minor structure breaks within major trends are normal":
                "procedure:structure-break-detection",
            # --- market state --------------------------------------------------------------------
            "Balance and Imbalance": "concept:market-regime",
            "Strategy Adaptation": "fact:regime-determines-archetype-effectiveness",
            "Classify market state before selecting strategy": "concept:market-regime",
            "Reduce position size during uncertain transitional": "concept:market-regime",
            "Mean Reversion in Ranges": "concept:ranging-market",
            "Do not apply trend-following strategies in ranges": "concept:ranging-market",
            "Expect failed breakouts from ranges": "concept:ranging-market",
            "Expect rotational behavior when opening inside value": "concept:ranging-market",
            "Compression Precedes Expansion": "concept:compression",
            "Watch for compression as setup": "concept:compression",
            "Volatility Cycles": "concept:expansion",
            "Use ATR and Bollinger Band width": "property:bollinger-band-width",
            # --- liquidity -----------------------------------------------------------------------
            "Place stops beyond obvious liquidity zones": "concept:liquidity-pool",
            "Wait for liquidity sweeps before entering": "concept:liquidity-grab",
            "Use liquidity grabs as entry signals": "concept:liquidity-grab",
            "attracts stop clusters": "concept:equal-highs-and-lows",
            "breakouts through liquidity often continue": "concept:buy-side-liquidity",
            "Differentiate between liquidity grabs": "concept:stop-hunt",
            "Imbalance: Zones represent unfilled orders": "concept:smart-money-concept",
            # --- volume --------------------------------------------------------------------------
            "Volume Confirms Price": "concept:volume-confirmation",
            "Require volume confirmation for breakout": "concept:volume-confirmation",
            "Volume Precedes Price": "concept:volume",
            "Effort vs. Result": "concept:volume",
            "Climactic Volume: Extreme volume": "concept:climactic-volume",
            "Watch for volume climaxes": "concept:climactic-volume",
            "Delta: Net difference": "property:order-flow-delta",
            "Monitor relative volume": "property:relative-volume",
            "Study order flow data": "concept:order-flow",
            # --- volume profile ------------------------------------------------------------------
            "Price as Advertisement": "concept:volume-profile",
            "Value Area: The price range containing": "concept:value-area-high",
            "Initiative moves break and hold outside value": "concept:value-area-high",
            "Point of Control (POC): The price level": "concept:point-of-control",
            "Use prior session's VA/POC": "concept:point-of-control",
            "POC is better as profit target": "concept:point-of-control",
            "Acceptance vs. Rejection": "concept:high-volume-node",
            "Use volume profile to identify high-volume nodes": "concept:high-volume-node",
            "Monitor value migration": "property:volume-profile-metric",
            # --- levels and zones ----------------------------------------------------------------
            "Role Reversal": "concept:support-and-resistance",
            "Combine structure analysis with key support/resistance":
                "concept:support-and-resistance",
            "Identify major support/resistance from higher timeframes":
                "concept:support-and-resistance",
            "Strength Through Tests": "property:level-strength-score",
            "Note how strongly price reacted": "property:level-strength-score",
            "Round Numbers": "concept:horizontal-level",
            "Expect some penetration of levels": "concept:horizontal-level",
            "Update levels as market structure evolves": "concept:dynamic-level",
            "Zones Over Lines": "property:support-resistance-zone-width",
            "Draw zones rather than single lines": "property:support-resistance-zone-width",
            "Look for confluence of multiple support/resistance factors": "property:zone-overlap",
            "Origin of Move": "concept:supply-demand-zone",
            "Strength Indication": "concept:supply-demand-zone",
            "Place stops beyond the zone": "concept:supply-demand-zone",
            "Combine FVGs with supply/demand zones": "concept:supply-demand-zone",
            "Fresh Zones": "property:zone-freshness",
            "One-Time Use": "property:zone-freshness",
            "Expect zones to work once or twice": "property:zone-freshness",
            "Mark zones at the origin": "procedure:zone-identification",
            "Focus on the consolidation/base": "concept:demand-zone",
            "Use the extreme of the zone for entries": "concept:supply-zone",
            # --- fair value gaps -----------------------------------------------------------------
            "Inefficient Price Delivery": "concept:fair-value-gap",
            "Rebalancing Tendency": "concept:fair-value-gap",
            "Magnet Effect": "concept:fair-value-gap",
            "Focus on FVGs created by strong impulse": "concept:fair-value-gap",
            "Higher timeframe FVGs are more significant": "concept:fair-value-gap",
            "Don't expect all FVGs to fill": "concept:fair-value-gap",
            "Imbalance Detection": "procedure:bullish-fvg-detection",
            "Partial vs. Full Fill": "procedure:fvg-fill-status",
            "Fresh (unfilled) FVGs": "procedure:fvg-fill-status",
            "Mark FVGs from significant moves": "procedure:fvg-validity",
            # --- timeframes and confluence -------------------------------------------------------
            "Higher Timeframe Dominance": "concept:multi-timeframe-analysis",
            "Top-Down Approach": "concept:multi-timeframe-analysis",
            "Context vs. Timing": "concept:multi-timeframe-analysis",
            "Use higher timeframes to establish context": "concept:multi-timeframe-analysis",
            "Higher timeframe zones take precedence": "concept:multi-timeframe-analysis",
            "Start analysis from higher timeframe": "concept:multi-timeframe-analysis",
            "Use higher timeframe levels for targets": "concept:multi-timeframe-analysis",
            "Use lower timeframe patterns for entry triggers": "concept:multi-timeframe-analysis",
            "Never trade against higher timeframe trend": "judgment:trend-is-your-friend",
            "Alignment: Best trades align": "property:trend-alignment-score",
            "Ensure at least 2 out of 3 timeframes agree": "property:trend-alignment-score",
            "Define your timeframes and stick to them": "fact:timeframe-ratio",
            "Multiple Timeframe Confluence": "concept:confluence",
            "Multiple Confirmation": "concept:confluence",
            "Independent Factors": "concept:confluence",
            "Probabilistic Thinking": "concept:confluence",
            "Look for confluence with key support/resistance levels": "concept:confluence",
            "Map all relevant factors": "concept:confluence",
            "Don't force confluence": "concept:confluence",
            "Note which types of confluence work best": "concept:confluence",
            "Document confluence levels": "concept:confluence",
            "Quality Over Quantity": "property:confluence-score",
            "Hierarchy of Factors": "property:confluence-score",
            "Require minimum 3 confirming factors": "property:confluence-score",
            "Weight factors by their historical reliability": "property:confluence-score",
        },
    },
    "instruments-market-mechanics": {
        # Four of the eight sections list real kinds. 2.1 names four spot markets, 2.3 the option
        # types, 2.5 the crypto venue models and 2.7 the settlement regimes. The other four are
        # arithmetic: 2.2 walks a contract spec and a funding payment, 2.4 works three leverage
        # sums, 2.6 four FX calculations, and 2.8 lists three named contracts with their
        # multipliers -- instances of a spec rather than kinds of one.
        # Read one at a time. Black-Scholes is a model you run. Three state identities that hold --
        # break one and there is an arbitrage, which is not what "run this" means. The Greeks names
        # five sensitivities rather than one calculation. Everything else is a quantity a contract,
        # a position or a pool has.
        "formula_primitive": {
            "Black-Scholes Call Price": "Procedure",
            "Put-Call Parity": "Fact",
            "Cost of Carry Relationship": "Fact",
            "Constant Product AMM (Uniswap V2)": "Fact",
            "The Greeks": "Concept",
        },
        # Same quantity stated twice under different headings: 2.2's Contract Value computes the
        # notional of 2.8, 2.6's position P&L is 2.8's P&L calculation, and 2.2's Futures Fair Value
        # is 2.1's cost of carry in symbols. One node each; where the two statements use different
        # conventions -- P&L in pips against P&L in ticks -- the second is written into the
        # explanation rather than dropped.
        #
        # `Price Impact (AMM)` is renamed for the opposite reason. Chapter 1's price impact is Kyle
        # lambda -- how far a book moves per unit of order flow. This is the constant-product curve,
        # a property of an AMM's arithmetic and not of anyone's order flow. They would have folded
        # onto one node on the strength of a shared name, which is the opposite of what folding is
        # for.
        "rename": {"Price Impact (AMM)": "property:amm-price-impact",
                   "Contract Value": "property:notional-value",
                   "Futures Fair Value": "fact:cost-of-carry-relationship",
                   "P&L Calculation": "property:position-profit-loss",
                   "Concentrated Liquidity (V3)": "property:concentrated-liquidity-efficiency"},
        # Labels that name their subject nowhere in themselves. §2.4 defines margin, leverage and
        # the liquidation engine together, and a return amplified by leverage says only "return".
        # The AMM arithmetic is the other case: §2.5's subject is the whole of crypto mechanics,
        # while these four quantify one venue model inside it, which is where they belong.
        "formula_subject": {"Return Amplification": "concept:leverage",
                            "Netting Benefit": "concept:clearing",
                            "Exposure at Default": "concept:central-counterparty",
                            "Constant Product AMM (Uniswap V2)": "concept:automated-market-maker",
                            "Price Impact (AMM)": "concept:automated-market-maker",
                            "Impermanent Loss": "concept:automated-market-maker",
                            "Concentrated Liquidity (V3)": "concept:concentrated-liquidity"},
        "taxonomy": {"Spot Markets", "Options", "Crypto-Specific Mechanics", "Settlement & Clearing"},
        # A formula the chapter states sits under the thing it quantifies and nowhere else, which
        # leaves it reachable only from that one subject -- and a quantity computed FROM another
        # quantity is the relationship a reader most wants. The chapter states the arithmetic and
        # never states the dependency, so these say it: `uses` where one formula consumes another's
        # output, `about` where a thing concerns a thing.
        "edges": [
            # --- crypto venues are venues ------------------------------------------------------
            ("concept:centralized-exchange", "kind-of", "concept:trading-venue",
             "matches crypto orders on a book it operates"),
            ("concept:decentralized-exchange", "kind-of", "concept:trading-venue",
             "matches through a contract on a chain rather than an operator"),
            ("concept:decentralized-exchange", "uses", "concept:automated-market-maker",
             "most price trades from a pooled curve rather than a book"),
            ("concept:cryptocurrency-spot-market", "about", "concept:crypto-settlement",
             "what immediate delivery means when settlement is a block confirmation"),
            ("concept:equity-settlement", "about", "concept:equity-spot-market",
             "how a purchase of shares completes: two business days after the trade"),
            ("property:cross-rate", "about", "concept:forex-spot-market",
             "the rate between two currencies neither of which is quoted against the other"),
            # --- options -----------------------------------------------------------------------
            ("fact:put-call-parity", "about", "concept:call-option",
             "fixes its price against the put at the same strike and expiration"),
            ("fact:put-call-parity", "about", "concept:put-option",
             "fixes its price against the call at the same strike and expiration"),
            ("concept:greeks", "uses", "procedure:black-scholes-call-price",
             "each sensitivity is a derivative of the value this prices"),
            ("property:intrinsic-and-time-value", "uses", "procedure:black-scholes-call-price",
             "the premium it splits is what the model prices"),
            # --- one quantity computed from another --------------------------------------------
            ("property:annualized-basis", "uses", "property:basis",
             "scales it by the days left to expiration"),
            ("property:amm-price-impact", "uses", "fact:constant-product-amm",
             "the price a trade gets follows from the invariant"),
            ("property:concentrated-liquidity-efficiency", "uses", "fact:constant-product-amm",
             "measures a range position against the flat curve it replaces"),
            ("property:margin-requirement", "uses", "property:notional-value",
             "a percentage of the notional it is posted against"),
            ("property:long-position-liquidation-price", "uses", "property:margin-requirement",
             "the initial and maintenance percentages it is computed from"),
            ("property:short-position-liquidation-price", "uses", "property:margin-requirement",
             "the initial and maintenance percentages it is computed from"),
            ("property:exposure-at-default", "uses", "property:margin-requirement",
             "what the collateral a clearing house holds is sized to cover"),
            ("property:netting-benefit", "about", "concept:central-counterparty",
             "what its netting saves the parties it stands between"),
            ("property:forward-rate", "uses", "fact:cost-of-carry-relationship",
             "interest rate parity is the carry identity with the other currency's rate as the yield"),
            ("property:swap-rollover-calculation", "uses", "property:forward-rate",
             "the overnight charge is the forward premium, paid one night at a time"),
            ("property:total-return", "uses", "property:spot-return",
             "the price return plus the income the holding paid"),
            ("property:position-profit-loss", "uses", "property:pip-value",
             "values a currency move in the quote currency"),
            ("property:position-profit-loss", "uses", "property:tick-value",
             "values a futures move by the worth of one tick"),
            # --- and back into chapter one -----------------------------------------------------
            ("property:historical-volatility", "uses", "property:spot-return",
             "the periodic returns whose dispersion it measures"),
        ],
        # Every one of this chapter's 95 stated lines names something the graph holds, because the
        # chapter states them about instruments and the instruments are now nodes. Where a line names
        # two things -- "Compare CEX and DEX execution" -- it goes to the node that holds both rather
        # than to whichever is mentioned first.
        "wired": {
            # --- spot ----------------------------------------------------------------------------
            "Immediate Settlement": "concept:settlement",
            "Physical or Book-Entry Delivery": "concept:settlement",
            "Price Transparency": "concept:spot-market",
            "No Expiration": "concept:spot-market",
            "Direct Ownership": "concept:spot-market",
            "Use spot markets for long-term directional exposure": "concept:spot-market",
            "Factor in custody and storage costs": "concept:commodity-spot-market",
            "corporate actions affecting equity positions": "concept:equity-spot-market",
            "Consider total cost of ownership": "fact:cost-of-carry-relationship",
            # --- futures and perpetuals ----------------------------------------------------------
            "Leverage: Futures allow exposure": "concept:futures",
            "Mark-to-Market": "concept:futures-settlement",
            "Convergence: Futures prices converge": "concept:futures",
            "Understand roll costs": "concept:futures",
            "Funding Rates (Perpetuals)": "property:perpetual-funding-rate",
            "Watch funding rates in perpetuals": "property:perpetual-funding-rate",
            "Monitor spot-futures basis": "property:basis",
            "Use contango/backwardation information": "property:basis",
            # --- options -------------------------------------------------------------------------
            "Asymmetric Payoff": "concept:option",
            "Implied Volatility: Market's expectation": "concept:option",
            "Exercise Styles": "concept:option",
            "Never sell naked options": "concept:option",
            "Calculate max loss before entering": "concept:option",
            "Use options for defined-risk directional bets": "concept:option",
            "Time Decay (Theta)": "concept:greeks",
            "Non-Linear Risk": "concept:greeks",
            "Understand all Greeks": "concept:greeks",
            "avoid gamma risk": "concept:greeks",
            "early exercise risk on American options": "concept:call-option",
            "Monitor implied volatility relative to historical volatility":
                "property:historical-volatility",
            # --- margin, leverage, liquidation ---------------------------------------------------
            "Leverage Amplification": "property:return-amplification",
            "Margin Call": "concept:margin",
            "Cross vs. Isolated Margin": "concept:margin",
            "Monitor margin requirements and maintain adequate buffer": "concept:margin",
            "Use isolated margin for high-risk trades": "concept:margin",
            "Maintain margin buffer significantly": "property:margin-ratio",
            "Forced Liquidation": "concept:liquidation-engine",
            "Insurance Funds": "concept:liquidation-engine",
            "Understand the exchange's liquidation mechanism": "concept:liquidation-engine",
            "Calculate liquidation price before entering": "property:long-position-liquidation-price",
            "Calculate effective leverage": "property:leverage-ratio",
            "Never use maximum available leverage": "concept:leverage",
            "position sizing given FX leverage": "concept:leverage",
            "Set stop-losses well above liquidation price": "concept:stop-order",
            "Monitor funding rates and margin requirements during volatility":
                "concept:high-volatility-regime",
            "Account for spread widening during volatile periods": "concept:bid-ask-spread",
            # --- crypto --------------------------------------------------------------------------
            "24/7 Markets": "concept:crypto-specific-mechanics",
            "Self-Custody": "concept:crypto-specific-mechanics",
            "Decentralization Spectrum": "concept:crypto-specific-mechanics",
            "Network Fees": "concept:crypto-specific-mechanics",
            "Use hardware wallets": "concept:crypto-specific-mechanics",
            "Compare CEX and DEX execution": "concept:crypto-specific-mechanics",
            "Use reputable bridges": "concept:crypto-specific-mechanics",
            "On-Chain vs. Off-Chain": "concept:crypto-settlement",
            "Finality: Settlement finality": "concept:crypto-settlement",
            "Monitor blockchain congestion": "concept:crypto-settlement",
            "Account for gas fees": "concept:decentralized-exchange",
            "MEV (Maximal Extractable Value)": "concept:decentralized-exchange",
            "Verify smart contract addresses": "concept:decentralized-exchange",
            "Understand impermanent loss": "property:impermanent-loss",
            # --- FX ------------------------------------------------------------------------------
            "Currency Pairs": "concept:fx",
            "Lot Sizes": "concept:fx",
            "Interbank Market": "concept:fx",
            "Understand the economic calendars": "concept:fx",
            "Monitor central bank communications": "concept:fx",
            "Be aware of market sessions": "concept:fx",
            "Consider correlation between currency pairs": "concept:fx",
            "Watch for intervention risk": "concept:fx",
            "Pips: Smallest price movement": "property:pip-value",
            "Interest Rate Differentials": "property:swap-rollover-calculation",
            "Account for swap rates": "property:swap-rollover-calculation",
            # --- settlement and clearing ---------------------------------------------------------
            "Delivery vs. Payment": "concept:settlement",
            "Settlement Cycles": "concept:settlement",
            "Understand settlement cycles": "concept:settlement",
            "Ensure sufficient funds available": "concept:settlement",
            "Understand settlement conventions": "concept:settlement",
            "Be aware of settlement failures": "concept:settlement",
            "Account for settlement timing": "concept:settlement",
            "trade date and settlement date accounting": "concept:settlement",
            "Netting: Reducing gross obligations": "concept:clearing",
            "Counterparty Risk Mitigation": "concept:central-counterparty",
            "Margin Requirements: Collateral held by CCPs": "concept:central-counterparty",
            "Monitor CCP margin requirements": "concept:central-counterparty",
            "Understand settlement procedures": "concept:futures-settlement",
            # --- contract specifications ---------------------------------------------------------
            # Both Standardization lines: §2.2 states it of futures and §2.8 of exchange-traded
            # derivatives generally, and they are the same claim about the same thing.
            "Standardization": "concept:contract-specification",
            "Expiration Rules": "concept:contract-specification",
            "Trading Hours": "concept:contract-specification",
            "Be aware of contract expiration dates": "concept:contract-specification",
            "Always verify contract specifications": "concept:contract-specification",
            "Be aware of contract roll dates": "concept:contract-specification",
            "Monitor for specification changes": "concept:contract-specification",
            "Use correct specifications in backtesting": "concept:contract-specification",
            "Multiplier/Contract Size": "property:notional-value",
            "Calculate notional exposure and tick value": "property:notional-value",
            "Tick Size: Minimum price increment": "property:tick-value",
        },
    },
    "market-foundations": {
        # §1.1 has no subject of its own: its Definition defines the FIELD ("the study of the
        # processes and mechanisms"), and its five Core Principles are the section's actual
        # concepts, each with a definition attached. Filed as principles, they sat inert in a list
        # while two of them -- order flow, market efficiency -- existed nowhere in the graph.
        "principle_concepts": {
            "Price Discovery": "concept", "Order Flow": "concept",
            "Information Asymmetry": "concept", "Transaction Costs": "concept",
            "Market Efficiency": "concept", "Information Leakage": "concept",
        },
        # Row label names an existing node; the remaining columns become its properties. The Order
        # Type Summary Table states execution and price certainty for all six order types and was
        # read by nothing.
        "table_properties": {"Order Type Summary Table":
                             ["execution_certainty", "price_certainty", "use_case"]},
        # Read one at a time. Two are models you RUN, one is an empirical regularity, and the other
        # twelve are quantities something has -- a spread a book has, a rate an execution has.
        "formula_primitive": {
            "Almgren-Chriss Market Impact Model": "Procedure",
            "GARCH(1,1) Model (Volatility Forecasting)": "Procedure",
            "Square Root Market Impact Rule (Empirical)": "Fact",
            # ATR is a quantity a bar has AND a function the library exposes. It is declared a
            # Procedure so it keeps the id that folds onto `procedure:indicator-atr` -- where a
            # thing is callable, the callable node is the one that should exist.
            "Average True Range (ATR)": "Procedure",
        },
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
                   "executes against the price series this computes"),
                  # Now that information leakage is a node rather than a line in a list, the order
                  # type that exists to reduce it points at the thing itself.
                  ("concept:iceberg-order", "about", "concept:information-leakage",
                   "displays partial size to reduce it"),
                  ("concept:dark-pool", "about", "concept:information-leakage",
                   "hides the order from the book entirely"),
                  # A taxonomy member reached by its `kind-of` and nothing else is a leaf: you can
                  # find it by walking down from its parent and never by asking what it has to do
                  # with anything. Each of these says the one thing the chapter states about it and
                  # never draws as an edge.
                  ("concept:arbitrageur", "about", "concept:market-efficiency",
                   "its trade is the mechanism that forces prices back together"),
                  ("concept:hedge-fund", "kind-of", "concept:institutional-investor",
                   "an institution running its own strategies with outside capital"),
                  ("concept:proprietary-trading-firm", "about", "concept:order-flow",
                   "trades its own capital on short-horizon reads of the orders arriving"),
                  ("concept:retail-trader", "about", "concept:information-asymmetry",
                   "sits at the bottom of the information hierarchy the chapter describes"),
                  ("concept:continuous-trading-discovery", "uses", "concept:order-flow",
                   "the price forms tick by tick out of the orders that arrive"),
                  ("concept:cross-market-discovery", "uses", "property:information-share",
                   "which venue moved first is what this measures"),
                  ("concept:lit-exchange", "about", "concept:price-discovery",
                   "displayed quotes are where public discovery happens"),
                  # Not `about liquidity`, though it supplies it: `about` edges into liquidity are
                  # read as "what quantifies this", and a venue is not a measurement of one.
                  ("concept:electronic-communication-network", "about", "concept:bid-ask-spread",
                   "participants matching directly, and competing to, is what narrows it"),
                  ("concept:internalization", "about", "concept:order-flow",
                   "a broker fills client orders in-house, so the flow never reaches an exchange"),
                  ("concept:over-the-counter-market", "about", "concept:information-leakage",
                   "a negotiated trade never displays, so the market learns of it late"),
                  ("concept:low-volatility-regime", "uses", "property:historical-volatility",
                   "the measurement that classifies it"),
                  ("concept:trailing-stop", "kind-of", "concept:stop-order",
                   "a stop whose trigger follows price in the favourable direction only"),
                  ("concept:chart-pattern", "about", "concept:pattern",
                   "the class of computation that measures these forms"),
                  # Same for a formula reachable only from the thing it quantifies.
                  ("property:effective-spread", "about", "concept:transaction-cost",
                   "the honest input to a cost calculation"),
                  ("property:simple-slippage", "about", "concept:transaction-cost",
                   "the realised cost of an execution against the price expected"),
                  ("property:relative-spread", "uses", "property:quoted-spread",
                   "the same spread as a fraction of the midpoint"),
                  ("property:realized-spread", "uses", "property:effective-spread",
                   "the comparison that separates what the maker kept from what it lost"),
                  ("property:price-impact", "uses", "concept:order-flow",
                   "measures how far price moves per unit of signed flow"),
                  ("property:component-share", "uses", "property:price-impact",
                   "builds a venue's share out of permanent impact"),
                  ("property:price-efficiency-ratio", "about", "concept:market-efficiency",
                   "how close prices are to a random walk is the testable form of it"),
                  ("property:volatility-ratio", "uses", "property:historical-volatility",
                   "compares a short window against a long one"),
                  ("fact:square-root-market-impact-rule", "uses", "property:participation-rate",
                   "impact scales with the share of volume taken"),
                  ("procedure:almgren-chriss-market-impact-model", "uses",
                   "property:historical-volatility",
                   "the volatility term in the risk half of its cost"),
                  ("procedure:garch-model", "uses", "property:historical-volatility",
                   "fits to the realised series it forecasts forward"),
                  ("procedure:implementation-shortfall", "about", "concept:market-impact",
                   "balances impact against the risk of price moving while it waits"),
                  ("procedure:twap", "about", "concept:market-impact",
                   "splits an order across time so no slice is large enough to move the price"),
                  ("procedure:sniper-liquidity-seeking", "about", "concept:dark-pool",
                   "pings hidden venues for liquidity that never displays")],
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
    "strategy-design": {
        # This chapter states nothing under `### Examples` and nothing under `### Mathematical
        # Rules/Formulas`. What earlier chapters wrote as a taxonomy block it writes as sibling
        # `###` headings, and what they wrote as a formula it writes as a python function.
        "taxonomy": set(),
        # §4.2 heads each archetype's definition `**Core Premise:**`, where §3.0 wrote
        # `**Definition:**`. Both name the same slot.
        "definition_labels": ("Definition", "Core Premise"),
        # §4.1 and §4.2 each list their members as headings of their own rather than under Examples.
        # Position trading is named only in the comparison table, and the table declaration below
        # creates it; the other three carry a block, and merge with their row.
        "blocks_as_nodes": {
            "Trading Styles": {"Scalping": "Concept", "Day Trading": "Concept",
                               "Swing Trading": "Concept"},
            "Strategy Archetypes": {"Trend Following": "Concept", "Momentum": "Concept",
                                    "Breakouts (Transition Archetype)": "Concept",
                                    "Volatility": "Concept", "Mean Reversion": "Concept"},
            # Headings holding one unlabelled recipe each. A rule you evaluate over bars is a
            # Procedure, whatever the chapter chose to head it with.
            "Exit Logic": {"Time-Based Exits": "Procedure"},
            "Time-Based Logic": {"Session Filters": "Procedure",
                                 "Holding Period Constraints": "Procedure",
                                 "Calendar Filters": "Procedure"},
            "Walk-Forward Optimization": {"Parameter Optimization": "Procedure"},
        },
        # §4.5 onwards states its rules as `**Label:**` sub-blocks rather than as headings. Each is
        # a named thing -- a stop placement, a regime test, a bias -- and left inside the heading
        # none of them can carry an edge.
        "labelled_nodes": {
            "Signal Generation Approaches": {"Indicator-Based": "Procedure",
                                             "Pattern-Based": "Procedure",
                                             "Statistical-Based": "Procedure"},
            "Entry Confirmation Methods": {"Multi-Factor Confirmation": "Procedure",
                                           "Timeframe Confirmation": "Procedure"},
            "Entry Timing Refinements": {"Pullback Entry": "Procedure",
                                         "Breakout Entry": "Procedure"},
            "Entry Filters": {"Regime Filter": "Procedure", "Volatility Filter": "Procedure"},
            "Stop-Loss Exits": {"Fixed Stop": "Procedure", "ATR-Based Stop": "Procedure"},
            "Profit Target Exits": {"Fixed Target": "Procedure",
                                    "Risk-Multiple Target": "Procedure"},
            "Trailing Stop Exits": {"Simple Trailing Stop": "Procedure",
                                    "ATR Trailing Stop": "Procedure"},
            "Signal-Based Exits": {"Indicator Exit": "Procedure",
                                   "Opposing Signal Exit": "Procedure"},
            "Trend vs. Range Detection": {"ADX-Based": "Procedure", "Efficiency Ratio": "Procedure"},
            "Volatility Regime Detection": {"Percentile-Based": "Procedure",
                                            "Hidden Markov Model": "Procedure"},
            "Data Cleaning": {"Handling Missing Data": "Procedure",
                              "Outlier Detection": "Procedure"},
            "Corporate Action Adjustments": {"Split Adjustment": "Procedure",
                                             "Dividend Adjustment": "Procedure"},
            "Avoiding Biases": {"Survivorship Bias Prevention": "Procedure",
                                "Look-Ahead Bias Prevention": "Procedure"},
            "Realistic Assumptions": {"Transaction Costs": "Procedure",
                                      "Slippage Modeling": "Procedure"},
            "Anchored vs. Rolling Walk-Forward": {"Anchored (Expanding Window)": "Concept",
                                                  "Rolling (Fixed Window)": "Concept"},
            # A bias is a thing that happens to a study, not a rule you run.
            "Common Biases to Avoid": {"Look-Ahead Bias": "Concept", "Survivorship Bias": "Concept",
                                       "Data Snooping Bias": "Concept", "Selection Bias": "Concept",
                                       "Overfitting": "Concept"},
            "Statistical Significance Testing": {"T-Test for Returns": "Procedure",
                                                 "Multiple Testing Correction": "Procedure"},
            "Robustness Checks": {"Parameter Sensitivity": "Procedure",
                                  "Time Period Stability": "Procedure",
                                  "Universe Stability": "Procedure"},
        },
        # An archetype is a family of strategies, not a thing an indicator measures. Momentum and
        # volatility are already in the graph as characters a computation reads -- rate of change,
        # dispersion of returns -- and folding a strategy family onto them would make "what
        # measures volatility" answer with a trading approach. Breakout is held apart from the
        # chart pattern of that name, which chapter 7 defines.
        "rename": {"Momentum": "concept:momentum-strategy",
                   "Volatility": "concept:volatility-strategy",
                   "Breakouts (Transition Archetype)": "concept:breakout-strategy",
                   # The two summary tables list it under the shorter name it is called everywhere
                   # else in the chapter.
                   "Breakouts": "concept:breakout-strategy",
                   # A heading names a section: "Building a Trade Plan" is the section, the trade
                   # plan is the thing. "Backtesting Best Practices" would singularise to
                   # `backtesting-best-practice`, which names the list rather than the procedure.
                   "Building a Trade Plan": "concept:trade-plan",
                   "Entry Logic Frameworks": "concept:entry-logic",
                   "Regime Detection & Filtering": "concept:regime-detection",
                   "Data Quality & Preprocessing": "concept:data-quality",
                   "Backtesting Best Practices": "concept:backtesting",
                   # The four signal types are the chapter's own words for the axis the library
                   # calls `role`. `Entry` alone would slug to `concept:entry`.
                   "Entry": "concept:entry-signal", "Exit": "concept:exit-signal",
                   "Filter": "concept:filter-signal", "Confirmation": "concept:confirmation-signal",
                   # §4.8's ADX rule IS §3.2's: trending above twenty-five, ranging below twenty.
                   # Same thresholds, same reading. It folds; the python arrives as a variant of
                   # the pseudocode already held.
                   "ADX-Based": "procedure:adx-trend-strength",
                   # Labels that name the approach and leave the subject implicit.
                   # `procedure:indicator-*` is the library's namespace -- 71 nodes built from the
                   # indicator classes -- and `procedure:indicator-based-entry` would be counted as
                   # a 72nd. Lead with the thing these are approaches TO.
                   "Indicator-Based": "procedure:entry-indicator-based",
                   "Pattern-Based": "procedure:entry-pattern-based",
                   "Statistical-Based": "procedure:entry-statistical-based",
                   "Indicator Exit": "procedure:exit-on-indicator",
                   "Percentile-Based": "procedure:volatility-percentile-regime",
                   "Hidden Markov Model": "procedure:hmm-regime-detection",
                   "T-Test for Returns": "procedure:returns-t-test",
                   # A cost model, not the cost: `concept:transaction-cost` is already the thing.
                   "Transaction Costs": "procedure:transaction-cost-model",
                   # Parenthesised ids: the slug drops what is in brackets, leaving `anchored`.
                   "Anchored (Expanding Window)": "concept:anchored-walk-forward",
                   "Rolling (Fixed Window)": "concept:rolling-walk-forward"},
        "retitle": {"Momentum": "momentum strategy", "Volatility": "volatility strategy",
                    "Breakouts (Transition Archetype)": "breakout strategy",
                    "Building a Trade Plan": "trade plan",
                    "Entry Logic Frameworks": "entry logic",
                    "Regime Detection & Filtering": "regime detection",
                    "Data Quality & Preprocessing": "data quality",
                    "Backtesting Best Practices": "backtesting",
                    "Strategy Validation (Avoiding Biases)": "strategy validation",
                    "Entry": "entry signal", "Exit": "exit signal",
                    "Filter": "filter signal", "Confirmation": "confirmation signal"},
        # Two tables whose rows are the members of a taxonomy, and two whose rows are properties of
        # members already created.
        "tables": {"Trading Style Comparison": ("concept:trading-style", "kind-of", "Concept"),
                   "The Four Signal Types": ("concept:signal-type", "kind-of", "Concept")},
        "table_properties": {
            "Trading Style Comparison": ["timeframe", "holding_period", "key_traits"],
            "Archetype Risk Summary Table": ["win_rate", "skew", "tail_risk", "best_regime"],
            "Archetype Contraindications": ["contraindicated_when", "why_it_fails"],
        },
        "edges": [
            ("concept:trend-following", "kind-of", "concept:strategy-archetype",
             "the family that holds while a direction persists"),
            ("concept:momentum-strategy", "kind-of", "concept:strategy-archetype",
             "the family that reads whether pressure is building or fading"),
            ("concept:breakout-strategy", "kind-of", "concept:strategy-archetype",
             "the family that acts as compression gives way"),
            ("concept:volatility-strategy", "kind-of", "concept:strategy-archetype",
             "the family that trades movement size rather than direction"),
            ("concept:mean-reversion", "kind-of", "concept:strategy-archetype",
             "the family that fades extension from fair value"),
            # --- the exit rules and the orders they place ------------------------------------
            # Chapter 2 defines the order; this chapter defines where it rests. §4.3 states the
            # stop-loss rules as "technical placement" and "ATR-based calculation (e.g. 1.5x ATR)".
            ("procedure:fixed-stop", "about", "concept:stop-order",
             "the distance from entry it places one at"),
            ("procedure:atr-based-stop", "about", "concept:stop-order",
             "the same placement, scaled to how far the instrument moves"),
            ("procedure:atr-based-stop", "uses", "procedure:indicator-atr",
             "the range it multiplies to get the stop distance"),
            ("procedure:atr-trailing-stop", "uses", "procedure:indicator-atr",
             "the range it holds the trail behind the extreme by"),
            ("procedure:simple-trailing-stop", "about", "concept:trailing-stop",
             "the level that follows price at a fixed percentage"),
            ("procedure:atr-trailing-stop", "about", "concept:trailing-stop",
             "the same level, held at a volatility-scaled distance"),
            # --- the archetype, and the regime that decides whether it works -------------------
            # Chapter 3 states this and had nothing to point it at: `strategy archetype` was not a
            # node until this chapter. Each `best_regime` below is the summary table's own column.
            ("fact:regime-determines-archetype-effectiveness", "about", "concept:strategy-archetype",
             "the family whose effectiveness it says the regime decides"),
            ("concept:trend-following", "about", "concept:trending-market",
             "best regime: strong trends -- and whipsaws accumulate in the absence of one"),
            ("concept:mean-reversion", "about", "concept:ranging-market",
             "best regime: range-bound only"),
            ("concept:mean-reversion", "about", "concept:trending-market",
             "the contraindication the chapter states most emphatically: it will blow up in one"),
            ("concept:volatility-strategy", "about", "concept:high-volatility-regime",
             "best regime: high volatility periods, with nothing to capture in a quiet one"),
            ("concept:breakout-strategy", "about", "concept:compression",
             "best regime: after compression, which is the setup it waits for"),
            # §4.2's warning quotes chapter 3's judgment by name -- '"The trend is your friend"
            # exists because fighting trends is dangerous' -- and restates its fact.
            ("concept:mean-reversion", "about", "judgment:trend-is-your-friend",
             "the reason the chapter gives for why fading a trend is dangerous"),
            ("concept:mean-reversion", "about", "fact:win-rate-is-not-risk",
             "sixty to seventy per cent right, and negative skew: the case the fact is about"),
        ],
        # What the resolver could not settle from the text: a statement whose subject is named
        # nowhere in it, a single ordinary word it refuses to treat as a citation, and three where
        # it matched the longer of two names and chose the wrong one. Keys are distinctive
        # fragments; a key matching no line raises, so a reworded source fails loudly.
        "wired": {
            # --- the resolver's three wrong picks, corrected -----------------------------------
            "Consider trailing stops for trend-following": "concept:trailing-stop",
            "Never combine conflicting archetypes": "concept:strategy-archetype",
            "Match signal types to archetype": "concept:signal-type",
            # --- single words it declined to draw on, accepted --------------------------------
            "Rolling Optimization": "concept:rolling-walk-forward",
            "Overfitting Prevention": "concept:overfitting",
            # --- §4.1 trading styles ----------------------------------------------------------
            "Timeframe Selection": "concept:trading-style",
            "Consistency: Stick to one primary style": "concept:trading-style",
            "Capital Requirements": "concept:trading-style",
            "Risk Profile: Each style": "concept:trading-style",
            "Lifestyle Fit": "concept:trading-style",
            "Match trading style to available time": "concept:trading-style",
            "Start with longer timeframes": "concept:trading-style",
            "Consider psychological fit": "concept:trading-style",
            "Paper trade the style": "concept:trading-style",
            # --- §4.2 archetypes --------------------------------------------------------------
            "Behavioral Alignment": "concept:strategy-archetype",
            "Regime Dependence": "concept:strategy-archetype",
            "Style Purity": "concept:strategy-archetype",
            "Distinct Risk Profiles": "concept:strategy-archetype",
            "Complementarity": "concept:strategy-archetype",
            "Match archetypes to current market regime": "concept:strategy-archetype",
            "Combine complementary archetypes": "concept:strategy-archetype",
            "Understand skew and tail risk": "concept:strategy-archetype",
            "Size positions according to archetype": "concept:strategy-archetype",
            "Monitor regime transitions": "concept:regime-shift",
            # --- §4.3 the trade plan ----------------------------------------------------------
            "Pre-Definition": "concept:trade-plan",
            "Specificity: Rules must be clear": "concept:trade-plan",
            "Completeness: Plan covers": "concept:trade-plan",
            "Documentation: Written down": "concept:trade-plan",
            "Evolution: Reviewed and updated": "concept:trade-plan",
            "Write your plan when not actively trading": "concept:trade-plan",
            "Be specific: vague rules": "concept:trade-plan",
            'Include "what if" scenarios': "concept:trade-plan",
            "Review plan performance": "concept:trade-plan",
            "Update based on data, not emotions": "concept:trade-plan",
            "Treat the plan as non-negotiable": "concept:trade-plan",
            # --- §4.4 signal types ------------------------------------------------------------
            "Layer signals intentionally": "concept:signal-type",
            "Test signal combinations": "concept:signal-type",
            "Document signal roles": "concept:signal-type",
            "Don't over-confirm": "concept:confirmation-signal",
            # --- §4.5 entry logic -------------------------------------------------------------
            "Objectivity: Rules should be unambiguous": "concept:entry-logic",
            "Edge Definition": "concept:entry-logic",
            "Timing: Entry timing": "concept:entry-logic",
            "Confirmation: Multiple confirming factors": "concept:confirmation-signal",
            "Filter Quality": "concept:filter-signal",
            "Define entry criteria precisely": "concept:entry-logic",
            "Use multiple confirmation factors": "procedure:multi-factor-confirmation",
            "Test entries with various exit rules": "concept:entry-logic",
            "Track entry efficiency": "concept:entry-logic",
            "Avoid overly complex entry rules that overfit": "concept:overfitting",
            "Include regime and volatility filters": "procedure:regime-filter",
            # --- §4.6 exit logic --------------------------------------------------------------
            "Protect Capital": "concept:exit-logic",
            "Let Winners Run": "concept:exit-logic",
            "Cut Losers Short": "concept:exit-logic",
            "Rule-Based: Exits should be as systematic": "concept:exit-logic",
            "Exit Reason": "concept:exit-logic",
            "Use ATR-based stops": "procedure:atr-based-stop",
            "Don't let winners turn into losers": "concept:exit-logic",
            "Test different exit strategies": "concept:exit-logic",
            "Document reason for each exit": "concept:exit-logic",
            # --- §4.7 time-based logic --------------------------------------------------------
            "Holding Period: Strategies have optimal": "procedure:holding-period-constraint",
            "Session Selection": "procedure:session-filter",
            "Calendar Awareness": "procedure:calendar-filter",
            "Time Decay": "concept:time-based-logic",
            "Periodicity": "concept:time-based-logic",
            # --- §4.8 regime detection --------------------------------------------------------
            "Market States": "concept:market-regime",
            "Strategy Matching": "concept:market-regime",
            "Probabilistic: Regime identification": "concept:regime-detection",
            "Adaptation: Strategies should adapt": "concept:regime-detection",
            "Use multiple regime indicators": "concept:regime-detection",
            "Have default behavior for uncertain": "concept:regime-detection",
            # --- §4.9 data quality ------------------------------------------------------------
            "Garbage In, Garbage Out": "concept:data-quality",
            "Point-in-Time: Use data as it was available": "procedure:look-ahead-bias-prevention",
            "Corporate Actions": "concept:data-quality",
            "Validate data against multiple sources": "concept:data-quality",
            "Check for obvious errors": "procedure:outlier-detection",
            "Document data sources": "concept:data-quality",
            "Use point-in-time databases": "procedure:look-ahead-bias-prevention",
            "Include delisted securities": "procedure:survivorship-bias-prevention",
            "Account for reporting lags": "procedure:look-ahead-bias-prevention",
            # --- §4.10 backtesting ------------------------------------------------------------
            "Historical Simulation": "concept:backtesting",
            "Out-of-Sample Testing": "concept:backtesting",
            "Realistic Assumptions": "concept:backtesting",
            "Multiple Tests: Test across different periods": "concept:backtesting",
            "Skepticism: Assume backtest overstates": "concept:backtesting",
            "Be skeptical of exceptional results": "concept:backtesting",
            "Compare to simple benchmarks": "concept:backtesting",
            "Document all assumptions and parameters": "concept:backtesting",
            # --- §4.11 walk-forward -----------------------------------------------------------
            "Out-of-Sample Validation": "concept:walk-forward-optimization",
            "Adaptive Parameters": "concept:walk-forward-optimization",
            "Realistic Performance": "concept:walk-forward-optimization",
            "Use at least 2-3 years of data": "concept:walk-forward-optimization",
            "Test windows should be long enough": "concept:walk-forward-optimization",
            "Monitor parameter stability": "procedure:parameter-sensitivity",
            "Aggregate OOS results": "concept:walk-forward-optimization",
            "Be wary of strategies that require frequent": "concept:walk-forward-optimization",
            # --- §4.12 validation. The longer key first: "final validation" is a prefix of it.
            "final validation only": "concept:strategy-validation",
            "Use out-of-sample data for final validation": "concept:backtesting",
            "Skepticism: Assume the strategy doesn't work": "concept:strategy-validation",
            "Multiple Testing: Account for trying many": "procedure:multiple-testing-correction",
            "Economic Rationale": "concept:strategy-validation",
            "Robustness: Results should hold": "concept:strategy-validation",
            "Statistical Significance: Returns should be": "procedure:returns-t-test",
            "Pre-register hypotheses": "concept:data-snooping-bias",
            "Account for multiple testing": "procedure:multiple-testing-correction",
            "Require economic rationale": "concept:strategy-validation",
            "Test robustness to reasonable parameter": "procedure:parameter-sensitivity",
            "Be skeptical of Sharpe ratios": "concept:strategy-validation",
            "Paper trade before committing real capital": "concept:strategy-validation",
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
              "Iceberg",
              # Attributes that make a zone strong, not a kind of zone; and a walkthrough of one
              # level turning into the other, not a third kind of level.
              "Zone Quality Factors", "Role Reversal Example", "Liquidity Sweep Setup",
              "FVG as Entry",
              # A covered call is a position built from an option and a holding of the underlying,
              # not a kind of option -- it sits beside the call and the put in §2.3's examples and
              # is a different sort of thing. Its walkthrough stays on the option; the strategies
              # themselves belong to the chapter that defines strategies.
              "Covered Call"}

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
    # §3.5 states the definition of two computations the library already ships. The formula is the
    # same formula; a second node would be the same measurement under a second name.
    "procedure:on-balance-volume": "procedure:indicator-obv",
    "procedure:volume-weighted-average-price": "procedure:indicator-vwap",
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

#: Authored prose, one entry per node: (definition, explanation). Written by reading the chapter,
#: and merged rather than substituted -- an OUTER JOIN with dedupe. Where the chapter states a real
#: definition it stays as the summary and this one is kept beside it; where the chapter offers only
#: a worked example ("Instruction: buy 100 shares at the best available price"), this becomes the
#: summary and the example moves to `examples`. The explanation has no counterpart in the source at
#: all -- the chapter never says WHY an iceberg order costs queue position -- so it is always added.
AUTHORED: dict[str, tuple[str, str]] = {
    # The four styles are characterised only by a comparison table, so the parsed summary was that
    # table's row -- "Seconds to minutes. Seconds to minutes. Tiny moves, high volume" -- repeating
    # the `timeframe` and `holding_period` props verbatim and saying nothing they do not.
    'concept:scalping': (
        'Trading in seconds to minutes for one to ten ticks at a time, dozens to hundreds of times '
        'a day.',
        'The edge per trade is smaller than the [[Bid-Ask Spread]] on most instruments, which is '
        'why it needs direct market access, low commissions and the tightest spreads available: '
        'costs are not a deduction from the profit here, they are comparable to it. It also needs '
        'uninterrupted attention, which is the constraint that rules it out for most traders '
        'rather than the strategy logic.'),
    'concept:day-trading': (
        'Trading intraday moves and closing every position before the session ends, typically one '
        'to ten trades a day.',
        'Flat at the close means the overnight gap cannot reach the position, and neither can the '
        'financing that [[Swap/Rollover Calculation]] measures -- the risk being avoided is the '
        'one that arrives while the market is shut and no stop can execute. The cost is that every '
        "position must resolve inside a session whether or not the move has finished."),
    'concept:swing-trading': (
        'Holding for days to weeks to capture a multi-day swing, trading selectively rather than '
        'often.',
        'Fewer, larger targets make transaction costs a small share of the gain, which is what '
        'lets the style tolerate a lower hit rate. Holding through the close accepts gap risk in '
        'exchange for not having to be at the screen, and it is the shortest style that can be run '
        'alongside a full-time job.'),
    'concept:position-trading': (
        'Holding for weeks to months on a regime or fundamental view rather than on a chart event.',
        'The thesis is about the [[Market Regime]] itself, so the position is sized and stopped '
        'against a regime change rather than against a level. It is the only style whose holding '
        'period is long enough for carry, financing and correlation to dominate the outcome.'),
    'concept:arbitrageur': (
        'Participants who exploit price discrepancies between related instruments, generally holding '
        'hedged, market-neutral positions.',
        'ETF against underlying, one exchange against another, statistical relationships between '
        'securities: in each case the trade is the difference rather than the direction. Their '
        'activity is the mechanism that forces prices back together, which makes them the enforcers '
        'of [[Market Efficiency]] and a driver of [[Cross-Market Discovery]].'),
    'concept:auction-based-discovery': (
        'Price discovery by batching orders and clearing them at a single price, as at the open and '
        'close.',
        "Aggregating a period's orders into one crossing dampens the volatility that continuous "
        'matching produces at those moments, which is why many equity markets set official opening '
        "and closing prices this way. The batch is also where the day's largest concentrations of "
        'interest meet.'),
    'concept:bid-ask-spread': (
        'The gap between the highest price a buyer will pay and the lowest a seller will accept -- '
        'the price of immediacy.',
        'It is what [[Market Makers]] earn for standing ready to trade, and it moves for reasons that '
        'are readable. It widens when they fear trading against someone informed, when inventory risk '
        'is high, and when [[Volatility]] rises; it narrows when more of them compete. Because it '
        'widens under uncertainty, the spread doubles as an indicator of market stress rather than '
        'only a cost.'),
    'concept:continuous-trading-discovery': (
        'Price discovery tick by tick, as individual orders match through the session.',
        'It gives a live price at every moment, which is its value, and it is noisy in thin markets, '
        'which is its cost -- a single small order can move the print. It is the mode in which most '
        'of the session runs, bracketed by [[Auction-Based Discovery]] at each end.'),
    'concept:cross-market-discovery': (
        'Price discovery that happens between related instruments rather than within one book.',
        'Futures often lead spot, options embed a volatility expectation the underlying does not '
        'show, and ETFs and their baskets are pulled together by arbitrage. The consequence is that '
        'the price of one instrument carries information about another before that other has moved, '
        'which is what lead-lag analysis looks for and what [[Arbitrageurs]] enforce.'),
    'concept:dark-pool': (
        'Venues with no pre-trade transparency, where orders stay hidden until they execute.',
        'The whole point is matching size without announcing it, often at the midpoint, which is why '
        '[[Institutional Investors]] use them for block trades. The trade-off is that you cannot see '
        'what is there, so execution quality has to be measured after the fact rather than assumed. '
        'They solve the same problem as [[Iceberg Order]] by a different route: hiding the order '
        'rather than hiding its size.'),
    'concept:electronic-communication-network': (
        'Automated venues that match buy and sell orders directly, often outside standard trading '
        'hours.',
        'They give direct access without an intermediary and typically extend the session, which is '
        'where early reaction to news happens. Fee structures vary and are worth reading, because on '
        'a small spread the fee can exceed it.'),
    'concept:execution-model': (
        'The methods and protocols by which orders are matched and filled, differing in transparency, '
        'speed and who may participate.',
        'A venue is where you trade; an execution model is how the match happens once you are there '
        '-- continuous price-time priority, periodic auction, dealer quotation, or an algorithm '
        'working an order across venues over time. [[TWAP]], [[VWAP]], [[Implementation Shortfall]] '
        'and liquidity-seeking algorithms are the schedules the chapter names.'),
    'concept:hedge-fund': (
        'Pooled investment firms running diverse strategies with leverage and shorter horizons than '
        'traditional asset managers.',
        'Long/short equity, macro and quantitative approaches sit under one label, so the category '
        'describes a structure rather than a method. They can be either side of the [[Liquidity]] '
        'relationship depending on the strategy, providing it when they quote and consuming it '
        'aggressively when they need to move.'),
    'concept:high-frequency-trader': (
        'Firms using ultra-low-latency technology to trade on horizons of milliseconds to seconds.',
        'Speed is the whole edge, applied to market making, arbitrage and latency arbitrage. They '
        'supply a great deal of [[Liquidity]] in normal conditions and can withdraw it under stress, '
        'which is the [[Liquidity]] illusion the chapter warns about. If an execution schedule is '
        'predictable they can trade ahead of it, so predictability is itself [[Information Leakage]].'),
    'concept:high-volatility-regime': (
        'A market state of large daily moves and persistent direction, conventionally marked by VIX '
        'above 25 to 30.',
        'Correlations rise together as everything trades risk-on or risk-off, so the diversification '
        'that worked in calm stops working. Momentum and trend-following do well and mean reversion '
        "suffers. The chapter's guidance is to cut position size and leverage here rather than to "
        'change the strategy.'),
    'concept:iceberg-order': (
        'A large order that displays only part of its size at a time, refreshing the visible slice as '
        'each one fills, so the book never shows how much is really there.',
        'Showing full size is itself information: a resting order for ten thousand shares tells '
        'everyone a large buyer is present and roughly what they will pay, and the market prices that '
        'before the order is done. The iceberg withholds it. The cost is queue position, since each '
        'refreshed slice goes to the back of its price level, so it trades speed for concealment. It '
        'exists to reduce [[Information Leakage]] and with it [[Market Impact]].'),
    'concept:information-asymmetry': (
        'The unequal distribution of information among participants, where some know more about an '
        "asset's value than the person on the other side of their trade.",
        'It is the reason a quote is not free. A [[Market Makers]] cannot tell an informed '
        'counterparty from an uninformed one, so it widens the [[Bid-Ask Spread]] to cover the losses '
        'it will take against the informed ones. Every participant class in the chapter sits '
        'somewhere on this gradient, which is what makes [[Market Participants]] worth classifying at '
        'all.'),
    'concept:information-leakage': (
        "The extent to which an order reveals a trader's intentions to the rest of the market before "
        'it is finished.',
        'Order types differ in how much they leak, and the difference is priced: once other '
        'participants can infer that size is coming, they move ahead of it and the remaining fills '
        'get worse. [[Iceberg Order]] and [[Dark Pools]] are the two answers the chapter gives, one '
        'hiding size in a lit book and the other moving the order off it. Leakage is the mechanism by '
        'which [[Information Asymmetry]] turns into a cost you pay.'),
    'concept:institutional-investor': (
        'Mutual funds, pension funds, insurance companies and endowments, trading large positions on '
        'long horizons.',
        'Size is their defining constraint: a position large enough to matter is large enough to move '
        'the price, so execution has to be spread over time. That is what makes [[Market Impact]] '
        'their central cost and why [[Dark Pools]] and schedule algorithms like [[VWAP]] exist. Their '
        'repositioning is visible in volume patterns, which is why other participants watch for it.'),
    'concept:internalization': (
        'A broker filling a customer order from its own inventory instead of sending it to an '
        'exchange.',
        'It avoids exchange fees and can be faster, and it puts the broker on the other side of its '
        'own customer -- which is why best-execution obligations exist and why the practice is '
        'scrutinised. The order never reaches a public book, so it contributes nothing to [[Price '
        'Discovery]].'),
    'concept:limit-order': (
        'An instruction to trade only at a stated price or better.',
        'The price is certain and execution is not. While it rests unfilled it is displayed liquidity '
        'that someone else can trade against, which makes the limit order the instrument by which '
        'ordinary participants supply [[Liquidity]] rather than consume it. It is also how a trader '
        'avoids paying the whole [[Bid-Ask Spread]].'),
    'concept:liquidity': (
        'The ease with which an asset can be bought or sold without materially moving its price.',
        'High liquidity shows up as a tight [[Bid-Ask Spread]], a deep book and small [[Market '
        'Impact]] -- three symptoms of one condition. It is not constant: it varies by time of day '
        'and by regime, and displayed size often disappears when it is tested, so the book overstates '
        'what is really available. Everything about execution cost follows from it.'),
    'concept:lit-exchange': (
        'Venues with full pre-trade transparency: the order book is visible and matching follows '
        'price-time priority.',
        'Because everyone can see resting size, they are where [[Price Discovery]] mostly happens -- '
        'and for the same reason they are where a large order leaks the most. Regulatory oversight '
        'and surveillance are part of the package.'),
    'concept:low-volatility-regime': (
        'A market state of tight ranges and mean-reverting price action, conventionally marked by VIX '
        'below 15.',
        'Correlations between assets are low, so diversification actually works. Carry and short-'
        'volatility strategies do well and trend-following underperforms, because there is no '
        'sustained direction to follow. It is the state in which risk looks cheapest and is being '
        'accumulated.'),
    'concept:market-efficiency': (
        'The degree to which prices already reflect the available information, set by how fast and '
        'how accurately price discovery works.',
        'Efficiency is a matter of degree and speed rather than a yes or no. It depends on market '
        'structure: fragmented venues, wide spreads and thin books all slow the incorporation of '
        'information. [[Arbitrageurs]] are the participants whose trading enforces it, and [[Price '
        'Discovery]] is the process it grades.'),
    'concept:market-impact': (
        "The effect a trader's own order has on the price, caused by consuming the liquidity that was "
        'there.',
        'It grows faster than linearly with size, so doubling an order more than doubles the damage '
        '-- which is the entire argument for breaking orders up and for [[VWAP]] and [[TWAP]] '
        'schedules. Part of it reverses once the order stops (temporary) and part persists because '
        'the market has learned something (permanent). Working slower reduces it but exposes the '
        'order to price movement, and that trade-off is what [[Implementation Shortfall]] tries to '
        'optimise.'),
    'concept:market-maker': (
        'Participants who quote both sides continuously, earning the spread in exchange for standing '
        'ready to trade.',
        'The [[Bid-Ask Spread]] is their compensation for two risks: holding inventory that may fall '
        'in value, and trading against someone who knows more. They widen the quote when they suspect '
        'the second, which is why spreads open up around uncertainty. Competition among them is what '
        'narrows the quote back down. In exchange markets the obligation to keep quoting is formal, '
        'which makes them the supply side of [[Liquidity]].'),
    'concept:market-microstructure': (
        'The study of how the specific rules, protocols and institutional arrangements of a market '
        'turn orders into trades and trades into prices.',
        'It is a field rather than a market object, and the chapter opens with it because everything '
        'below is one of its subjects: [[Price Discovery]], [[Order Flow]], [[Information '
        'Asymmetry]], [[Transaction Costs]] and [[Market Efficiency]]. Its practical claim is that '
        "the venue's design changes the outcome, so two identical strategies on two venues do not "
        'earn the same amount.'),
    'concept:market-order': (
        'An instruction to trade immediately at the best price currently available.',
        'Execution is certain and the price is not: the order walks the book until it is filled, so '
        'in a thin market the average fill can be far from the quote. It is the order type that pays '
        'the full [[Bid-Ask Spread]] and generates the most [[Slippage]], which is why the chapter '
        'advises using it only when speed genuinely matters. A triggered [[Stop Order]] becomes one '
        'of these.'),
    'concept:market-participant': (
        'The individuals, institutions and firms buying and selling in a market, each with distinct '
        'motives, time horizons and information.',
        "The chapter's claim is that who is trading changes how the market behaves. Motives differ -- "
        'speculation, hedging, liquidity provision, arbitrage -- and so do horizons, from the '
        'microseconds of [[High-Frequency Traders]] to the years of [[Institutional Investors]]. The '
        'relationship is adversarial in one direction only: informed participants profit from '
        'uninformed ones, which is [[Information Asymmetry]] seen from the participant side.'),
    'concept:market-regime': (
        'Distinct periods in which volatility, trend behaviour and correlation structure are '
        'characteristically different.',
        'A regime is a persistent state rather than a mood: markets stay in one until a catalyst '
        'moves them, which is why a strategy can work for a year and then stop. The chapter names two '
        'by their volatility, [[Low Volatility Regime]] and [[High Volatility Regime]], and '
        'correlations behave differently in each -- they compress in calm and converge in stress, so '
        'diversification fails exactly when it is needed.'),
    'concept:order-flow': (
        'The sequence and volume of buy and sell orders arriving at a market, which is what drives '
        'price over short horizons.',
        'Flow is directional information before it is price: a run of buy orders consumes the offers '
        'and lifts the quote. Because the size and sequence of orders reveals intent, flow is both '
        'the raw material of [[Price Discovery]] and the reason [[Information Leakage]] costs money. '
        '[[Market Impact]] is what your own contribution to the flow does to the price you get.'),
    'concept:order-type': (
        'The instructions a trader gives a market about how a trade should be executed: what price is '
        'acceptable, when it should trigger, and how much of it to reveal.',
        'Every order type buys one thing at the price of another. [[Market Order]] buys certainty of '
        'execution with uncertainty of price; [[Limit Order]] does the reverse. [[Stop Order]] and '
        '[[Stop-Limit Order]] add a trigger condition; [[Trailing Stop]] moves that trigger with the '
        'price; [[Iceberg Order]] buys concealment with queue position. Choosing among them is '
        'choosing which risk to keep.'),
    'concept:over-the-counter-market': (
        'Bilateral markets where dealers trade directly with each other or with clients rather than '
        'through an exchange.',
        'Terms are negotiable rather than standardised, which is what makes them the home of bonds, '
        'many derivatives and FX. The cost of that flexibility is counterparty risk and less price '
        'transparency, since there is no central book to look at.'),
    'concept:price-discovery': (
        'The process by which a market price is determined, as buyers and sellers interact and their '
        'orders are continuously matched.',
        'Prices are not announced, they are discovered. Each match moves the price a little, so the '
        'sequence of trades is the mechanism by which dispersed information becomes one number. It '
        'runs through [[Auction-Based Discovery]] at the open and close, [[Continuous Trading '
        'Discovery]] during the session, and [[Cross-Market Discovery]] between related instruments. '
        'How fast it works is what [[Market Efficiency]] measures.'),
    'concept:proprietary-trading-firm': (
        'Firms trading their own capital, systematically or discretionarily, with no external '
        'investors to answer to.',
        'The absence of client money removes the constraints that shape [[Institutional Investors]] '
        '-- no redemption risk, no mandate, no reporting horizon -- which lets them specialise '
        'narrowly. Some operate at the speed of [[High-Frequency Traders]] and others on much longer '
        'systematic horizons.'),
    'concept:regime-shift': (
        'The transition from one market regime to another, triggered by a change in fundamentals, '
        'sentiment or structure.',
        'Central bank policy, geopolitics, credit events and data surprises are the usual catalysts. '
        'The practical problem is asymmetry of speed: the shift happens faster than any detector '
        'recognises it, so a strategy that switches on a detected regime is always switching late. '
        'That argues for deciding in advance what to do rather than reacting.'),
    'concept:retail-trader': (
        'Individuals trading their own accounts, typically in small size and over longer holding '
        'periods.',
        'They tend to be net takers of [[Liquidity]] rather than providers of it, and they lean on '
        'technical analysis and are prone to behavioural bias. Their size rarely causes [[Market '
        'Impact]], which means the costs that dominate for them are the [[Bid-Ask Spread]] and '
        '[[Slippage]] rather than the impact of their own flow.'),
    'concept:slippage': (
        'The difference between the price a trade was expected to get and the price it actually got.',
        'It comes from two sources that are worth separating: the market moving while the order '
        'works, and the book being too thin to fill it at the quote. The second is [[Liquidity]] and '
        "is partly under the trader's control through sizing and timing; the first is not. Because a "
        'backtest fills at a price nobody was offering, slippage assumptions are what make simulated '
        'results comparable to real ones.'),
    'concept:stop-limit-order': (
        'A stop order that becomes a limit order rather than a market order when triggered.',
        'It bounds the fill price at the cost of possibly not filling at all -- exactly the risk a '
        'plain [[Stop Order]] avoids and exactly the protection it lacks. The chapter recommends it '
        'in volatile conditions, where the distance a triggered market order can travel is largest.'),
    'concept:stop-order': (
        'A resting instruction that becomes a market order once the price reaches a trigger level.',
        'The trigger is certain; the fill is not, because once triggered it is a [[Market Order]] and '
        'takes whatever the book offers. In a fast market that gap can be large, which is the failure '
        'mode the chapter warns about. Used below a position it caps loss, used above it enters on a '
        'breakout.'),
    'concept:trading-venue': (
        'The platforms and marketplaces where instruments trade: exchanges, alternative trading '
        'systems and over-the-counter markets.',
        'Modern markets are fragmented across many of them, which is why routing is a decision at '
        'all. They differ along a transparency spectrum from fully lit to fully dark, in latency, and '
        'in the regulation they operate under. Brokers are obliged to seek the best price across '
        'them, which is what makes fragmentation tractable rather than chaotic.'),
    'concept:trailing-stop': (
        'A stop whose trigger level follows the price at a fixed distance, moving only in the '
        'favourable direction.',
        'It converts a static exit into a ratchet: as the position gains, the stop rises behind it '
        'and locks in part of the move, but it never retreats. The distance is the whole design '
        'decision, and setting it from [[Volatility]] rather than from a round percentage is what '
        'makes it survive normal noise.'),
    'concept:transaction-cost': (
        'The total cost of trading: explicit costs such as commissions and fees, plus implicit costs '
        'such as the spread, market impact and timing.',
        'The implicit half is usually the larger one and is invisible on a statement. Crossing the '
        '[[Bid-Ask Spread]] is a cost, [[Slippage]] is a cost, and [[Market Impact]] is a cost you '
        'inflict on yourself. A strategy evaluated without them is being measured against a market '
        'that does not exist.'),
    'procedure:garch-model': (
        "A model that forecasts next period's variance from the last shock and the last variance.",
        'It is the formal statement of two facts about [[Volatility]] -- that shocks persist and that '
        'variance reverts to a long-run level -- with one parameter for each plus a weight on the '
        'long-run term. It is a model you run rather than a quantity you read off the tape, which is '
        'what separates it from [[Historical Volatility]].'),
    'procedure:implementation-shortfall': (
        'An execution schedule that balances market impact against the risk of the price moving while '
        'the order works.',
        'It is the explicit statement of the urgency-cost trade-off: going fast costs [[Market '
        'Impact]], going slow costs drift, and the optimum depends on volatility and order size. '
        'Where [[TWAP]] and [[VWAP]] follow a fixed rule, this one solves for a schedule.'),
    'procedure:indicator-atr': (
        "The smoothed average of the true range, where true range is the largest of the bar's own "
        'span and its two gaps from the previous close.',
        "Including the gaps is the point: a bar that opens away from yesterday's close has moved "
        "further than its high minus its low admits. It is expressed in the instrument's own price "
        'units, so it sizes stops and positions directly but does not compare across instruments.'),
    'procedure:indicator-vwap': (
        'An execution schedule that trades in proportion to market volume, so participation tracks '
        "the day's own profile.",
        'Trading more when the market is busy and less when it is thin keeps [[Participation Rate]] '
        'roughly constant, which is the quantity [[Market Impact]] actually responds to. The name is '
        'shared with the volume-weighted average price itself -- the benchmark the schedule is trying '
        'to match -- and the library implements that price series as an indicator.'),
    'procedure:twap': (
        'An execution schedule that splits an order evenly across a time window.',
        'It makes no attempt to predict volume: it just spreads participation so no single moment '
        'carries the whole order, which limits [[Market Impact]] at the cost of exposure to price '
        'drift over the window. Its evenness is also its weakness, since it trades the same amount in '
        'thin periods as in thick ones.'),
    'property:effective-spread': (
        'Twice the distance between the trade price and the midpoint at the time -- the spread '
        'actually paid.',
        'It measures the cost that was really incurred rather than the one advertised, and it differs '
        'from [[Quoted Spread]] whenever a trade fills inside the quote or walks through it. It is '
        'the honest input to a [[Transaction Costs]] calculation.'),
    'property:historical-volatility': (
        'The realised dispersion of returns over a window, the standard deviation of returns scaled '
        'to a common horizon.',
        'It is what volatility actually was, not what it is expected to be, and annualising it by the '
        'square root of the number of periods is what makes two windows comparable. Being backward-'
        'looking it reacts to a regime change only after the fact, which is the gap [[GARCH]] and '
        '[[Volatility Ratio]] try to close.'),
    'property:participation-rate': (
        'Order size as a fraction of the volume traded over the execution window -- how much of the '
        "market's activity is you.",
        "It is the practical control on [[Market Impact]]: the chapter's guidance is to stay under "
        'roughly ten per cent of average daily volume, because impact scales with the share of flow '
        'you represent rather than with the absolute size. It is computed as order size divided by '
        'average daily volume times the duration in days.'),
    'property:quoted-spread': (
        'Ask minus bid -- the spread as displayed, before anyone trades.',
        'It is the headline number and the one that overstates what a patient trader pays, since a '
        'limit order need not cross it at all. Expressed as a fraction of the midpoint it becomes '
        'comparable across instruments at different price levels.'),
    'property:realized-spread': (
        'Twice the signed distance between the trade price and the midpoint some interval later -- '
        'what the market maker kept.',
        'Comparing it with [[Effective Spread]] separates the two halves of the spread: what the '
        'liquidity provider earned, and what it lost to price movement against it. The difference is '
        'the cost of [[Information Asymmetry]], measured rather than assumed.'),
    'property:volatility-ratio': (
        'The dispersion of returns for a security or index, conventionally measured as their standard '
        'deviation or variance.',
        'It behaves in ways that make it forecastable even though returns are not: it clusters, so '
        'high volatility follows high volatility; it reverts to a long-run average; and it rises more '
        'on down moves than up ones. Those regularities are what [[GARCH]] models. It is measured '
        'historically by [[Historical Volatility]], per bar by [[Average True Range]], and its change '
        'by [[Volatility Ratio]].'),

    # --- 02 instruments & market mechanics -------------------------------------------------------
    # The chapter explains most instruments through a priced example -- "AAPL Call, Strike $180,
    # Premium $3.50" -- which says what one contract cost on one day and not what a call option is.
    # Those examples are kept; these are the definitions they illustrate.
    'concept:automated-market-maker': (
        'A venue that prices trades from a formula over a pool of deposited reserves rather than by '
        'matching orders against a book.',
        'The pool always quotes, so there is no waiting for a counterparty, and the price walks along '
        'the curve as the reserves shift -- which is why size costs more here than in a book of '
        'comparable depth. Liquidity comes from depositors who earn the fees and carry '
        '[[Impermanent Loss]] against simply holding the two assets.'),
    'concept:call-option': (
        'The right, not the obligation, to buy the underlying at the strike price on or before '
        'expiration.',
        'The buyer risks only the premium and keeps everything above the strike, which is the '
        'asymmetry that makes an option a defined-risk way to hold a directional view. The seller has '
        'the mirror image: the premium is the most that can be made and the loss above the strike is '
        'unbounded unless the underlying is already held.'),
    'concept:central-counterparty': (
        'An entity that steps between the two sides of a trade, becoming buyer to the seller and '
        'seller to the buyer so that neither depends on the other.',
        'It converts a web of bilateral exposures into exposures to one guaranteed party, which is '
        'what makes anonymous trading and [[Netting]] possible at all. The guarantee is paid for with '
        'margin, and it concentrates the risk it removes -- the CCP is the party that must not fail.'),
    'concept:centralized-exchange': (
        'A crypto venue that holds customer assets and matches orders on its own book, off chain.',
        'It offers the deepest liquidity and the fastest matching in the asset class, at the cost of '
        'custody: the balance is the exchange\'s promise rather than a key you hold. Access is gated '
        'by identity checks, and settlement is an entry in an internal ledger until a withdrawal '
        'takes it on chain.'),
    'concept:clearing': (
        'Validating and matching a trade after execution, and netting the obligations it creates, so '
        'that it is ready to settle.',
        'It is the step between agreeing a trade and exchanging value, and its main economy is '
        'netting: many gross obligations collapse into one net amount per party, so far less cash and '
        'stock needs to move. Where a [[Central Counterparty]] clears, it also guarantees the '
        'obligations it has netted.'),
    'concept:commodity-spot-market': (
        'The market for immediate purchase of a physical commodity, at the price for prompt delivery.',
        'Ownership here is of a physical thing, so the cost of holding it -- storage, insurance, '
        'financing -- is real and shows up in the [[Cost of Carry Relationship]] between spot and '
        'futures. Settlement conventions vary with the commodity, and delivery can be taken or the '
        'position held in a vault.'),
    'concept:concentrated-liquidity': (
        'An AMM design in which a provider supplies liquidity only across a chosen price range '
        'instead of the whole curve.',
        'Capital sitting where price never trades earns nothing, so restricting the range multiplies '
        'the fees earned per unit deposited. The cost is that the position must be managed: once '
        'price leaves the range the position stops earning and is left entirely in one of the two '
        'assets.'),
    'concept:contract-specification': (
        'The standardised terms of a derivative contract -- size, tick increment, expiration and '
        'settlement method.',
        'The specification is what makes one contract fungible with another and is the arithmetic '
        'behind every position calculation: [[Notional Value]], [[Tick Value]] and margin all follow '
        'from the multiplier and the tick. Getting it wrong misstates exposure by whatever factor the '
        'multiplier is.'),
    'concept:crypto-settlement': (
        'Settlement of a crypto trade, either as an entry in an exchange ledger or as a confirmed '
        'transaction on a blockchain.',
        'The two are different in kind. On a centralized venue the trade settles instantly because '
        'nothing leaves the exchange; on chain, finality waits on block confirmation and costs a '
        'network fee. A withdrawal is where the internal ledger becomes an on-chain fact.'),
    'concept:crypto-specific-mechanics': (
        'The trading infrastructure particular to digital assets: continuous markets, self-custody, '
        'on-chain settlement and pool-based venues.',
        'What sets the asset class apart is not the price behaviour but the plumbing. Markets never '
        'close, so there is no opening auction and no overnight gap; assets can be held directly, so '
        'counterparty risk is a choice; and settlement is a blockchain fact with a fee and a '
        'confirmation time attached.'),
    'concept:cryptocurrency-spot-market': (
        'The market for immediate purchase of a cryptocurrency, settling on the blockchain or within '
        'an exchange ledger.',
        'Settlement is close to immediate and the asset can be withdrawn to a wallet the holder '
        'controls, which is the feature the asset class is built around. Trading runs continuously, '
        'so a position is exposed at every hour rather than only during a session.'),
    'concept:decentralized-exchange': (
        'A crypto venue where trades execute against a smart contract and assets stay in the '
        "trader's own custody throughout.",
        'Nothing is deposited with an operator and nothing is gated by identity checks, which is what '
        'permissionless access means in practice. The costs are network fees on every interaction and '
        'exposure to having the trade front-run by whoever orders the block.'),
    'concept:equity-settlement': (
        'Transfer of shares and cash two business days after an equity trade is executed.',
        'The gap between trade date and settlement date is why the cash for a purchase must be there '
        'later than the trade suggests, and why an entitlement such as a dividend depends on which '
        'date the holder is recorded on.'),
    'concept:equity-spot-market': (
        'The market for immediate purchase of shares, conveying ownership of the company.',
        'The buyer receives the full rights of a shareholder -- dividends, votes, corporate actions '
        '-- which is the difference between holding stock and holding a derivative on it. Settlement '
        'takes two business days.'),
    'concept:forex-spot-market': (
        'The market for immediate exchange of one currency for another at the prevailing rate.',
        'Every price is a ratio of two currencies rather than the price of a thing, so a position is '
        'always long one and short the other. Major pairs settle two business days out, and holding '
        'past the close pays or receives the interest differential between them.'),
    'concept:futures': (
        'A standardised contract to buy or sell an asset at an agreed price on a stated future date.',
        'The obligation is symmetric -- unlike an [[Option]], both sides must perform -- and the '
        'position is marked to market daily, so profit and loss are paid as they accrue rather than '
        'at expiration. Because only margin is posted, a small deposit controls a large notional, and '
        'the price converges on spot as expiration approaches.'),
    'concept:futures-settlement': (
        'Daily exchange of variation margin against the marked price, with a final settlement at '
        'expiration.',
        'A futures position is settled continuously rather than once: each day the gain or loss moves '
        'in cash, which is what keeps the exposure of the clearing house bounded. The final settlement '
        'is in cash or in delivery, depending on the contract.'),
    'concept:fx': (
        'The global market for exchanging currencies, the largest and most liquid market there is.',
        'It runs around the clock through overlapping regional sessions, with liquidity concentrated '
        'where they overlap, and prices are driven by the policy and rate expectations of the two '
        'central banks behind the pair. Its conventions -- pairs, pips, lots -- are what the '
        'arithmetic of a position rests on.'),
    'concept:greeks': (
        'The family of sensitivities of an option price: to the underlying, to the rate of that '
        'sensitivity, to time, to volatility and to interest rates.',
        'Together they say how a position will behave when something changes, which is the whole of '
        'options risk management: delta is directional exposure, gamma how fast it moves, theta the '
        'daily cost of holding, vega exposure to a change in implied volatility, and rho to rates. '
        'They are the reason an option position cannot be managed by direction alone.'),
    'concept:leverage': (
        'The ratio of position size to the capital backing it.',
        'It amplifies the return on capital in both directions by the same factor, which is why the '
        'move that liquidates a position gets smaller as leverage rises: at five times, a twenty per '
        'cent adverse move is the whole margin. What it buys is capital efficiency, not edge.'),
    'concept:liquidation-engine': (
        'The exchange system that closes a position automatically once its margin falls below the '
        'maintenance requirement.',
        'It exists to stop an account going negative and taking the venue with it, so it acts on the '
        'exchange\'s schedule rather than the trader\'s: the position is closed at whatever the book '
        'offers, in the conditions that caused the shortfall. A stop placed above the liquidation '
        'price is the trader keeping that decision.'),
    'concept:margin': (
        'Collateral posted against a position: an initial amount to open it and a maintenance amount '
        'to keep it.',
        'It is a performance bond rather than a payment, and the gap between the two thresholds is '
        'the whole of the buffer -- once equity falls through the maintenance level the '
        '[[Liquidation Engine]] acts. Held across the account it cushions more, and exposes more; '
        'isolated to one position it caps the loss at that position.'),
    'concept:option': (
        'A contract conveying the right, but not the obligation, to buy or sell the underlying at a '
        'stated strike price by a stated expiration.',
        'The asymmetry is the point: the buyer can lose only the premium while the payoff above the '
        'strike is open-ended, which makes an option the instrument for a view with a defined worst '
        'case. That optionality is paid for in time value, which decays every day and vanishes at '
        'expiration, and is priced from volatility rather than from direction.'),
    'concept:perpetual-swap': (
        'A futures-like contract with no expiration, held to the spot price by a periodic funding '
        'payment between longs and shorts.',
        'Without an expiration there is no convergence to enforce the price, so funding does it: when '
        'the contract trades above spot, longs pay shorts and the premium is arbitraged away. It is '
        'the dominant crypto derivative, and the funding rate is a running cost or income on a '
        'position rather than a detail of it.'),
    'concept:put-option': (
        'The right, not the obligation, to sell the underlying at the strike price on or before '
        'expiration.',
        'It pays as the underlying falls, bounded by a price of zero, which makes it the direct way '
        'to insure a holding: the premium is the cost of the insurance and the strike is the level '
        'insured. The seller is paid that premium to stand ready to buy at the strike.'),
    'concept:settlement': (
        'The transfer of securities and cash that completes a trade and moves ownership.',
        'A trade is an agreement; settlement is the moment it becomes ownership, and the delay '
        'between the two is what a settlement cycle names. Exchanging both legs simultaneously is '
        'what removes the risk of paying and receiving nothing.'),
    'concept:spot-market': (
        'A market where an instrument is bought and sold for immediate delivery at the current price.',
        'What is traded is the asset itself rather than a claim on it later, so there is no '
        'expiration to manage and the holder has the full rights of ownership. The spot price is the '
        'reference every derivative is priced against, through the [[Cost of Carry Relationship]].'),

    # --- 02 formulas -----------------------------------------------------------------------------
    'fact:constant-product-amm': (
        'The invariant of a constant-product pool: the product of the two reserves is unchanged by a '
        'trade.',
        'Holding the product constant is what defines the price at every point on the curve, and it '
        'is why the price moves against the trader as size grows -- the curve steepens as one reserve '
        'is drawn down. The output for a given input follows from the invariant alone.'),
    'fact:cost-of-carry-relationship': (
        'The fair price of a forward or future is the spot price carried forward at the financing '
        'rate net of any yield the asset pays.',
        'It is an arbitrage identity rather than a forecast: if the future strays from it, the trade '
        'is to buy one leg, sell the other and hold to expiration. It explains contango and '
        'backwardation as facts about rates, storage and convenience yield rather than as opinions '
        'about direction, and it is the same identity §2.2 restates as F = S * e^((r - y) * T).'),
    'fact:put-call-parity': (
        'The identity linking a call and a put at the same strike and expiration to the underlying '
        'and a discounted bond.',
        'It holds by arbitrage, so it fixes each of the four prices in terms of the other three: an '
        'option can be replicated synthetically, and a violation is a riskless trade rather than a '
        'view. It is also the check that an implied volatility surface is internally consistent.'),
    'procedure:black-scholes-call-price': (
        'Prices a European call from the spot price, strike, time to expiration, interest rate and '
        'volatility.',
        'Every input but one is observable, which is what makes the model useful in reverse: quoted '
        'against a market price it returns implied volatility, the number options actually trade on. '
        'Its assumptions -- constant volatility, continuous hedging, no jumps -- are why the surface '
        'is not flat in practice.'),
    'property:amm-price-impact': (
        'How far a trade moves the price of a constant-product pool, as a share of the reserve it '
        'trades against.',
        'It follows from the size of the trade relative to the pool and from nothing else -- no '
        'queue, no counterparty, no time of day -- which makes execution cost on an AMM entirely '
        'predictable before the trade. It is a different quantity from the order-book '
        '[[Price Impact]] of chapter one, which measures how a book responds to order flow.'),
    'property:annualized-basis': (
        'The basis expressed as an annual rate, scaled by the days remaining to expiration.',
        'It is what makes two contracts with different expirations comparable, and it turns the basis '
        'into the yield of a cash-and-carry trade: buy spot, sell the future, and collect it to '
        'expiration.'),
    'property:basis': (
        'The difference between the futures price and the spot price, in price terms or as a '
        'percentage of spot.',
        'It carries the market\'s financing and storage costs and converges to zero at expiration, '
        'which is what makes it tradeable in its own right. Positive is contango, negative is '
        'backwardation, and the sign is information about supply rather than about direction.'),
    'property:concentrated-liquidity-efficiency': (
        'The real reserves a concentrated position must hold to provide a given depth over its chosen '
        'price range.',
        'Narrowing the range means the same depth is supplied by less capital, which is the whole '
        'gain of the design and the reason the position must be watched: outside the range it '
        'provides no depth at all.'),
    'property:cross-rate': (
        'The rate between two currencies derived from each of their rates against a common third.',
        'Most pairs are quoted against the dollar, so a rate between two others is implied by the two '
        'quotes; when the implied and quoted rates differ, the difference is a triangular arbitrage.'),
    'property:exposure-at-default': (
        'What would be owed if a counterparty failed now: the cost of replacing the position plus '
        'what it could still move against you.',
        'It is the number margin is sized against, and it is forward-looking on purpose -- the '
        'replacement cost at the moment of default is not the exposure, because the position must be '
        'reopened into whatever market caused the default.'),
    'property:forward-rate': (
        'The exchange rate for a future date implied by the interest rates of the two currencies.',
        'Interest rate parity fixes it: the forward must offset the rate differential exactly, or '
        'borrowing in one currency and lending in the other would be riskless profit. It is also why '
        'a carry trade earns the differential only if the spot rate does not move to erase it.'),
    'property:impermanent-loss': (
        'The shortfall of a liquidity position against simply holding the two assets, caused by the '
        'pool rebalancing as their relative price moves.',
        'The pool sells the asset that rises and buys the one that falls, so any divergence leaves '
        'the provider with less than the holder; it is called impermanent because it reverses if the '
        'price ratio returns. Fees are what has to cover it for provision to be worthwhile.'),
    'property:intrinsic-and-time-value': (
        'The split of an option premium into what it would be worth if exercised now and what is paid '
        'for the time remaining.',
        'Intrinsic value is arithmetic on the strike and the spot price; everything above it is the '
        'market\'s price for uncertainty, and it decays to nothing by expiration. The split is what '
        'separates a directional gain from the cost of waiting for one.'),
    'property:leverage-ratio': (
        'Position size divided by the capital backing it; effective leverage compares notional '
        'exposure with account equity.',
        'The two differ once there is more than one position or unrealised profit and loss, and the '
        'effective figure is the one that governs risk. It is the multiplier on both return and loss, '
        'and it sets how far price can move before the margin is gone.'),
    'property:long-position-liquidation-price': (
        'The price at which a long position\'s equity falls to the maintenance requirement and it is '
        'closed automatically.',
        'It follows from entry price and the two margin percentages, so it is knowable before the '
        'position is opened -- which is what makes it the first calculation rather than a surprise. '
        'Fees and funding move it closer over time.'),
    'property:margin-ratio': (
        'Maintenance margin required as a share of account equity.',
        'It is the single number that says how close a position is to being closed out: at a hundred '
        'per cent the [[Liquidation Engine]] acts. Watching it is how leverage is managed in practice, '
        'because it moves with price, with funding and with the margin the venue demands in '
        'volatility.'),
    'property:margin-requirement': (
        'The collateral needed to open a position, as a percentage of its notional value.',
        'It is set by the venue rather than the trader and rises when volatility does, so the capital '
        'a position needs is not constant -- a requirement raised mid-position must be met from the '
        'same account that is already losing.'),
    'property:netting-benefit': (
        'How much of a set of gross obligations disappears once offsetting positions are netted.',
        'It is the efficiency clearing exists to produce: the cash and stock that must actually move '
        'is the net, not the gross, and the ratio between them is what a clearing house is measured '
        'on.'),
    'property:notional-value': (
        'The value a contract controls: multiplier times price times the number of contracts.',
        'It is the exposure, as distinct from the margin posted against it, and the two are confused '
        'at the trader\'s expense -- risk is a share of notional while capital is a share of margin. '
        'Every position calculation starts here.'),
    'property:perpetual-funding-rate': (
        'The periodic payment between longs and shorts on a perpetual contract, proportional to '
        'position value.',
        'It is the mechanism that substitutes for expiration: a positive rate means the contract is '
        'above spot and longs pay to hold, which draws in the arbitrage that closes the premium. As a '
        'running cost it can exceed the move being traded, and as a signal it says which side is '
        'crowded.'),
    'property:pip-value': (
        'What one pip of movement is worth in the quote currency, for a given lot size.',
        'It is what turns a rate move into money, and it depends on the pair and the lot rather than '
        'being a constant: sizing an FX position without it is sizing by rate rather than by risk.'),
    'property:position-profit-loss': (
        'The gain or loss on a position: the distance price travelled, valued at what one unit of '
        'movement is worth.',
        'The two conventions in the chapter are the same arithmetic in different units -- FX values '
        'the move in pips times pip value, futures in ticks times [[Tick Value]] times contracts -- '
        'and both reduce to price distance times value per unit times size.'),
    'property:return-amplification': (
        'The return on capital under leverage: the underlying return multiplied by the leverage used.',
        'It is symmetric, which is the part that gets forgotten -- five times leverage turns a two per '
        'cent move into ten per cent in whichever direction it goes, and a twenty per cent adverse '
        'move into the whole account.'),
    'property:short-position-liquidation-price': (
        'The price at which a short position\'s equity falls to the maintenance requirement and it is '
        'closed automatically.',
        'The arithmetic mirrors the long case, but the exposure does not: a short loses as price '
        'rises, and price can rise without bound, so the distance to liquidation is the whole of the '
        'protection.'),
    'property:spot-return': (
        'The change in price over a period, as a simple percentage or as a log return.',
        'The two are not interchangeable: simple returns aggregate across positions in a portfolio, '
        'log returns aggregate across time and are what volatility and most models are computed on.'),
    'property:swap-rollover-calculation': (
        'The interest paid or received for holding an FX position overnight, from the rate '
        'differential between the two currencies.',
        'It is the carry in a carry trade, applied nightly: long the higher-yielding currency earns '
        'it, and the reverse pays it. Over a long hold it can dominate the price move it was meant to '
        'accompany.'),
    'property:tick-value': (
        'What one minimum price increment is worth: tick size times the contract multiplier.',
        'It is the unit every futures profit and loss is counted in, and the reason two contracts on '
        'the same underlying can carry very different risk per point of index movement.'),
    'property:total-return': (
        'The return of a holding including the income it pays, not only its change in price.',
        'Price return understates what a dividend-paying holding earned and misstates any comparison '
        'against an instrument that pays nothing; it is also the yield term that shows up in the '
        '[[Cost of Carry Relationship]].'),

    # --- 03 core trading concepts ----------------------------------------------------------------
    # This chapter characterises most things by what they look like on a chart -- "moving averages
    # flat and intertwined" -- which tells a reader how to recognise one and not what it is. The
    # characterisation is kept; these are the definitions beside them.
    'concept:accumulation-pattern': (
        'Sideways price with volume weighted towards up days -- the footprint of a buyer working a '
        'large order without moving the price.',
        'The tell is effort without result in one direction only: [[On-Balance Volume]] rises while '
        'price stays flat. It is read as a large participant building a position quietly, and it '
        'ends when the range breaks upward.'),
    'concept:bearish-fair-value-gap': (
        'A three-candle imbalance where the third candle\'s high stays below the first candle\'s '
        'low, leaving a band price fell through without trading.',
        'The gap is where selling was so one-sided that no two-way trade happened, and price often '
        'returns to it before continuing down. The band runs from the first low to the third high.'),
    'concept:break-of-structure': (
        'Price closing beyond the most recent swing point in the direction of the trend.',
        'It is the continuation signal: the sequence of higher highs and higher lows extends rather '
        'than fails, which is what distinguishes it from a [[Change of Character]]. It is also where '
        'the invalidation level for the position moves to.'),
    'concept:buy-side-liquidity': (
        'Resting buy orders above the market -- the stops of short positions and the entry orders of '
        'breakout buyers.',
        'It sits where everyone can see it: above swing highs and above [[Equal Highs and Lows]]. '
        'That visibility is the point, because a large seller needs buyers to sell into, and this is '
        'where they are.'),
    'concept:bullish-fair-value-gap': (
        'A three-candle imbalance where the third candle\'s low stays above the first candle\'s '
        'high, leaving a band price rose through without trading.',
        'It marks delivery too fast to be two-sided, and the market tends to return and trade the '
        'band before continuing up. The band runs from the first high to the third low.'),
    'concept:change-of-character': (
        'Price breaking structure against the prevailing trend -- the first break that does not fit '
        'the sequence.',
        'It is a warning rather than a reversal: the trend has stopped extending, which is not yet '
        'the same as turning. Treating it as an entry rather than as notice to tighten is the '
        'mistake the chapter warns about.'),
    'concept:climactic-volume': (
        'A volume spike several times normal at a price extreme.',
        'It reads as exhaustion rather than confirmation: everyone who was going to act has acted, '
        'and there is no one left to continue the move. The same magnitude in the middle of a range '
        'means nothing of the kind.'),
    'concept:compression': (
        'A phase of contracting range and falling volatility.',
        'Ranges narrow, bands squeeze and volume dries up while the market waits. It resolves into '
        '[[Expansion]], which is why compression is read as a setup rather than as a state to trade '
        'inside.'),
    'concept:confluence': (
        'Several independent methods marking the same price or the same moment.',
        'What earns the extra confidence is the independence: a moving average, a prior swing and a '
        'retracement level agreeing say more together than any of them repeated. It raises the odds '
        'and settles nothing on its own, which is why the chapter pairs it with position sizing '
        'rather than with certainty.'),
    'concept:demand-zone': (
        'The base a strong rally departed from, taken to hold buying that was never filled.',
        'The claim is about the origin of the move rather than the number of touches, which is what '
        'separates it from [[Support and Resistance]]. It is strongest untested, and it weakens each '
        'time price returns to it.'),
    'concept:distribution-pattern': (
        'Sideways price with volume weighted towards down days -- a large seller working out of a '
        'position near the highs.',
        'It is the mirror of [[Accumulation Pattern]]: [[On-Balance Volume]] falls while price holds '
        'up, and the range usually breaks down. Price alone shows nothing, which is the reason to '
        'look at volume at all.'),
    'concept:dynamic-level': (
        'A support or resistance level that moves with price: a moving average, a trend line, VWAP, '
        'a band.',
        'It is the same idea as a horizontal level with a different anchor -- the level is computed '
        'from recent price rather than fixed at one -- and it is why the same instrument can respect '
        'a rising line it never touched at a fixed price.'),
    'concept:equal-highs-and-lows': (
        'Two or more touches at the same level, which is where stops collect.',
        'The obviousness is what makes them liquidity: every trader who drew the same line put a '
        'stop just beyond it. The chapter\'s advice follows from that -- expect the level to be '
        'swept before any real move, and place stops past it rather than at it.'),
    'concept:expansion': (
        'A phase of widening range and rising volatility.',
        'Directional candles, rising [[Average True Range]] and rising volume: this is where trends '
        'begin and resume, and where a strategy fitted to the quiet phase before it stops working.'),
    'concept:fair-value-gap': (
        'A band of price that one impulsive move passed through without two-sided trade.',
        'The market treats it as unfinished business and tends to return to it, which makes it a '
        'target for a pullback entry and a magnet for price that has run too far. A gap that is '
        'filled has done its work; an unfilled one is still pulling.'),
    'concept:high-volume-node': (
        'A price level where a lot of volume has traded.',
        'Business done at a price is agreement about value, and price tends to slow there, which is '
        'why these act as support and resistance without being drawn from swings.'),
    'concept:horizontal-level': (
        'A support or resistance level fixed at a price -- a prior swing, a level tested repeatedly, '
        'a round number, a high-volume node.',
        'It holds because enough participants remember the same price, which is also why it stops '
        'holding once everyone has traded around it.'),
    'concept:liquidity-grab': (
        'A quick move into a pool of resting orders followed immediately by a reversal.',
        'It is how a large order gets filled without paying for the whole move: the stops it '
        'triggers supply the other side. Read as a breakout it is a loss; read as a sweep it is the '
        'entry.'),
    'concept:liquidity-pool': (
        'A cluster of resting orders -- stops and pending entries -- at a level everyone can see.',
        'Price is drawn towards them because that is where size can be filled, which inverts the '
        'naive reading of a level: the obvious stop is not protection but a target.'),
    'concept:low-volume-node': (
        'A price level where little volume has traded.',
        'Little business means little agreement, so price crosses these quickly rather than settling '
        'in them -- which makes them poor targets and good places to expect acceleration.'),
    'concept:market-structure': (
        'The arrangement of swing highs and lows that says whether a market is trending or ranging.',
        'It gives trend a definition that can be checked rather than eyeballed: higher highs with '
        'higher lows, or lower lows with lower highs, and neither in a range. Because it is defined '
        'by swings it repeats at every timeframe, and it supplies the level at which a position is '
        'wrong -- the structural point whose break invalidates the read.'),
    'concept:multi-timeframe-analysis': (
        'Reading the same market on several timeframes, taking context from the higher and timing '
        'from the lower.',
        'The higher timeframe wins where they disagree, because more participants and more capital '
        'are expressed in it. Working downward -- trend, then level, then trigger -- is what stops a '
        'good entry being taken against the move that matters.'),
    'concept:point-of-control': (
        'The price with the most volume traded in a session -- where the most business was done.',
        'It is the session\'s fairest price by the market\'s own vote, and price returns to it '
        'during balanced trade, which makes it a better target than an entry.'),
    'concept:ranging-market': (
        'A market oscillating between a floor and a ceiling, making no directional progress.',
        'Moving averages flatten and cross, and [[ADX]] sits below twenty. Mean reversion is what '
        'works here and trend following is what bleeds, which is the whole reason to classify the '
        'state before choosing the strategy.'),
    'concept:sell-side-liquidity': (
        'Resting sell orders below the market -- the stops of long positions and the entry orders of '
        'breakdown sellers.',
        'It gathers under swing lows and under [[Equal Highs and Lows]], and it is where a large '
        'buyer finds the size to buy.'),
    'concept:smart-money-concept': (
        'The reading of price as the footprint of participants large enough to need other people\'s '
        'orders to fill their own.',
        'The claim is mechanical rather than conspiratorial: size cannot be filled where there is no '
        'liquidity, so it is filled where the stops are. Whether the label is right, the constraint '
        'it names is real.'),
    'concept:stop-hunt': (
        'A move that runs the stops clustered at an obvious level and then turns.',
        'It is [[Liquidity Grab]] seen from the side of the trader who was stopped out, and it is '
        'the argument for placing stops past the obvious level rather than on it.'),
    'concept:supply-demand-zone': (
        'The area a strong impulsive move began from, expected to matter again when price returns.',
        'It is defined by the origin of a move rather than by how often a level has been touched, '
        'which is what distinguishes it from [[Support and Resistance]]. Fresh zones are the claim; '
        'a zone tested twice has spent whatever imbalance it held.'),
    'concept:supply-zone': (
        'The base a strong decline departed from, taken to hold selling that was never filled.',
        'The mirror of [[Demand Zone]]: the stronger and faster the move away, the stronger the '
        'claim that unfilled orders remain behind it.'),
    'concept:support-and-resistance': (
        'Price levels where buying or selling has repeatedly been strong enough to stop a move.',
        'They work because participants remember them and act again at the same price, which is why '
        'a broken level reverses role: the buyers defending it become the sellers trapped above it. '
        'They are zones rather than lines, and their weight comes from the timeframe they were drawn '
        'on and how strongly price reacted before.'),
    'concept:trending-market': (
        'A market making higher highs and higher lows, or lower lows and lower highs, with pullbacks '
        'shallow against the moves that make them.',
        'Moving averages separate and slope, and [[ADX]] holds above twenty-five. This is where '
        'trend following and momentum work and where mean reversion is most dangerous, because the '
        'reversion it waits for does not come.'),
    'concept:value-area-high': (
        'The upper edge of the range holding roughly seventy per cent of a session\'s volume.',
        'It is the boundary between accepted value and price the market has rejected, so a session '
        'opening above it is making a directional statement rather than rotating.'),
    'concept:value-area-low': (
        'The lower edge of the range holding roughly seventy per cent of a session\'s volume.',
        'Together with [[Value Area High]] it bounds where business was done, and both act as levels '
        'in the next session for the same reason a [[High Volume Node]] does.'),
    'concept:volume': (
        'How much traded in a period -- the amount of activity behind a price move.',
        'It is the second dimension of every move: the same distance travelled on twice the volume '
        'is a different event, because more participants had to agree to produce it. Comparing '
        'effort against result is what separates a move that will hold from one that will not.'),
    'concept:volume-confirmation': (
        'The requirement that a breakout come with above-average volume before it is believed.',
        'A move on thin volume is a move few people took part in, and those are the breakouts that '
        'fail back into the range. Requiring it costs some genuine breakouts and avoids most false '
        'ones.'),
    'concept:volume-divergence': (
        'Price making new extremes while volume does not follow.',
        'Participation is draining out of the move even as it continues, which is a warning rather '
        'than a signal: divergences persist far longer than they look like they should.'),
    'concept:volume-profile': (
        'The distribution of traded volume across price rather than across time.',
        'It answers a different question from a chart of price over time: not where price went, but '
        'where business was actually done. From it come the [[Point of Control]] and the value area, '
        'and with them the auction reading of a market -- price advertises, volume accepts or '
        'rejects, and value migrates when one side keeps making progress.'),
    'fact:risk-is-multi-dimensional': (
        'Risk is not one number: per-trade exposure, the skew of the strategy, its fit to the '
        'regime, drawdown, tail losses and correlation are each a separate one.',
        'They are independent, which is the part that gets missed -- tightening a stop lowers the '
        'first and leaves the second untouched. A mean reversion strategy with small losses still '
        'holds a large one, and positions that look diversified converge exactly when it matters.'),
    'fact:regime-determines-archetype-effectiveness': (
        'Which family of strategy works is decided by the regime, not by the strategy.',
        'Trend following and momentum earn in a strong trend and bleed in a range; mean reversion '
        'does the reverse. Breakouts need volatility and carry needs quiet. So the regime is read '
        'first and the archetype chosen second -- applying one without that read is a bet on the '
        'market being in the state the strategy happens to need.'),
    'fact:timeframe-ratio': (
        'Timeframes are worth watching together when each is roughly four to six times the one '
        'below it.',
        'Closer than that and the two show the same thing twice; further apart and the lower gives '
        'no context for the higher. Daily against four-hour is six to one; four-hour against hourly '
        'is four to one.'),
    'procedure:adx-trend-strength': (
        'Classifies the market as trending, ranging or transitional from the level of [[ADX]].',
        'Above twenty-five is a trend, below twenty is a range, and between them is the state in '
        'which most strategies are least reliable. It measures how strong a trend is and says '
        'nothing about which way it points.'),
    'procedure:bearish-fvg-detection': (
        'Detects a bearish gap: the third candle\'s high below the first candle\'s low.',
        'The two bounding prices become the zone, and its size is what the significance filter is '
        'applied to.'),
    'procedure:bullish-fvg-detection': (
        'Detects a bullish gap: the third candle\'s low above the first candle\'s high.',
        'Three candles are enough because the imbalance is defined by the outer two failing to '
        'overlap -- the middle candle is the impulse that caused it.'),
    'procedure:equal-level-detection': (
        'Finds highs or lows matching within a tolerance -- the levels where stops gather.',
        'The tolerance is what makes it usable: exact equality almost never occurs, and a level a '
        'few ticks apart is the same level to everyone looking at it.'),
    'procedure:fvg-fill-status': (
        'Classifies a gap as unfilled, partially filled or filled by how far price has traded back '
        'through it.',
        'The status is what makes a gap tradeable or spent: an unfilled gap is still a target, and a '
        'filled one is history.'),
    'procedure:fvg-validity': (
        'Keeps only gaps larger than half the [[Average True Range]].',
        'Every noisy series produces small gaps constantly; without a size filter the chart fills '
        'with them and none of them mean anything.'),
    'procedure:liquidity-zone-identification': (
        'Places the buy-side and sell-side pools a fraction of an [[Average True Range]] beyond the '
        'recent swing high and low.',
        'The buffer is the point: stops sit past the level rather than on it, so the zone that gets '
        'swept is above the high rather than at it.'),
    'procedure:structure-break-detection': (
        'Marks a break of structure when a close passes the previous swing high or low.',
        'On the close rather than on the wick, which is what separates a structural break from a '
        'sweep of the same level.'),
    'procedure:swing-point-identification': (
        'Marks a bar as a swing high or low when it exceeds the bars either side of it.',
        'It is the primitive the rest of the chapter is built on: structure, liquidity pools and '
        'zones are all defined in terms of swings, so the lookback chosen here sets what everything '
        'downstream calls a trend.'),
    'procedure:trend-classification': (
        'Classifies the market as up, down or ranging by comparing consecutive swing highs and lows.',
        'It turns "the trend is up" into something two people can check and agree on, and it returns '
        'a range whenever the two conditions disagree rather than guessing.'),
    'procedure:value-area-calculation': (
        'Grows a range outward from the [[Point of Control]], taking the busier side each step, '
        'until it holds seventy per cent of the volume.',
        'Building outward from the busiest price is what makes the area an observation about where '
        'business was done rather than a standard deviation of a distribution nobody checked was '
        'normal.'),
    'procedure:volume-profile': (
        'Sums traded volume at each price level and takes the busiest as the point of control.',
        'This is the computation behind the profile: bin by price rather than by time, and the shape '
        'that results is where the levels come from.'),
    'procedure:zone-identification': (
        'Marks the consolidation before an impulsive move as a zone, valid when the departure '
        'exceeds twice the [[Average True Range]].',
        'The size test is what keeps every pause from becoming a zone; the base itself is bounded by '
        'the extreme of the consolidation and the last body before the move.'),
    'property:atr-percentage': (
        'The [[Average True Range]] as a percentage of price.',
        'Expressing range against price is what makes two instruments comparable, and its direction '
        'is the objective form of [[Compression]] and [[Expansion]].'),
    'property:bollinger-band-width': (
        'The distance between the bands as a fraction of the middle band.',
        'It is the standard measure of a squeeze: low and falling is compression, rising is the '
        'expansion that follows it.'),
    'property:candle-body-size': (
        'The anatomy of one bar -- body, upper and lower wick, range, and the body as a share of the '
        'range.',
        'It is what the reading of a single candle reduces to: a large body is agreement through the '
        'period, a long wick is a price the market visited and rejected.'),
    'property:confluence-score': (
        'The weighted count of independent factors agreeing at one level.',
        'Weighting is what stops five weak agreements outranking one strong one; the chapter\'s '
        'weights put a higher-timeframe level at three and a round number at one.'),
    'property:level-strength-score': (
        'How much weight a level carries, from the number of touches, the timeframes it appears on '
        'and the volume traded there.',
        'It makes explicit what is usually a judgement call, so that two levels can be ranked '
        'instead of both being drawn and treated alike.'),
    'property:order-flow-delta': (
        'Buy volume minus sell volume, and its running total.',
        'Volume says how much traded; delta says which side was the aggressor. A rising price on '
        'negative cumulative delta is a move being sold into, which is invisible in volume alone.'),
    'property:pivot-point': (
        'A level derived from the previous period\'s high, low and close, with supports and '
        'resistances stepped out from it.',
        'The value is not in the arithmetic but in how many participants compute the same numbers '
        'from the same bar, which is what makes them levels at all.'),
    'property:range-ratio': (
        'The current range against the average range of recent periods.',
        'Below half is compression and above one and a half is expansion, which turns the phase of '
        'the volatility cycle into a number rather than an impression.'),
    'property:relative-volume': (
        'Current volume against the average for the same period.',
        'Absolute volume says nothing without its own baseline: above one and a half is real '
        'participation, and it is the objective form of the confirmation the chapter demands of a '
        'breakout.'),
    'property:support-resistance-zone-width': (
        'How wide to draw a level, scaled to the [[Average True Range]].',
        'Drawing a zone rather than a line is what accommodates the wicks that pierce every level; '
        'scaling it to volatility is what keeps one instrument\'s zone from being another\'s noise.'),
    'property:trend-alignment-score': (
        'The weighted sum of each timeframe\'s direction, scored plus one, minus one or zero.',
        'It reduces the multi-timeframe read to one number, which is what the chapter\'s "two of '
        'three must agree" rule is checking.'),
    'property:volume-profile-metric': (
        'The width of the value area, in price and as a share of the session range.',
        'A narrow value area against a wide session says the market spent its time in one place and '
        'travelled through the rest -- a directional day. A wide one says it rotated.'),
    'property:zone-freshness': (
        'How many times price has already traded into a zone.',
        'Untouched is the whole claim: the orders presumed to rest there are filled by the first '
        'test, so a second visit is weaker and a third is not worth taking.'),
    'property:zone-overlap': (
        'The intersection of the individual zones a level is made of.',
        'It is what turns several near-agreements into one tradeable area, and it is only high '
        'confluence if the overlap is tighter than an [[Average True Range]] and at least three '
        'factors are in it.'),
}

#: Typed I/O for a chapter's stated formulas, in the shape the 71 code-derived indicators use. The
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
FORMULA_IO = {
    "property:quoted-spread": (
        {"bid": "highest price a buyer will pay", "ask": "lowest price a seller will accept"},
        {"quoted_spread": {**PRICE, "range": [0, None], "canonical_name": "Quoted Spread"}}),
    "property:relative-spread": (
        {"bid": "highest price a buyer will pay", "ask": "lowest price a seller will accept"},
        {"relative_spread": {"type": "series", "units": "percent", "range": [0, None],
                             "canonical_name": "Relative Spread"}}),
    "property:effective-spread": (
        {"trade_price": "price actually paid or received", "midpoint": "(bid + ask) / 2 at the time"},
        {"effective_spread": {**PRICE, "range": [0, None], "canonical_name": "Effective Spread"}}),
    "property:realized-spread": (
        {"trade_price": "price actually paid or received",
         "midpoint_after": "midpoint a fixed interval after the trade",
         "direction": "+1 buyer-initiated, -1 seller-initiated"},
        {"realized_spread": {**PRICE, "range": [None, None],
                             "canonical_name": "Realized Spread"}}),
    "property:simple-slippage": (
        {"execution_price": "average price actually filled", "expected_price": "price expected"},
        {"slippage": {**PRICE, "range": [None, None], "canonical_name": "Slippage"},
         "slippage_pct": {"type": "series", "units": "percent", "range": [None, None]}}),
    "property:price-impact": (
        {"order_flow": "signed order flow over the interval",
         "lam": "market price sensitivity to order flow (Kyle lambda)"},
        {"delta_p": {**PRICE, "range": [None, None], "canonical_name": "Price Impact"}}),
    "procedure:almgren-chriss-market-impact-model": (
        {"order_size": "shares or contracts to execute", "adv": "average daily volume",
         "sigma": "daily volatility", "eta": "temporary-impact coefficient",
         "gamma": "permanent-impact coefficient"},
        {"temporary_impact": {**PRICE, "range": [0, None]},
         "permanent_impact": {**PRICE, "range": [0, None]}}),
    "fact:square-root-market-impact-rule": (
        {"order_size": "shares or contracts to execute", "adv": "average daily volume",
         "sigma": "daily volatility"},
        {"impact": {**PRICE, "range": [0, None], "canonical_name": "Square-Root Impact"}}),
    "property:participation-rate": (
        {"order_size": "shares or contracts to execute", "adv": "average daily volume",
         "duration_days": "execution horizon in days"},
        {"participation_rate": {"type": "series", "units": "fraction", "range": [0, 1],
                                "canonical_name": "Participation Rate"}}),
    "property:historical-volatility": (
        {"returns": "periodic returns series", "periods": "periods per year for annualisation"},
        {"sigma": {"type": "series", "units": "fraction", "range": [0, None],
                   "canonical_name": "Historical Volatility"}}),
    "procedure:garch-model": (
        {"returns": "periodic returns series", "omega": "long-run variance weight",
         "alpha": "reaction to recent shocks", "beta": "persistence of volatility"},
        {"sigma2": {"type": "series", "units": "variance", "range": [0, None],
                    "canonical_name": "Conditional Variance"}}),
    "property:volatility-ratio": (
        {"short_vol": "short-window volatility", "long_vol": "long-window volatility"},
        {"vol_ratio": {"type": "series", "units": "ratio", "range": [0, None],
                       "canonical_name": "Volatility Ratio"}}),
    "property:information-share": (
        {"variance_contribution": "variance of this market's contribution to the efficient price",
         "variance_total": "variance of the total efficient price"},
        {"information_share": {"type": "series", "units": "fraction", "range": [0, 1],
                               "canonical_name": "Information Share"}}),
    "property:component-share": (
        {"permanent_impact_market": "permanent price impact from this market",
         "permanent_impact_total": "total permanent price impact"},
        {"component_share": {"type": "series", "units": "fraction", "range": [0, 1],
                             "canonical_name": "Component Share"}}),
    "property:price-efficiency-ratio": (
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
                  "dynamics", "mechanisms", "basics"}

#: A category node is singular: one `market maker`, not `market makers`. The chapter titles its
#: sections and example blocks in the plural because they head a list.
IRREGULAR = {"mechanics": "mechanics", "analysis": "analysis", "series": "series",
             "venues": "venue", "networks": "network",
             # Not plurals. "Basis" and "Greeks" are the terms themselves, and a futures contract
             # is "futures" -- a `future` is a different word. Stripping the s invented three terms
             # nobody uses: `basi`, `greek`, `future`.
             "basis": "basis", "greeks": "greeks", "futures": "futures",
             # "Status" is not a plural either; it was becoming `statu`.
             "status": "status",
             # Nor is "bias": chapter 4's five named biases were becoming `look-ahead-bia`,
             # `survivorship-bia` and `selection-bia`.
             "bias": "bias"}


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


#: A summary the chapter gave as a worked instance rather than a definition -- "Instruction: buy
#: 100 shares", "AAPL Call, Strike $180". It belongs in `examples`, not in the summary slot, and it
#: is not a competing definition to be preserved beside the real one.
_ILLUSTRATION = ("instruction:", "buy ", "sell ", "own ", "purchase ")


def _same_claim(a: str, b: str) -> bool:
    """Two wordings of one statement. The dedupe half of the outer join.

    "the ease with which an asset can be bought or sold without significantly affecting its price"
    against "...without materially moving its price" is one definition twice, and keeping both as
    rival wordings is noise presented as a conflict.
    """
    def toks(s):
        return {w for w in re.sub(r"[^a-z0-9 ]", " ", s.lower()).split() if len(w) > 3}
    x, y = toks(a), toks(b)
    return bool(x and y) and len(x & y) / max(len(x), len(y)) >= 0.6


def _is_illustration(text: str) -> bool:
    low = text.strip().lower()
    return low.startswith(_ILLUSTRATION) or "$" in text[:80]


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

#: A bullet or a numbered step. §3.7 and §3.10 walk a zone and a gap through numbered steps rather
#: than bullets, and reading only the bullets dropped every one of those blocks -- four concepts the
#: chapter defines, and nothing said so.
ITEM = re.compile(r"^(?:-|\d+\.)\s+")


def split_block(body: list[str]) -> tuple[str, str]:
    """Return (definition, illustration) for one Examples sub-block.

    Blocks that draw the distinction explicitly (the order types) are split on the prefix. Blocks
    that do not (the participant and venue taxonomies) are wholly definitional -- every bullet says
    what the thing is -- so the illustration is empty rather than guessed at."""
    define, show = [], []
    for line in body:
        s = line.strip()
        if not ITEM.match(s):
            continue
        s = ITEM.sub("", s).strip()
        low = s.lower()
        if low.startswith(ILLUSTRATIVE):
            show.append(s)
        elif low.startswith(DEFINITIONAL):
            define.append(s.split(":", 1)[1].strip().strip('"'))
        else:
            define.append(s)
    return " ".join(define), " ".join(show)


#: `**Label:** text on the same line` -- the shape §3.0 states a claim in, as against the
#: `**Label:**` on a line of its own that Examples and Formulas use.
INLINE_LABEL = re.compile(r"^\*\*(.+?):?\*\*:?\s*(.*)$")


#: The first line of a python docstring -- what the recipe says it does. Chapter 4 states its rules
#: as functions rather than as prose, and every one of them is documented: `"""Exit on fixed
#: percentage loss"""` is the definition of a fixed stop, in the chapter's own words.
_DOCSTRING = re.compile(r'"""\s*(.*?)\s*"""', re.S)


def docstring_of(code: str) -> str:
    if not (m := _DOCSTRING.search(code)):
        return ""
    lines = [l.strip() for l in m.group(1).splitlines() if l.strip()]
    return lines[0].rstrip(".") if lines else ""


def unfenced(lines: list[str]) -> list[str]:
    """Everything outside the code fences."""
    out, inside = [], False
    for line in lines:
        if line.strip().startswith("```"):
            inside = not inside
            continue
        if not inside:
            out.append(line)
    return out


def free_block(lines: list[str], definition_labels: tuple[str, ...] = ("definition",)) -> dict:
    """A block that follows no scaffold, read for the five things such a block ever holds.

    §3.0 states each piece of market wisdom as a definition, a list of reasons, sometimes a table
    and sometimes a warning in a blockquote -- and the warning is the part that matters most
    ("do NOT describe mean reversion as safer"). Reading only the bullets would drop it.

    Chapter 4 states most of its content as python. The code is the rule and belongs in `formula`,
    the way a stated equation does; read as prose it became a summary reading
    "def fixed_stop_exit(entry_price, current_price, stop_pct=0.02, direction='long'):".
    """
    out: dict = {}
    code, doc = code_of(lines), ""
    if code:
        out["formula"] = code
        doc = docstring_of(code)
    bullet_lines, quote, rows, prose = [], [], [], []
    for raw in unfenced(lines):
        s = raw.strip()
        if not s:
            continue
        if m := INLINE_LABEL.match(s):
            label, rest = m.group(1).strip(), m.group(2).strip()
            # Which label carries the definition is the chapter's choice: §3.0 writes
            # `**Definition:**`, §4.2 writes `**Core Premise:**`. Read as an ordinary label the
            # premise became the summary with its own label glued to the front of it.
            if label.lower() in definition_labels and rest:
                out["summary"] = rest
            elif rest:
                prose.append(f"{label}: {rest}")
            continue
        if s.startswith(">"):
            quote.append(s.lstrip("> ").strip().replace("**", ""))
        elif s.startswith("|"):
            if set(s) <= set("|- :"):
                continue
            cells = [c.strip().replace("**", "") for c in s.strip("|").split("|")]
            rows.append(" · ".join(c for c in cells if c))
        elif s.startswith("-"):
            bullet_lines.append(s.lstrip("- ").strip())
        else:
            prose.append(s.replace("**", ""))
    # What the block says it is, in order of how directly it says it: the label the chapter uses
    # for a definition, then the docstring of the rule it states, then its opening prose, then its
    # first bullet -- "Using information not available at trade time" is what look-ahead bias IS,
    # and read as one more reason among five it left the node with no summary at all.
    if not out.get("summary"):
        if doc:
            out["summary"] = doc
        elif prose:
            out["summary"] = prose.pop(0)
        elif bullet_lines:
            out["summary"] = bullet_lines.pop(0)
    if bullet_lines:
        out["explanation"] = " ".join(bullet_lines)
    if rows:
        out["comparison"] = rows
    if quote:
        out["caution"] = " ".join(quote)
    if prose:
        out["notes"] = prose
    return out


def block_text(lines: list[str]) -> str:
    """Everything a block says, code fences and all -- for a block nothing else claims."""
    return " ".join(l.strip() for l in lines if l.strip() and not l.strip().startswith("```"))


def table_rows(lines: list[str]) -> list[tuple[str, str]]:
    """`| name | ... |` rows as (name, the rest joined). Rule rows and the header are skipped.

    The header is the FIRST row, by position. Naming the header cells that had been seen so far
    read "Style", "Archetype" and "Type" as members, and a taxonomy whose first kind is `concept:style`
    looks like a real node in every count. Cell emphasis is markup: `| **Entry** |` names the same
    thing as `| Entry |`, and keeping the stars puts them in the id.
    """
    out = []
    for line in lines:
        s = line.strip()
        if not s.startswith("|") or set(s) <= set("|- :"):
            continue
        cells = [c.strip().replace("**", "") for c in s.strip("|").split("|")]
        if len(cells) < 2:
            continue
        out.append((cells[0], ". ".join(c for c in cells[1:] if c)))
    return out[1:]


def code_of(lines: list[str]) -> str:
    inside, out = False, []
    for line in lines:
        if line.strip().startswith("```"):
            inside = not inside
            continue
        if inside:
            out.append(line)
    return "\n".join(out).strip()


#: What the formula path writes when the chapter states a formula and no definition: "The quantity
#: effective spread." is a label, not a wording worth keeping when a real one displaces it.
_GENERATED_SUMMARY = ("The quantity ", "The identity ", "Computes ", "The family ")

#: A name appearing in more than this share of the GRAPH is ordinary vocabulary rather than a
#: reference to one node: `signal` is in 289 of 571 nodes, `strategy` 98, `indicator` 95, against
#: `stop loss` at 12 and `transaction cost` at 3. Measured over the whole graph and not over the
#: chapter, which is the mistake that let "reveal your strategy to sophisticated participants" draw
#: an edge to `schema:strategy`: a hundred statements are far too small a corpus to tell a common
#: noun from a name. Same corpus-derived rule the query layer uses for stop words, no hand list.
GENERIC_SHARE = 0.05

#: An abbreviation is short by construction and still unambiguous -- ATR, OBV, VWAP. Everything
#: else has to be long enough that a chance substring is not a match.
MIN_ALIAS, MIN_ABBREVIATION = 6, 3


def _norm(text: str) -> str:
    """Space-padded, punctuation-free, for whole-word containment. "stop-loss" and "stop loss" are
    the same term, and the padding is what stops `entry` matching inside `re-entry`."""
    return f" {re.sub(r'[^a-z0-9]+', ' ', text.lower()).strip()} "


def aliases_of(node: dict) -> set[str]:
    """Every name a statement might call this node by.

    A title carries more than one: `stop order (stop-loss)` is called both, and the parenthetical is
    usually the one prose uses -- "always have a stop-loss for every position" names that node and
    matches neither the id nor the full title.
    """
    out: set[str] = set()
    if title := " ".join((node.get("title") or "").split()).lower():
        out.add(title)
        out.add(" ".join(re.sub(r"\(.*?\)", " ", title).split()))
        out.update(" ".join(m.split()) for m in re.findall(r"\((.*?)\)", title))
    out = {a for a in out if len(a) >= MIN_ALIAS}
    if isinstance(abbr := node.get("props", {}).get("abbreviation"), str):
        if len(abbr) >= MIN_ABBREVIATION:
            out.add(abbr.lower())
    return out


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
        nid = decl.get("rename", {}).get(title) or f"{kind.lower()}:{slug(title)}"
        # The code-derived builder owns `procedure:indicator-*`, one node per indicator class, and
        # anything counting indicators counts that prefix. A chapter minting an id inside it makes
        # a trading rule indistinguishable from a library indicator.
        if nid.startswith("procedure:indicator-") and nid not in existing:
            raise ValueError(
                f"{title!r} would take {nid!r}, inside the library's indicator namespace. Declare a "
                "`rename` that leads with something else.")
        # A heading is written to head a section, not to name a node: "Trending Market
        # Characteristics" heads a list of them. `rename` fixes the id; this fixes what it is called.
        title = decl.get("retitle", {}).get(title, title)
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
        summary = " ".join(summary.split())
        if summary and summary != cur["summary"]:
            # Whichever wording loses is still something the chapter says. §4.1 characterises
            # scalping in a block and again in the comparison table, and the row -- being longer --
            # was replacing "Best For: full-time traders with direct market access" with nothing.
            loser = cur["summary"] if len(summary) > len(cur["summary"]) else summary
            if loser and not loser.startswith(_GENERATED_SUMMARY):
                notes = cur["props"].setdefault("notes", [])
                if loser not in notes:
                    notes.append(loser)
        if len(summary) > len(cur["summary"]):
            cur["summary"] = summary
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
        kind of VOLATILITY rather than of market regime. Match on the label's head noun, then on any
        other word in it -- "Long Position Liquidation Price" heads on `price`, which names nothing,
        while `liquidation` names the subject exactly. Fall back to the first subject only when
        nothing matches, which is the single-subject case anyway.

        `formula_subject` overrides both, for a label that names its subject nowhere in itself:
        "Return Amplification" is about leverage and says so only in the formula body.
        """
        if declared := decl.get("formula_subject", {}).get(label):
            return declared
        if len(subjects) == 1:
            return subjects[0]
        head = head_noun(label)
        words = [w for w in slug(re.sub(r"\(.*?\)", " ", label)).split("-") if w]
        for candidate in ([head] if head else []) + list(reversed(words)):
            for sid in subjects:
                if candidate in sid.split(":", 1)[1].split("-"):
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
        if src == dst:
            # A section that defines the subject the whole chapter hangs off -- §3.1 defines price
            # action, and price action is the chapter's parent -- would otherwise be part of itself.
            return
        if not any(r["from_id"] == src and r["rel"] == relation and r["to_id"] == dst for r in rels):
            rels.append({"from": name_of(src), "rel": relation, "to": name_of(dst),
                         "why": why, "from_id": src, "to_id": dst})

    principles, practices = [], []
    deferred_uses: dict[str, list[str]] = {}
    def_labels = tuple(l.lower() for l in decl.get("definition_labels", ("Definition",)))

    for num, sec in sorted(sections.items()):
        blocks = sec["blocks"]
        definition = blocks.get("Definition", [])
        defined = bullets([l for l in definition if BULLET.match(l)])
        prose = " ".join(l.strip() for l in definition
                         if l.strip() and not l.strip().startswith("-")).replace("**", "")
        use_bullets = bullets(blocks.get("Common Use Cases", []))
        # §1.2 labels each use case with the order type it belongs to. Flattening them onto the
        # section subject gave `order-type` five sentences and left every member with none.
        per_member = {name: text for name, text in use_bullets if name}
        uses = [text for name, text in use_bullets if not name]

        # Blocks this chapter declares to be nodes in their own right. §3.0 states four pieces of
        # market wisdom under headings of their own, with no Definition block and no subject: each
        # is a claim about how trading behaves, not a thing the section is about.
        as_nodes = decl.get("blocks_as_nodes", {}).get(sec["title"], {})
        for heading in as_nodes:
            if heading not in blocks:
                raise ValueError(f"`blocks_as_nodes` names {heading!r}, which {sec['title']!r} "
                                 "does not contain -- reworded?")

        # The section's subject(s). Bolded bullets mean the section defines several things and has
        # no single subject; prose means the section IS about one thing, named by its own heading.
        # A section with no Definition at all has no subject: it is a container for its blocks, and
        # every one of them must be declared or the chapter refuses to build.
        if defined:
            subjects = [atom("Concept", name, text, _section=num) for name, text in defined]
        elif not definition and as_nodes:
            undeclared = [h for h in blocks if h not in as_nodes and h not in SCAFFOLD]
            if undeclared:
                raise ValueError(f"{sec['title']!r} has no Definition and no subject to hang "
                                 f"{undeclared} on -- declare them in `blocks_as_nodes`")
            subjects = []
        else:
            subjects = [atom("Concept", sec["title"], prose, applications=uses, _section=num)]
        for s in subjects:
            # The section's NAME, not its number. `§1.1` records a position in a file; the graph
            # holds what a thing is and where it is defined, and "market microstructure" says that.
            rel(s, "part-of", parent, f"defined under {sec['title'].lower()}")
        for heading, primitive in as_nodes.items():
            read = free_block(blocks[heading], def_labels)
            nid = atom(primitive, heading, read.pop("summary", ""), _section=num, **read)
            rel(nid, "part-of", parent, f"stated under {sec['title'].lower()}")
            # §3.0's blocks had no subject to point at, so this edge never existed. §4.6 heads a
            # rule "Time-Based Exits" inside a section about exit logic, and without it the rule was
            # reachable only by walking down from the chapter.
            for sub in ({subject_for(heading, subjects)} if subjects else set()) - {nid}:
                rel(nid, "about", sub, f"stated under {sec['title'].lower()}")

        for label, text in per_member.items():
            deferred_uses.setdefault(f"concept:{slug(label)}", []).append(text)

        # Chapter 4 writes its rules as `**Label:**` sub-blocks inside a heading, where earlier
        # chapters wrote a heading per rule. Left whole, a heading holds eight named things as one
        # string: the ADX regime rule cannot fold onto the identical rule chapter 3 already states,
        # and an ATR stop cannot say which indicator it reads. Declaring the labels promotes them.
        for heading, labels in decl.get("labelled_nodes", {}).items():
            if heading not in blocks:
                continue
            found = labelled_blocks(blocks[heading])
            if undeclared := [l for l, _ in found if l not in labels]:
                raise ValueError(f"{heading!r} states {undeclared}, which `labelled_nodes` does "
                                 "not name -- declare them, or the heading keeps them whole")
            for label, body in found:
                read = free_block(body, def_labels)
                nid = atom(labels[label], label, read.pop("summary", ""), _section=num, **read)
                rel(nid, "part-of", parent, f"stated under {sec['title'].lower()}")
                # The same two edges the principle-concepts get: `part-of` is scope, `about` is
                # what the thing concerns. A fixed stop is about exit logic, not about the chapter.
                for sub in ({subject_for(label, subjects)} if subjects else set()) - {nid}:
                    rel(nid, "about", sub, f"stated under {heading.lower()}")

        if defined and uses:
            # The section's subject may have folded into a node already in the graph, in which case
            # its use cases are an enrichment rather than a property of something new. Dropping them
            # would lose the section's Common Use Cases without saying so.
            if subjects[0] in atoms:
                atoms[subjects[0]]["props"].setdefault("applications", uses)
            else:
                extra.setdefault(subjects[0], {}).setdefault("applications", uses)

        for name, text in bullets(blocks.get("Core Principles", [])):
            prim = decl.get("principle_concepts", {}).get(name)
            if prim:
                # A definition, not a claim: it becomes the thing it defines.
                cid = atom(prim.capitalize(), name, text, _section=num)
                rel(cid, "part-of", parent, f"defined under {sec['title'].lower()}")
                # TWO edges, saying two different things. `part-of` the chapter is scope -- which
                # subject area holds the term, and what `under=` walks. This one is subject: a
                # liquidity pool is about LIQUIDITY, not about price action in general, and without
                # it the route from liquidity to the sweep that empties it ran up to the chapter
                # node and back down. `about` rather than `part-of` because the chapter says these
                # concern the subject; it does not say they constitute it.
                for sub in ({subject_for(name, subjects)} if subjects else set()) - {cid}:
                    rel(cid, "about", sub, f"stated as a principle of {name_of(sub)}")
                continue
            principles.append(f"{name}: {text}" if name else text)
        # Every heading that advises, not only the one worded "for Traders": §3.11 titles its list
        # "Best Practices for Volume Profile" and six practices were being dropped for it.
        for heading, body in blocks.items():
            if heading.startswith("Best Practices"):
                for name, text in bullets(body):
                    # Same shape as a principle. Dropping the bolded name lost what the practice is
                    # CALLED -- "Layer signals intentionally" -- and kept only its elaboration.
                    practices.append(f"{name}: {text}" if name else text)

        if sec["title"] in decl["taxonomy"]:
            for label, body in labelled_blocks(blocks.get("Examples", [])):
                if label in NOT_A_KIND:
                    # Not a kind, but not rubbish either -- "Regime Shift Triggers" lists what
                    # causes a shift. Kept on the subject rather than discarded.
                    txt = " ".join(ITEM.sub("", b.strip()).strip() for b in body
                                   if ITEM.match(b.strip()))
                    if txt:
                        target = subject_for(label, subjects)
                        (atoms[target]["props"].setdefault("examples", []).append(f"{label}: {txt}")
                         if target in atoms else
                         extra.setdefault(target, {}).setdefault("examples", []).append(f"{label}: {txt}"))
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
                # Bullets AND anything fenced: §3.2 draws its uptrend as ASCII art inside a code
                # block, and reading only the bullets kept the caption and dropped the picture.
                text = " ".join([ITEM.sub("", b.strip()).strip()
                                 for b in body if ITEM.match(b.strip())]
                                + ([code_of(body)] if code_of(body) else []))
                if not text.strip():
                    continue
                key = slug(re.sub(r"\bexample\b", "", label, flags=re.I))
                target = next((s for s in subjects if s.endswith(f":{key}")), subjects[0])
                if target in atoms:
                    atoms[target]["props"].setdefault("examples", []).append(f"{label}: {text}")
                else:
                    extra.setdefault(target, {}).setdefault("examples", []).append(
                        f"{label}: {text}")

        for heading, spec in decl.get("tables", {}).items():
            target, relation, primitive = (*spec, "Procedure")[:3]
            for name, rest in table_rows(blocks.get(heading, [])):
                if name in NOT_A_KIND:
                    continue
                nid = atom(primitive, name, rest, _generated=True, _section=num)
                rel(nid, relation, target, f"listed under {heading.lower()}")

        for heading, columns in decl.get("table_properties", {}).items():
            for name, rest in table_rows(blocks.get(heading, [])):
                # `rename` is where this chapter's ids are decided, and a row names the node under
                # the same heading the node was created under. Resolving the slug alone sent the
                # archetype rows at `concept:momentum` -- the character an indicator measures.
                mid = decl.get("rename", {}).get(name) \
                    or (f"concept:{slug(name)}-order" if f"concept:{slug(name)}-order" in atoms
                        else f"concept:{slug(name)}")
                values = [c.strip() for c in rest.split(".")]
                if mid not in atoms:
                    raise ValueError(f"table row {name!r} names no node in this chapter")
                for col, val in zip(columns, values):
                    if val:
                        atoms[mid]["props"][col] = val

        for label, body in labelled_blocks(blocks.get("Mathematical Rules/Formulas", [])):
            formula = code_of(body)
            if not formula:
                continue
            # A formula says nothing about what a thing IS. `Basis = Futures - Spot` defines a
            # QUANTITY a contract has; `Put-Call Parity` states an identity that holds; only
            # Black-Scholes and GARCH are things you RUN. Reading every formula as a Procedure gave
            # chapter 2 thirty-two of them and the graph zero Properties, because this path could
            # not emit one. Property is the default and the exceptions are declared per chapter.
            prim = decl.get("formula_primitive", {}).get(label, "Property")
            verb = {"Property": "The quantity", "Fact": "The identity",
                    "Procedure": "Computes", "Concept": "The family"}[prim]
            pid = atom(prim, label, f"{verb} {label.lower()}.",
                       formula=formula, _generated=True, _section=num)
            quantified = subject_for(label, subjects)
            rel(pid, "about", quantified, f"quantifies {name_of(quantified)}")

        # Anything else the section says. A chapter is free to add a heading nobody anticipated --
        # §3.11 has five of them, holding the interpretation of a volume profile and the auction
        # scenarios it is read through -- and a block that matches no rule was previously dropped
        # without a word. It is kept on the section's subject under its own name instead.
        handled = set(SCAFFOLD) | set(as_nodes) | set(decl.get("tables", {})) \
            | set(decl.get("table_properties", {})) | set(decl.get("labelled_nodes", {}))
        for heading, body in blocks.items():
            if heading in handled or heading.startswith("Best Practices"):
                continue
            text = block_text(body)
            if not text or not subjects:
                if text and not subjects:
                    raise ValueError(f"{sec['title']!r} says {heading!r} with no subject to keep "
                                     "it on")
                continue
            target = subject_for(heading, subjects)
            key = slug(heading).replace("-", "_")
            (atoms[target]["props"] if target in atoms
             else extra.setdefault(target, {})).setdefault(key, text)

    # The chapter's opening paragraph and its Summary section state what the chapter is for and
    # what it claims to deliver. Both were parsed and thrown away -- the only text in the file that
    # described the whole subject rather than one part of it.
    raw_text = path.read_text(encoding="utf-8")
    intro = re.search(r"^# .+?\n\n(.+?)\n\n---", raw_text, re.S | re.M)
    closing = re.search(r"^## Summary\n\n(.+)$", raw_text, re.S | re.M)
    chapter_props = {}
    if intro:
        chapter_props["explanation"] = " ".join(intro.group(1).split())
    if closing:
        chapter_props["applications"] = [
            re.sub(r"^\d+\.\s*", "", l.strip()).replace("**", "")
            for l in closing.group(1).split("\n") if re.match(r"^\d+\.", l.strip())]
        # §4's Summary ends in a blockquote -- "strategies do not fail randomly, they fail when
        # applied to the wrong market behaviour" -- and reading only the numbered items dropped it.
        if quote := [l.strip().lstrip("> ").replace("**", "").strip()
                     for l in closing.group(1).split("\n") if l.strip().startswith(">")]:
            chapter_props["caution"] = " ".join(q for q in quote if q)
    if chapter_props:
        extra.setdefault(parent, {}).update(chapter_props)

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
    def resolve_statements(lines: list[str]) -> dict[str, str]:
        """Which node each statement names, by reading the statement rather than by declaration.

        A statement earns its edge when it names the node it concerns, and many of them do -- the
        chapter writes "always have a stop-loss for every position" and the node is called
        `stop order (stop-loss)`. Transcribing those by hand is copying out something the text
        already says, which is where the mistakes come from.

        Four rules keep it from inventing edges, because a wrong edge answers a query and a missing
        one does not:

        * A name in a large share of the graph is vocabulary, not a reference.
        * Only a compound name or an abbreviation is a citation. One ordinary word is not --
          "reveal your strategy to sophisticated participants" does not cite `schema:strategy` --
          and frequency alone cannot tell, because the graph is smaller when chapter 1 builds than
          when chapter 4 does and the same word scores differently. Single-word matches are printed
          as candidates for `wired` to accept, never drawn.
        * The longest name wins: `mean reversion` is more specific than `reversion`.
        * Two nodes matching at that length is an ambiguity, not a coin toss. Reported, not guessed.
        """
        index: dict[str, str] = {}
        abbreviations: set[str] = set()
        for nid, node in list(atoms.items()) + list(existing.items()):
            if nid in (parent, fid, jid):
                continue
            for alias in aliases_of(node):
                key = _norm(alias).strip()
                index.setdefault(key, nid)
                if isinstance(node.get("props", {}).get("abbreviation"), str) \
                        and key == node["props"]["abbreviation"].lower():
                    abbreviations.add(key)
        corpus = [_norm(json.dumps(node))
                  for node in list(atoms.values()) + list(existing.values())]
        generic = {a for a in index
                   if sum(f" {a} " in doc for doc in corpus) > GENERIC_SHARE * len(corpus)}
        out, ambiguous, candidates = {}, [], []
        for line in lines:
            norm = _norm(line)
            matched = [(a, index[a]) for a in index
                       if a not in generic and f" {a} " in norm]
            strong = [(a, n) for a, n in matched if " " in a or a in abbreviations]
            if not strong:
                if matched:
                    candidates.append((line, sorted({n for _, n in matched})))
                continue
            best = max(len(a) for a, _ in strong)
            top = {n for a, n in strong if len(a) == best}
            if len(top) > 1:
                ambiguous.append((line, sorted(top)))
                continue
            out[line] = top.pop()
        for label, rows in (("names more than one node", ambiguous),
                            ("names one ordinary word", candidates)):
            if rows:
                print(f"  wiring: {len(rows)} statement(s) {label} -- `wired` decides:",
                      file=sys.stderr)
                for line, ids in rows:
                    print(f"    {line[:66]!r} -> {ids}", file=sys.stderr)
        return out

    resolved = resolve_statements(principles + practices)

    def wire(list_id: str, lines: list[str]) -> list[str]:
        """Move every wired line out of the list and onto an `about` edge carrying it as the why."""
        kept = []
        for line in lines:
            # The declaration wins: it exists to correct or to supply what the text does not say.
            target = next((v for k, v in decl["wired"].items() if k in line), resolved.get(line))
            if target is None:
                kept.append(line)
                continue
            if target not in atoms and target not in existing:
                raise ValueError(f"`wired` points at {target!r}, which is not a node")
            # FROM the node, TO the list it draws on. A reader arrives at a concept and asks what
            # is known about it, and outgoing edges are the answer to that question -- so the
            # concept points at the principles and practices that govern it, not the reverse. It
            # also keeps the two list nodes from accumulating every statement as an outgoing
            # edge apiece while every concept sits there with none.
            prior = next((r for r in rels if r["from_id"] == target and r["rel"] == "about"
                          and r["to_id"] == list_id), None)
            if prior:
                prior["why"] += " · " + line
            else:
                rels.append({"from": name_of(target), "rel": "about", "to": atoms[list_id]["title"],
                             "why": line, "from_id": target, "to_id": list_id})

        return kept

    for mid, texts in deferred_uses.items():
        if mid in atoms:
            atoms[mid]["props"].setdefault("applications", []).extend(texts)
        elif mid in existing:
            extra.setdefault(mid, {}).setdefault("applications", []).extend(texts)
        else:
            raise ValueError(f"a use case names {mid!r}, which is not a node in this chapter")

    # A term in backticks is the chapter citing something by the name the library registers it
    # under -- §4.4 illustrates each signal type with `macd_bullish_cross`, `rsi_overbought`,
    # `adx_strong_trend`, and all twelve it names are nodes. Code fences are excluded: `close` and
    # `df` inside a python block are variables, not citations.
    # The edge runs FROM the thing named TO the node that cites it, which is the direction
    # everything else in this graph points: a member at its type, `instance-of` and `kind-of` and
    # `has-role` all aim up. Drawn the other way it fans out of the citing node, and `all_paths`
    # suppresses a detour through a hub by spotting two edges that both point AT it -- so twelve
    # signals hanging off `concept:signal-type` became mutually two hops apart, and the suppression
    # could not see it. Same edge, same claim, and the existing guard works.
    named = {(a.get("title") or "").strip().lower(): nid
             for nid, a in list(existing.items()) + list(atoms.items())}
    for nid, a in atoms.items():
        text = " ".join(str(v) for k, v in a["props"].items() if k != "formula")
        for token in re.findall(r"`([^`\n]+)`", f"{a['summary']} {text}"):
            if (src := named.get(token.strip().lower())) and src != nid:
                rel(src, "about", nid, f"the chapter's example of {a['title']}")

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
    # The measure of the chapter's connectedness, printed rather than inferred: what remains in the
    # two lists is exactly what nothing in the graph is known to be about yet.
    left = atoms[fid]["props"]["principles"] + atoms[jid]["props"]["practices"]
    print(f"  wiring: {len(principles) + len(practices)} statements -- "
          f"{len(resolved)} resolved by name, "
          f"{len([l for l in principles + practices if any(k in l for k in decl['wired'])])} "
          f"declared, {len(left)} unresolved", file=sys.stderr)
    # Every resolution is printed, not just the failures: a name match is a proposal, and a wrong
    # edge answers a query, which is worse than a missing one. `wired` is where a wrong one is
    # overruled, so the reviewer has to be able to see them all.
    for line, target in resolved.items():
        print(f"    resolved:   {target:38} <- {line[:70]}", file=sys.stderr)
    for line in left:
        print(f"    unresolved: {line[:96]}", file=sys.stderr)
    atoms[fid]["summary"] = FACT_SUMMARY
    atoms[jid]["summary"] = JUDGMENT_SUMMARY

    for i in (fid, jid):
        rels.append({"from": atoms[i]["title"], "rel": "part-of", "to": parent.split(":", 1)[1].replace("-", " "),
                     "why": f"stated across {chapter}", "from_id": i, "to_id": parent})

    for nid, a in atoms.items():
        a["props"].pop("_section", None)
        a["props"].pop("_generated", None)
        a["props"].pop("merged_from", None)
        if nid in AUTHORED:
            summary, explanation = AUTHORED[nid]
            # Outer join: keep both statements, never silently replace one with the other.
            if a["summary"] and a["summary"] != summary:
                if _is_illustration(a["summary"]):
                    a["props"].setdefault("examples", []).insert(0, a["summary"])
                elif not _same_claim(a["summary"], summary):
                    a["props"].setdefault("source_wording", a["summary"])
            a["summary"] = summary
            if explanation:
                # Same outer join as the summary above: the chapter's own bullets are kept, not
                # replaced. Scalping's four characteristics were vanishing behind authored prose.
                if (parsed := a["props"].get("explanation")) and parsed != explanation:
                    notes = a["props"].setdefault("notes", [])
                    if parsed not in notes:
                        notes.append(parsed)
                a["props"]["explanation"] = explanation
        if nid in DEFINITION and nid not in AUTHORED:
            # The parsed text was an instance, not a definition: keep it as the illustration.
            if a["summary"] and a["summary"] not in (a["props"].get("examples") or []):
                a["props"].setdefault("examples", []).insert(0, a["summary"])
            a["summary"] = DEFINITION[nid]
        if nid in FORMULA_IO:
            ins, outs = FORMULA_IO[nid]
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

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
}

#: Blocks inside a taxonomy section that are still NOT kinds: "Regime Shift Triggers" lists causes
#: of a shift and "Information Events" lists occasions for discovery. Both read like members and
#: are not, which no rule about the text can tell apart from the ones that are.
NOT_A_KIND = {"Regime Shift Triggers", "Information Events",
              # The execution-algorithm table lists Iceberg beside TWAP and VWAP. It is the same
              # thing as the order type of that name, which is already a node; a second one under a
              # different primitive would be a duplicate wearing a different hat.
              "Iceberg",
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
             "basis": "basis", "greeks": "greeks", "futures": "futures"}


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
        nid = decl.get("rename", {}).get(title) or f"{kind.lower()}:{slug(title)}"
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
        if not any(r["from_id"] == src and r["rel"] == relation and r["to_id"] == dst for r in rels):
            rels.append({"from": name_of(src), "rel": relation, "to": name_of(dst),
                         "why": why, "from_id": src, "to_id": dst})

    principles, practices = [], []
    deferred_uses: dict[str, list[str]] = {}

    for num, sec in sorted(sections.items()):
        blocks = sec["blocks"]
        definition = blocks.get("Definition", [])
        defined = bullets([l for l in definition if BULLET.match(l)])
        prose = " ".join(l.strip() for l in definition if l.strip() and not l.strip().startswith("-"))
        use_bullets = bullets(blocks.get("Common Use Cases", []))
        # §1.2 labels each use case with the order type it belongs to. Flattening them onto the
        # section subject gave `order-type` five sentences and left every member with none.
        per_member = {name: text for name, text in use_bullets if name}
        uses = [text for name, text in use_bullets if not name]

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
        for label, text in per_member.items():
            deferred_uses.setdefault(f"concept:{slug(label)}", []).append(text)

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
                continue
            principles.append(f"{name}: {text}" if name else text)
        for _, text in bullets(blocks.get("Best Practices for Traders", [])):
            practices.append(text)

        if sec["title"] in decl["taxonomy"]:
            for label, body in labelled_blocks(blocks.get("Examples", [])):
                if label in NOT_A_KIND:
                    # Not a kind, but not rubbish either -- "Regime Shift Triggers" lists what
                    # causes a shift. Kept on the subject rather than discarded.
                    txt = " ".join(b.strip().lstrip("- ").strip() for b in body
                                   if b.strip().startswith("-"))
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

        for heading, columns in decl.get("table_properties", {}).items():
            for name, rest in table_rows(blocks.get(heading, [])):
                mid = f"concept:{slug(name)}-order" if f"concept:{slug(name)}-order" in atoms \
                      else f"concept:{slug(name)}"
                values = [c.strip() for c in rest.split(".")]
                if mid not in atoms:
                    raise ValueError(f"table row {name!r} names no node in this chapter")
                for col, val in zip(columns, values):
                    if val:
                        atoms[mid]["props"][col] = val

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

    for mid, texts in deferred_uses.items():
        if mid in atoms:
            atoms[mid]["props"].setdefault("applications", []).extend(texts)
        elif mid in existing:
            extra.setdefault(mid, {}).setdefault("applications", []).extend(texts)
        else:
            raise ValueError(f"a use case names {mid!r}, which is not a node in this chapter")

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

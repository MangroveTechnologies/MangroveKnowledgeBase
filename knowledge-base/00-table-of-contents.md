# Knowledge Base - Table of Contents

This document provides a comprehensive index of the trading knowledge base, organized by topic with summaries and searchable tags for each section.

---

# 0. Usage Guide

## Using This Knowledge Base

**Using this TOC:**
- Review the chapter list below to identify relevant document slugs
- Use `kb_get_document(slug)` or `kb_get_sections(slug, anchors)` to retrieve content
- Use `kb_search()` for concept discovery when document structure is unclear

**For signal planning (plan_signals state):**
- Call `kb_get_signal_quick_reference()` to discover all available signals with types and categories
- Call `kb_get_sections(slug="06-indicators", anchors=["<indicator>"])` for detailed parameters
- Call `kb_search(q="momentum indicators")` to find signals by concept
- Use these to intelligently select signals that match user strategy goals

**For other questions:**
- Strategy concepts: `kb_get_document(slug="04-strategy-design-modeling")`
- Risk management: `kb_get_document(slug="05-risk-management")`
- General search: `kb_search(q="your question")`

## Available Tools

**kb_search(q, expand, limit)**
- Full-text search across all KB documents
- Example: `kb_search(q="momentum trading", expand=true, limit=3)`

**kb_list_documents(limit)**
- List all KB documents with summaries
- Example: `kb_list_documents(limit=20)`

**kb_get_document(slug, max_chars)**
- Get full document by slug (see chapter list below)
- Example: `kb_get_document(slug="04-strategy-design-modeling", max_chars=6000)`

**kb_get_signal_quick_reference(max_chars)**
- Get Chapter 10 signals quick reference (all 136 signals)
- Example: `kb_get_signal_quick_reference(max_chars=6000)`

**kb_list_sections(slug)**
- List section anchors for a document
- Example: `kb_list_sections(slug="06-indicators")`

**kb_get_sections(slug, anchors, max_chars_per_section)**
- Get specific sections from a document
- Example: `kb_get_sections(slug="06-indicators", anchors=["rsi"], max_chars_per_section=3000)`

---

# 1. Market Foundations

This document covers the fundamental concepts underlying financial markets, including market structure, order mechanics, participant dynamics, and execution considerations essential for systematic trading. It provides the essential infrastructure knowledge required for understanding how markets operate at a mechanical level. Topics range from microstructure theory and order flow dynamics to trading venues and price discovery mechanisms. Mastery of these concepts enables traders to execute efficiently, manage risk, and develop robust strategies.

Tags: market-structure, microstructure, order-types, execution, liquidity, volatility

## 1.1 Market Microstructure

Examines the processes and mechanisms through which securities are traded, including order flow, price formation, transaction costs, and information asymmetry. Understanding microstructure enables traders to optimize execution and minimize costs.

Tags: order-flow, price-formation, transaction-costs, information-asymmetry

## 1.2 Order Types

Covers the various order types available to traders including market, limit, stop, stop-limit, trailing stops, and iceberg orders. Each order type has specific use cases balancing execution certainty against price control.

Tags: market-order, limit-order, stop-order, trailing-stop, iceberg-order

## 1.3 Market Participants

Describes the different types of market participants including retail traders, institutional investors, market makers, HFT firms, and arbitrageurs. Understanding participant behavior helps anticipate market dynamics.

Tags: retail-traders, institutional, market-makers, HFT, arbitrage

## 1.4 Liquidity, Slippage & Market Impact

Explains liquidity as the ease of trading without price impact, slippage as the difference between expected and actual execution prices, and market impact as the effect of orders on prices. Critical for realistic strategy development.

Tags: liquidity, slippage, market-impact, execution-cost, VWAP, TWAP

## 1.5 Volatility, Regimes & Regime Shifts

Covers volatility measurement, market regimes (trending, ranging, volatile, calm), and the transitions between them. Different strategies perform optimally in different regimes, making regime detection essential.

Tags: volatility, VIX, ATR, market-regimes, regime-detection, GARCH

## 1.6 Trading Venues & Execution Models

Describes the various trading venues (exchanges, dark pools, ECNs, OTC) and execution algorithms (TWAP, VWAP, Implementation Shortfall). Proper venue selection impacts execution quality.

Tags: exchanges, dark-pools, ECN, execution-algorithms, smart-order-routing

## 1.7 Bid-Ask Spread Dynamics

Explains the bid-ask spread as compensation to liquidity providers, factors affecting spread width, and how to interpret spread changes as market condition signals.

Tags: bid-ask-spread, market-making, liquidity-provision, transaction-costs

## 1.8 Price Discovery Mechanisms

Covers how market prices are determined through buyer-seller interaction, including auction mechanisms, continuous trading, and cross-market price discovery.

Tags: price-discovery, auctions, market-efficiency, information-aggregation

---

# 2. Instruments & Market Mechanics

This document covers various financial instruments and their specific mechanics, including spot markets, derivatives, margin trading, and crypto-specific considerations. Understanding instrument mechanics is essential for proper position sizing, risk management, and strategy selection. Topics include futures contracts, options Greeks, perpetual swaps, and the unique characteristics of cryptocurrency markets.

Tags: instruments, futures, options, derivatives, margin, leverage, crypto

## 2.1 Spot Markets

Describes spot markets where assets are traded for immediate delivery at current market prices. Covers price determination, settlement, and the relationship between spot and derivative markets.

Tags: spot-market, settlement, price-determination

## 2.2 Futures Contracts

Comprehensive coverage of futures contracts including specifications, margin requirements, expiration, rollover, and the concepts of contango and backwardation.

Tags: futures, margin, contango, backwardation, rollover, expiration

## 2.3 Perpetual Swaps

Explains cryptocurrency perpetual swaps that have no expiration, including the funding rate mechanism that anchors price to spot markets.

Tags: perpetual-swaps, funding-rate, crypto-derivatives

## 2.4 Options Fundamentals

Covers options basics including calls, puts, strike prices, expiration, and the Greeks (Delta, Gamma, Theta, Vega) for understanding options price sensitivity.

Tags: options, calls, puts, Greeks, delta, gamma, theta, vega

## 2.5 Options Pricing Models

Describes mathematical models for options valuation including Black-Scholes and binomial models, along with their assumptions and limitations.

Tags: Black-Scholes, options-pricing, implied-volatility, binomial-model

## 2.6 Margin Trading & Leverage

Explains margin mechanics, leverage ratios, initial and maintenance margin, and the risks associated with leveraged trading including liquidation.

Tags: margin, leverage, liquidation, margin-call, risk

## 2.7 Crypto-Specific Mechanics

Covers unique aspects of cryptocurrency markets including centralized vs decentralized exchanges, AMMs, on-chain vs off-chain trading, and tokenomics.

Tags: crypto, DEX, CEX, AMM, tokenomics, blockchain

## 2.8 FX Basics

Introduces foreign exchange markets including currency pairs, pips, lots, and the 24-hour nature of forex trading across global sessions.

Tags: forex, currency-pairs, pips, FX-sessions

---

# 3. Core Trading Concepts

This document covers the fundamental analytical frameworks and concepts used by traders to interpret market behavior, identify opportunities, and make trading decisions. These concepts form the foundation for technical analysis and discretionary trading. Topics include core market wisdom, price action theory, market structure, support and resistance, supply and demand zones, and multi-timeframe analysis.

Tags: price-action, market-structure, support-resistance, supply-demand, technical-analysis, market-wisdom, risk-dimensions

## 3.0 Core Market Wisdom

Foundational truths that govern market behavior and strategy selection. Covers "The Trend Is Your Friend" doctrine, why win rate is not the same as risk, the multi-dimensional nature of risk (per-trade, skew, regime, drawdown, tail, correlation), and how regime determines archetype effectiveness.

Tags: market-wisdom, trend-is-your-friend, win-rate, skew, risk-dimensions, regime

## 3.1 Price Action Theory

Explains trading methodology based on pure price movement without lagging indicators. Covers candlestick anatomy, reading market sentiment through bars, and the principle that price discounts all information.

Tags: price-action, candlesticks, raw-price, sentiment

## 3.2 Market Structure

Describes the framework of highs and lows that define market state: higher highs/higher lows for uptrends, lower highs/lower lows for downtrends, and key concepts like Break of Structure (BOS) and Change of Character (CHoCH).

Tags: market-structure, HH, HL, LH, LL, BOS, CHoCH, trend

## 3.3 Trend, Range, Compression/Expansion

Covers the three primary market states (trending, ranging, transitional) and volatility cycles. Explains how compression (decreasing volatility) often precedes expansion (breakouts).

Tags: trend, range, compression, expansion, volatility-cycle, ADX

## 3.4 Liquidity Theory

Explains where resting orders accumulate (liquidity pools) and how price tends to seek these areas. Covers stop hunts, liquidity grabs, and the concept of equal highs/lows as liquidity targets.

Tags: liquidity-pools, stop-hunt, liquidity-grab, smart-money

## 3.5 Volume & Order Flow

Describes volume as confirmation of price moves, order flow analysis for identifying institutional activity, and concepts like volume divergence, accumulation, distribution, and climactic volume.

Tags: volume, order-flow, OBV, VWAP, accumulation, distribution

## 3.6 Support & Resistance

Covers horizontal and dynamic support/resistance levels, the principle of role reversal when levels break, and methods for identifying significant levels.

Tags: support, resistance, role-reversal, pivot-points

## 3.7 Supply & Demand Zones

Explains supply and demand zones as areas of price imbalance where institutions accumulate or distribute. Covers zone identification, freshness, and trading approaches.

Tags: supply-zone, demand-zone, imbalance, institutional-trading

## 3.8 Multi-Timeframe Analysis

Describes the practice of analyzing multiple timeframes for comprehensive market view. Covers top-down analysis, timeframe alignment, and using higher timeframes for context with lower timeframes for entry.

Tags: multi-timeframe, top-down-analysis, timeframe-alignment

## 3.9 Confluence

Explains how multiple independent technical factors aligning at the same level increases trade probability. Covers building confluence through various factors and scoring systems.

Tags: confluence, probability, multiple-confirmation

## 3.10 Fair Value Gaps

Describes Fair Value Gaps (FVGs) as price imbalances created by rapid price movement. Covers identification, the rebalancing tendency, and using FVGs for entry targets.

Tags: fair-value-gap, FVG, imbalance, rebalancing

## 3.11 Volume Profile & Market Auction Theory

Explains Volume Profile as a display of trading activity across price levels and Market Auction Theory viewing markets as continuous auctions seeking fair value. Covers Point of Control (POC), Value Area (VA), and using these for trading decisions.

Tags: volume-profile, POC, value-area, VAH, VAL, auction-theory

---

# 4. Strategy Design & Modeling

This document covers the principles and methodologies for designing, developing, and validating systematic trading strategies. Topics include trading styles, strategy archetypes (now with clear separation of trend following and momentum), signal types, entry/exit logic, regime detection, data quality, backtesting, walk-forward optimization, and validation to avoid biases. A comprehensive guide from concept through deployment, with explicit risk profiles for each archetype.

Tags: strategy-design, signals, backtesting, validation, entry-logic, exit-logic, optimization, risk-profiles, archetypes

## 4.1 Trading Styles

Defines the major trading styles (scalping, day trading, swing trading, position trading) with their timeframes, characteristics, capital requirements, and lifestyle considerations. Clarifies that style defines **when** you trade, while archetypes define **why** you trade.

Tags: scalping, day-trading, swing-trading, position-trading, timeframe

## 4.2 Strategy Archetypes

Describes fundamental strategy categories with **explicit separation**: Trend Following (regime/direction), Momentum (timing/acceleration), Breakouts (transition), Mean Reversion, Carry, and Event-Driven. Each archetype includes its core premise, mechanism, risk profile (win rate, skew, tail risk), contraindications, and example strategies. Includes archetype risk summary table and contraindications table.

Tags: trend-following, momentum, mean-reversion, carry, event-driven, breakouts, risk-profile, skew, contraindications

## 4.3 Building a Trade Plan

Comprehensive guide to creating a trading plan including entry criteria, confirmation rules, exit criteria, position sizing, and documentation. Includes trade plan template.

Tags: trade-plan, entry-criteria, exit-rules, trading-rules

## 4.4 Signal Types

Defines the four signal types used in trading strategies: Entry (triggers opening positions), Exit (triggers closing positions), Filter (screens trades / sets context), and Confirmation (validates other signals). Explains how these work together in a complete strategy. Includes mapping of signal types to archetypes (e.g., Trend -> Filter, Momentum -> Entry/Exit).

Tags: signal-types, entry, exit, filter, confirmation, strategy-building, archetype-mapping

## 4.5 Entry Logic Frameworks

Covers systematic entry approaches including indicator-based, pattern-based, and statistical entries. Includes multi-factor confirmation and entry filter concepts.

Tags: entry-logic, signals, confirmation, filters

## 4.6 Exit Logic

Describes exit strategies including stop-loss variants (fixed, ATR-based, structure-based), profit targets (fixed, risk-multiple), trailing stops, and signal-based exits.

Tags: exit-logic, stop-loss, take-profit, trailing-stop

## 4.7 Time-Based Logic

Covers temporal factors in trading including session filters, holding period constraints, calendar-based adjustments, and time decay considerations.

Tags: time-based, session-filter, holding-period, calendar

## 4.8 Regime Detection & Filtering

Explains methods for identifying market regimes (trending, ranging, volatile, calm) and adapting strategy behavior based on detected conditions. Includes conceptual anchor: regime detection selects which archetypes to deploy, not which direction to trade.

Tags: regime-detection, ADX, efficiency-ratio, HMM, adaptation, archetype-selection

## 4.9 Data Quality & Preprocessing

Covers data cleaning, handling missing data, corporate action adjustments, and avoiding biases (survivorship, look-ahead) in historical data.

Tags: data-quality, survivorship-bias, look-ahead-bias, data-cleaning

## 4.10 Backtesting Best Practices

Describes proper backtesting methodology including realistic cost assumptions, out-of-sample testing, and interpreting backtest results skeptically.

Tags: backtesting, transaction-costs, slippage, out-of-sample

## 4.11 Walk-Forward Optimization

Explains walk-forward optimization as a method to avoid overfitting by repeatedly optimizing on in-sample data and testing on subsequent out-of-sample periods.

Tags: walk-forward, optimization, overfitting, out-of-sample

## 4.12 Strategy Validation (Avoiding Biases)

Covers validation procedures including statistical significance testing, robustness checks, multiple testing corrections, and the validation checklist for genuine strategies.

Tags: validation, statistical-significance, robustness, biases

---

# 5. Risk Management

This document covers comprehensive risk management principles and techniques essential for preserving capital and achieving sustainable trading performance. Topics include risk dimensions framework, trading rules, position sizing, drawdown controls, stop-loss engineering, portfolio risk, and scenario analysis. Risk management is the foundation upon which all successful trading is built.

Tags: risk-management, position-sizing, drawdown, stop-loss, portfolio-risk, risk-dimensions, skew

## 5.0 Risk Dimensions in Strategy Design

Explains that risk is multi-dimensional: per-trade risk, strategy skew, regime risk, drawdown risk, tail risk, correlation risk, and liquidity risk. Covers why win rate is misleading (high win rate with negative skew is dangerous), per-trade risk vs strategy risk distinction, and the strategy-level risk assessment checklist.

Tags: risk-dimensions, skew, win-rate, tail-risk, regime-risk, strategy-risk

## 5.1 Trading Rules & Protocols

Establishes predefined guidelines governing trading behavior including max risk per trade, daily/weekly loss limits, max positions, reward-to-risk requirements, trading hours, and cool-down periods.

Tags: trading-rules, loss-limits, protocols, discipline

## 5.2 Position Sizing

Covers position sizing methods including fixed fractional, volatility-adjusted, ATR-based, and Kelly Criterion approaches to ensure consistent risk across trades.

Tags: position-sizing, fixed-fractional, Kelly-Criterion, ATR-sizing

## 5.3 Drawdown Controls

Describes mechanisms to limit cumulative losses including maximum drawdown limits, progressive response frameworks, daily loss limits, and recovery protocols.

Tags: drawdown, loss-limits, circuit-breaker, recovery

## 5.4 Stop-Loss & Take-Profit Engineering

Comprehensive coverage of stop-loss placement (fixed, ATR-based, structure-based), trailing stops, break-even stops, and take-profit strategies including scale-out approaches.

Tags: stop-loss, take-profit, trailing-stop, ATR-stop, scale-out

## 5.5 Portfolio Risk

Addresses aggregate risk of multiple positions including correlation-adjusted sizing, concentration limits, Value at Risk (VaR), Expected Shortfall, and portfolio beta.

Tags: portfolio-risk, correlation, VaR, concentration, diversification

## 5.6 Capital Efficiency

Covers capital deployment optimization including allocation frameworks, leverage management, cash buffers, and return on capital metrics.

Tags: capital-efficiency, leverage, allocation, margin

## 5.7 Risk-Reward Ratios

Explains risk-reward calculation, the relationship between win rate and required R:R, expectancy calculation, and setting realistic profit targets.

Tags: risk-reward, R:R, expectancy, win-rate

## 5.8 Risk of Ruin

Describes the probability of catastrophic loss based on position sizing and strategy characteristics, including Monte Carlo simulation for risk estimation.

Tags: risk-of-ruin, survival, Monte-Carlo, position-sizing

## 5.9 Scenario Analysis

Covers stress testing against historical and hypothetical scenarios, correlation breakdown analysis, tail risk assessment, and contingency planning.

Tags: scenario-analysis, stress-testing, tail-risk, contingency

---

# 6. Indicators

This document provides detailed coverage of technical indicators organized by category: trend, momentum, volatility, volume, and market breadth. Each indicator includes its calculation, interpretation, best use cases, common parameters, **MangroveAI API reference**, and **related trading signals**. Understanding indicators and their corresponding signals helps confirm price action signals and build systematic trading strategies.

**NEW: Each indicator section now includes:**
- Educational content (formula, interpretation, trading applications)
- MangroveAI API Reference (class name, parameters, usage examples)
- Related Trading Signals (all signals built from that indicator with parameters and usage)

Tags: indicators, signals, trend, momentum, volatility, volume, oscillators, api-reference, cross-reference

## 6.1 Trend Indicators

Covers trend-following indicators including Simple Moving Average (SMA), Exponential Moving Average (EMA), DEMA, TEMA, Average Directional Index (ADX), Parabolic SAR, and Ichimoku Cloud. Each indicator includes API reference and related signals (e.g., SMA includes sma_cross_up, sma_cross_down, is_above_sma, sma_crossover).

Tags: SMA, EMA, ADX, Parabolic-SAR, Ichimoku, trend-following, crossover-signals

## 6.2 Momentum Indicators

Describes momentum oscillators including Relative Strength Index (RSI), MACD, Stochastic Oscillator, Commodity Channel Index (CCI), Rate of Change (ROC), Williams %R, and Money Flow Index (MFI). Each indicator includes API reference and related signals (e.g., RSI includes rsi_oversold, rsi_overbought, rsi_divergence).

Tags: RSI, MACD, Stochastic, CCI, momentum, overbought, oversold, divergence-signals

## 6.3 Volatility Indicators

Covers volatility measurement tools including Bollinger Bands, Average True Range (ATR), Keltner Channels, Standard Deviation bands, and volatility percentile rankings. Each indicator includes API reference and related signals (e.g., Bollinger Bands includes bb_upper_breakout, bb_lower_breakout, bb_squeeze).

Tags: Bollinger-Bands, ATR, Keltner-Channels, volatility, squeeze, breakout-signals

## 6.4 Volume Indicators

Describes volume-based indicators including On-Balance Volume (OBV), Accumulation/Distribution Line (ADL), Volume Weighted Average Price (VWAP), Chaikin Money Flow (CMF), and Klinger Oscillator. Each indicator includes API reference and related signals (e.g., OBV includes obv_bullish, obv_bearish).

Tags: OBV, VWAP, volume-analysis, accumulation, distribution, volume-signals

## 6.5 Market Breadth Indicators

Covers market-wide indicators including Advance-Decline Line, McClellan Oscillator, TRIN (Arms Index), and their use in assessing overall market health.

Tags: breadth, advance-decline, McClellan, TRIN, market-health

## 6.6 Oscillators Deep Dive

Provides advanced analysis of oscillators including divergence types (regular, hidden), oscillator failure swings, and multi-timeframe oscillator analysis.

Tags: divergence, oscillator, failure-swing, momentum-analysis

## 6.7 Moving Average Variants

Detailed comparison of moving average types (SMA, EMA, WMA, DEMA, TEMA, KAMA) with their specific characteristics, lag properties, and optimal use cases.

Tags: moving-averages, EMA, SMA, DEMA, TEMA, crossover

---

# 7. Chart Patterns

This document provides a comprehensive reference for technical chart patterns including candlestick patterns, multi-bar formations, and classical chart patterns. Covers pattern identification, reliability statistics, context requirements, and completion criteria. Pattern recognition is a core skill for both discretionary and systematic traders.

Tags: chart-patterns, candlesticks, reversal, continuation, technical-analysis

## 7.1 Candlestick Patterns

Comprehensive coverage of single and multi-candlestick patterns including Doji, Hammer, Shooting Star, Engulfing, Harami, Morning/Evening Star, and Three White Soldiers/Black Crows. Each pattern includes anatomy, identification, and interpretation.

Tags: candlesticks, Doji, Hammer, Engulfing, reversal-patterns

## 7.2 Multi-Bar Patterns

Covers multi-bar formations including Inside Bar, Outside Bar, Pin Bar, Two-Bar Reversal, and NR4/NR7 (Narrow Range) patterns. Includes detection logic and trading applications.

Tags: inside-bar, outside-bar, pin-bar, narrow-range, consolidation

## 7.3 Chart Patterns

Describes classical chart patterns including Head and Shoulders, Double/Triple Top/Bottom, Triangles, Flags, Pennants, Wedges, Channels, and Cup and Handle. Includes measured move targets.

Tags: head-shoulders, double-top, triangle, flag, wedge, cup-handle

## 7.4 Algorithmic / Programmatic Patterns

Covers patterns suitable for systematic detection including swing point detection, trend line detection, and support/resistance identification algorithms. References TA-Lib candlestick functions.

Tags: algorithmic, pattern-detection, TA-Lib, systematic

## 7.5 Pattern Reliability & Failure Modes

Presents reliability statistics for various patterns and explains common failure modes including false breakouts, premature entry, and wrong context. Includes strategies for trading failed patterns.

Tags: reliability, failure-modes, false-breakout, pattern-failure

## 7.6 Pattern Context Requirements

Explains the market conditions required for patterns to be valid: trend alignment, location at key levels, timeframe hierarchy, and confluence requirements by pattern type.

Tags: context, trend-alignment, pattern-validity, filtering

## 7.7 Pattern Completion Criteria

Describes specific conditions for pattern completion including breakout confirmation, volume requirements, time elements, and entry timing options (aggressive, standard, conservative).

Tags: completion, confirmation, breakout, entry-timing

---

# 8. Quantitative Analysis

This document covers quantitative patterns and statistical approaches to trading including seasonality, volatility modeling, mean reversion signals, breakout detection, and machine learning applications. These methods provide systematic, data-driven approaches to identifying trading opportunities.

Tags: quantitative, statistics, seasonality, mean-reversion, machine-learning

## 8.1 Seasonality & Time-of-Day Effects

Covers calendar-based patterns including day-of-week effects, month-of-year patterns, holiday effects, and intraday seasonality. Includes statistical validation approaches.

Tags: seasonality, calendar-effects, time-of-day, statistical-patterns

## 8.2 Volatility Clustering (GARCH)

Explains volatility persistence and GARCH modeling for forecasting future volatility. Covers regime-switching models and practical applications for risk management.

Tags: GARCH, volatility-clustering, volatility-forecasting, regime-switching

## 8.3 Mean Reversion Signals

Describes statistical arbitrage, pairs trading, and z-score based mean reversion strategies. Includes cointegration testing and spread trading mechanics.

Tags: mean-reversion, pairs-trading, z-score, cointegration, statistical-arbitrage

## 8.4 Breakout Signals

Covers systematic breakout detection using Donchian channels, volatility expansion signals, and range breakout strategies with validation criteria.

Tags: breakout, Donchian, volatility-expansion, range-break

## 8.5 Autocorrelation & Momentum Persistence

Explains momentum as autocorrelation in returns, time-series momentum strategies, and cross-sectional momentum approaches.

Tags: autocorrelation, momentum, time-series, cross-sectional

## 8.6 Machine-Learned Patterns

Introduces machine learning applications in trading including feature engineering, classification vs regression approaches, and avoiding overfitting in ML models.

Tags: machine-learning, ML, features, classification, overfitting

## 8.7 Cross-Sectional vs Time-Series Patterns

Distinguishes between patterns that compare assets at a point in time (cross-sectional) vs patterns in a single asset over time (time-series), with different strategy implications.

Tags: cross-sectional, time-series, factor-investing, momentum

## 8.8 Carry Strategies

Explains carry as return from yield differentials, including FX carry, futures roll yield, and volatility risk premium strategies with their characteristic return profiles.

Tags: carry, yield, roll-yield, risk-premium

---

# 9. Glossary of Terms

A comprehensive alphabetized reference of 80+ trading terms with definitions. Each term includes its abbreviation (if applicable) and category for easy lookup. Categories include: Chart Patterns, Futures, Indicators, Market Structure, Order & Execution, Price Action, Psychology, Risk Management, Statistics & Quant, Technical Analysis, Trading Sessions, and Volume & Order Flow.

Tags: glossary, terminology, definitions, abbreviations, reference, alphabetical

---

# 10. Trading Signals Quick Reference

Alphabetical index of all 136 trading signals available in MangroveKnowledgeBase. Each signal entry includes its parent indicator (with link to full documentation in Chapter 6), signal type (Entry, Exit, Filter, Confirmation), category, and a human-readable description. For detailed parameters, usage examples, trading strategies, and combinations, see the parent indicator section in Chapter 6.

**How to use this reference:**
- Quick lookup by signal name alphabetically
- Find parent indicator for comprehensive documentation
- Organized by category (momentum, trend, volume, volatility)
- Links back to indicators chapter for full details
- For strategy rule planning: start here to identify signal names, then read Chapter 6 (Indicators) for the indicator definitions and usage details.

Tags: signals, quick-reference, alphabetical, index, api-reference, cross-reference

---

# Quick Reference Index

## By Topic

**Market Basics**: Chapters 1, 2
**Core Analysis**: Chapter 3
**Strategy & Risk**: Chapters 4, 5
**Technical Tools**: Chapters 6, 7
**Quantitative Methods**: Chapter 8
**Reference**: Chapters 9, 10

## By Skill Level

**Beginner**: 1.1-1.4, 2.1-2.2, 3.1-3.3, 3.6, 5.1-5.4, 7.1, 9
**Intermediate**: 1.5-1.8, 2.3-2.8, 3.4-3.11, 4.1-4.6, 5.5-5.7, 6.1-6.7, 7.2-7.7
**Advanced**: 4.7-4.12, 5.8-5.9, 8.1-8.8

## By Trading Style

**Day Trading**: 1.4, 3.1-3.5, 3.11, 4.1-4.3, 5.1-5.4, 6.1-6.3, 7.1-7.2
**Swing Trading**: 3.6-3.10, 4.1-4.6, 5.1-5.7, 6.1-6.4, 7.3-7.5
**Systematic/Quant**: 4.7-4.12, 5.5-5.9, 8.1-8.8

## Document Flow for Learning

1. **Foundations First**: Start with Chapters 1-3 for market and trading fundamentals
2. **Strategy & Risk**: Move to Chapters 4-5 to understand strategy design and risk management
3. **Technical Tools**: Learn Chapters 6-7 for indicators and patterns
4. **Advanced Quant**: Explore Chapter 8 for quantitative approaches
5. **Reference**: Use Chapters 9-10 as ongoing lookup resources

---
title: "Risk Management"
description: "Comprehensive risk management principles -- position sizing, stop-losses, portfolio risk, and drawdown management."
tags: ["risk", "position-sizing", "stop-loss", "drawdown", "risk-management", "portfolio-risk", "risk-dimensions", "skew", "win-rate", "tail-risk", "regime-risk", "strategy-risk", "trading-rules", "loss-limits", "protocols", "discipline", "fixed-fractional", "Kelly-Criterion", "ATR-sizing", "circuit-breaker", "recovery", "take-profit", "trailing-stop", "ATR-stop", "scale-out", "correlation", "VaR", "concentration", "diversification", "capital-efficiency", "leverage", "allocation", "margin", "risk-reward", "R:R", "expectancy", "risk-of-ruin", "survival", "Monte-Carlo", "scenario-analysis", "stress-testing", "contingency"]
source_type: trading
---

# 5. Risk Management

This document covers comprehensive risk management principles and techniques essential for preserving capital and achieving sustainable trading performance. Risk management is the foundation upon which all successful trading is built.

---

## 5.0 Risk Dimensions in Strategy Design

Before implementing specific risk controls, traders must understand that **risk is multi-dimensional**. Focusing on one dimension while ignoring others leads to false confidence.

### The Risk Dimensions Framework

| Dimension | Definition | What It Measures | Common Mistake |
|-----------|------------|------------------|----------------|
| **Per-Trade Risk** | Capital at risk on a single trade | Position size, stop loss distance | Confusing small stops with low risk |
| **Strategy Skew** | Shape of the return distribution | Positive (trend) vs. negative (MR) | Assuming high win rate = low risk |
| **Regime Risk** | Mismatch between strategy and market | Strategy applied to wrong conditions | Not adapting to changing markets |
| **Drawdown Risk** | Maximum capital decline | Peak-to-trough loss, recovery time | Ignoring time-in-drawdown |
| **Tail Risk** | Extreme loss probability | VaR, Expected Shortfall | Underestimating "black swan" events |
| **Correlation Risk** | Positions moving together | Portfolio-level diversification | "Diversification" failing in crisis |
| **Liquidity Risk** | Ability to exit positions | Slippage, market impact | Assuming orderly exits in stress |

### Why Win Rate Is Misleading

A common error is equating **high win rate with low risk**. This is dangerously wrong.

| Strategy Type | Win Rate | Skew | Tail Risk | Blow-Up Risk |
|---------------|----------|------|-----------|--------------|
| Trend Following | 30-40% | Positive | Moderate | **Low** |
| Mean Reversion | 60-70% | Negative | **High** | **High** |
| Carry | 70-80% | Negative | **High** | **High** |

**The Psychological Trap:**
- High win rate strategies feel safer because you win frequently
- This masks the tail risk: when you lose, you lose big
- A single large loss can wipe out months of accumulated small wins

> **CRITICAL WARNING:**  
> Do NOT suggest mean reversion or carry strategies are "safer" or "lower risk" based on win rate.  
> Their negative skew means tail losses are disproportionately large.

### Per-Trade Risk vs. Strategy Risk

**Common Misconception:** "I use tight stops, so my strategy is low risk."

**Reality:** Per-trade risk controls (position sizing, stop losses) do NOT change strategy-level risk.

| Control | What It Does | What It Does NOT Do |
|---------|--------------|---------------------|
| Tight stop loss | Limits loss on single trade | Does not change skew or regime risk |
| Small position size | Reduces dollar loss per trade | Does not prevent strategy blow-up |
| Diversification | Reduces single-asset risk | Fails when correlations spike |

**Example:**
- Mean reversion with 0.5% per-trade risk still has negative skew
- Many small losses can accumulate into large drawdown
- A regime change can cause all positions to fail simultaneously

### Strategy-Level Risk Assessment Checklist

Before deploying any strategy, answer these questions:

1. **What is the skew?** Positive (trend) or Negative (MR/carry)?
2. **What regime does it require?** Trending, ranging, or low volatility?
3. **What causes it to blow up?** Trend emergence? Volatility spike? Correlation breakdown?
4. **How long can drawdowns last?** Weeks? Months? Years?
5. **What is the maximum historical drawdown?** Can you survive it?
6. **How correlated are the positions?** Is diversification real or illusory?

### Practical Application

When evaluating or building a strategy:

1. **Classify the archetype** - Trend following, momentum, mean reversion, carry, event-driven
2. **Identify the skew** - Will wins or losses be larger on average?
3. **Define the failure mode** - Under what conditions does this strategy fail catastrophically?
4. **Size for the tail** - Position size assuming the worst-case scenario happens
5. **Monitor regime fit** - Continuously assess if market conditions suit the strategy

> **The First Rule of Risk:** Preserve capital. You cannot recover from total loss.

---

## 5.1 Trading Rules & Protocols

### Definition

Trading rules and protocols are predefined guidelines that govern trading behavior, risk limits, and decision-making processes. These rules establish boundaries that protect capital, enforce discipline, and remove emotional decision-making from trading operations.

### Core Principles

- **Pre-Commitment**: Rules must be established before trading, not during
- **Non-Negotiable Limits**: Certain rules (max loss, max positions) are absolute
- **Consistency**: Rules must be applied uniformly across all trades
- **Periodic Review**: Rules should be reviewed and adjusted based on performance data
- **Written Documentation**: All rules must be documented and accessible

### Risk Rules Reference Table

| Rule | Description | Default Value |
|------|-------------|---------------|
| Max Risk per Trade | Amount willing to lose on a single trade | 1% of account |
| Max Daily Loss | Daily drawdown limit before stopping trading | 5% of account |
| Max Weekly Loss | Weekly drawdown limit before break/cooldown | 10% of account |
| Max Open Trades | Maximum simultaneous positions | 25 positions |
| Reward-to-Risk Ratio | Minimum acceptable R:R for any setup | >= 2:1 |
| Position Sizing | Contracts per trade | (Account Balance x max risk) / (entry price - stop loss) |
| Cool Down Period | Time to stop trading after hitting daily loss | Remainder of the day |
| Trading Hours | Allowed trading window | 8:00 AM - 11:30 AM |
| Profit Lock Rule | Stop trading after hitting daily goal | 1%-2% gain (competition: >5%) |

### Implementation Framework

Implementation should behave like a pre-trade checklist with hard stops.

How to operationalize:

- Convert each rule into a measurable threshold (percent of equity, counts, ratios).
- Run the checks before opening a trade, not after.
- Treat violations as automatic "no trade" outcomes.
- Review and adjust thresholds on a schedule (monthly/quarterly), not during a drawdown.

Common failure modes:

- Risk is computed using a stop you would not actually execute.
- Multiple small, correlated positions create one big bet.
- "Make it back" sizing after losses (breaks survival math).

Toolkit: `TradingRules`, `check_trading_rules`, `daily_loss_limit_status` in `MangroveAI.domains.managers.risk_management_toolkit`.

### Best Practices for Trading Rules

- Document all rules in a trading plan before trading
- Review rules weekly and adjust based on performance metrics
- Never override rules during active trading sessions
- Use automated systems to enforce hard limits where possible
- Track rule violations and their outcomes in a trading journal
- Implement cool-down periods after hitting loss limits

---

## 5.2 Position Sizing

### Definition

Position sizing determines the amount of capital to allocate to each trade based on risk parameters, account size, and strategy characteristics. Proper position sizing balances potential returns against risk of ruin. The goal is to keep risk constant across trades regardless of entry price or volatility.

### Core Principles

- **Capital Preservation**: Position sizes should not threaten account survival
- **Risk Normalization**: Equal risk per trade, not equal dollar amount
- **Volatility Adjustment**: Higher volatility assets require smaller positions
- **Conviction Scaling**: Option to size based on signal strength
- **Portfolio Context**: Individual positions must fit portfolio constraints

### Common Use Cases

- Determining number of shares/contracts per trade
- Normalizing risk across different asset volatilities
- Managing overall portfolio exposure
- Scaling positions based on conviction
- Adapting to changing market conditions

---

### Fixed Fractional Position Sizing

**Definition:** Risk a fixed percentage of capital on each trade.

**Formula:**
Position Size = floor((Account Value x Risk Fraction) / abs(Entry Price - Stop Price))

Implementation note: See `MangroveAI.domains.managers.risk_management_toolkit.position_size_fixed_fractional`.

**Example:**
- Account: $100,000
- Risk per trade: 1% ($1,000)
- Entry: $50, Stop: $48
- Risk per share: $2
- Position size: $1,000 / $2 = 500 shares

**Recommended Risk Levels:**
- Conservative: 0.5% per trade
- Moderate: 1% per trade
- Aggressive: 2% per trade
- Maximum: 5% per trade (very risky)

---

### Volatility-Adjusted Position Sizing

**Definition:** Size positions inversely to asset volatility for equal risk contribution.

**Formula:**
Position Value = (Account Value x Target Volatility) / Asset Volatility
Position Size = floor(Position Value / Asset Price)

Implementation note: See `MangroveAI.domains.managers.risk_management_toolkit.position_size_volatility_target`.

**ATR-Based Sizing:**
Risk per Unit = ATR x ATR Multiplier
Position Size = floor((Account Value x Risk Fraction) / Risk per Unit)

Implementation note: See `MangroveAI.domains.managers.risk_management_toolkit.position_size_atr`.

---

### Kelly Criterion

**Definition:** Mathematically optimal bet size to maximize long-term growth.

**Formula:**
Kelly Fraction = W - (1 - W) / R

Where:
W = Win rate (probability of winning, 0-1)
R = Win/Loss ratio (average win / average loss)

**Implementation:**
Implementation note: See `MangroveAI.domains.managers.risk_management_toolkit.kelly_fraction` and `MangroveAI.domains.managers.risk_management_toolkit.fractional_kelly_fraction`.

**Caution:** Full Kelly is very aggressive. Most practitioners use Half-Kelly or Quarter-Kelly.

---

### Best Practices for Position Sizing

- Never risk more than 2% of account on single trade
- Use volatility-adjusted sizing for consistent risk
- Consider Kelly as upper bound, not target
- Account for correlation when sizing multiple positions
- Reduce size during drawdowns (some prefer fixed sizing)
- Include commission and slippage in risk calculations

### Universal Position Sizing Formula

The fundamental position sizing formula ensures consistent risk across all trades:

Position Size = (Account Balance x Risk per Trade) / abs(Entry Price - Stop Loss)

Implementation note: See `MangroveAI.domains.managers.risk_management_toolkit.position_size_fixed_fractional`.

**Example Calculation:**
- Account Balance: $50,000
- Risk per Trade: 1% ($500)
- Entry Price: $100
- Stop Loss: $95
- Risk per Share: $5
- Position Size: $500 / $5 = 100 shares

This formula normalizes risk regardless of the stock price or stop distance, ensuring each trade risks the same percentage of capital.

---

## 5.3 Drawdown Controls

### Definition

Drawdown controls are mechanisms to limit cumulative losses during adverse periods, protecting capital and allowing recovery. They trigger protective actions when losses exceed predefined thresholds.

### Core Principles

- **Survival First**: Preserving capital enables recovery
- **Circuit Breakers**: Automatic stops when losses accumulate
- **Recovery Math**: Larger drawdowns require exponentially larger recoveries
- **Psychological Protection**: Limits prevent emotional decision-making
- **Progressive Response**: Graduated actions as drawdown deepens

### Common Use Cases

- Daily loss limits for day traders
- Strategy-level drawdown stops
- Portfolio-level risk budgets
- Position reduction during adverse periods
- Trading suspension triggers

---

### Recovery Mathematics

| Drawdown | Required Recovery |
|----------|-------------------|
| 10% | 11.1% |
| 20% | 25% |
| 30% | 42.9% |
| 40% | 66.7% |
| 50% | 100% |
| 60% | 150% |
| 75% | 300% |

**Implication:** Avoiding large drawdowns is more important than maximizing returns.

---

### Maximum Drawdown Limits

Maximum drawdown limits are portfolio-level circuit breakers. They are not predictions; they are safety rails.

Practical guidance:

- Set a hard drawdown limit that halts trading (e.g., 20%).
- Add a warning level that forces size reduction (e.g., 10% if the limit is 20%).
- Decide resumption rules in advance (time-based cooldown, or performance-based reset).

Toolkit: `max_drawdown_action`.

---

### Progressive Drawdown Response

A progressive response reduces exposure as losses accumulate, which helps avoid keeping full size during your worst regime.

One simple ladder:

- 0-5% drawdown: normal
- 5-10%: caution (reduce size modestly)
- 10-15%: reduce (cut size materially)
- 15-20%: minimal (only highest quality trades)
- >20%: stop

Toolkit: `progressive_drawdown_response`.

---

### Daily Loss Limits

Daily loss limits protect you from both streaks and emotional decision-making after losses.

Implementation principles:

- Use a clear threshold in dollars or percent of equity (or both).
- Include a warning band (e.g., 80% of the limit) that forces reduced size.
- When the limit is hit, stop trading for the rest of the day.

Toolkit: `daily_loss_limit_status`.

---

### Time-Based Drawdown Recovery

Drawdown depth is only half the story. Time-in-drawdown matters because strategies can be statistically viable but psychologically impossible to follow.

Track:

- Frequency: how often you exceed a threshold.
- Duration: how long you remain above it.
- Trend: whether recovery time is increasing over months (possible regime change).

Toolkit: `drawdown_recovery_stats`.

---

### Best Practices for Drawdown Controls

- Set drawdown limits before trading, not during
- Use multiple levels (warning, reduce, stop)
- Include daily and cumulative limits
- Don't override limits during drawdown (emotional state)
- Have clear rules for resuming after drawdown stop
- Track time in drawdown as well as depth

---

## 5.4 Stop-Loss & Take-Profit Engineering

### Definition

Stop-loss (SL) and take-profit (TP) orders are predetermined exit points that define risk and reward for each trade. A stop-loss caps potential losses by automatically closing a position when price moves against you, while a take-profit locks in gains by closing when price reaches a target level. Well-engineered SL/TP levels balance protecting capital against allowing normal price fluctuations.

### Core Principles

- **Risk Definition**: Stop defines the risk per trade
- **Breathing Room**: Stops must allow normal volatility
- **Technical Validity**: Stops should be at meaningful levels
- **Time Consistency**: Stop logic should match trading timeframe
- **Execution Consideration**: Wide stops in illiquid markets

---

### Fixed Percentage Stop

Fixed percentage stops are simple, but volatility is not constant, so this method is easy to mis-calibrate.

When it works:

- Very liquid instruments with stable volatility.
- Short horizons where structure is unclear.

When it fails:

- High-volatility assets: frequent whipsaws.
- Trend days: too tight relative to ATR.

Toolkit: `fixed_percentage_stop`.

**Limitations:** Doesn't account for asset volatility or market structure.

---

### ATR-Based Stop

ATR-based stops scale with volatility, producing more consistent behavior across assets and regimes.

How to choose a multiplier:

- 1.5 ATR: tight, more whipsaws
- 2.0 ATR: common default
- 3.0 ATR: wide, fewer whipsaws but larger losses per stop

Calibration rule: pick a multiplier that matches your timeframe and validate it with backtests.

Toolkit: `atr_stop`.

**Recommended Multipliers:**
- Tight: 1.5 ATR (more whipsaws, quicker exit)
- Standard: 2.0 ATR (balanced)
- Wide: 3.0 ATR (fewer whipsaws, larger losses)

---

### Structure-Based Stop

Structure-based stops place the stop where the trade thesis is invalidated (e.g., below the swing low for a long).

Guidelines:

- Use obvious invalidation points (prior swing, range boundary, key level).
- Add a buffer (often ATR-based) to reduce stop hunts.
- If the stop is too far, reduce size or skip the trade; do not widen risk beyond plan.

Toolkit: `structure_stop`.

---

### Trailing Stop Variants

**Percentage Trailing:**
Percentage trailing is simple and works best in smooth trends. It often fails in choppy conditions.

Toolkit: `percentage_trailing_stop`.

**Chandelier Exit (ATR Trailing):**
Chandelier exits adapt to volatility by trailing from the best price by an ATR multiple.

Toolkit: `chandelier_exit`.

**Parabolic SAR-Based:**
Parabolic SAR is a momentum-based trailing mechanism. It tends to flip quickly in sideways markets.

Toolkit: `parabolic_sar_stop`.

---

### Break-Even Stop

Break-even stops reduce downside after the trade has proven itself, but they also increase the chance of getting stopped out before the real move.

Use a trigger:

- Trigger on profit fraction (e.g., +0.5% to +1%) or on an R multiple (e.g., 1R).
- Avoid moving to break-even too early in volatile markets.

Toolkit: `break_even_stop`.

---

### Stop Placement Guidelines

**Where NOT to Place Stops:**
- Exactly at round numbers (obvious to everyone)
- Exactly at obvious support/resistance (liquidity targets)
- Too tight (normal volatility triggers)
- Too wide (defeats purpose of risk management)

**Where to Place Stops:**
- Below significant swing lows (for longs)
- Above significant swing highs (for shorts)
- Beyond ATR-defined volatility range
- At levels that invalidate trade thesis

---

### Best Practices for Stop-Loss Engineering

- Use ATR for volatility-appropriate stops
- Place stops at technically meaningful levels
- Add buffer beyond obvious levels
- Trail stops as trade moves in favor
- Use break-even stops to lock in risk-free trades
- Don't move stops to increase loss (never widen)

### Take-Profit Strategies

**Fixed Target:**
- Set TP at predetermined price level based on structure or measured move
- Simple to implement but may leave profits on table

**Risk-Multiple Targets:**
- TP based on multiples of risk (1.5R, 2R, 3R)
- Ensures favorable risk-reward mathematics

**Partial Exits / Scale-Out:**
Scale-outs balance realized gains with participation in extended moves. A typical plan is 1.5R / 2R / 3R targets with a runner.

Risk controls:

- Define target fractions ahead of time (e.g., 33% / 33% / 34%).
- Move stops only according to plan (break-even after 1R, trail after 1.5R, etc.).

Toolkit: `scale_out_targets`.

**Trailing Behavior After Targets:**
- Move stop to break-even after 1R
- Trail stop to lock in 1R after 1.5R
- Trail stop to lock in 1.5R after 2R
- Let runner ride with trailing stop

### Stop-Loss Placement Guidelines

| Position | Stop Placement |
|----------|----------------|
| Long | Below support level or swing low |
| Short | Above resistance level or swing high |
| Volatility-Adjusted | Entry minus (ATR x 1.5 to 2.0) |

**Where NOT to Place Stops:**
- Exactly at round numbers (obvious to all)
- Exactly at obvious support/resistance (liquidity targets)
- Too tight (normal volatility triggers)
- Too wide (defeats risk management purpose)

---

## 5.5 Portfolio Risk

### Definition

Portfolio risk management addresses the aggregate risk of multiple positions, considering correlations, concentration, and the interaction effects between positions.

### Core Principles

- **Diversification**: Reduce risk through uncorrelated positions
- **Correlation Awareness**: Correlated positions multiply risk
- **Concentration Limits**: No single position dominates portfolio
- **Sector/Factor Exposure**: Monitor and limit exposure concentrations
- **Tail Risk**: Consider extreme scenarios where correlations spike

---

### Correlation-Adjusted Position Sizing

Correlation-adjusted sizing prevents accidental concentration. When assets are highly correlated, "diversification" is an illusion.

Practical approach:

- Compute covariance from recent returns.
- Estimate portfolio volatility under target weights.
- Scale weights down if volatility exceeds your budget.

Toolkit: `correlation_adjusted_weights`, `portfolio_volatility_from_covariance`.

---

### Concentration Limits

Concentration limits cap the damage from a single bad thesis.

Toolkit: `check_concentration_limits`.

**Typical Concentration Limits:**
- Single position: 5-10% of portfolio
- Sector: 20-30% of portfolio
- Asset class: 40-60% of portfolio
- Correlated cluster: 15-25% of portfolio

---

### Value at Risk (VaR)

**Definition:** Maximum expected loss over a time period at a confidence level.

VaR is a quantile of the loss distribution. It is a communication and budgeting tool, not a guarantee.

Key caveats:

- VaR ignores the severity beyond the threshold (tail risk).
- VaR depends heavily on the chosen window and regime.

Toolkit: `value_at_risk_historical`.

**Interpretation:** 95% VaR of 2% means there's a 5% chance of losing more than 2% on any given day.

---

### Expected Shortfall (CVaR)

**Definition:** Expected loss given that loss exceeds VaR (average of worst cases).

Expected Shortfall (CVaR) estimates the average loss in the worst tail and is generally more informative than VaR for risk control.

Toolkit: `expected_shortfall_historical`.

**Use:** More informative than VaR for tail risk assessment.

---

### Portfolio Beta and Market Exposure

Portfolio beta estimates sensitivity to a broad market factor. It helps answer: "If the market drops 1%, how much should I expect to lose?"

Good practice:

- Compute beta over multiple windows (short and medium term).
- Treat beta as a moving estimate, not a constant.

Toolkit: `portfolio_beta`.

---

### Best Practices for Portfolio Risk

- Monitor correlation changes, especially during stress
- Maintain diversification across uncorrelated strategies
- Set and enforce concentration limits
- Calculate VaR/ES regularly
- Stress test portfolio for extreme scenarios
- Consider gross and net exposure separately

---

## 5.6 Capital Efficiency

### Definition

Capital efficiency measures how effectively capital is deployed to generate returns, balancing the use of leverage, margin, and buying power against risk.

### Core Principles

- **Return on Capital**: Maximize risk-adjusted returns per dollar deployed
- **Margin Efficiency**: Use margin wisely without excessive leverage
- **Cash Management**: Maintain appropriate cash buffers
- **Opportunity Cost**: Unused capital has cost (opportunity)
- **Leverage Trade-offs**: Leverage increases both returns and risk

---

### Capital Allocation Framework

Capital allocation should separate "risk budget" from "capital budget." The same dollar allocation can produce very different risk.

Guidelines:

- Reserve a cash buffer (for margin calls, volatility spikes, opportunities).
- Define allocation weights per strategy and review periodically.
- Avoid reallocating reactively based on short-term performance.

Toolkit: `allocate_capital`.

---

### Leverage Management

Leverage is exposure relative to equity. It amplifies both returns and drawdowns.

Monitor:

- Gross leverage (sum of absolute exposures / equity)
- Net leverage (net exposure / equity)
- Long/short balance (for hedged books)

Toolkit: `effective_leverage`.

**Recommended Leverage Limits:**
- Conservative: 1x gross
- Moderate: 2x gross
- Aggressive: 3-4x gross
- Maximum institutional: 6-8x gross (hedge funds)

---

### Capital Utilization Metrics

Capital utilization matters because deploying capital without a risk budget is a common failure mode.

Simple metrics:

- Utilization = capital deployed / max capital
- Return on deployed capital (annualized)
- Return on max capital (return on deployed x utilization)
- Efficiency ratio (return on deployed / utilization)

Toolkit: `capital_efficiency_metrics`.

---

### Best Practices for Capital Efficiency

- Maintain cash buffer for opportunities and margin calls
- Monitor leverage continuously, not just at trade entry
- Calculate return on total capital, not just deployed capital
- Consider margin requirements in position sizing
- Balance capital efficiency against liquidity needs

---

## 5.7 Risk-Reward Ratios

### Definition

Risk-reward ratio (R:R) compares the potential profit of a trade to its potential loss. It is a fundamental metric for evaluating trade quality and setting realistic expectations.

### Core Principles

- **Minimum Standards**: Set minimum R:R thresholds for trades
- **Win Rate Relationship**: Lower win rate requires higher R:R
- **Realistic Targets**: Targets must be achievable, not aspirational
- **Risk-First Thinking**: Define risk before considering reward
- **System Expectancy**: Combine R:R with win rate for expectancy

---

### Risk-Reward Calculation

Risk-reward is only meaningful if the stop is real and the target is realistic.

Checklist:

- Stop is placed at invalidation (not a random percent).
- Target is based on structure (not hope).
- If computed risk is non-positive, the setup is invalid.

Toolkit: `risk_reward_ratio`.

---

### Win Rate and R:R Relationship

**Break-Even Win Rate:**
Break-even Win Rate = 1 / (1 + R:R)

Toolkit: `breakeven_win_rate`.

| R:R Ratio | Break-Even Win Rate |
|-----------|---------------------|
| 0.5:1 | 66.7% |
| 1:1 | 50% |
| 1.5:1 | 40% |
| 2:1 | 33.3% |
| 3:1 | 25% |

---

### Expectancy Calculation

**Definition:** Expected return per dollar risked.

Expectancy summarizes your edge:

- Expectancy = (Win Rate x Avg Win) - ((1 - Win Rate) x Avg Loss)

Toolkit: `expectancy`.

**R-Multiple Expectancy:**
Use R-multiples to compare strategies across assets and timeframes.

Toolkit: `r_multiple_expectancy`.

---

### Setting Realistic Targets

Targets should be achievable given volatility and nearby structure.

Sanity checks:

- Target distance in ATR multiples (very large multiples are rarely hit).
- Obstacles between entry and target (major levels, ranges, pivots).
- If the target requires a market regime change, it is not a target, it is a dream.

Toolkit: `evaluate_target_realism` is not implemented in the toolkit; treat this as a framework to build per-strategy.

---

### Best Practices for Risk-Reward

- Set minimum R:R requirement (typically 1.5:1 or 2:1)
- Calculate R:R before entering trade
- Ensure target is realistic given market structure
- Track actual R:R achieved vs. planned
- Combine R:R with win rate for complete picture

---

## 5.8 Risk of Ruin

### Definition

Risk of ruin is the probability of losing a specified percentage of capital (often defined as 50% or total loss) based on position sizing and strategy characteristics. It quantifies the survivability of a trading approach.

### Core Principles

- **Survival Probability**: Trading survival is prerequisite for profits
- **Edge and Sizing**: Ruin depends on edge size and bet size
- **Compounding Effect**: Small edges compounded beat large bets
- **Conservative Sizing**: Lower bet sizes dramatically reduce ruin probability
- **Long-Term Perspective**: Even small ruin probability matters over time

---

### Risk of Ruin Formula

**Classic Formula (Simplified):**
Risk of ruin depends primarily on edge and risk-per-trade. Small increases in risk-per-trade can massively increase ruin probability.

Toolkit: `risk_of_ruin_classic`.

---

### Monte Carlo Ruin Estimation

Monte Carlo simulation helps model streaks and compounding. Use conservative assumptions.

Toolkit: `monte_carlo_ruin`.

---

### Risk Per Trade vs. Ruin Probability

| Risk Per Trade | Approximate Ruin Probability* |
|----------------|------------------------------|
| 1% | < 1% |
| 2% | 1-5% |
| 5% | 5-20% |
| 10% | 20-50% |
| 20% | > 50% |

*Assumes modest positive edge (55% win rate, 1:1 R:R)

---

### Reducing Risk of Ruin

Treat risk-per-trade as the main dial:

- Reduce risk-per-trade during drawdowns.
- Use fraction-of-Kelly as a ceiling, not a target.
- Prefer robustness over theoretical optimality.

Toolkit: `safe_risk_fraction_for_target_ruin`, `fractional_kelly_fraction`.

---

### Best Practices for Risk of Ruin

- Keep risk per trade below 2% for sustainable trading
- Understand that even 1% ruin probability compounds over time
- Use Monte Carlo simulation for realistic estimates
- Reduce position size during losing streaks
- Never risk total capital on any single strategy
- Have capital reserves outside trading account

---

## 5.9 Scenario Analysis

### Definition

Scenario analysis evaluates portfolio performance under specific hypothetical market conditions, including historical stress events and constructed worst-case scenarios.

### Core Principles

- **Stress Testing**: Test portfolio against extreme conditions
- **Historical Scenarios**: Use past crises as test cases
- **Hypothetical Scenarios**: Construct plausible adverse scenarios
- **Correlation Changes**: Model correlation increases during stress
- **Tail Events**: Focus on outcomes beyond normal distribution

---

### Historical Stress Tests

Historical stress tests approximate: "What would have happened if we lived through that again?"

Important:

- Stress tests are scenarios, not forecasts.
- Include correlation spikes (diversification breaks in crises).

Toolkit: `historical_stress_test`.

---

### Hypothetical Scenario Construction

Hypothetical scenarios let you test combinations you have not experienced in the data.

Approach:

- Start from a base scenario and apply adjustments (worse equities, worse bonds, vol shock).
- Include a liquidity shock (wider spreads, bigger gaps) in operational planning.

Toolkit: `construct_scenario`.

---

### Correlation Stress Testing

Correlation stress testing asks: "What if correlations move toward 1?" This is often the real risk in diversified portfolios.

Practical steps:

- Compute volatility under normal covariance.
- Replace covariance/correlation with a stressed version and recompute.
- Compare the increase; size down if the stressed case is unacceptable.

Toolkit: `correlation_adjusted_weights`, `portfolio_volatility_from_covariance`.

---

### Tail Risk Analysis

Tail risk analysis focuses on the worst outcomes rather than the average.

What to watch:

- Left tail mean and worst loss (bad days)
- Right tail mean and best gain (good days)
- Tail ratio (are good tails large enough to justify bad tails?)

Toolkit: `tail_risk_analysis`.

---

### Scenario Action Plans

Scenario action plans turn risk metrics into behavior so you are not improvising under stress.

Example actions:

- Severe scenario: cut risk in half, remove leverage, raise cash
- Moderate: reduce size, tighten risk controls, add hedges
- Mild: monitor and review exposures

Toolkit: `scenario_response_plan`.

---

### Best Practices for Scenario Analysis

- Test against both historical and hypothetical scenarios
- Include correlation breakdown in stress scenarios
- Update scenarios as market conditions evolve
- Have pre-defined action plans for each scenario
- Run scenarios regularly (monthly or quarterly)
- Include scenarios where multiple risks occur simultaneously

---

## Summary

Risk management is the foundation of sustainable trading success:

1. **Position Sizing**: Risk appropriate amounts per trade
2. **Drawdown Controls**: Protect against cumulative losses
3. **Stop-Loss Engineering**: Balance protection against whipsaws
4. **Portfolio Risk**: Manage aggregate exposure and correlation
5. **Capital Efficiency**: Deploy capital wisely
6. **Risk-Reward**: Ensure favorable trade mathematics
7. **Risk of Ruin**: Ensure long-term survival
8. **Scenario Analysis**: Prepare for adverse conditions

**The First Rule of Trading:** Preserve capital. You cannot recover from total loss.

**The Second Rule:** See Rule One.

Successful traders are not those who never lose, but those who manage losses so they can continue trading and capitalize on future opportunities.


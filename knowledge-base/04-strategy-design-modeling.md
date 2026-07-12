# 4. Strategy Design & Modeling

This document covers the principles and methodologies for designing, developing, and validating systematic trading strategies, from initial concept through backtesting to deployment.

---

## 4.1 Trading Styles

### Definition

Trading styles define the **timeframe and execution cadence** a trader uses to engage with markets. Trading style is independent of strategy logic and reflects constraints such as available time, attention, and risk tolerance.

> **Important Distinction:**  
> *Trading style defines **when** you trade. Strategy archetypes define **why** a trade has edge.*

### Core Principles

- **Timeframe Selection**: Choose style based on available time, personality, and goals
- **Consistency**: Stick to one primary style rather than mixing approaches
- **Capital Requirements**: Different styles have different capital and margin needs
- **Risk Profile**: Each style has characteristic risk/reward patterns
- **Lifestyle Fit**: Trading style must align with personal schedule and temperament

### Trading Style Comparison

| Style | Timeframe | Holding Period | Key Traits |
|-------|-----------|----------------|------------|
| Scalping | Seconds to minutes | Seconds to minutes | Tiny moves, high volume, requires intense focus |
| Day Trading | Minutes to hours | Same day | Exploit intraday moves, avoid overnight risk |
| Swing Trading | Days to weeks | Days to weeks | Fewer trades, larger moves, higher selectivity |
| Position Trading | Weeks to months | Weeks to months | Regime- or fundamentally driven |

### Scalping

**Characteristics:**
- Trade duration: Seconds to a few minutes
- Profit targets: 1-10 ticks/pips
- High frequency: Dozens to hundreds of trades per day
- Requires: Fast execution, tight spreads, intense focus

**Best For:** Full-time traders with direct market access and low commissions.

**Challenges:** High transaction costs, requires constant attention, mentally exhausting.

### Day Trading

**Characteristics:**
- Trade duration: Minutes to hours
- All positions closed by market close
- No overnight risk exposure
- Typical trades: 1-10 per day

**Best For:** Traders who can dedicate market hours to active trading.

**Advantages:** No overnight gap risk, fresh start each day, compounds learning quickly.

### Swing Trading

**Characteristics:**
- Trade duration: Days to weeks
- Captures multi-day price swings
- Fewer trades, higher quality setups
- Can be done with a full-time job

**Best For:** Part-time traders, those seeking work-life balance.

**Advantages:** Less screen time, larger profit targets, lower transaction costs as percentage of gains.

### Best Practices for Style Selection

- Match trading style to available time and lifestyle
- Start with longer timeframes (swing) before attempting shorter (day/scalp)
- Account for transaction costs relative to target profits
- Consider psychological fit: can you hold overnight? Can you focus for hours?
- Paper trade the style before committing capital

---

## 4.2 Strategy Archetypes

### Definition

Strategy archetypes classify trading strategies by the **market behavior they exploit**, not by timeframe or instrument. Archetypes describe *why* a strategy has expected positive return under certain conditions.

### Core Principles

- **Behavioral Alignment**: Each archetype exploits a specific market dynamic
- **Regime Dependence**: Archetypes rotate in effectiveness across regimes
- **Style Purity**: Mixing archetypes without intention creates fragile strategies
- **Distinct Risk Profiles**: Each archetype has characteristic skew and drawdowns
- **Complementarity**: Robust systems often combine multiple archetypes with clear hierarchy

### Common Use Cases

- Strategy selection based on market conditions
- Portfolio diversification across archetypes
- Understanding strategy performance attribution
- Designing hybrid approaches with clear signal hierarchy
- Setting appropriate expectations for win rate and skew

---

### Trend Following

**Core Premise:** Markets exhibit persistent directional regimes driven by sustained capital flows.

**What it answers:**  
> *Should we be exposed in this direction?*

**Mechanism:**
- Identify sustained directional movement
- Enter after trend confirmation
- Exit on regime break, not noise

**Risk Profile:**
- Win Rate: 30-40% (low)
- Skew: POSITIVE (occasional large wins)
- Tail Risk: MODERATE - losses are bounded by stops
- Drawdowns: Extended choppy periods cause bleeding

**Characteristics:**
- Large winners offset frequent small losses
- Performs well in trending markets
- Underperforms in range-bound markets
- Positive skew means you profit from fat tails

**Example Strategies:**
- Moving average crossovers
- Donchian channel breakouts
- Time-series momentum
- Managed futures / CTA strategies

> **Risk Warning:** Trend following has LOW win rate. Do NOT expect to be right often. The edge comes from letting winners run far enough to compensate for frequent small losses.

---

### Momentum

**Core Premise:** Price movement exhibits short-term persistence due to acceleration, positioning pressure, and behavioral effects.

**What it answers:**  
> *Is directional pressure increasing or fading right now?*

**Mechanism:**
- Measure rate of change or acceleration
- Enter during expansion of pressure
- Exit as momentum decays

**Risk Profile:**
- Win Rate: 50-60% (moderate)
- Skew: NEUTRAL to slightly positive
- Tail Risk: MODERATE - vulnerable to sharp reversals
- Drawdowns: Quick reversals can trap momentum traders

**Characteristics:**
- Higher win rate than trend following
- Shorter holding periods
- Vulnerable to sharp reversals
- Works both within and outside trends

**Example Strategies:**
- RSI / ROC momentum
- MACD-based systems
- Cross-sectional momentum
- Short-term continuation models

> **Relationship to Trend Following:**  
> Trend defines *regime*. Momentum defines *timing*.  
> In practice, trend is often used as a filter and momentum as an entry/exit engine.

---

### Breakouts (Transition Archetype)

**Core Premise:** Periods of volatility compression are followed by expansion as new information is revealed.

**What it answers:**  
> *Is a new move beginning?*

**Role in Systems:**
- Often marks **trend initiation**
- Combines momentum entry with trend potential
- Accepts false breakouts as cost of discovery

**Risk Profile:**
- Win Rate: 40-50%
- Skew: POSITIVE (breakouts that work tend to run)
- Tail Risk: MODERATE - false breakouts are common
- Drawdowns: Choppy markets produce many false signals

**Example Strategies:**
- Range breakouts
- Volatility squeeze breakouts (Bollinger Band squeeze)
- Opening range breakouts

> **Usage Note:** Breakouts bridge momentum (entry timing) and trend (regime establishment). They work best when combined with regime filters.

---

### Volatility

**Core Premise:** Profit from significant price movements regardless of direction.

**What it answers:**  
> *Is the market moving enough to capture profitable swings?*

**Mechanism:**
- Trade when volatility expands
- Direction-agnostic (long or short based on breakout direction)
- Exit when volatility contracts or move exhausts

**Risk Profile:**
- Win Rate: 30-50%
- Skew: NEUTRAL to slightly positive
- Tail Risk: MODERATE - whipsaws during false breakouts
- Drawdowns: Choppy, range-bound markets produce losses

**Characteristics:**
- Works in both trending and ranging markets
- Requires volatility to capture meaningful moves
- Often uses ATR, Bollinger Bands, or volatility indicators
- Not directionally biased

**Example Strategies:**
- ATR breakout strategies
- Bollinger Band squeeze breakouts
- Straddle/strangle equivalents in spot
- Keltner Channel expansions
- Volatility expansion trades

> **Usage Note:** Volatility strategies don't predict direction - they trade movement size. Best in markets with alternating quiet and active periods.

---

### Mean Reversion

**Core Premise:** Prices temporarily deviate from equilibrium and revert as liquidity providers and arbitrageurs act.

**What it answers:**  
> *Has price extended too far from fair value?*

**Mechanism:**
- Buy oversold conditions
- Sell overbought conditions
- Exit near perceived mean

**Risk Profile:**
- Win Rate: 60-70% (high)
- Skew: NEGATIVE (occasional large losses)
- Tail Risk: HIGH - can fail catastrophically during trend emergence
- Drawdowns: Single large losses can wipe out many small wins

**Characteristics:**
- High win rate is psychologically seductive
- Performs best in range-bound regimes
- **DANGEROUS** in trending markets
- Negative skew means tail losses are disproportionately large

**Example Strategies:**
- RSI mean reversion
- Bollinger Band reversion
- Pairs trading
- Statistical arbitrage

> **CRITICAL WARNING:**  
> **DO NOT describe mean reversion as "lower risk" or "safer."**  
> High win rate does NOT equal low risk. The negative skew means losses, when they occur, are disproportionately large. Mean reversion strategies can and do blow up when trends emerge.  
> "The trend is your friend" exists because fighting trends is dangerous.

---

### Archetype Risk Summary Table

| Archetype | Win Rate | Skew | Tail Risk | Best Regime |
|-----------|----------|------|-----------|-------------|
| Trend Following | 30-40% | Positive | Moderate | Strong trends |
| Momentum | 50-60% | Neutral | Moderate | Any with clear direction |
| Volatility | 40-50% | Neutral | Moderate | High volatility periods |
| Breakouts | 40-50% | Positive | Moderate | After compression |
| Mean Reversion | 60-70% | **Negative** | **High** | Range-bound only |

---

### Archetype Contraindications

| Archetype | DO NOT USE WHEN | Why It Fails |
|-----------|-----------------|--------------|
| Trend Following | Choppy/range-bound markets | Whipsaws accumulate losses |
| Momentum | End of trend / momentum divergence | Reversal traps |
| Volatility | Sustained low volatility | No meaningful moves to capture |
| Breakouts | Low volatility / no compression | False breakouts dominate |
| Mean Reversion | **Strong directional trends** | **Will blow up** |

---

### Best Practices for Archetype Selection

- Match archetypes to current market regime
- Combine complementary archetypes with clear hierarchy
- Understand skew and tail risk for each archetype
- **Never combine conflicting archetypes without explicit priority** (e.g., momentum vs mean reversion)
- Monitor regime transitions and adapt allocation
- Size positions according to archetype risk profile, not just win rate

---

## 4.3 Building a Trade Plan

### Definition

A trade plan is a comprehensive document that defines all aspects of your trading approach, including entry criteria, exit rules, risk parameters, and psychological guidelines. It serves as your trading rulebook and removes emotional decision-making from the trading process.

### Core Principles

- **Pre-Definition**: All rules defined before trading, not during
- **Specificity**: Rules must be clear enough that another trader could execute them
- **Completeness**: Plan covers all scenarios: entry, exit, sizing, timing
- **Documentation**: Written down and accessible during trading
- **Evolution**: Reviewed and updated based on performance data

### Trade Plan Components

#### 1. Entry Criteria

Conditions required before taking a trade:
- Price action setup (pattern, structure break, etc.)
- Indicator alignment (trend confirmation, momentum)
- Volume confirmation requirements
- Higher timeframe alignment
- Minimum reward-to-risk threshold

```python
def entry_checklist(setup):
    """
    Validate all entry conditions are met
    """
    criteria = {
        'price_action_setup': setup.has_valid_pattern(),
        'trend_alignment': setup.higher_tf_trend == setup.trade_direction,
        'indicator_confirmation': setup.indicators_aligned(),
        'volume_confirmation': setup.volume > setup.avg_volume,
        'rr_threshold': setup.reward_risk >= 2.0,
    }
    
    # All criteria must be True
    return all(criteria.values()), criteria
```

#### 2. Confirmation Rules

Additional validation before execution:
- Wait for candle close (don't enter on wick)
- Retest of broken level
- Volume spike on breakout
- Indicator crossover completion

#### 3. Exit Criteria

**Stop-Loss Rules:**
- Technical placement (below support, above resistance)
- ATR-based calculation (e.g., 1.5x ATR)
- Maximum dollar/percentage loss per trade

**Take-Profit Rules:**
- Technical targets (next resistance/support)
- Risk-multiple targets (1.5R, 2R, 3R)
- Partial exit strategy (scale out at levels)

**Trailing Stop Rules:**
- When to activate trailing stop
- How much to trail (fixed % or ATR-based)

**Indicator-Driven Exits:**
- Specific conditions that signal exit regardless of P/L

### Trade Plan Template

```
TRADE PLAN: [Strategy Name]
Date: [Creation Date]
Last Updated: [Date]

MARKET & TIMEFRAME:
- Markets traded: [e.g., ES, NQ, BTC]
- Primary timeframe: [e.g., 15-min]
- Higher timeframe for context: [e.g., 4-hour]

ENTRY RULES:
1. [Specific condition 1]
2. [Specific condition 2]
3. [Specific condition 3]
- Minimum R:R required: [e.g., 2:1]

CONFIRMATION:
- [What confirms the entry]

EXIT RULES:
- Stop-loss: [How determined]
- Take-profit 1: [Level and size]
- Take-profit 2: [Level and size]
- Trailing stop: [When and how]

POSITION SIZING:
- Risk per trade: [e.g., 1% of account]
- Maximum positions: [e.g., 3]

TRADING HOURS:
- [e.g., 8:00 AM - 11:30 AM EST]

DAILY RULES:
- Max daily loss: [e.g., 3%]
- Stop trading after: [e.g., 3 consecutive losses]
```

### Best Practices for Trade Plans

- Write your plan when not actively trading (clear head)
- Be specific: vague rules lead to inconsistent execution
- Include "what if" scenarios and how to handle them
- Review plan performance weekly/monthly
- Update based on data, not emotions or single trades
- Treat the plan as non-negotiable during trading hours

---

## 4.4 Signal Types

### Definition

Signal types classify trading signals by their role in the decision-making process. Understanding signal types helps traders combine signals effectively and build robust strategies.

### The Four Signal Types

| Type | Purpose | When It Fires | Example |
|------|---------|---------------|---------|
| **Entry** | Triggers opening a new position | When conditions favor starting a trade | `macd_bullish_cross` - MACD line crosses above signal line |
| **Exit** | Triggers closing an existing position | When conditions suggest ending a trade | `rsi_overbought` - RSI exceeds 70, indicating potential reversal |
| **Filter** | Screens out trades / Sets context | Continuous condition check that gates other signals | `adx_strong_trend` - Only trade when ADX > 25 |
| **Confirmation** | Validates another signal | Secondary check that strengthens conviction | `macd_positive` - Histogram positive confirms bullish momentum |

### Mapping Signal Types to Archetypes

| Archetype | Typical Signal Role |
|-----------|---------------------|
| Trend Following | **Filter** - Establishes directional context |
| Momentum | **Entry / Exit** - Times entries and exits |
| Mean Reversion | **Entry** - Triggers counter-trend position |
| Regime Detection | **Meta-Filter** - Gates which archetypes to deploy |

### How Signal Types Work Together

A typical strategy combines multiple signal types:

```python
def generate_trade_signal(data):
    """
    Combine signal types for robust decision-making
    """
    # FILTER: Is the environment right for trading?
    if not filter_price_above_200_sma(data):
        return None  # Only trade in uptrend
    
    # ENTRY: Should we get in now?
    if not entry_rsi_oversold(data):
        return None  # Wait for entry trigger
    
    # CONFIRMATION: Are we sure?
    if not confirmation_macd_positive(data):
        return None  # Need momentum confirmation
    
    return "LONG"  # All conditions met

def check_exit(data, position):
    """
    Exit signals close positions
    """
    if position == "LONG":
        if exit_rsi_overbought(data):
            return "CLOSE"
    return "HOLD"
```

### Signal Type Characteristics

**Entry Signals:**
- Fire at specific moments when trade setup is complete
- Typically require immediate action
- Often based on crossovers, breakouts, or pattern completions
- Examples: `sma_cross_up`, `macd_bullish_cross`, `rsi_oversold`

**Exit Signals:**
- Indicate when to close existing positions
- Can be based on profit targets, stop losses, or reversal conditions
- Should be defined before trade entry
- Examples: `sma_cross_down`, `macd_bearish_cross`, `rsi_overbought`

**Filter Signals:**
- Provide ongoing context rather than discrete triggers
- Answer: "Should we be trading in this direction at all?"
- Reduce false signals by ensuring market environment is favorable
- Examples: `is_above_sma`, `adx_strong_trend`, `vwap_above`

**Confirmation Signals:**
- Add conviction to entry signals
- Reduce false positives by requiring multiple conditions
- Often come from different indicator categories (trend + momentum + volume)
- Examples: `macd_positive`, `obv_bullish`, `bb_squeeze`

### Best Practices for Signal Types

- **Layer signals intentionally**: Filter -> Entry -> Confirmation is a common flow
- **Don't over-confirm**: 2-3 signals is usually sufficient; more adds lag
- **Match signal types to archetype**: Trend-following needs different filters than mean reversion
- **Test signal combinations**: Backtest which combinations improve expectancy
- **Document signal roles**: Know why each signal is in your strategy

---

## 4.5 Entry Logic Frameworks

### Definition

Entry logic frameworks are systematic approaches for determining when to initiate positions. A robust entry framework provides clear, repeatable criteria that generate consistent signal quality.

### Core Principles

- **Objectivity**: Rules should be unambiguous and programmable
- **Edge Definition**: Understand why the entry has expected positive return
- **Confirmation**: Multiple confirming factors improve reliability
- **Timing**: Entry timing affects risk/reward ratio
- **Filter Quality**: Pre-entry filters reduce false signals

---

### Signal Generation Approaches

**Indicator-Based:**
```python
def indicator_entry(data, indicator_threshold):
    """
    Enter when indicator crosses threshold
    """
    indicator_value = calculate_indicator(data)
    signal = indicator_value > indicator_threshold
    return signal
```

**Pattern-Based:**
```python
def pattern_entry(data, pattern_func):
    """
    Enter when pattern is detected
    """
    pattern_detected = pattern_func(data)
    return pattern_detected
```

**Statistical-Based:**
```python
def statistical_entry(returns, threshold_zscore=2):
    """
    Enter on statistical deviation
    """
    zscore = (returns - returns.mean()) / returns.std()
    long_signal = zscore < -threshold_zscore
    short_signal = zscore > threshold_zscore
    return long_signal, short_signal
```

---

### Entry Confirmation Methods

**Multi-Factor Confirmation:**
```python
def multi_factor_entry(data):
    """
    Require multiple signals to align
    """
    trend_signal = calculate_trend_signal(data)
    momentum_signal = calculate_momentum_signal(data)
    volume_signal = calculate_volume_signal(data)
    
    # Require at least 2 of 3 signals
    confirmation_count = trend_signal + momentum_signal + volume_signal
    entry = confirmation_count >= 2
    return entry
```

**Timeframe Confirmation:**
```python
def multi_timeframe_entry(data_dict):
    """
    Require alignment across timeframes
    """
    htf_trend = calculate_trend(data_dict['daily'])
    mtf_signal = calculate_signal(data_dict['4h'])
    ltf_trigger = calculate_trigger(data_dict['1h'])
    
    # Long: HTF uptrend + MTF bullish + LTF trigger
    long_entry = (htf_trend > 0) & (mtf_signal > 0) & ltf_trigger
    return long_entry
```

---

### Entry Timing Refinements

**Pullback Entry:**
```python
def pullback_entry(price, trend_signal, pullback_threshold=0.02):
    """
    Enter on pullback within trend
    """
    recent_high = price.rolling(20).max()
    pullback_pct = (recent_high - price) / recent_high
    
    entry = trend_signal & (pullback_pct > pullback_threshold)
    return entry
```

**Breakout Entry:**
```python
def breakout_entry(price, period=20):
    """
    Enter on breakout of recent range
    """
    high = price.rolling(period).max()
    low = price.rolling(period).min()
    
    long_entry = price > high.shift(1)
    short_entry = price < low.shift(1)
    return long_entry, short_entry
```

---

### Entry Filters

**Regime Filter:**
```python
def regime_filtered_entry(signal, regime):
    """
    Only trade in favorable regime
    """
    favorable_regime = regime == 'trending'
    filtered_signal = signal & favorable_regime
    return filtered_signal
```

**Volatility Filter:**
```python
def volatility_filtered_entry(signal, volatility, min_vol, max_vol):
    """
    Avoid extremes of volatility
    """
    vol_okay = (volatility > min_vol) & (volatility < max_vol)
    filtered_signal = signal & vol_okay
    return filtered_signal
```

---

### Best Practices for Entry Logic

- Define entry criteria precisely before coding
- Use multiple confirmation factors
- Test entries with various exit rules to isolate entry quality
- Track entry efficiency (how far price moves from entry in intended direction)
- Avoid overly complex entry rules that overfit
- Include regime and volatility filters

---

## 4.6 Exit Logic

### Definition

Exit logic determines when to close positions. Effective exit management is often more important than entry timing for overall strategy performance.

### Core Principles

- **Protect Capital**: Exits should limit losses first, maximize gains second
- **Let Winners Run**: Don't exit winning trades prematurely
- **Cut Losers Short**: Remove losing positions quickly
- **Rule-Based**: Exits should be as systematic as entries
- **Exit Reason**: Know why you're exiting (stop, target, time, signal)

---

### Stop-Loss Exits

**Fixed Stop:**
```python
def fixed_stop_exit(entry_price, current_price, stop_pct=0.02, direction='long'):
    """
    Exit on fixed percentage loss
    """
    if direction == 'long':
        stop_price = entry_price * (1 - stop_pct)
        exit_signal = current_price <= stop_price
    else:
        stop_price = entry_price * (1 + stop_pct)
        exit_signal = current_price >= stop_price
    return exit_signal, stop_price
```

**ATR-Based Stop:**
```python
def atr_stop_exit(entry_price, current_price, atr, multiplier=2.0, direction='long'):
    """
    Exit based on ATR distance
    """
    stop_distance = atr * multiplier
    if direction == 'long':
        stop_price = entry_price - stop_distance
        exit_signal = current_price <= stop_price
    else:
        stop_price = entry_price + stop_distance
        exit_signal = current_price >= stop_price
    return exit_signal, stop_price
```

---

### Profit Target Exits

**Fixed Target:**
```python
def fixed_target_exit(entry_price, current_price, target_pct=0.04, direction='long'):
    """
    Exit on fixed percentage profit
    """
    if direction == 'long':
        target_price = entry_price * (1 + target_pct)
        exit_signal = current_price >= target_price
    else:
        target_price = entry_price * (1 - target_pct)
        exit_signal = current_price <= target_price
    return exit_signal, target_price
```

**Risk-Multiple Target:**
```python
def risk_multiple_target(entry_price, stop_price, risk_multiple=2.0, direction='long'):
    """
    Target based on multiple of risk
    """
    risk = abs(entry_price - stop_price)
    if direction == 'long':
        target = entry_price + (risk * risk_multiple)
    else:
        target = entry_price - (risk * risk_multiple)
    return target
```

---

### Trailing Stop Exits

**Simple Trailing Stop:**
```python
def trailing_stop(prices, trail_pct=0.02, direction='long'):
    """
    Trail stop behind price
    """
    if direction == 'long':
        highest = prices.expanding().max()
        stop = highest * (1 - trail_pct)
    else:
        lowest = prices.expanding().min()
        stop = lowest * (1 + trail_pct)
    return stop
```

**ATR Trailing Stop:**
```python
def atr_trailing_stop(prices, atr, multiplier=2.5, direction='long'):
    """
    Trail stop by ATR distance
    """
    if direction == 'long':
        highest = prices.expanding().max()
        stop = highest - (atr * multiplier)
    else:
        lowest = prices.expanding().min()
        stop = lowest + (atr * multiplier)
    return stop
```

---

### Signal-Based Exits

**Indicator Exit:**
```python
def indicator_exit(position, indicator_value, exit_threshold):
    """
    Exit when indicator crosses threshold
    """
    if position == 'long':
        exit_signal = indicator_value < exit_threshold
    else:
        exit_signal = indicator_value > exit_threshold
    return exit_signal
```

**Opposing Signal Exit:**
```python
def opposing_signal_exit(current_position, new_signal):
    """
    Exit when opposite signal triggers
    """
    exit_signal = (current_position * new_signal) < 0
    return exit_signal
```

---

### Time-Based Exits

```python
def time_based_exit(entry_time, current_time, max_holding_period):
    """
    Exit after maximum holding period
    """
    holding_time = current_time - entry_time
    exit_signal = holding_time >= max_holding_period
    return exit_signal
```

---

### Best Practices for Exit Logic

- Always have a stop-loss for every position
- Use ATR-based stops for volatility-adjusted risk
- Consider trailing stops for trend-following strategies
- Don't let winners turn into losers (use break-even stops)
- Test different exit strategies with same entry to find optimal
- Document reason for each exit in trade log
- **Always define at least one exit signal before backtesting.** A strategy
  with entry signals but no exit signal still runs, but it never closes a
  position on its own -- the Mangrove backtester force-closes every open
  position at the end of the simulation window. That end-of-sim liquidation
  understates drawdown and can overstate returns and Sharpe, so the reported
  metrics will not reflect how the strategy would trade live.

> **Backtest Warning:** When a strategy defines entry signals but an empty
> `exit` list, the backtest is not rejected -- it returns a non-fatal
> `NO_EXIT_SIGNAL` warning in the response `warnings` array (and the AI copilot
> flags it). Treat the resulting metrics with caution until you add an exit
> rule.

---

## 4.7 Time-Based Logic

### Definition

Time-based logic incorporates temporal factors into trading decisions, including holding period constraints, session filtering, and calendar-based adjustments.

### Core Principles

- **Holding Period**: Strategies have optimal holding periods
- **Session Selection**: Not all trading hours are equal
- **Calendar Awareness**: Certain dates have predictable behavior
- **Time Decay**: Time affects option and volatility strategies
- **Periodicity**: Returns may cluster at specific times

---

### Session Filters

```python
def session_filter(timestamp, allowed_sessions):
    """
    Filter trades by market session
    """
    # Example sessions
    sessions = {
        'asia': ('00:00', '08:00'),
        'london': ('08:00', '16:00'),
        'new_york': ('13:00', '21:00')
    }
    
    time = timestamp.time()
    for session in allowed_sessions:
        start, end = sessions[session]
        if start <= time <= end:
            return True
    return False
```

### Holding Period Constraints

```python
def enforce_holding_period(position_time, min_hold, max_hold):
    """
    Enforce minimum and maximum holding periods
    """
    can_exit = position_time >= min_hold
    must_exit = position_time >= max_hold
    return can_exit, must_exit
```

### Calendar Filters

```python
def calendar_filter(date):
    """
    Avoid trading on specific dates
    """
    # Avoid NFP days, FOMC days, etc.
    blackout_dates = load_economic_calendar()
    
    if date in blackout_dates:
        return False
    
    # Avoid first/last day of month for some strategies
    if date.day == 1 or date.day == date.days_in_month:
        return False
    
    return True
```

---

## 4.8 Regime Detection & Filtering

### Conceptual Anchor

Market regimes explain **why archetypes rotate in effectiveness**.  
Regime detection does not predict markets - it **selects which behaviors to exploit**.

### Definition

Regime detection identifies the current market state (trending, ranging, volatile, calm) to adapt strategy behavior or filter signals inappropriate for current conditions.

### Core Principles

- **Market States**: Markets cycle through distinct regimes
- **Strategy Matching**: Different strategies excel in different regimes
- **Lag Acceptance**: Regime detection has inherent lag
- **Probabilistic**: Regime identification is probabilistic, not certain
- **Adaptation**: Strategies should adapt to detected regime

---

### Trend vs. Range Detection

**ADX-Based:**
```python
def adx_regime(adx, trend_threshold=25, range_threshold=20):
    """
    Classify regime based on ADX
    """
    if adx > trend_threshold:
        return 'trending'
    elif adx < range_threshold:
        return 'ranging'
    else:
        return 'transitional'
```

**Efficiency Ratio:**
```python
def efficiency_ratio_regime(price, period=20):
    """
    Efficiency ratio: Direction / Volatility
    """
    direction = abs(price.diff(period))
    volatility = price.diff().abs().rolling(period).sum()
    
    efficiency = direction / volatility
    
    if efficiency > 0.6:
        return 'trending'
    elif efficiency < 0.3:
        return 'ranging'
    else:
        return 'mixed'
```

---

### Volatility Regime Detection

**Percentile-Based:**
```python
def volatility_regime(current_vol, historical_vol, lookback=252):
    """
    Classify volatility regime by percentile
    """
    percentile = (historical_vol < current_vol).rolling(lookback).mean()
    
    if percentile > 0.8:
        return 'high_volatility'
    elif percentile < 0.2:
        return 'low_volatility'
    else:
        return 'normal_volatility'
```

**Hidden Markov Model:**
```python
from hmmlearn import hmm

def hmm_regime_detection(returns, n_states=2):
    """
    HMM-based regime detection
    """
    model = hmm.GaussianHMM(n_components=n_states, covariance_type="diag")
    model.fit(returns.values.reshape(-1, 1))
    
    regime = model.predict(returns.values.reshape(-1, 1))
    return regime
```

---

### Strategy Adaptation by Regime

```python
def regime_adapted_strategy(price, regime):
    """
    Select strategy based on regime
    """
    if regime == 'trending':
        signal = trend_following_signal(price)
    elif regime == 'ranging':
        signal = mean_reversion_signal(price)
    else:
        signal = 0  # No trade in uncertain regime
    
    return signal
```

---

### Best Practices for Regime Detection

- Accept lag in regime detection; don't expect real-time accuracy
- Use multiple regime indicators for confirmation
- Have default behavior for uncertain/transitional regimes
- Backtest regime detection separately from strategy
- Consider regime detection failures in risk management

---

## 4.9 Data Quality & Preprocessing

### Definition

Data quality and preprocessing ensure that strategy inputs are accurate, complete, and properly formatted. Poor data quality is a leading cause of strategy failure.

### Core Principles

- **Garbage In, Garbage Out**: Strategy is only as good as its data
- **Survivorship Bias**: Ensure delisted assets are included
- **Look-Ahead Bias**: Never use future information
- **Point-in-Time**: Use data as it was available at each historical point
- **Corporate Actions**: Adjust for splits, dividends, mergers

---

### Data Cleaning

**Handling Missing Data:**
```python
def clean_missing_data(df):
    """
    Handle missing values appropriately
    """
    # Forward fill for prices (common approach)
    df['close'] = df['close'].fillna(method='ffill')
    
    # Don't fill volume - missing volume is meaningful
    # df['volume'] remains NaN
    
    # Drop rows with critical missing data
    df = df.dropna(subset=['open', 'high', 'low', 'close'])
    
    return df
```

**Outlier Detection:**
```python
def detect_outliers(returns, threshold=5):
    """
    Identify potential data errors
    """
    zscore = (returns - returns.mean()) / returns.std()
    outliers = abs(zscore) > threshold
    return outliers
```

---

### Corporate Action Adjustments

**Split Adjustment:**
```python
def adjust_for_splits(price, splits):
    """
    Adjust historical prices for stock splits
    """
    adjusted = price.copy()
    for split_date, split_ratio in splits.items():
        adjusted.loc[:split_date] *= split_ratio
    return adjusted
```

**Dividend Adjustment:**
```python
def adjust_for_dividends(price, dividends):
    """
    Create total return series including dividends
    """
    # Calculate adjustment factor
    adjustment = (price + dividends) / price
    adjusted_price = price * adjustment.cumprod()
    return adjusted_price
```

---

### Avoiding Biases

**Survivorship Bias Prevention:**
```python
def include_delisted(universe, date):
    """
    Include stocks that existed on date, even if later delisted
    """
    # Point-in-time universe
    available_stocks = universe[universe['listing_date'] <= date]
    available_stocks = available_stocks[
        (available_stocks['delisting_date'].isna()) | 
        (available_stocks['delisting_date'] > date)
    ]
    return available_stocks
```

**Look-Ahead Bias Prevention:**
```python
def point_in_time_data(df, target_date):
    """
    Return only data available on target_date
    """
    # Shift data to simulate reporting lag
    reporting_lag = pd.Timedelta(days=1)  # Or appropriate lag
    available_data = df[df.index <= target_date - reporting_lag]
    return available_data
```

---

### Best Practices for Data Quality

- Validate data against multiple sources
- Check for obvious errors (negative prices, impossible moves)
- Document data sources and any adjustments made
- Use point-in-time databases when available
- Include delisted securities in backtests
- Account for reporting lags in fundamental data

---

## 4.10 Backtesting Best Practices

### Definition

Backtesting is the process of applying a trading strategy to historical data to evaluate how it would have performed. Proper backtesting methodology is critical for realistic performance estimation.

### Core Principles

- **Historical Simulation**: Test strategy on past data
- **Out-of-Sample Testing**: Reserve data for validation
- **Realistic Assumptions**: Include costs, slippage, constraints
- **Multiple Tests**: Test across different periods and conditions
- **Skepticism**: Assume backtest overstates live performance

---

### Backtesting Framework

```python
class Backtester:
    def __init__(self, data, strategy, capital=100000):
        self.data = data
        self.strategy = strategy
        self.capital = capital
        self.positions = []
        self.equity_curve = []
    
    def run(self):
        """
        Execute backtest
        """
        equity = self.capital
        position = 0
        
        for i in range(len(self.data)):
            # Get signal
            signal = self.strategy.generate_signal(self.data.iloc[:i+1])
            
            # Execute trades with realistic costs
            if signal != position:
                trade_cost = self.calculate_costs(position, signal)
                equity -= trade_cost
                position = signal
            
            # Update equity
            if position != 0:
                returns = self.data['returns'].iloc[i]
                equity *= (1 + position * returns)
            
            self.equity_curve.append(equity)
        
        return self.calculate_metrics()
    
    def calculate_costs(self, old_pos, new_pos):
        """
        Realistic transaction costs
        """
        commission = 0.001  # 0.1%
        slippage = 0.0005   # 0.05%
        return abs(new_pos - old_pos) * (commission + slippage) * self.capital
```

---

### Realistic Assumptions

**Transaction Costs:**
```python
def calculate_transaction_costs(trade_value, asset_class):
    """
    Realistic cost assumptions by asset class
    """
    costs = {
        'equities': 0.001,      # 10 bps
        'futures': 0.0002,      # 2 bps
        'fx': 0.0001,           # 1 bp
        'crypto': 0.002,        # 20 bps
        'options': 0.01         # $1 per contract + spread
    }
    return trade_value * costs.get(asset_class, 0.001)
```

**Slippage Modeling:**
```python
def estimate_slippage(trade_size, adv, volatility):
    """
    Market impact estimation
    """
    participation = trade_size / adv
    impact = volatility * np.sqrt(participation) * 0.1
    return impact
```

---

### Performance Metrics

```python
def calculate_backtest_metrics(returns):
    """
    Standard backtest performance metrics
    """
    metrics = {
        'total_return': (1 + returns).prod() - 1,
        'annual_return': returns.mean() * 252,
        'annual_volatility': returns.std() * np.sqrt(252),
        'sharpe_ratio': returns.mean() / returns.std() * np.sqrt(252),
        'max_drawdown': calculate_max_drawdown(returns),
        'win_rate': (returns > 0).mean(),
        'profit_factor': returns[returns > 0].sum() / abs(returns[returns < 0].sum()),
        'avg_win': returns[returns > 0].mean(),
        'avg_loss': returns[returns < 0].mean(),
        'num_trades': count_trades(returns)
    }
    return metrics
```

---

### Best Practices for Backtesting

- Use out-of-sample data for final validation
- Include realistic transaction costs and slippage
- Test across multiple market regimes
- Be skeptical of exceptional results
- Compare to simple benchmarks
- Document all assumptions and parameters

---

## 4.11 Walk-Forward Optimization

### Definition

Walk-forward optimization (WFO) is a method for optimizing strategy parameters while avoiding overfitting by repeatedly optimizing on in-sample data and testing on subsequent out-of-sample data.

### Core Principles

- **Rolling Optimization**: Optimize on window, test on next period
- **Out-of-Sample Validation**: Only OOS results count
- **Adaptive Parameters**: Parameters adjust to changing market conditions
- **Overfitting Prevention**: Reduces curve-fitting to historical data
- **Realistic Performance**: OOS results estimate true performance

---

### Walk-Forward Process

```python
def walk_forward_optimization(data, strategy_class, 
                             optimization_window=252,
                             test_window=63,
                             param_grid=None):
    """
    Walk-forward optimization framework
    """
    results = []
    
    for i in range(optimization_window, len(data) - test_window, test_window):
        # In-sample optimization window
        train_data = data.iloc[i-optimization_window:i]
        
        # Out-of-sample test window
        test_data = data.iloc[i:i+test_window]
        
        # Optimize parameters on training data
        best_params = optimize_parameters(train_data, strategy_class, param_grid)
        
        # Test on out-of-sample data
        strategy = strategy_class(**best_params)
        oos_returns = strategy.backtest(test_data)
        
        results.append({
            'period_start': data.index[i],
            'period_end': data.index[i+test_window],
            'params': best_params,
            'oos_returns': oos_returns,
            'oos_sharpe': calculate_sharpe(oos_returns)
        })
    
    return pd.DataFrame(results)
```

---

### Parameter Optimization

```python
from itertools import product

def optimize_parameters(data, strategy_class, param_grid):
    """
    Grid search for optimal parameters
    """
    best_sharpe = -np.inf
    best_params = None
    
    # Generate all parameter combinations
    param_combinations = list(product(*param_grid.values()))
    
    for params in param_combinations:
        param_dict = dict(zip(param_grid.keys(), params))
        
        strategy = strategy_class(**param_dict)
        returns = strategy.backtest(data)
        sharpe = calculate_sharpe(returns)
        
        if sharpe > best_sharpe:
            best_sharpe = sharpe
            best_params = param_dict
    
    return best_params
```

---

### Anchored vs. Rolling Walk-Forward

**Anchored (Expanding Window):**
```python
def anchored_walk_forward(data, strategy_class, test_window=63):
    """
    Training window expands over time
    """
    min_train = 252
    results = []
    
    for i in range(min_train, len(data) - test_window, test_window):
        # Training: all data from start to i
        train_data = data.iloc[:i]
        test_data = data.iloc[i:i+test_window]
        
        # ... rest of optimization
```

**Rolling (Fixed Window):**
```python
def rolling_walk_forward(data, strategy_class, train_window=252, test_window=63):
    """
    Training window is fixed size
    """
    results = []
    
    for i in range(train_window, len(data) - test_window, test_window):
        # Training: fixed window before i
        train_data = data.iloc[i-train_window:i]
        test_data = data.iloc[i:i+test_window]
        
        # ... rest of optimization
```

---

### Best Practices for Walk-Forward

- Use at least 2-3 years of data for optimization windows
- Test windows should be long enough for statistical significance
- Monitor parameter stability across periods
- Aggregate OOS results for overall performance estimate
- Be wary of strategies that require frequent reoptimization

---

## 4.12 Strategy Validation (Avoiding Biases)

### Definition

Strategy validation involves rigorous testing procedures to ensure a strategy has genuine predictive power rather than being an artifact of data mining, overfitting, or statistical flukes.

### Core Principles

- **Skepticism**: Assume the strategy doesn't work until proven otherwise
- **Multiple Testing**: Account for trying many strategies/parameters
- **Economic Rationale**: Strategy should have logical explanation
- **Robustness**: Results should hold across variations
- **Statistical Significance**: Returns should be statistically significant

---

### Common Biases to Avoid

**Look-Ahead Bias:**
- Using information not available at trade time
- Prevention: Use only data available at decision point

**Survivorship Bias:**
- Excluding failed companies/assets from analysis
- Prevention: Use point-in-time databases with delisted securities

**Data Snooping Bias:**
- Testing many variations until one works
- Prevention: Pre-specify tests, use out-of-sample data

**Selection Bias:**
- Cherry-picking favorable time periods
- Prevention: Test across full available history

**Overfitting:**
- Fitting noise rather than signal
- Prevention: Use simple models, walk-forward optimization

---

### Statistical Significance Testing

**T-Test for Returns:**
```python
from scipy import stats

def test_significance(returns, null_return=0):
    """
    Test if mean return is significantly different from null
    """
    t_stat, p_value = stats.ttest_1samp(returns, null_return)
    
    return {
        't_statistic': t_stat,
        'p_value': p_value,
        'significant_5pct': p_value < 0.05,
        'significant_1pct': p_value < 0.01
    }
```

**Multiple Testing Correction:**
```python
def bonferroni_correction(p_values, alpha=0.05):
    """
    Adjust for multiple hypothesis tests
    """
    n_tests = len(p_values)
    adjusted_alpha = alpha / n_tests
    
    significant = p_values < adjusted_alpha
    return significant, adjusted_alpha
```

---

### Robustness Checks

**Parameter Sensitivity:**
```python
def parameter_sensitivity(data, strategy_class, param_name, param_range):
    """
    Test how sensitive results are to parameter changes
    """
    results = {}
    for param_value in param_range:
        strategy = strategy_class(**{param_name: param_value})
        returns = strategy.backtest(data)
        results[param_value] = calculate_sharpe(returns)
    
    # Check if results are stable across parameter range
    values = list(results.values())
    stability = np.std(values) / np.mean(values)
    
    return results, stability
```

**Time Period Stability:**
```python
def period_stability(data, strategy, periods):
    """
    Test performance across different time periods
    """
    period_results = {}
    for period_name, (start, end) in periods.items():
        period_data = data[start:end]
        returns = strategy.backtest(period_data)
        period_results[period_name] = calculate_metrics(returns)
    
    return period_results
```

**Universe Stability:**
```python
def universe_stability(strategy, universes):
    """
    Test on different asset universes
    """
    universe_results = {}
    for universe_name, universe_data in universes.items():
        returns = strategy.backtest(universe_data)
        universe_results[universe_name] = calculate_metrics(returns)
    
    return universe_results
```

---

### Validation Checklist

1. **Economic Rationale**: Can you explain why the strategy works?
2. **Out-of-Sample Testing**: Does it work on data not used in development?
3. **Statistical Significance**: Are returns significantly different from zero?
4. **Parameter Stability**: Do results hold across parameter variations?
5. **Time Period Stability**: Does it work in different market regimes?
6. **Transaction Costs**: Does it survive realistic costs?
7. **Capacity**: Can it be implemented at desired scale?
8. **Simplicity**: Is the strategy simpler than alternatives?

---

### Best Practices for Validation

- Pre-register hypotheses before testing
- Use out-of-sample data for final validation only
- Account for multiple testing in significance claims
- Require economic rationale, not just statistical evidence
- Test robustness to reasonable parameter perturbations
- Be skeptical of Sharpe ratios above 2.0 without clear edge
- Paper trade before committing real capital

---

## Summary

Effective strategy design requires:

1. **Clear separation of style, archetype, and signal** - Know when you trade vs. why you trade
2. **Explicit alignment between market behavior and strategy logic** - Match archetypes to regimes
3. **Understanding of risk profiles** - Win rate alone is misleading; skew determines survivability
4. **Regime-aware deployment** - Don't apply mean reversion in trends or trend following in ranges
5. **Robust execution and exits** - Entry is less important than risk management
6. **Rigorous validation and skepticism** - Assume strategies don't work until proven otherwise

> **Critical Insight:**  
> Strategies do not fail randomly - they fail when applied to the wrong market behavior.  
> Mean reversion in a trend will blow up. Trend following in a range will bleed out.  
> Know your archetype's risk profile and contraindications.

# 8. Quantitative Analysis

This document covers quantitative patterns and statistical phenomena exploited in systematic trading strategies, including seasonality effects, volatility dynamics, mean reversion signals, and machine learning approaches.

---

## 8.1 Seasonality & Time-of-Day Effects

### Definition

Seasonality refers to predictable, recurring patterns in asset prices or market behavior based on calendar time (time of day, day of week, month of year). These patterns arise from structural factors, fund flows, and behavioral tendencies that repeat cyclically.

### Core Principles

- **Structural Causes**: Many seasonal effects stem from institutional behavior or market mechanics
- **Decay Risk**: Well-known effects may diminish as markets adapt
- **Statistical Significance**: Effects must be tested for statistical validity
- **Transaction Costs**: Small effects may not survive after costs
- **Regime Dependency**: Seasonality can vary across market regimes

### Common Use Cases

- Timing entries and exits to exploit intraday patterns
- Avoiding low-probability trading periods
- Calendar-based strategy overlays
- Volatility scheduling for execution algorithms
- Month-end and quarter-end rebalancing trades

---

### Intraday Patterns

**Opening Range Dynamics:**
- First 30-60 minutes: High volatility, gap filling, price discovery
- Amateur hour: Retail orders cluster at open
- Institutional orders distributed throughout day

**Lunch Hour Effect:**
- Reduced liquidity (11:30 AM - 1:30 PM ET in US markets)
- Lower volume, wider spreads
- Choppy, mean-reverting price action
- Often poor time for trend trades

**Power Hour / Closing Auction:**
- Last hour (3-4 PM ET): Increased volume and volatility
- MOC (Market on Close) orders create directional pressure
- Trend day confirmation or reversal often occurs
- Best liquidity of the day

**Detection Algorithm:**
```python
def calculate_intraday_return(data, start_time, end_time):
    # Filter data for time window
    window_data = data.between_time(start_time, end_time)
    # Calculate return for each day
    returns = window_data.groupby(window_data.index.date)['close'].apply(
        lambda x: (x.iloc[-1] / x.iloc[0] - 1) if len(x) > 1 else 0
    )
    return returns.mean(), returns.std()
```

---

### Day-of-Week Effects

**Monday Effect:**
- Historically negative returns on Mondays (less pronounced now)
- Weekend news digestion
- Reduced institutional participation

**Turn-of-Week Effect:**
- Positive returns on Fridays (position squaring)
- Some studies show Tuesday strength

**Turnaround Tuesday:**
- After large Monday moves, Tuesday often reverses
- Contrarian opportunity after weekend gap

---

### Monthly / Calendar Effects

**Turn-of-Month Effect:**
- Last trading day and first 4 days: Positive bias
- Pension fund flows, payroll investing
- One of the most persistent calendar anomalies

**January Effect:**
- Small-cap stocks historically outperform in January
- Tax-loss selling reversal
- Less pronounced in recent decades

**Sell in May:**
- May-October period historically weaker than November-April
- "Sell in May and go away"
- Works some years, not others

**Quarter-End Rebalancing:**
- Last week of quarter: Fund rebalancing flows
- Window dressing by fund managers
- Increased volatility around month/quarter end

**Options Expiration (OPEX):**
- Third Friday of each month (monthly options)
- Gamma exposure affects price dynamics
- Pin risk around popular strikes

---

### Statistical Testing for Seasonality

**T-Test for Period Effect:**
```python
from scipy import stats

def test_seasonal_effect(returns, is_seasonal):
    seasonal_returns = returns[is_seasonal]
    non_seasonal_returns = returns[~is_seasonal]
    
    t_stat, p_value = stats.ttest_ind(seasonal_returns, non_seasonal_returns)
    
    return {
        'seasonal_mean': seasonal_returns.mean(),
        'non_seasonal_mean': non_seasonal_returns.mean(),
        't_statistic': t_stat,
        'p_value': p_value,
        'significant': p_value < 0.05
    }
```

---

### Best Practices for Seasonality

- Test effects on out-of-sample data before trading
- Account for transaction costs and slippage
- Monitor for decay of effects over time
- Use as filter/overlay, not sole strategy basis
- Be aware that well-publicized effects often diminish

---

## 8.2 Volatility Clustering

### Definition

Volatility clustering is the empirically observed phenomenon where large price changes tend to be followed by large price changes (of either sign), and small price changes tend to be followed by small price changes. This creates persistence in volatility that can be modeled and exploited.

### Core Principles

- **Persistence**: Today's volatility is predictive of tomorrow's volatility
- **Mean Reversion**: Extreme volatility eventually reverts to normal levels
- **Asymmetry**: Negative returns often increase volatility more than positive returns
- **Regime Structure**: Markets shift between high and low volatility states
- **Forecastability**: Unlike returns, volatility is partially predictable

### Common Use Cases

- Volatility forecasting for risk management
- Options pricing and trading
- Dynamic position sizing
- Regime detection for strategy switching
- Stop-loss optimization

---

### GARCH Family Models

**GARCH(1,1) - Generalized Autoregressive Conditional Heteroskedasticity:**
```
sigma_t^2 = omega + alpha * epsilon_(t-1)^2 + beta * sigma_(t-1)^2
```

Where:
- sigma_t^2 = Conditional variance at time t
- omega = Long-run variance weight
- alpha = Reaction to recent shock (typically 0.05-0.15)
- beta = Persistence parameter (typically 0.80-0.95)
- alpha + beta < 1 for stationarity

**Key Insight:** alpha + beta close to 1 means high persistence (volatility shocks take long to decay).

**Implementation:**
```python
from arch import arch_model

# Fit GARCH(1,1)
model = arch_model(returns, vol='Garch', p=1, q=1)
results = model.fit()

# Forecast volatility
forecast = results.forecast(horizon=5)
predicted_vol = np.sqrt(forecast.variance.values[-1])
```

---

### EGARCH (Exponential GARCH)

**Formula:**
```
log(sigma_t^2) = omega + alpha * (|z_(t-1)| - E|z|) + gamma * z_(t-1) + beta * log(sigma_(t-1)^2)
```

**Key Feature:** Captures asymmetry - gamma parameter allows negative returns to impact volatility differently than positive returns (leverage effect).

---

### Realized Volatility

**Definition:** Volatility calculated from high-frequency intraday returns.

**Formula:**
```
RV_t = sqrt(sum(r_i^2)) for all intraday returns r_i

# With 5-minute returns
RV = sqrt(sum of squared 5-minute returns * 252) for annualized
```

**Advantage:** More accurate than daily close-to-close volatility.

---

### Volatility Regime Detection

**Hidden Markov Model Approach:**
```python
from hmmlearn import hmm

# Fit 2-state HMM to volatility
model = hmm.GaussianHMM(n_components=2, covariance_type="diag")
model.fit(volatility_data.reshape(-1, 1))

# Predict regime
regime = model.predict(volatility_data.reshape(-1, 1))
```

**Regime Characteristics:**
- State 0: Low volatility regime (calm market)
- State 1: High volatility regime (stressed market)
- Transition probabilities indicate regime persistence

---

### Trading Applications

**Volatility Targeting:**
```python
def volatility_target_position(target_vol, current_vol, base_position):
    """Adjust position to maintain target volatility"""
    return base_position * (target_vol / current_vol)
```

**Volatility Breakout:**
```python
def volatility_breakout_signal(current_range, atr, threshold=1.5):
    """Signal when current range exceeds ATR by threshold"""
    return current_range > (threshold * atr)
```

---

### Best Practices for Volatility Modeling

- Use rolling windows appropriate to trading horizon
- Incorporate realized volatility for more accurate estimates
- Account for volatility asymmetry (leverage effect)
- Test regime models out-of-sample
- Remember volatility forecasts are imperfect

---

## 8.3 Mean Reversion Signals

### Definition

Mean reversion is the tendency for prices to return to an average level over time. Mean reversion strategies profit by identifying temporary deviations from fair value and trading on the expectation that prices will revert.

### Core Principles

- **Equilibrium**: Prices fluctuate around an equilibrium/fair value
- **Deviation Thresholds**: Trade when deviation exceeds statistical threshold
- **Holding Period**: Mean reversion typically works on shorter timeframes
- **Risk of Trend**: What appears to be deviation may be new trend
- **Pairs/Spreads**: More reliable on relative value than absolute price

### Common Use Cases

- Statistical arbitrage pairs trading
- RSI/Bollinger Band reversal trades
- ETF premium/discount arbitrage
- Cross-sectional equity strategies
- Funding rate arbitrage in crypto

---

### Z-Score Methodology

**Definition:** Standard deviation distance from mean.

**Formula:**
```
Z-Score = (Price - Moving_Average) / Standard_Deviation
```

**Trading Rules:**
- Z < -2: Oversold, potential long
- Z > +2: Overbought, potential short
- Z crosses 0: Exit signal

**Implementation:**
```python
def calculate_zscore(series, window=20):
    mean = series.rolling(window).mean()
    std = series.rolling(window).std()
    zscore = (series - mean) / std
    return zscore

def mean_reversion_signals(zscore, entry_threshold=2, exit_threshold=0):
    signals = pd.Series(0, index=zscore.index)
    signals[zscore < -entry_threshold] = 1  # Long
    signals[zscore > entry_threshold] = -1  # Short
    signals[abs(zscore) < exit_threshold] = 0  # Exit
    return signals
```

---

### Pairs Trading

**Concept:** Trade two correlated securities, going long the underperformer and short the outperformer, betting on convergence.

**Cointegration Test:**
```python
from statsmodels.tsa.stattools import coint

def test_cointegration(series1, series2):
    score, pvalue, _ = coint(series1, series2)
    return pvalue < 0.05  # Cointegrated if p-value < 0.05
```

**Spread Calculation:**
```python
from statsmodels.regression.linear_model import OLS

# Find hedge ratio
model = OLS(series1, series2).fit()
hedge_ratio = model.params[0]

# Calculate spread
spread = series1 - hedge_ratio * series2
```

**Trading the Spread:**
- Calculate z-score of spread
- Long spread when z < -2 (buy series1, sell series2)
- Short spread when z > +2 (sell series1, buy series2)
- Exit when z approaches 0

---

### Bollinger Band Mean Reversion

**Strategy Logic:**
```python
def bollinger_mean_reversion(close, window=20, num_std=2):
    middle = close.rolling(window).mean()
    std = close.rolling(window).std()
    upper = middle + (num_std * std)
    lower = middle - (num_std * std)
    
    signals = pd.Series(0, index=close.index)
    signals[close < lower] = 1   # Long when below lower band
    signals[close > upper] = -1  # Short when above upper band
    signals[close.between(middle - std, middle + std)] = 0  # Exit near middle
    
    return signals
```

---

### RSI Mean Reversion

**Strategy Logic:**
```python
def rsi_mean_reversion(rsi, oversold=30, overbought=70, exit=50):
    signals = pd.Series(0, index=rsi.index)
    signals[rsi < oversold] = 1   # Long when oversold
    signals[rsi > overbought] = -1  # Short when overbought
    
    # Exit conditions
    # Long exit: RSI crosses above exit threshold
    # Short exit: RSI crosses below exit threshold
    
    return signals
```

---

### Half-Life of Mean Reversion

**Concept:** Time for deviation to decay by half.

**Formula (Ornstein-Uhlenbeck process):**
```python
def calculate_half_life(spread):
    spread_lag = spread.shift(1)
    spread_diff = spread - spread_lag
    
    # Regress: spread_diff = beta * spread_lag + error
    spread_lag = spread_lag.dropna()
    spread_diff = spread_diff.dropna()
    
    model = OLS(spread_diff, spread_lag).fit()
    half_life = -np.log(2) / model.params[0]
    
    return half_life
```

**Interpretation:**
- Half-life < 5 days: Fast mean reversion, good for short-term trading
- Half-life 5-30 days: Moderate, suitable for swing trading
- Half-life > 30 days: Slow, may be trending or structural

---

### Best Practices for Mean Reversion

- Test for cointegration/stationarity before assuming mean reversion
- Use appropriate lookback periods for mean and standard deviation
- Account for regime changes that can break mean reversion
- Include transaction costs in backtest (frequent trading)
- Set maximum holding periods to limit trend risk
- Size positions inversely to deviation magnitude

---

## 8.4 Breakout Signals

### Definition

Breakout signals identify when price moves beyond a defined range or threshold, indicating potential start of a new trend or acceleration of existing trend. They are the foundation of trend-following strategies.

### Core Principles

- **Range Expansion**: Breakouts represent volatility expansion from compression
- **Momentum Persistence**: True breakouts tend to continue in breakout direction
- **False Breakouts**: Many breakouts fail; filtering and confirmation reduce failures
- **Time Element**: Breakouts are more reliable from longer consolidations
- **Volume Confirmation**: Volume should expand on valid breakouts

### Common Use Cases

- Trend-following entry signals
- Volatility breakout strategies
- Channel breakout systems
- News/event trading
- Swing trading entries

---

### Donchian Channel Breakout

**Definition:** Breakout of N-period high or low.

**Formula:**
```
Upper Channel = Highest High over N periods
Lower Channel = Lowest Low over N periods
```

**Trading Rules (Classic Turtle Trading):**
```python
def donchian_breakout(high, low, close, entry_period=20, exit_period=10):
    upper = high.rolling(entry_period).max()
    lower = low.rolling(entry_period).min()
    
    exit_upper = high.rolling(exit_period).max()
    exit_lower = low.rolling(exit_period).min()
    
    signals = pd.Series(0, index=close.index)
    signals[close > upper.shift(1)] = 1   # Long breakout
    signals[close < lower.shift(1)] = -1  # Short breakout
    
    # Exit signals
    exit_long = close < exit_lower.shift(1)
    exit_short = close > exit_upper.shift(1)
    
    return signals, exit_long, exit_short
```

**Parameters:**
- Entry: 20-period (Turtle system)
- Exit: 10-period
- Variations: 55-period for longer-term

---

### Volatility Breakout

**Concept:** Enter when price moves by more than a volatility threshold from a reference point.

**ATR Breakout:**
```python
def atr_breakout(close, atr, multiplier=2.0):
    reference = close.shift(1)  # Previous close
    threshold = atr * multiplier
    
    signals = pd.Series(0, index=close.index)
    signals[close > reference + threshold] = 1   # Bullish breakout
    signals[close < reference - threshold] = -1  # Bearish breakout
    
    return signals
```

**Opening Range Breakout:**
```python
def opening_range_breakout(data, orb_minutes=30):
    """Trade breakout of first N minutes range"""
    # Calculate opening range high/low
    # Go long if price breaks above OR high
    # Go short if price breaks below OR low
    pass
```

---

### Bollinger Band Breakout

**Concept:** Breakout when price closes outside bands after squeeze.

**Squeeze Detection:**
```python
def bollinger_squeeze(close, bb_period=20, keltner_period=20, bb_std=2, kelt_mult=1.5):
    # Bollinger Bands
    bb_middle = close.rolling(bb_period).mean()
    bb_std_val = close.rolling(bb_period).std()
    bb_upper = bb_middle + bb_std * bb_std_val
    bb_lower = bb_middle - bb_std * bb_std_val
    
    # Keltner Channels (for squeeze detection)
    # ATR calculation needed
    # ...
    
    # Squeeze: BB inside Keltner
    squeeze = (bb_upper < kelt_upper) & (bb_lower > kelt_lower)
    
    # Breakout: Price closes outside BB after squeeze
    breakout_up = (close > bb_upper) & squeeze.shift(1)
    breakout_down = (close < bb_lower) & squeeze.shift(1)
    
    return squeeze, breakout_up, breakout_down
```

---

### Breakout Confirmation Filters

**Volume Confirmation:**
```python
def volume_confirmed_breakout(price_breakout, volume, avg_volume_period=20, threshold=1.5):
    avg_volume = volume.rolling(avg_volume_period).mean()
    volume_confirmation = volume > (threshold * avg_volume)
    
    confirmed_breakout = price_breakout & volume_confirmation
    return confirmed_breakout
```

**Momentum Confirmation:**
```python
def momentum_confirmed_breakout(price_breakout, rsi, rsi_threshold=50):
    # Bullish breakout confirmed by RSI > 50
    # Bearish breakout confirmed by RSI < 50
    bullish_confirmed = price_breakout & (price_breakout > 0) & (rsi > rsi_threshold)
    bearish_confirmed = price_breakout & (price_breakout < 0) & (rsi < rsi_threshold)
    
    return bullish_confirmed, bearish_confirmed
```

---

### Best Practices for Breakout Trading

- Trade breakouts in direction of higher timeframe trend
- Use volume/momentum confirmation to filter false breakouts
- Accept that 50-60% of breakouts may fail
- Use tight initial stops and trail as position profits
- Consider pyramiding into winning breakouts
- Avoid breakouts in choppy, range-bound markets

---

## 8.5 Autocorrelation & Momentum Persistence

### Definition

Autocorrelation measures the correlation of a time series with its own lagged values. Positive autocorrelation in returns indicates momentum (trending behavior), while negative autocorrelation indicates mean reversion.

### Core Principles

- **Momentum Effect**: Past winners tend to continue winning short-term
- **Reversal Effect**: Extreme past winners tend to reverse long-term
- **Time-Varying**: Autocorrelation structure changes over time and across assets
- **Cross-Sectional vs. Time-Series**: Different momentum types behave differently
- **Risk-Adjusted**: Raw momentum should be adjusted for volatility

### Common Use Cases

- Momentum factor construction
- Trend-following signal generation
- Market regime classification
- Strategy selection (trend vs. mean reversion)
- Lookback period optimization

---

### Autocorrelation Analysis

**Formula:**
```
Autocorrelation(k) = Corr(r_t, r_(t-k))
```

**Implementation:**
```python
def autocorrelation_analysis(returns, max_lag=20):
    """Calculate autocorrelation for multiple lags"""
    from statsmodels.tsa.stattools import acf
    
    ac_values = acf(returns.dropna(), nlags=max_lag)
    
    return pd.Series(ac_values, index=range(max_lag + 1))
```

**Interpretation:**
- Positive lag-1 autocorrelation: Trend/momentum
- Negative lag-1 autocorrelation: Mean reversion
- Significant at longer lags: Longer-term patterns

---

### Time-Series Momentum

**Definition:** Go long assets that have risen over lookback period, short those that have fallen.

**Formula:**
```python
def time_series_momentum(returns, lookback=252):
    """
    Calculate time-series momentum signal
    Signal: Sign of cumulative return over lookback
    """
    cumulative_return = returns.rolling(lookback).sum()
    signal = np.sign(cumulative_return)
    return signal
```

**Volatility-Adjusted Momentum:**
```python
def volatility_adjusted_momentum(returns, lookback=252, vol_lookback=60):
    """
    Return / Volatility scaling
    """
    cumulative_return = returns.rolling(lookback).sum()
    volatility = returns.rolling(vol_lookback).std() * np.sqrt(252)
    
    signal = cumulative_return / volatility
    return signal
```

---

### Cross-Sectional Momentum

**Definition:** Rank assets by past performance, go long top performers, short bottom performers.

**Implementation:**
```python
def cross_sectional_momentum(returns_df, lookback=252, top_pct=0.2, bottom_pct=0.2):
    """
    Cross-sectional momentum for universe of assets
    """
    # Calculate lookback returns for each asset
    lookback_returns = returns_df.rolling(lookback).sum()
    
    # Rank assets
    ranks = lookback_returns.rank(axis=1, pct=True)
    
    # Long top performers, short bottom performers
    long_signals = (ranks > (1 - top_pct)).astype(int)
    short_signals = (ranks < bottom_pct).astype(int) * -1
    
    signals = long_signals + short_signals
    return signals
```

---

### Momentum Decay and Lookback Selection

**Optimal Lookback Testing:**
```python
def test_momentum_lookbacks(returns, lookbacks=[21, 63, 126, 252]):
    """
    Test different lookback periods for momentum
    """
    results = {}
    for lb in lookbacks:
        signal = np.sign(returns.rolling(lb).sum())
        strategy_returns = signal.shift(1) * returns
        
        results[lb] = {
            'return': strategy_returns.mean() * 252,
            'sharpe': strategy_returns.mean() / strategy_returns.std() * np.sqrt(252),
            'win_rate': (strategy_returns > 0).mean()
        }
    
    return pd.DataFrame(results).T
```

---

### Momentum Crashes

**Phenomenon:** Momentum strategies can experience severe drawdowns during market reversals (momentum crashes).

**Detection:**
```python
def momentum_crash_indicator(market_returns, lookback=60):
    """
    Detect conditions that precede momentum crashes
    High market volatility + recent market decline
    """
    volatility = market_returns.rolling(lookback).std() * np.sqrt(252)
    cumulative = market_returns.rolling(lookback).sum()
    
    # High crash risk: High volatility AND recent decline
    crash_risk = (volatility > volatility.quantile(0.8)) & (cumulative < 0)
    return crash_risk
```

---

### Best Practices for Momentum

- Use volatility-adjusted momentum for more stable signals
- Combine time-series and cross-sectional approaches
- Be aware of momentum crash risk during market reversals
- Consider reducing momentum exposure during high volatility
- Test multiple lookback periods; no single optimal choice

---

## 8.6 Machine-Learned Patterns

### Definition

Machine learning patterns are price or feature formations discovered through algorithmic analysis rather than human observation. ML models can identify complex, non-linear relationships that may not be visible to traditional technical analysis.

### Core Principles

- **Data-Driven Discovery**: Patterns emerge from data, not predefined rules
- **Overfitting Risk**: ML models easily overfit to historical noise
- **Feature Engineering**: Input features often matter more than model choice
- **Interpretability Trade-off**: Complex models may be black boxes
- **Out-of-Sample Validation**: Critical for avoiding false discoveries

### Common Use Cases

- Feature-based return prediction
- Regime classification
- Pattern recognition enhancement
- Alternative data signal extraction
- Risk model calibration

---

### Feature Engineering for Trading

**Price-Based Features:**
```python
def create_price_features(df, periods=[5, 10, 20, 50]):
    features = pd.DataFrame(index=df.index)
    
    for p in periods:
        # Returns
        features[f'return_{p}d'] = df['close'].pct_change(p)
        
        # Moving average distance
        features[f'ma_dist_{p}d'] = df['close'] / df['close'].rolling(p).mean() - 1
        
        # Volatility
        features[f'vol_{p}d'] = df['close'].pct_change().rolling(p).std()
        
        # Range
        features[f'range_{p}d'] = (df['high'].rolling(p).max() - df['low'].rolling(p).min()) / df['close']
    
    return features
```

**Technical Indicator Features:**
```python
def create_indicator_features(df):
    features = pd.DataFrame(index=df.index)
    
    # RSI
    features['rsi_14'] = calculate_rsi(df['close'], 14)
    
    # MACD
    features['macd'], features['macd_signal'], features['macd_hist'] = calculate_macd(df['close'])
    
    # Bollinger %B
    features['bb_pct_b'] = calculate_bollinger_pct_b(df['close'])
    
    # ADX
    features['adx'] = calculate_adx(df['high'], df['low'], df['close'])
    
    return features
```

---

### Classification Models

**Setup:**
```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit

def train_direction_classifier(features, returns, n_splits=5):
    """
    Predict next-period return direction
    """
    # Create target: 1 if positive return, 0 if negative
    target = (returns.shift(-1) > 0).astype(int)
    
    # Align features and target
    aligned = pd.concat([features, target], axis=1).dropna()
    X = aligned.iloc[:, :-1]
    y = aligned.iloc[:, -1]
    
    # Time series cross-validation
    tscv = TimeSeriesSplit(n_splits=n_splits)
    
    scores = []
    for train_idx, test_idx in tscv.split(X):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        
        model = RandomForestClassifier(n_estimators=100, max_depth=5)
        model.fit(X_train, y_train)
        
        score = model.score(X_test, y_test)
        scores.append(score)
    
    return np.mean(scores), model
```

---

### Neural Network Patterns

**LSTM for Sequential Patterns:**
```python
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout

def build_lstm_model(sequence_length, n_features):
    model = Sequential([
        LSTM(50, return_sequences=True, input_shape=(sequence_length, n_features)),
        Dropout(0.2),
        LSTM(50, return_sequences=False),
        Dropout(0.2),
        Dense(25, activation='relu'),
        Dense(1, activation='sigmoid')  # Binary classification
    ])
    
    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
    return model
```

---

### Avoiding Overfitting

**Techniques:**
```python
def walk_forward_validation(features, target, model_class, window=252, step=21):
    """
    Walk-forward validation to avoid look-ahead bias
    """
    results = []
    
    for i in range(window, len(features) - step, step):
        # Train on historical window
        X_train = features.iloc[i-window:i]
        y_train = target.iloc[i-window:i]
        
        # Test on next step
        X_test = features.iloc[i:i+step]
        y_test = target.iloc[i:i+step]
        
        model = model_class()
        model.fit(X_train, y_train)
        
        predictions = model.predict(X_test)
        results.append({
            'start': features.index[i],
            'accuracy': (predictions == y_test).mean(),
            'predictions': predictions
        })
    
    return pd.DataFrame(results)
```

**Feature Importance Analysis:**
```python
def analyze_feature_importance(model, feature_names):
    """
    Understand which features drive predictions
    """
    importance = pd.DataFrame({
        'feature': feature_names,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    return importance
```

---

### Best Practices for ML in Trading

- Use walk-forward validation, never standard cross-validation
- Keep models simple; complex models overfit
- Feature engineering matters more than model choice
- Require statistical significance across multiple time periods
- Include transaction costs in performance evaluation
- Monitor model performance and retrain periodically
- Be skeptical of high backtest performance

---

## 8.7 Cross-Sectional vs Time-Series Patterns

### Definition

Cross-sectional patterns compare assets relative to each other at a point in time (relative value), while time-series patterns analyze individual assets over time (absolute value). Both frameworks offer distinct trading opportunities.

### Core Principles

- **Cross-Sectional**: Ranking and relative performance drive signals
- **Time-Series**: Trend and momentum in individual asset drive signals
- **Diversification**: Combining both approaches improves risk-adjusted returns
- **Market Neutrality**: Cross-sectional strategies can be market neutral
- **Capacity**: Time-series often has more capacity than cross-sectional

---

### Time-Series Momentum (TSMOM)

**Logic:** Go long assets with positive past returns, short assets with negative past returns.

**Formula:**
```python
def time_series_momentum_signal(returns, lookback=252):
    """
    Binary signal based on sign of cumulative return
    """
    cumulative = returns.rolling(lookback).sum()
    return np.sign(cumulative)

def scaled_tsmom(returns, lookback=252, vol_target=0.15, vol_lookback=60):
    """
    Volatility-targeted TSMOM
    """
    signal = np.sign(returns.rolling(lookback).sum())
    realized_vol = returns.rolling(vol_lookback).std() * np.sqrt(252)
    position = signal * (vol_target / realized_vol)
    return position.clip(-2, 2)  # Cap leverage
```

---

### Cross-Sectional Momentum (XSMOM)

**Logic:** Go long top-performing assets, short bottom-performing assets based on relative ranking.

**Formula:**
```python
def cross_sectional_momentum_signal(returns_df, lookback=252, long_pct=0.2, short_pct=0.2):
    """
    Rank-based long/short portfolio
    """
    # Calculate lookback returns
    cumulative = returns_df.rolling(lookback).sum()
    
    # Rank within universe (0 to 1)
    ranks = cumulative.rank(axis=1, pct=True)
    
    # Long top quintile, short bottom quintile
    signals = pd.DataFrame(0.0, index=returns_df.index, columns=returns_df.columns)
    signals[ranks > (1 - long_pct)] = 1 / (long_pct * len(returns_df.columns))
    signals[ranks < short_pct] = -1 / (short_pct * len(returns_df.columns))
    
    return signals
```

---

### Comparison

| Aspect | Time-Series | Cross-Sectional |
|--------|-------------|-----------------|
| Signal | Individual asset trend | Relative ranking |
| Market Exposure | Net long/short varies | Can be market neutral |
| Capacity | Higher | Lower |
| Diversification | Across time | Across assets |
| Crash Risk | Vulnerable in reversals | More stable |
| Implementation | Simpler | Requires universe |

---

### Combining Approaches

**Dual Momentum:**
```python
def dual_momentum(returns_df, lookback=252):
    """
    Combine time-series and cross-sectional momentum
    """
    # Time-series filter: Only trade assets with positive absolute momentum
    ts_signal = (returns_df.rolling(lookback).sum() > 0).astype(int)
    
    # Cross-sectional ranking among those with positive momentum
    positive_only = returns_df.where(ts_signal == 1)
    ranks = positive_only.rolling(lookback).sum().rank(axis=1, pct=True)
    
    # Go long only top-ranked assets that also have positive momentum
    signals = ts_signal * (ranks > 0.8).astype(int)
    
    return signals
```

---

## 8.8 Carry Strategies

### Definition

Carry strategies aim to profit from holding positions that benefit from differences in yield, interest rates, or roll yield. Unlike momentum or mean reversion, carry generates returns from the passage of time and structural premiums, not price movement.

### Core Principles

- **Yield Differential**: Profit from interest rate or yield differences
- **Roll Yield**: Profit from futures curve structure (contango/backwardation)
- **Time Premium**: Options theta capture
- **Structural Premium**: Compensation for providing liquidity or insurance
- **Negative Convexity**: Carry strategies often have drawdown risk

### Common Use Cases

- FX carry trades
- Futures roll yield capture
- Options premium selling
- Fixed income carry
- Volatility risk premium harvesting

---

### FX Carry Trade

**Logic:** Borrow low-yielding currency, invest in high-yielding currency.

**Implementation:**
```python
def fx_carry_signal(interest_rates_df):
    """
    Rank currencies by interest rate for carry trade
    """
    # Higher rate = long, lower rate = short
    ranks = interest_rates_df.rank(axis=1, pct=True)
    
    signals = pd.DataFrame(0.0, index=interest_rates_df.index, 
                          columns=interest_rates_df.columns)
    signals[ranks > 0.8] = 1  # Long high yielders
    signals[ranks < 0.2] = -1  # Short low yielders
    
    return signals

def calculate_carry_return(fx_return, rate_differential, holding_period=1/252):
    """
    Total return = FX return + Interest differential
    """
    return fx_return + (rate_differential * holding_period)
```

---

### Futures Roll Yield

**Logic:** Go long futures in backwardation (roll yield positive), short futures in contango (roll yield negative).

**Implementation:**
```python
def futures_carry_signal(front_price, back_price, days_to_roll=30):
    """
    Calculate roll yield and generate carry signal
    """
    # Annualized roll yield
    roll_yield = (front_price / back_price - 1) * (365 / days_to_roll)
    
    # Long positive carry (backwardation), short negative carry (contango)
    signal = np.sign(roll_yield)
    
    return signal, roll_yield
```

---

### Volatility Risk Premium

**Logic:** Implied volatility typically exceeds realized volatility (volatility risk premium). Capture by selling options.

**Implementation:**
```python
def volatility_risk_premium(implied_vol, realized_vol):
    """
    Calculate VRP and signal
    """
    vrp = implied_vol - realized_vol
    
    # Signal: Sell vol when VRP is high
    signal = -np.sign(vrp) if abs(vrp) > threshold else 0
    
    return vrp, signal
```

---

### Best Practices for Carry Strategies

- Understand that carry strategies have crash risk (negative skew)
- Diversify across multiple carry sources
- Use position limits and stop-losses for tail protection
- Monitor macro conditions that can trigger carry unwinds
- Size positions based on expected carry, not just signal
- Combine carry with momentum for improved risk-adjusted returns

---

## Summary

Quantitative patterns provide systematic, data-driven approaches to trading:

1. **Seasonality**: Exploit predictable calendar-based effects
2. **Volatility Clustering**: Forecast and adapt to volatility regimes
3. **Mean Reversion**: Trade deviations from equilibrium
4. **Breakouts**: Capture trend initiations and continuations
5. **Momentum**: Ride persistent price trends
6. **Machine Learning**: Discover complex, non-linear patterns
7. **Cross-Sectional**: Exploit relative value differences
8. **Carry**: Harvest structural yield premiums

Successful quant trading requires rigorous statistical testing, out-of-sample validation, and realistic accounting for transaction costs and market impact.


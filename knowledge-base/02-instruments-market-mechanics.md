# 2. Instruments & Market Mechanics

This document covers the various financial instruments available for trading and the specific mechanics governing each market type, including derivatives, leverage, and crypto-specific considerations.

---

## 2.1 Spot Markets

### Definition

Spot markets (also called cash markets) are financial markets where financial instruments are traded for immediate delivery and settlement. The "spot price" represents the current market price at which an asset can be bought or sold for immediate exchange.

### Core Principles

- **Immediate Settlement**: Transactions settle within a short timeframe (T+0 to T+2 depending on asset class)
- **Physical or Book-Entry Delivery**: Actual ownership transfer of the underlying asset
- **Price Transparency**: Spot prices reflect current supply and demand equilibrium
- **No Expiration**: Unlike derivatives, spot positions have no expiration date
- **Direct Ownership**: Holder has full ownership rights including dividends, voting rights, etc.

### Common Use Cases

- Long-term investment and portfolio construction
- Basis for derivatives pricing (spot-futures relationships)
- Arbitrage between spot and derivative markets
- Direct exposure to asset price movements
- Dividend capture and income strategies

### Examples

**Equity Spot Market:**
- Purchase 100 shares of AAPL at $175.50
- Settlement: T+2 (trade date plus two business days)
- Ownership: Full shareholder rights, dividends, voting

**Forex Spot Market:**
- Buy EUR/USD at 1.0850
- Settlement: T+2 (standard for major pairs)
- Delivery: Exchange of currency amounts

**Cryptocurrency Spot Market:**
- Buy 1 BTC at $45,000
- Settlement: Near-instantaneous (blockchain confirmation)
- Custody: Direct ownership, can withdraw to personal wallet

**Commodity Spot Market:**
- Buy 100 oz gold at $1,950/oz
- Settlement: Varies (T+2 or physical delivery arrangements)
- Delivery: Can take physical delivery or hold in vault

### Best Practices for Traders

- Understand settlement cycles to manage cash flow and margin requirements
- Factor in custody and storage costs for physical commodities
- Be aware of corporate actions affecting equity positions
- Use spot markets for long-term directional exposure
- Monitor spot-futures basis for arbitrage opportunities
- Consider total cost of ownership including financing costs

### Mathematical Rules/Formulas

**Spot Return:**
```
Simple Return = (P_t - P_(t-1)) / P_(t-1)
Log Return = ln(P_t / P_(t-1))
```

**Total Return (with dividends):**
```
Total Return = (P_t - P_(t-1) + Dividends) / P_(t-1)
```

**Cost of Carry Relationship:**
```
Futures Price = Spot Price * e^((r - y) * T)
```
Where r = risk-free rate, y = yield/dividend rate, T = time to expiration.

---

## 2.2 Futures & Perpetual Swaps

### Definition

- **Futures**: Standardized contracts obligating the buyer to purchase, or the seller to sell, an asset at a predetermined price on a specified future date.
- **Perpetual Swaps**: Derivative contracts similar to futures but with no expiration date, commonly used in cryptocurrency markets, with periodic funding rate payments to maintain price alignment with spot.

### Core Principles

- **Leverage**: Futures allow exposure to large notional values with smaller margin deposits
- **Mark-to-Market**: Daily settlement of profits and losses
- **Standardization**: Contract specifications (size, expiration, tick size) are standardized
- **Convergence**: Futures prices converge to spot prices at expiration
- **Funding Rates (Perpetuals)**: Periodic payments between longs and shorts to anchor price to spot

### Common Use Cases

- Hedging existing spot positions against price risk
- Speculating on price direction with leverage
- Calendar spreads (trading the difference between expiration months)
- Basis trading (spot-futures arbitrage)
- Rolling exposure without physical delivery

### Examples

**Futures Contract:**
- Asset: E-mini S&P 500 (ES)
- Contract Size: $50 x S&P 500 Index
- Tick Size: 0.25 points ($12.50)
- Expiration: Quarterly (March, June, September, December)
- Settlement: Cash settled to index value

**Contango vs. Backwardation:**
- **Contango**: Futures price > Spot price (normal for storable commodities)
- **Backwardation**: Futures price < Spot price (indicates supply shortage or high convenience yield)

**Perpetual Swap Funding:**
- BTC-PERP trading at $45,100 (spot at $45,000)
- Premium indicates more longs than shorts
- Funding rate: +0.01% every 8 hours
- Longs pay shorts to hold positions
- Incentivizes arbitrage to close premium

### Best Practices for Traders

- Monitor margin requirements and maintain adequate buffer above maintenance margin
- Understand roll costs when maintaining continuous exposure
- Watch funding rates in perpetuals to avoid unexpected costs
- Use contango/backwardation information for directional signals
- Be aware of contract expiration dates and auto-liquidation rules
- Calculate effective leverage including notional exposure

### Mathematical Rules/Formulas

**Futures Fair Value:**
```
F = S * e^((r - y) * T)
```

**Basis:**
```
Basis = Futures Price - Spot Price
Basis (%) = (F - S) / S * 100%
```

**Annualized Basis:**
```
Annualized Basis = (F/S - 1) * (365 / Days to Expiry) * 100%
```

**Perpetual Funding Rate:**
```
Funding Payment = Position Value * Funding Rate
```
If funding rate is positive: longs pay shorts
If funding rate is negative: shorts pay longs

**Contract Value:**
```
Notional Value = Contract Multiplier * Current Price * Number of Contracts
```

---

## 2.3 Options

### Definition

Options are derivative contracts that give the holder the right, but not the obligation, to buy (call) or sell (put) an underlying asset at a specified price (strike) before or on a specified date (expiration).

### Core Principles

- **Asymmetric Payoff**: Limited downside (premium paid) with unlimited upside potential for buyers
- **Time Decay (Theta)**: Option value erodes as expiration approaches
- **Implied Volatility**: Market's expectation of future volatility embedded in option prices
- **Non-Linear Risk**: Option Greeks describe sensitivity to various factors
- **Exercise Styles**: American (any time), European (expiration only)

### Common Use Cases

- Hedging portfolio against downside risk (protective puts)
- Generating income from existing positions (covered calls)
- Speculating on direction with defined risk
- Volatility trading (straddles, strangles)
- Complex multi-leg strategies for specific market views

### Examples

**Call Option:**
- AAPL Call, Strike $180, Expiration 30 days
- Premium: $3.50
- Breakeven: $183.50 ($180 + $3.50)
- Max Loss: $3.50 (premium paid)
- Max Gain: Unlimited (above breakeven)

**Put Option:**
- SPY Put, Strike $440, Expiration 45 days
- Premium: $5.00
- Breakeven: $435.00 ($440 - $5.00)
- Max Loss: $5.00 (premium paid)
- Max Gain: $435.00 (if underlying goes to zero)

**Covered Call:**
- Own 100 shares AAPL at $175
- Sell 1 Call, Strike $185, Premium $2.50
- Outcome if price stays below $185: Keep shares + $250 premium
- Outcome if price exceeds $185: Shares called away at $185, total gain $12.50/share

### Best Practices for Traders

- Never sell naked options without understanding unlimited loss potential
- Monitor implied volatility relative to historical volatility
- Understand all Greeks, especially for complex positions
- Calculate max loss before entering any options trade
- Be aware of dividend dates for early exercise risk on American options
- Use options for defined-risk directional bets rather than naked futures/spot
- Close or roll positions well before expiration to avoid gamma risk

### Mathematical Rules/Formulas

**Black-Scholes Call Price:**
```
C = S * N(d1) - K * e^(-rT) * N(d2)

d1 = (ln(S/K) + (r + sigma^2/2) * T) / (sigma * sqrt(T))
d2 = d1 - sigma * sqrt(T)
```

**Put-Call Parity:**
```
C - P = S - K * e^(-rT)
```

**The Greeks:**
```
Delta = dV/dS (sensitivity to underlying price)
Gamma = d(Delta)/dS (rate of change of delta)
Theta = dV/dT (time decay per day)
Vega = dV/d(sigma) (sensitivity to volatility)
Rho = dV/dr (sensitivity to interest rates)
```

**Intrinsic and Time Value:**
```
Call Intrinsic = max(S - K, 0)
Put Intrinsic = max(K - S, 0)
Time Value = Option Price - Intrinsic Value
```

---

## 2.4 Margin, Leverage & Liquidation Engines

### Definition

- **Margin**: Collateral deposited to cover potential losses, expressed as initial margin (to open) and maintenance margin (to maintain positions)
- **Leverage**: The ratio of position size to margin, amplifying both gains and losses
- **Liquidation Engine**: Automated system that forcibly closes positions when margin falls below maintenance requirements

### Core Principles

- **Leverage Amplification**: Leverage multiplies returns in both directions
- **Margin Call**: Warning when equity approaches maintenance margin
- **Forced Liquidation**: Automatic position closure to prevent negative equity
- **Cross vs. Isolated Margin**: Cross uses entire account balance; isolated limits risk per position
- **Insurance Funds**: Exchange reserves to cover liquidation shortfalls in volatile markets

### Common Use Cases

- Increasing capital efficiency for qualified strategies
- Hedging with reduced capital requirements
- Short selling (borrowing assets)
- Futures and derivatives trading
- Crypto perpetual swap trading

### Examples

**Leverage Calculation:**
- Account Balance: $10,000
- Position Size: $50,000
- Leverage: 5x ($50,000 / $10,000)

**Margin Requirements:**
- Initial Margin: 20% ($10,000 for $50,000 position)
- Maintenance Margin: 10% ($5,000)
- Liquidation Trigger: When equity falls below $5,000

**Liquidation Scenario:**
- Position: 5x Long BTC at $50,000 (1 BTC exposure, $10,000 margin)
- Liquidation Price: ~$40,000 (20% drop = 100% of margin)
- Calculation: Entry - (Margin / Position Size) = $50,000 - $10,000 = $40,000

**Cross vs. Isolated Margin:**
- Cross Margin: All account funds available for all positions
- Isolated Margin: Only allocated margin used for specific position
- Trade-off: Cross provides more buffer but exposes entire account to any position's loss

### Best Practices for Traders

- Never use maximum available leverage
- Calculate liquidation price before entering any leveraged position
- Maintain margin buffer significantly above maintenance requirements
- Use isolated margin for high-risk trades to limit account exposure
- Set stop-losses well above liquidation price
- Understand the exchange's liquidation mechanism (gradual vs. full)
- Monitor funding rates and margin requirements during volatility spikes
- Account for spread widening during volatile periods when calculating liquidation risk

### Mathematical Rules/Formulas

**Leverage Ratio:**
```
Leverage = Position Size / Margin
Effective Leverage = Notional Exposure / Account Equity
```

**Long Position Liquidation Price:**
```
Liquidation Price = Entry Price * (1 - Initial Margin % + Maintenance Margin %)
```

**Short Position Liquidation Price:**
```
Liquidation Price = Entry Price * (1 + Initial Margin % - Maintenance Margin %)
```

**Margin Ratio:**
```
Margin Ratio = Maintenance Margin Required / Account Equity
```
Liquidation occurs when Margin Ratio >= 100%

**Return Amplification:**
```
Leveraged Return = Leverage * Underlying Return
5x leverage, 2% move = 10% return (or loss)
```

---

## 2.5 Crypto-Specific Mechanics

### Definition

Crypto-specific mechanics encompass the unique trading infrastructure, settlement systems, and market structures particular to cryptocurrency and digital asset markets, including decentralized exchanges, automated market makers, and blockchain-based settlement.

### Core Principles

- **24/7 Markets**: No close, continuous trading globally
- **Self-Custody**: Users can hold assets directly without intermediaries
- **On-Chain vs. Off-Chain**: Settlement can occur on blockchain or within exchange databases
- **Decentralization Spectrum**: From fully decentralized (DEX) to centralized (CEX)
- **Network Fees**: Blockchain transactions incur gas/network fees
- **Finality**: Settlement finality depends on blockchain confirmation times

### Common Use Cases

- Trading on centralized exchanges (CEX) for liquidity and speed
- Decentralized exchange (DEX) trading for self-custody and permissionless access
- Yield farming and liquidity provision on AMMs
- Cross-chain arbitrage
- On-chain derivatives trading

### Examples

**Centralized Exchange (CEX):**
- Examples: Binance, Coinbase, Kraken
- Order book model, high liquidity
- Custody held by exchange
- KYC required, faster execution
- Counterparty risk to exchange

**Decentralized Exchange (DEX):**
- Examples: Uniswap, SushiSwap, dYdX
- Self-custody throughout trading
- Permissionless, no KYC
- Higher fees (gas), potential MEV exposure
- Liquidity from liquidity pools

**Automated Market Maker (AMM):**
- Bonding curve pricing (x * y = k constant product)
- No order book, trades against liquidity pool
- Price impact proportional to trade size
- Liquidity providers earn fees but face impermanent loss
- Examples: Uniswap V2/V3, Curve, Balancer

**Concentrated Liquidity (CLMM):**
- Liquidity providers set price ranges
- More capital efficient than constant product AMMs
- Higher yields but requires active management
- Example: Uniswap V3

### Best Practices for Traders

- Use hardware wallets for significant holdings
- Compare CEX and DEX execution for best prices
- Account for gas fees in trade profitability calculations
- Be aware of MEV (Maximal Extractable Value) risks on DEX
- Monitor blockchain congestion before executing time-sensitive trades
- Use reputable bridges for cross-chain operations
- Verify smart contract addresses before interacting
- Understand impermanent loss before providing liquidity

### Mathematical Rules/Formulas

**Constant Product AMM (Uniswap V2):**
```
x * y = k

Output Amount = (y * Input Amount) / (x + Input Amount)
```

**Price Impact (AMM):**
```
Price Impact = Trade Size / (Pool Reserve + Trade Size)
```

**Impermanent Loss:**
```
IL = 2 * sqrt(price_ratio) / (1 + price_ratio) - 1
```
Where price_ratio = new_price / original_price

**Concentrated Liquidity (V3):**
```
Real Reserves = Virtual Reserves * (sqrt(P_upper) - sqrt(P_lower)) / sqrt(P_current)
```

---

## 2.6 FX Basics

### Definition

The foreign exchange (FX or forex) market is the global marketplace for trading currencies. It is the largest and most liquid financial market, with daily turnover exceeding $7 trillion, operating 24 hours from Sydney open to New York close.

### Core Principles

- **Currency Pairs**: Currencies traded in pairs (EUR/USD, USD/JPY), first is base, second is quote
- **Pips**: Smallest price movement, typically 0.0001 for most pairs (0.01 for JPY pairs)
- **Lot Sizes**: Standard (100,000 units), Mini (10,000), Micro (1,000)
- **Interest Rate Differentials**: Carry trade opportunities from rate differences
- **Interbank Market**: Primary market among major banks, others access via brokers

### Common Use Cases

- Hedging foreign currency exposure for businesses
- Carry trades exploiting interest rate differentials
- Speculating on macroeconomic trends and central bank policy
- Portfolio diversification across currencies
- Arbitrage across currency crosses

### Examples

**Quote Convention:**
- EUR/USD = 1.0850
- Interpretation: 1 Euro costs 1.0850 US Dollars
- Base currency: EUR
- Quote currency: USD

**Pip Value Calculation:**
- EUR/USD position: 100,000 units (1 standard lot)
- Pip = 0.0001
- Pip Value = 100,000 * 0.0001 = $10 per pip

**Carry Trade:**
- Borrow JPY at 0.1% interest
- Invest in AUD at 4.0% interest
- Carry = 3.9% annually
- Risk: Currency movement can exceed carry return

**Cross Rates:**
- EUR/USD = 1.0850
- USD/JPY = 150.00
- EUR/JPY = 1.0850 * 150.00 = 162.75

### Best Practices for Traders

- Understand the economic calendars driving FX moves
- Monitor central bank communications and interest rate expectations
- Be aware of market sessions and liquidity variations
- Use appropriate position sizing given FX leverage availability
- Consider correlation between currency pairs in portfolio construction
- Account for swap rates (rollover) for positions held overnight
- Watch for intervention risk in certain currency pairs

### Mathematical Rules/Formulas

**Pip Value:**
```
Pip Value = (Pip Size / Exchange Rate) * Lot Size
```

**Position Profit/Loss:**
```
P/L = (Exit Price - Entry Price) * Lot Size * Pip Value
```

**Swap/Rollover Calculation:**
```
Swap = Position Size * (Base Currency Rate - Quote Currency Rate) / 365
```

**Cross Rate:**
```
If EUR/USD = a and USD/JPY = b
Then EUR/JPY = a * b
```

**Forward Rate (Interest Rate Parity):**
```
F = S * ((1 + r_quote) / (1 + r_base))^T
```

---

## 2.7 Settlement & Clearing

### Definition

- **Settlement**: The process of transferring ownership of securities and funds between parties to complete a trade
- **Clearing**: The process of validating, matching, and preparing trades for settlement, including netting of obligations
- **Central Counterparty (CCP)**: Entity that interposes itself between buyers and sellers to guarantee trade completion

### Core Principles

- **Counterparty Risk Mitigation**: CCPs reduce bilateral counterparty exposure
- **Netting**: Reducing gross obligations to net amounts for efficiency
- **Delivery vs. Payment (DvP)**: Simultaneous exchange of securities and cash
- **Settlement Cycles**: T+0 (same day) to T+2 (trade date plus two days)
- **Margin Requirements**: Collateral held by CCPs to cover potential losses

### Common Use Cases

- Understanding when funds and securities become available
- Managing cash flow around settlement dates
- Assessing counterparty risk in OTC markets
- Calculating margin requirements for cleared derivatives
- Corporate action processing

### Examples

**Equity Settlement (T+2):**
- Trade executed Monday
- Settlement Wednesday
- Cash debited/credited and shares transferred

**Futures Settlement (Daily):**
- Daily mark-to-market
- Variation margin exchanged each day
- Final settlement at expiration

**Crypto Settlement:**
- CEX: Internal ledger, instant
- DEX: On-chain, block confirmation time (seconds to minutes)
- Withdrawal: Network confirmation required

### Best Practices for Traders

- Ensure sufficient funds available on settlement date
- Understand settlement conventions for each asset class
- Monitor CCP margin requirements for cleared positions
- Be aware of settlement failures and their implications
- Account for settlement timing in cash management
- Understand the difference between trade date and settlement date accounting

### Mathematical Rules/Formulas

**Netting Benefit:**
```
Gross Obligations = Sum of all trade values
Net Obligation = |Total Buys - Total Sells|
Netting Efficiency = (Gross - Net) / Gross * 100%
```

**Exposure at Default:**
```
EAD = Replacement Cost + Potential Future Exposure
```

---

## 2.8 Contract Specifications

### Definition

Contract specifications define the standardized terms and conditions of derivative contracts, including size, tick increments, expiration rules, and settlement methods. Understanding specifications is essential for proper position sizing, risk calculation, and P&L computation.

### Core Principles

- **Standardization**: Exchange-traded derivatives have fixed specifications
- **Multiplier/Contract Size**: Defines notional value per contract
- **Tick Size**: Minimum price increment
- **Expiration Rules**: When and how contracts expire and settle
- **Trading Hours**: Session times and any restrictions

### Common Use Cases

- Calculating position size and notional exposure
- Determining margin requirements
- Understanding roll procedures
- Comparing similar contracts across exchanges
- Backtesting with accurate contract specifications

### Examples

**E-mini S&P 500 (ES):**
- Exchange: CME
- Multiplier: $50
- Tick Size: 0.25 points ($12.50)
- Settlement: Cash settled to S&P 500 index
- Expiration: Third Friday of contract month

**Bitcoin Futures (BTC):**
- Exchange: CME
- Multiplier: 5 BTC per contract
- Tick Size: $5 ($25 per tick)
- Settlement: Cash settled to CME CF Bitcoin Reference Rate

**Crude Oil (CL):**
- Exchange: NYMEX
- Multiplier: 1,000 barrels
- Tick Size: $0.01 ($10 per tick)
- Settlement: Physical delivery (most traders roll before expiration)

### Best Practices for Traders

- Always verify contract specifications before trading new instruments
- Calculate notional exposure and tick value before entering positions
- Understand settlement procedures (cash vs. physical)
- Be aware of contract roll dates and procedures
- Monitor for specification changes announced by exchanges
- Use correct specifications in backtesting and risk systems

### Mathematical Rules/Formulas

**Notional Value:**
```
Notional = Price * Multiplier * Number of Contracts
```

**Tick Value:**
```
Tick Value = Tick Size * Multiplier
```

**P&L Calculation:**
```
P/L = (Exit Price - Entry Price) / Tick Size * Tick Value * Contracts
```

**Margin Requirement (Initial):**
```
Initial Margin = Notional Value * Initial Margin Percentage
```

---

## Summary

Understanding instruments and market mechanics is fundamental to successful trading. Each instrument type has unique characteristics affecting:

1. **Capital Efficiency**: Leverage availability varies dramatically across instruments
2. **Risk Profile**: Options offer defined risk; futures have unlimited downside
3. **Settlement**: Timing and method of settlement impacts cash management
4. **Costs**: Transaction costs, funding rates, and carry vary by instrument
5. **Liquidity**: Market depth and trading hours affect execution quality

Traders should match instrument selection to their strategy requirements, risk tolerance, and operational capabilities. Master the mechanics before deploying capital.


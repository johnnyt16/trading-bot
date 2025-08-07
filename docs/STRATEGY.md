# Trading Strategy - Momentum Trading

## How It Works

The bot uses a momentum-based strategy to identify stocks that are likely to continue moving in their current direction.

## Entry Signals

The bot enters a position when:

1. **Price Momentum** (25% weight)
   - Stock moves up >1% in 5 minutes
   
2. **Volume Spike** (25% weight)  
   - Current volume >1.5x average volume
   
3. **RSI Oversold** (25% weight)
   - RSI between 30-40 (potential bounce)
   
4. **Above SMA20** (15% weight)
   - Price above 20-period moving average

**Minimum Confidence**: 60% combined score

## Exit Strategy

### Take Profit
- Automatically sells at +5% gain
- Locks in profits quickly

### Stop Loss  
- Automatically sells at -3% loss
- Limits downside risk

## Risk Management

- **Position Size**: Max 5% of portfolio per trade
- **Max Positions**: 5 concurrent positions
- **Daily Loss Limit**: Stops trading after -5% daily loss
- **Correlation Check**: Avoids highly correlated positions

## Watchlist

Default stocks monitored:
- TSLA - High volatility tech
- NVDA - Semiconductor momentum
- AMD - Volatile chip stock
- AAPL - Large cap tech
- MSFT - Stable tech giant
- META - Social media volatility
- GOOGL - Search giant
- AMZN - E-commerce leader

## Expected Performance

- **Target Win Rate**: 55-60%
- **Risk/Reward**: 1:1.67 (3% risk, 5% reward)
- **Trades per Day**: 2-5 on average
- **Hold Time**: Minutes to hours

## Optimization Tips

1. **Increase Confidence Threshold**: Set to 0.65 or 0.70 for fewer, higher quality trades
2. **Adjust Watchlist**: Focus on most profitable symbols
3. **Time of Day**: Most volatile at market open (9:30-10:30 AM) and close (3:00-4:00 PM)
4. **Market Conditions**: Works best in trending markets, not sideways
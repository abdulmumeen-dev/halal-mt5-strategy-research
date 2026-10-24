# Strategy and validation notes

## Baseline logic

The signal is a fresh EMA(20)/EMA(50) crossover confirmed by ADX(14) above 18. The stop is 1.8 ATR away and the target is 1.5 times the stop distance. This is intentionally plain so that results can be inspected and falsified.

## Risk profile

The default research risk is 0.5% of hypothetical balance per signal. The backtester blocks new entries after a 2% modeled daily loss or 8% modeled peak-to-trough drawdown. These are not guarantees and do not account for all execution risks.

## Halal constraints attempted by this profile

- No interest/carry logic.
- No swap income or swap expense is modeled as a source of profit.
- No martingale, grid recovery, or averaging down.
- No unlimited holding; positions are intended to be flat before the configured session close.
- No signal when the trend/volatility filter fails.

These constraints do not establish that the underlying product is halal. A swap-free account is a broker account feature, not a complete Islamic-finance ruling. Forex CFDs, leverage, short selling, and contract structure require review by a qualified scholar familiar with the exact instrument and account terms.

## Validation checklist

- Use a clean, broker-consistent OHLCV export.
- Include spread, commission, slippage, and rejected-order assumptions.
- Keep training, validation, and out-of-sample periods separate.
- Test different symbols and timeframes, not only the best result.
- Use walk-forward testing and parameter sensitivity checks.
- Track losing streaks, maximum drawdown, exposure, and time in market.
- Forward-observe signals without execution for at least 8–12 weeks.
- Treat every return, fill, and balance in the report as hypothetical.

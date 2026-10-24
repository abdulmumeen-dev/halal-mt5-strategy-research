# Halal-Constrained MT5 Strategy Research

This repository contains a reproducible strategy-research backtester and a signal-only MetaTrader 5 Expert Advisor. It does **not** place, modify, or cancel broker orders.

## Contents

- `backtest.py` — hypothetical CSV backtester
- `config.json` — baseline parameters
- `sample_ohlcv.csv` — tiny smoke-test dataset
- `HalalConstrainedSignals.mq5` — MT5 signal-only EA
- `STRATEGY.md` — assumptions, constraints, and validation checklist

## Run the backtest

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python backtest.py --csv sample_ohlcv.csv --initial-balance 1000 --risk-per-trade 0.005
```

The CSV must contain `time,open,high,low,close,volume`. Results are hypothetical and should not be interpreted as a performance claim.

## MT5

Copy `HalalConstrainedSignals.mq5` into the MT5 `MQL5/Experts` folder, compile it in MetaEditor, and attach it to a chart for alerts only. The file intentionally contains no `CTrade`, `OrderSend`, `PositionOpen`, `Buy`, or `Sell` order-submission calls.

## Halal caveat

The constraints in this project avoid swap/carry logic, martingale, grid recovery, averaging down, and unlimited holding. They do **not** certify that forex, CFDs, leverage, short selling, a broker account, or any instrument is halal. A qualified Islamic-finance scholar should review the exact account and contract structure. Swap-free status alone is not a complete halal ruling.

## Risk notice

The strategy is a transparent baseline, not a promise of profit. Test with broker-consistent data, realistic spread/commission/slippage, separate out-of-sample periods, walk-forward validation, and extended signal-only observation before making any independent decision.

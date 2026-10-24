#!/usr/bin/env python3
"""Hypothetical, signal-only strategy backtester.

This module never connects to a broker and never submits orders.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def indicators(df: pd.DataFrame, fast: int, slow: int, atr_period: int, adx_period: int) -> pd.DataFrame:
    out = df.copy()
    out["ema_fast"] = out["close"].ewm(span=fast, adjust=False).mean()
    out["ema_slow"] = out["close"].ewm(span=slow, adjust=False).mean()
    prev_close = out["close"].shift(1)
    tr = pd.concat(
        [out["high"] - out["low"], (out["high"] - prev_close).abs(), (out["low"] - prev_close).abs()], axis=1
    ).max(axis=1)
    out["atr"] = tr.ewm(alpha=1 / atr_period, adjust=False).mean()
    up = out["high"].diff()
    down = -out["low"].diff()
    plus_dm = up.where((up > down) & (up > 0), 0.0)
    minus_dm = down.where((down > up) & (down > 0), 0.0)
    atr = out["atr"].replace(0, np.nan)
    plus_di = 100 * plus_dm.ewm(alpha=1 / adx_period, adjust=False).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1 / adx_period, adjust=False).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    out["adx"] = dx.ewm(alpha=1 / adx_period, adjust=False).mean()
    return out


def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"time", "open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.sort_values("time").drop_duplicates("time").reset_index(drop=True)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="raise")
    if (df[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("Prices must be positive")
    return df


def run(df: pd.DataFrame, cfg: dict, initial_balance: float) -> tuple[dict, pd.DataFrame]:
    df = indicators(df, cfg["ema_fast"], cfg["ema_slow"], cfg["atr_period"], cfg["adx_period"])
    balance = float(initial_balance)
    peak = balance
    position = None
    trades = []
    daily_start = {}
    max_drawdown = 0.0
    spread = cfg["assumed_spread_points"] * cfg["point_size"]

    def day_key(ts):
        return ts.date().isoformat()

    def flat_time(ts):
        return ts.hour >= cfg["session_end_utc"] or ts.hour < cfg["session_start_utc"]

    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i - 1]
        day = day_key(row["time"])
        daily_start.setdefault(day, balance)
        daily_loss = (balance - daily_start[day]) / daily_start[day]
        drawdown = (balance - peak) / peak
        max_drawdown = min(max_drawdown, drawdown)

        if position:
            position["bars"] += 1
            exit_price = None
            reason = None
            if position["side"] == "long":
                if row["low"] <= position["stop"]:
                    exit_price, reason = position["stop"], "stop"
                elif row["high"] >= position["target"]:
                    exit_price, reason = position["target"], "target"
            else:
                if row["high"] >= position["stop"]:
                    exit_price, reason = position["stop"], "stop"
                elif row["low"] <= position["target"]:
                    exit_price, reason = position["target"], "target"
            if flat_time(row["time"]):
                exit_price, reason = row["close"], "session_flat"
            elif position["bars"] >= cfg["max_bars_in_trade"]:
                exit_price, reason = row["close"], "time_exit"
            if exit_price is not None:
                gross = (exit_price - position["entry"]) * position["units"]
                if position["side"] == "short":
                    gross = -gross
                cost = spread * position["units"]
                pnl = gross - cost
                balance += pnl
                trades.append({**position, "exit_time": row["time"].isoformat(), "exit": exit_price, "reason": reason, "pnl": pnl, "balance": balance})
                position = None
                peak = max(peak, balance)
                continue

        if position or flat_time(row["time"]):
            continue
        if daily_loss <= -cfg["max_daily_loss_fraction"] or drawdown <= -cfg["max_drawdown_fraction"]:
            continue
        if not np.isfinite(row["atr"]) or not np.isfinite(row["adx"]) or row["adx"] < cfg["adx_min"]:
            continue

        cross_up = prev["ema_fast"] <= prev["ema_slow"] and row["ema_fast"] > row["ema_slow"]
        cross_down = prev["ema_fast"] >= prev["ema_slow"] and row["ema_fast"] < row["ema_slow"]
        side = "long" if cross_up else "short" if cross_down else None
        if not side:
            continue
        entry = float(row["close"] + spread / 2 if side == "long" else row["close"] - spread / 2)
        risk_distance = float(row["atr"] * cfg["atr_stop_multiple"])
        if risk_distance <= 0:
            continue
        risk_cash = balance * cfg["risk_per_trade"]
        units = risk_cash / risk_distance
        stop = entry - risk_distance if side == "long" else entry + risk_distance
        target_distance = risk_distance * cfg["reward_risk"]
        target = entry + target_distance if side == "long" else entry - target_distance
        position = {"entry_time": row["time"].isoformat(), "side": side, "entry": entry, "stop": stop, "target": target, "units": units, "bars": 0}

    if position:
        row = df.iloc[-1]
        exit_price = float(row["close"])
        gross = (exit_price - position["entry"]) * position["units"] * (1 if position["side"] == "long" else -1)
        pnl = gross - spread * position["units"]
        balance += pnl
        trades.append({**position, "exit_time": row["time"].isoformat(), "exit": exit_price, "reason": "end_of_data", "pnl": pnl, "balance": balance})

    trade_df = pd.DataFrame(trades)
    wins = int((trade_df["pnl"] > 0).sum()) if not trade_df.empty else 0
    summary = {
        "hypothetical": True,
        "initial_balance": initial_balance,
        "final_balance": balance,
        "return_fraction": balance / initial_balance - 1,
        "trades": len(trade_df),
        "wins": wins,
        "win_rate": wins / len(trade_df) if len(trade_df) else 0.0,
        "max_drawdown_fraction": max_drawdown,
        "config": cfg,
    }
    return summary, trade_df


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--initial-balance", type=float, default=1000.0)
    parser.add_argument("--risk-per-trade", type=float, default=None)
    args = parser.parse_args()
    cfg = json.loads(Path("config.json").read_text())
    if args.risk_per_trade is not None:
        cfg["risk_per_trade"] = args.risk_per_trade
    summary, trades = run(load_csv(args.csv), cfg, args.initial_balance)
    Path("reports").mkdir(exist_ok=True)
    Path("reports/backtest.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    trades.to_csv("reports/trades.csv", index=False)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()

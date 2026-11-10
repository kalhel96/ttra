"""Agent 6 - Equity curve: marks the account to market and summarizes performance."""
import sqlite3

import pandas as pd


def mark_to_market(broker, positions, feed):
    value = broker.cash()
    for p in positions.values():
        bars = feed.bars(p["symbol"])
        px = float(bars["Close"].iloc[-1]) if len(bars) else p["entry_price"]
        value += px * p["qty"]
    return value


def summary(db_path):
    con = sqlite3.connect(db_path)
    trades = pd.read_sql("SELECT * FROM trades", con)
    eq = pd.read_sql("SELECT * FROM equity", con)
    con.close()
    if trades.empty:
        return {"trades": 0}
    curve = eq["equity"]
    drawdown = (curve / curve.cummax() - 1).min() * 100
    wins = trades[trades.pnl > 0]
    losses = trades[trades.pnl <= 0]
    out = {
        "trades": len(trades),
        "win_rate_pct": round(len(wins) / len(trades) * 100, 1),
        "total_pnl": round(trades.pnl.sum(), 2),
        "avg_win": round(wins.pnl.mean(), 2) if len(wins) else 0.0,
        "avg_loss": round(losses.pnl.mean(), 2) if len(losses) else 0.0,
        "profit_factor": round(wins.pnl.sum() / -losses.pnl.sum(), 2) if losses.pnl.sum() < 0 else None,
        "max_drawdown_pct": round(drawdown, 2),
        "avg_slippage_bps": round((trades.entry_slippage_bps + trades.exit_slippage_bps).mean() / 2, 2),
        "start_equity": round(curve.iloc[0], 2),
        "end_equity": round(curve.iloc[-1], 2),
    }
    return {k: (float(v) if v is not None and k != "trades" else v) for k, v in out.items()}

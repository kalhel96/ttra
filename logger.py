"""Agent 5 - Logger: writes every decision (and the reason for it) to SQLite.

Tables
    events  - everything: signals, rejections, opens, closes, errors
    trades  - one row per round-trip trade
    equity  - equity snapshot after each close (and at start)
"""
import json
import sqlite3


SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY, ts TEXT, agent TEXT, kind TEXT, symbol TEXT, reason TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY, symbol TEXT, qty INTEGER,
    entry_time TEXT, entry_price REAL, expected_entry REAL, entry_slippage_bps REAL,
    exit_time TEXT, exit_price REAL, expected_exit REAL, exit_slippage_bps REAL,
    stop REAL, target REAL, pnl REAL, pnl_pct REAL, entry_reason TEXT, exit_reason TEXT);
CREATE TABLE IF NOT EXISTS equity (id INTEGER PRIMARY KEY, ts TEXT, equity REAL, cash REAL);
"""


class Logger:
    def __init__(self, path, echo=True):
        self.db = sqlite3.connect(path)
        self.db.executescript(SCHEMA)
        self.echo = echo

    def event(self, ts, agent, kind, reason, symbol=None, **data):
        self.db.execute(
            "INSERT INTO events (ts, agent, kind, symbol, reason, data) VALUES (?,?,?,?,?,?)",
            (str(ts), agent, kind, symbol, reason, json.dumps(data, default=str)),
        )
        self.db.commit()
        if self.echo:
            print(f"[{str(ts)[:16]}] {agent:<9} {kind:<8} {symbol or '':<6} {reason}")

    def trade(self, pos, close, exit_time, entry_reason, exit_reason):
        self.db.execute(
            """INSERT INTO trades (symbol, qty, entry_time, entry_price, expected_entry,
               entry_slippage_bps, exit_time, exit_price, expected_exit, exit_slippage_bps,
               stop, target, pnl, pnl_pct, entry_reason, exit_reason)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (pos["symbol"], pos["qty"], str(pos["entry_time"]), pos["entry_price"],
             pos["expected_entry"], pos["entry_slippage_bps"], str(exit_time),
             close["exit_price"], close["expected_exit"], close["exit_slippage_bps"],
             pos["stop"], pos["target"], close["pnl"], close["pnl_pct"], entry_reason, exit_reason),
        )
        self.db.commit()

    def equity(self, ts, equity, cash):
        self.db.execute("INSERT INTO equity (ts, equity, cash) VALUES (?,?,?)", (str(ts), equity, cash))
        self.db.commit()

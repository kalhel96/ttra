"""Orchestrator: runs the six agents in order on every new bar.

    python main.py live            # real-time; broker and data source from config.py
    python main.py replay          # offline test on synthetic bars (sim broker)
    python main.py replay --real   # replay the last 5 trading days of real bars (sim broker)
"""
import argparse
import os
import time

import config
from agents import equity as equity_agent
from agents import executor, risk_filter, scanner, sizer
from agents.logger import Logger
from brokers.sim import SimBroker
from data import AlpacaFeed, LiveFeed, ReplayFeed, synthetic_frames


def make_broker(mode):
    if mode == "live" and config.BROKER == "alpaca":
        from brokers.alpaca_paper import AlpacaPaperBroker
        return AlpacaPaperBroker()
    if mode == "live" and config.BROKER == "webull":
        from brokers.webull_paper import WebullPaperBroker
        return WebullPaperBroker()
    return SimBroker()


def make_feed():
    if config.DATA_SOURCE == "alpaca":
        return AlpacaFeed(config.WATCHLIST, config.BAR_INTERVAL)
    return LiveFeed(config.WATCHLIST, config.BAR_INTERVAL)


def market_open(now):
    return now.weekday() < 5 and "09:30" <= now.strftime("%H:%M") < "16:00"


class Bot:
    def __init__(self, feed, broker, log):
        self.feed, self.broker, self.log = feed, broker, log
        self.positions = {}        # symbol -> position dict
        self.entry_reasons = {}
        self.last_bar_time = {}    # avoid re-processing the same bar in live mode

    def tick(self):
        now = self.feed.now()
        self.manage_open_positions(now)
        self.look_for_entries(now)

    # -- exits ----------------------------------------------------------------
    def manage_open_positions(self, now):
        for sym in list(self.positions):
            pos = self.positions[sym]
            bars = self.feed.bars(sym)
            if bars.empty or self.last_bar_time.get(sym) == bars.index[-1]:
                continue
            self.last_bar_time[sym] = bars.index[-1]
            pos["bars_held"] += 1
            why, px = executor.exit_reason(pos, bars.iloc[-1], now)
            if not why:
                continue
            res = executor.close_position(self.broker, pos, px)
            if res is None:
                self.log.event(now, "executor", "error", "close order failed", sym)
                continue
            self.log.event(now, "executor", "close", (
                f"{why}; sold {pos['qty']} @ {res['exit_price']:.2f} "
                f"(slip {res['exit_slippage_bps']:.1f} bps) P&L ${res['pnl']:+,.2f} ({res['pnl_pct']:+.2f}%)"), sym)
            self.log.trade(pos, res, now, self.entry_reasons.pop(sym), why)
            del self.positions[sym]
            eq = equity_agent.mark_to_market(self.broker, self.positions, self.feed)
            self.log.equity(now, eq, self.broker.cash())
            self.log.event(now, "equity", "update", f"equity ${eq:,.2f}")

    # -- entries --------------------------------------------------------------
    def look_for_entries(self, now):
        sigs = scanner.scan(self.feed, config.WATCHLIST)
        sigs = [s for s in sigs if self.last_bar_time.get(("sig", s.symbol)) != now]
        for s in sigs:
            self.last_bar_time[("sig", s.symbol)] = now
            self.log.event(now, "scanner", "signal", s.reason, s.symbol)
        if not sigs:
            return

        passed, rejected = risk_filter.check(sigs, self.feed, set(self.positions))
        for s, why in rejected:
            self.log.event(now, "risk", "reject", why, s.symbol)

        for s in passed:
            eq = equity_agent.mark_to_market(self.broker, self.positions, self.feed)
            plan = sizer.size(s, self.feed.bars(s.symbol), eq, self.broker.cash())
            if plan is None:
                self.log.event(now, "sizer", "skip", "position would be under 1 share", s.symbol)
                continue
            self.log.event(now, "sizer", "plan", plan.reason, s.symbol)
            pos = executor.open_position(self.broker, s, plan, now)
            if pos is None:
                self.log.event(now, "executor", "error", "buy order failed", s.symbol)
                continue
            self.positions[s.symbol] = pos
            self.last_bar_time[s.symbol] = self.feed.bars(s.symbol).index[-1]
            self.entry_reasons[s.symbol] = f"{s.reason} | {plan.reason}"
            self.log.event(now, "executor", "open",
                           f"bought {pos['qty']} @ {pos['entry_price']:.2f} "
                           f"(expected {pos['expected_entry']:.2f}, slip {pos['entry_slippage_bps']:.1f} bps)",
                           s.symbol)


def run_replay(real, db):
    if real:
        live = make_feed()
        live.refresh()
        frames = {s: live.bars(s) for s in config.WATCHLIST if len(live.bars(s))}
    else:
        frames = synthetic_frames(config.WATCHLIST)
    feed = ReplayFeed(frames)
    broker = SimBroker()
    log = Logger(db)
    log.equity(feed.now(), broker.cash(), broker.cash())
    bot = Bot(feed, broker, log)
    while feed.step():
        bot.tick()
    print("\nSummary:", equity_agent.summary(db))


def run_live(db):
    feed = make_feed()
    broker = make_broker("live")
    log = Logger(db)
    log.equity(feed.now(), broker.cash(), broker.cash())
    log.event(feed.now(), "system", "start", f"live mode, broker={broker.name}, data={config.DATA_SOURCE}")
    bot = Bot(feed, broker, log)
    while True:
        now = feed.now()
        if market_open(now):
            try:
                feed.refresh()
                bot.tick()
            except Exception as e:  # keep running; log the problem
                log.event(now, "system", "error", repr(e))
        else:
            print(f"[{now:%H:%M}] market closed; waiting...", end="\r")
        time.sleep(config.LOOP_SECONDS)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["live", "replay"])
    ap.add_argument("--real", action="store_true", help="replay real recent bars (from DATA_SOURCE) instead of synthetic")
    ap.add_argument("--fresh", action="store_true", help="delete the old database first")
    a = ap.parse_args()
    if a.fresh and os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    if a.mode == "replay":
        run_replay(a.real, config.DB_PATH)
    else:
        run_live(config.DB_PATH)

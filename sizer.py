"""Agent 3 - Sizer: sets share count from account equity and volatility (ATR),
not a fixed ticket size."""
from dataclasses import dataclass
import math

import config


@dataclass
class Plan:
    qty: int
    stop: float
    target: float
    atr: float
    reason: str


def atr(bars, period):
    h, l, c = bars["High"], bars["Low"], bars["Close"]
    prev = c.shift(1)
    tr = (h - l).combine((h - prev).abs(), max).combine((l - prev).abs(), max)
    return float(tr.tail(period).mean())


def size(sig, bars, equity, cash) -> Plan | None:
    a = atr(bars, config.ATR_PERIOD)
    if not a or math.isnan(a):
        return None
    stop = sig.price - config.STOP_ATR_MULT * a
    target = sig.price + config.TARGET_ATR_MULT * a
    risk_per_share = sig.price - stop

    risk_dollars = equity * config.RISK_PER_TRADE_PCT / 100
    qty_by_risk = int(risk_dollars // risk_per_share)
    qty_by_cap = int((equity * config.MAX_POSITION_PCT / 100) // sig.price)
    qty_by_cash = int(cash // sig.price)
    qty = min(qty_by_risk, qty_by_cap, qty_by_cash)
    if qty < 1:
        return None

    binding = {qty_by_risk: "risk budget", qty_by_cap: "position cap", qty_by_cash: "available cash"}[qty]
    return Plan(
        qty=qty, stop=round(stop, 2), target=round(target, 2), atr=a,
        reason=(f"{qty} sh (limited by {binding}); risking ${qty * risk_per_share:,.2f} "
                f"= {qty * risk_per_share / equity * 100:.2f}% of ${equity:,.2f} equity; "
                f"stop {stop:.2f}, target {target:.2f} (ATR {a:.2f})"),
    )

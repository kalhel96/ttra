"""Agent 4 - Executor: opens and closes positions through the broker and
records slippage (expected price vs. actual fill)."""
import config


def _slip_bps(side, expected, fill):
    # Positive = worse for us
    sign = 1 if side == "BUY" else -1
    return sign * (fill - expected) / expected * 10_000


def open_position(broker, sig, plan, now):
    fill = broker.buy(sig.symbol, plan.qty, sig.price)
    if fill is None:
        return None
    return {
        "symbol": sig.symbol, "qty": plan.qty, "entry_time": now,
        "expected_entry": sig.price, "entry_price": fill,
        "entry_slippage_bps": _slip_bps("BUY", sig.price, fill),
        "stop": plan.stop, "target": plan.target, "bars_held": 0,
    }


def exit_reason(pos, last_bar, now):
    """Decide whether an open position should be closed on this bar."""
    if now.strftime("%H:%M") >= config.FLATTEN_AT:
        return "end-of-day flatten", float(last_bar["Close"])
    if last_bar["Low"] <= pos["stop"]:
        return f"stop hit at {pos['stop']:.2f}", pos["stop"]
    if last_bar["High"] >= pos["target"]:
        return f"target hit at {pos['target']:.2f}", pos["target"]
    if pos["bars_held"] >= config.MAX_HOLD_BARS:
        return f"time stop after {config.MAX_HOLD_BARS} bars", float(last_bar["Close"])
    return None, None


def close_position(broker, pos, expected_price):
    fill = broker.sell(pos["symbol"], pos["qty"], expected_price)
    if fill is None:
        return None
    pnl = (fill - pos["entry_price"]) * pos["qty"]
    return {
        "exit_price": fill, "expected_exit": expected_price,
        "exit_slippage_bps": _slip_bps("SELL", expected_price, fill),
        "pnl": pnl,
        "pnl_pct": (fill / pos["entry_price"] - 1) * 100,
    }

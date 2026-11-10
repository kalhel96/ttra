"""Agent 2 - Risk filter: the stock-market version of a "rug check".

Rejects signals that are cheap, thin, overextended, late in the day, or that would
exceed the position limit. Returns (passed, rejected_with_reason).
"""
import config


def _hhmm(ts):
    return ts.strftime("%H:%M")


def check(signals, feed, open_symbols):
    passed, rejected = [], []
    now = feed.now()
    slots = config.MAX_OPEN_POSITIONS - len(open_symbols)
    min_dv = (config.MIN_AVG_DOLLAR_VOLUME_IEX if type(feed).__name__ == "AlpacaFeed"
              else config.MIN_AVG_DOLLAR_VOLUME)

    for sig in signals:
        bars = feed.bars(sig.symbol)
        last = bars.iloc[-1]
        avg_dollar_vol = float((bars["Close"] * bars["Volume"]).tail(config.VOLUME_LOOKBACK).mean())
        bar_range_pct = (last["High"] - last["Low"]) / last["Low"] * 100

        why = None
        if sig.symbol in open_symbols:
            why = "already holding it"
        elif _hhmm(now) >= config.NO_NEW_ENTRIES_AFTER:
            why = f"too late in the session (after {config.NO_NEW_ENTRIES_AFTER} ET)"
        elif sig.price < config.MIN_PRICE:
            why = f"price {sig.price:.2f} under ${config.MIN_PRICE:.2f} minimum"
        elif avg_dollar_vol < min_dv:
            why = f"thin: ${avg_dollar_vol:,.0f}/bar under ${min_dv:,.0f}"
        elif bar_range_pct > config.MAX_BAR_RANGE_PCT:
            why = f"overextended: bar range {bar_range_pct:.1f}% > {config.MAX_BAR_RANGE_PCT}%"
        elif slots <= 0:
            why = f"max {config.MAX_OPEN_POSITIONS} open positions reached"

        if why:
            rejected.append((sig, why))
        else:
            passed.append(sig)
            slots -= 1
    return passed, rejected

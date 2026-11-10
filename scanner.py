"""Agent 1 - Scanner: finds volume spikes that break out above recent highs."""
from dataclasses import dataclass

import config


@dataclass
class Signal:
    symbol: str
    price: float
    volume_mult: float
    breakout_level: float
    reason: str


def scan(feed, symbols) -> list[Signal]:
    signals = []
    need = max(config.VOLUME_LOOKBACK, config.BREAKOUT_LOOKBACK) + 1
    for s in symbols:
        bars = feed.bars(s)
        if len(bars) < need:
            continue
        last = bars.iloc[-1]
        prior = bars.iloc[-need:-1]
        avg_vol = prior["Volume"].tail(config.VOLUME_LOOKBACK).mean()
        if avg_vol <= 0:
            continue
        mult = last["Volume"] / avg_vol
        level = prior["High"].tail(config.BREAKOUT_LOOKBACK).max()
        if mult >= config.VOLUME_SPIKE_MULT and last["Close"] > level and last["Close"] > last["Open"]:
            signals.append(Signal(
                symbol=s,
                price=float(last["Close"]),
                volume_mult=float(mult),
                breakout_level=float(level),
                reason=(f"volume {mult:.1f}x the {config.VOLUME_LOOKBACK}-bar average, "
                        f"closed {last['Close']:.2f} above {config.BREAKOUT_LOOKBACK}-bar high {level:.2f}"),
            ))
    return sorted(signals, key=lambda x: x.volume_mult, reverse=True)

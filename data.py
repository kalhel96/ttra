"""Market data: free yfinance bars for live mode, plus a replay feed for testing.

Every feed exposes the same two methods:
    bars(symbol)  -> DataFrame [Open, High, Low, Close, Volume], index = tz-aware ET timestamps,
                     containing only bars that are *closed* as of "now"
    now()         -> current ET timestamp
"""
from __future__ import annotations

import numpy as np
import pandas as pd

ET = "America/New_York"


class LiveFeed:
    """Pulls the last few days of intraday bars from Yahoo Finance (free, ~delayed)."""

    def __init__(self, symbols, interval="5m"):
        import yfinance as yf  # imported lazily so replay mode works without it
        self.yf = yf
        self.symbols = symbols
        self.interval = interval
        self._cache: dict[str, pd.DataFrame] = {}

    def refresh(self):
        df = self.yf.download(
            self.symbols, period="5d", interval=self.interval,
            group_by="ticker", auto_adjust=False, progress=False, threads=True,
        )
        for s in self.symbols:
            try:
                d = df[s] if len(self.symbols) > 1 else df
                d = d[["Open", "High", "Low", "Close", "Volume"]].dropna()
                d.index = d.index.tz_convert(ET)
                # Drop the bar that is still forming
                minutes = int(self.interval.rstrip("m"))
                cutoff = self.now() - pd.Timedelta(minutes=minutes)
                self._cache[s] = d[d.index <= cutoff]
            except Exception:
                self._cache[s] = pd.DataFrame()

    def bars(self, symbol):
        return self._cache.get(symbol, pd.DataFrame())

    def now(self):
        return pd.Timestamp.now(tz=ET)


class AlpacaFeed(LiveFeed):
    """Free real-time IEX bars from Alpaca (needs the same paper keys as the broker).
    More reliable than Yahoo for live trading; IEX volume is a slice of total volume,
    but volume *spikes* relative to its own average still show up."""

    def __init__(self, symbols, interval="5m"):
        from alpaca.data.enums import DataFeed
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
        from keys import alpaca_keys

        key, secret = alpaca_keys()
        self.client = StockHistoricalDataClient(key, secret)
        self.Req, self.DataFeed = StockBarsRequest, DataFeed
        self.minutes = int(interval.rstrip("m"))
        self.tf = TimeFrame(self.minutes, TimeFrameUnit.Minute)
        self.symbols = symbols
        self._cache = {}

    def refresh(self):
        req = self.Req(symbol_or_symbols=self.symbols, timeframe=self.tf,
                       start=(self.now() - pd.Timedelta(days=5)).to_pydatetime(),
                       feed=self.DataFeed.IEX)
        df = self.client.get_stock_bars(req).df
        cutoff = self.now() - pd.Timedelta(minutes=self.minutes)
        for s in self.symbols:
            try:
                d = df.xs(s, level="symbol").rename(columns=str.title)
                d = d[["Open", "High", "Low", "Close", "Volume"]]
                d.index = d.index.tz_convert(ET)
                d = d.between_time("09:30", "15:59")      # regular session only
                self._cache[s] = d[d.index <= cutoff]
            except KeyError:
                self._cache[s] = pd.DataFrame()


class ReplayFeed:
    """Steps through pre-loaded bars one at a time. Used for testing and backtests."""

    def __init__(self, frames: dict[str, pd.DataFrame]):
        self.frames = frames
        self.timeline = sorted(set().union(*[f.index for f in frames.values()]))
        self.i = 0

    def refresh(self):
        pass

    def step(self) -> bool:
        self.i += 1
        return self.i < len(self.timeline)

    def now(self):
        return self.timeline[self.i]

    def bars(self, symbol):
        f = self.frames[symbol]
        return f[f.index <= self.now()]


def synthetic_frames(symbols, days=3, seed=7) -> dict[str, pd.DataFrame]:
    """Random-walk 5-minute bars with occasional volume bursts, for offline testing."""
    rng = np.random.default_rng(seed)
    sessions = pd.bdate_range("2026-11-02", periods=days)
    idx = []
    for d in sessions:
        start = pd.Timestamp(d.date()).tz_localize(ET) + pd.Timedelta(hours=9, minutes=30)
        idx.extend(start + pd.Timedelta(minutes=5 * k) for k in range(78))
    idx = pd.DatetimeIndex(idx)

    frames = {}
    for s in symbols:
        n = len(idx)
        price0 = rng.uniform(20, 300)
        rets = rng.normal(0, 0.0025, n)
        burst = rng.random(n) < 0.03                      # ~3% of bars are "news"
        rets[burst] += rng.normal(0.006, 0.006, burst.sum())
        close = price0 * np.exp(np.cumsum(rets))
        open_ = np.r_[price0, close[:-1]]
        spread = np.abs(rng.normal(0, 0.0015, n)) * close
        high = np.maximum(open_, close) + spread
        low = np.minimum(open_, close) - spread
        vol = rng.lognormal(11, 0.35, n)
        vol[burst] *= rng.uniform(3, 6, burst.sum())
        frames[s] = pd.DataFrame(
            {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": vol.round()},
            index=idx,
        )
    return frames

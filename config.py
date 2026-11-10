"""All tunable settings in one place. Edit these, not the agents."""

# ---- Broker -----------------------------------------------------------------
# "sim"     -> local simulated broker (always works, no account needed)
# "alpaca"  -> Alpaca paper account, official API (recommended; keys go in .env)
# "webull"  -> Webull paper account via the unofficial `webull` package (experimental)
BROKER = "alpaca"
STARTING_CASH = 1_000.00          # only used by the sim broker

# ---- Market data for live mode ---------------------------------------------
# "alpaca" -> free real-time IEX bars (needs the same .env keys)
# "yahoo"  -> free, no keys, but delayed and occasionally rate-limited
DATA_SOURCE = "alpaca"

# ---- Universe the scanner watches ------------------------------------------
# Liquid US stocks/ETFs. Keep it to a few dozen so free data stays fast.
WATCHLIST = [
    "SPY", "QQQ", "IWM", "AAPL", "MSFT", "NVDA", "AMD", "TSLA", "META", "AMZN",
    "GOOGL", "NFLX", "PLTR", "SOFI", "INTC", "BAC", "F", "UBER", "COIN", "SHOP",
]
BAR_INTERVAL = "5m"               # yfinance intraday interval
LOOP_SECONDS = 60                 # how often the bot wakes up in live mode

# ---- Scanner ----------------------------------------------------------------
VOLUME_LOOKBACK = 20              # bars used for the "normal" volume average
VOLUME_SPIKE_MULT = 2.5           # last bar volume must be >= this x average
BREAKOUT_LOOKBACK = 20            # close must beat the high of the previous N bars

# ---- Risk filter (stock version of the "rug check") -------------------------
MIN_PRICE = 5.00                  # skip penny stocks
MIN_AVG_DOLLAR_VOLUME = 2_000_000 # per bar; skip thin names (Yahoo = full market volume)
MIN_AVG_DOLLAR_VOLUME_IEX = 100_000  # used instead with Alpaca's free IEX data (~2-3% of volume)
MAX_BAR_RANGE_PCT = 4.0           # skip bars that already moved too far (chasing)
MAX_OPEN_POSITIONS = 3
NO_NEW_ENTRIES_AFTER = "15:30"    # US/Eastern
FLATTEN_AT = "15:50"              # close everything before the bell

# ---- Sizer -----------------------------------------------------------------
RISK_PER_TRADE_PCT = 1.0          # % of equity lost if the stop is hit
MAX_POSITION_PCT = 25.0           # never put more than this % of equity in one name
ATR_PERIOD = 14
STOP_ATR_MULT = 1.5
TARGET_ATR_MULT = 3.0
MAX_HOLD_BARS = 24                # time stop (24 x 5m = 2 hours)

# ---- Executor --------------------------------------------------------------
SIM_SLIPPAGE_BPS = 5              # sim broker fills 0.05% worse than quote
SIM_COMMISSION = 0.0

# ---- Storage ---------------------------------------------------------------
DB_PATH = "paperbot.db"

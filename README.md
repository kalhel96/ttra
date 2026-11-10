# Paper Bot: six agents, one screen, $0

A free, paper-only version of the "six agents" trading terminal, rebuilt for US stocks.

| Agent | File | Job |
|---|---|---|
| Scanner | `agents/scanner.py` | Finds volume spikes (≥2.5x average) that break above the 20-bar high |
| Risk filter | `agents/risk_filter.py` | The stock version of a "rug check": rejects penny stocks, thin volume, overextended bars, late-day entries, too many positions |
| Sizer | `agents/sizer.py` | Sizes from account equity and ATR: risks 1% of equity per trade, caps any one position at 25% |
| Executor | `agents/executor.py` | Opens/closes, tracks slippage (expected vs. fill), manages stop, target, time stop, end-of-day flatten |
| Logger | `agents/logger.py` | Writes every signal, rejection, order and the reason behind it to SQLite |
| Equity curve | `agents/equity.py` + `dashboard.py` | Updates equity on every close; dashboard shows curve, stats, activity feed, trade log |

## Setup (once)

```bash
cd paperbot
python -m venv .venv
# Windows: .venv\Scripts\activate     Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

## Run it

**1. Test offline first (no internet, fake data):**
```bash
python main.py replay --fresh
streamlit run dashboard.py
```
The synthetic data is random. Its result means nothing; it only proves the pipeline works.

**2. Replay the last 5 real trading days (real bars, simulated fills):**
```bash
python main.py replay --real --fresh
```

**3. Run live during market hours (9:30–4:00 ET):**
```bash
python main.py live            # terminal 1: the bot
streamlit run dashboard.py     # terminal 2: the screen
```
Leave both open. Outside market hours it waits.

## Alpaca paper account (default)

1. Sign up free at alpaca.markets. No deposit needed for paper trading.
2. In the dashboard, switch to **Paper Trading**, open **API Keys**, and click **Generate**.
3. Copy `.env.example` to `.env` and paste the key and secret. Keep `.env` private (it's in `.gitignore`).
4. Optional: paper accounts start at $100,000. Use the reset option on the paper account to start from a smaller, realistic balance like $1,000, so the sizer behaves like it would with your real money.
5. `python main.py live`. On start it prints your paper account number and equity, and warns you about any positions it didn't open.

`paper=True` is hard-coded in `brokers/alpaca_paper.py`, so this code can't place real orders.

With `DATA_SOURCE = "alpaca"`, live bars come from Alpaca's free IEX feed (real-time, more reliable than Yahoo). IEX is only a slice of total market volume, so the thin-volume filter uses the lower `MIN_AVG_DOLLAR_VOLUME_IEX` threshold. Volume *spikes* still show up relative to IEX's own average. Set `DATA_SOURCE = "yahoo"` to use Yahoo instead.

The bot keeps its open positions in memory. If you stop it mid-day, close leftover positions in the Alpaca dashboard (it also flattens everything at 3:50 PM ET).

## Webull paper account (experimental)

Set `BROKER = "webull"` in `config.py`, then `pip install webull`.

Important things to know:

- **Webull's official API doesn't support paper trading.** This uses the community `webull` package, which talks to the same private endpoints as the Webull app. It's unofficial, can break without notice, and Webull's login sometimes blocks it (extra verification, captchas). If that happens, go back to `BROKER = "sim"`.
- **You log in yourself**, by typing your username, password and trade PIN into your own terminal when the bot starts. The code never saves your password. The package may save a session token file `webull_credentials.json`; don't share or commit it.
- Only the paper account (`paper_webull`) is used. Never point this at your real account.

## Tuning

Everything lives in `config.py`: watchlist, spike threshold, risk %, stop/target multiples, cut-off times, slippage assumption. Change one thing at a time and compare results in the dashboard.

## Reading the results honestly

- **Profit factor** below ~1.2 after slippage usually means no real edge.
- **Max drawdown** matters more than total P&L.
- The bot only reacts on bar closes, so real fills would be worse than the sim assumes. Raise `SIM_SLIPPAGE_BPS` to stress-test.
- A few good days prove nothing. Judge it over weeks and 100+ trades.

Paper trading only. This is a learning project, not financial advice.

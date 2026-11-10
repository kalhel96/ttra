"""One-screen dashboard: equity curve, stats, open activity feed, trade log.

    streamlit run dashboard.py
"""
import sqlite3

import pandas as pd
import streamlit as st

import config
from agents.equity import summary

st.set_page_config(page_title="Paper Bot", layout="wide")
st.title("Paper Bot terminal")
st.caption(f"Broker: **{config.BROKER}** · paper only · auto-refresh every 30s")

@st.fragment(run_every="30s")
def terminal():
    try:
        con = sqlite3.connect(config.DB_PATH)
        eq = pd.read_sql("SELECT ts, equity FROM equity ORDER BY id", con)
        trades = pd.read_sql("SELECT * FROM trades ORDER BY id DESC", con)
        events = pd.read_sql("SELECT ts, agent, kind, symbol, reason FROM events ORDER BY id DESC LIMIT 200", con)
        con.close()
    except Exception:
        st.info("No data yet. Run `python main.py replay` or `python main.py live` first.")
        return

    s = summary(config.DB_PATH)
    c = st.columns(6)
    c[0].metric("Equity", f"${s.get('end_equity', eq.equity.iloc[-1] if len(eq) else 0):,.2f}",
                f"{s.get('total_pnl', 0):+,.2f}")
    c[1].metric("Trades", s.get("trades", 0))
    c[2].metric("Win rate", f"{s.get('win_rate_pct', 0)}%")
    c[3].metric("Profit factor", s.get("profit_factor") or "–")
    c[4].metric("Max drawdown", f"{s.get('max_drawdown_pct', 0)}%")
    c[5].metric("Avg slippage", f"{s.get('avg_slippage_bps', 0)} bps")

    left, right = st.columns([3, 2])
    with left:
        st.subheader("Equity curve")
        if len(eq):
            eq["ts"] = pd.to_datetime(eq["ts"], utc=True)
            st.line_chart(eq.set_index("ts")["equity"])
        st.subheader("Trade log")
        st.dataframe(
            trades[["exit_time", "symbol", "qty", "entry_price", "exit_price", "pnl", "pnl_pct",
                    "entry_slippage_bps", "exit_slippage_bps", "exit_reason", "entry_reason"]],
            width="stretch", hide_index=True)
    with right:
        st.subheader("Activity feed")
        agents = st.multiselect("Agents", sorted(events.agent.unique()), default=sorted(events.agent.unique()))
        st.dataframe(events[events.agent.isin(agents)], width="stretch", hide_index=True, height=650)



terminal()

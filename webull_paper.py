"""Webull PAPER account broker (EXPERIMENTAL).

Webull's official OpenAPI does not expose its paper-trading account, so this uses the
community `webull` package (pip install webull), which calls the same private endpoints
the Webull app uses. It can break whenever Webull changes things. If it does, switch
BROKER back to "sim" in config.py.

Login is interactive: you type your Webull username, password and trade PIN into YOUR
OWN terminal. This code never stores your password; the package may save a session
token file (webull_credentials.json) next to the script. Keep that file private.
"""
import time

import config


class WebullPaperBroker:
    name = "webull-paper"

    def __init__(self):
        try:
            from webull import paper_webull
        except ImportError as e:
            raise SystemExit("Run `pip install webull` first, or set BROKER = 'sim' in config.py") from e
        self.wb = paper_webull()
        print("Log in to Webull (paper orders only; nothing here touches real money).")
        self.wb.login_prompt()
        if not self.wb.get_account_id():
            raise SystemExit("Logged in, but no paper account id came back. Open Paper Trading "
                             "once in the Webull app, then retry, or use BROKER = 'sim'.")

    # -- account ------------------------------------------------------------
    def cash(self):
        acct = self.wb.get_account()
        for key in ("usableCash", "cashBalance", "totalCash"):
            if key in acct:
                return float(acct[key])
        return float(acct.get("netLiquidation", 0))

    # -- orders --------------------------------------------------------------
    def _market(self, symbol, qty, side):
        resp = self.wb.place_order(stock=symbol, action=side, orderType="MKT",
                                   enforce="DAY", quant=qty, outsideRegularTradingHour=False)
        order_id = (resp or {}).get("orderId")
        if not order_id:
            print(f"  ! Webull rejected {side} {qty} {symbol}: {resp}")
            return None
        return self._wait_fill(order_id)

    def _wait_fill(self, order_id, timeout=20):
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                for o in self.wb.get_history_orders(status="Filled", count=20) or []:
                    if str(o.get("orderId")) == str(order_id):
                        px = o.get("avgFilledPrice") or o.get("filledPrice") or o.get("lmtPrice")
                        if px:
                            return float(px)
            except Exception:
                pass
            time.sleep(2)
        print(f"  ! order {order_id} not confirmed filled within {timeout}s")
        return None

    def buy(self, symbol, qty, expected_price):
        return self._market(symbol, qty, "BUY")

    def sell(self, symbol, qty, expected_price):
        return self._market(symbol, qty, "SELL")

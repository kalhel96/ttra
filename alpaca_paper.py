"""Alpaca PAPER trading broker (official API, free).

Needs ALPACA_API_KEY and ALPACA_SECRET_KEY from your Alpaca *paper* account,
set as environment variables or in a .env file next to main.py (see .env.example).
paper=True is hard-coded below so this can never send real orders.
"""
import time

from keys import alpaca_keys


class AlpacaPaperBroker:
    name = "alpaca-paper"

    def __init__(self):
        try:
            from alpaca.trading.client import TradingClient
            from alpaca.trading.enums import OrderSide, OrderStatus, TimeInForce
            from alpaca.trading.requests import MarketOrderRequest
        except ImportError as e:
            raise SystemExit("Run `pip install alpaca-py` first.") from e
        self.OrderSide, self.OrderStatus = OrderSide, OrderStatus
        self.TimeInForce, self.MarketOrderRequest = TimeInForce, MarketOrderRequest

        key, secret = alpaca_keys()
        self.client = TradingClient(key, secret, paper=True)
        acct = self.client.get_account()
        print(f"Connected to Alpaca paper account {acct.account_number} "
              f"(equity ${float(acct.equity):,.2f}, status {acct.status})")
        held = self.client.get_all_positions()
        if held:
            names = ", ".join(f"{p.qty} {p.symbol}" for p in held)
            print(f"  ! Account already holds: {names}. The bot only manages positions it opens "
                  f"itself, so close these in the Alpaca dashboard if they're left over.")

    def cash(self):
        return float(self.client.get_account().cash)

    def _market(self, symbol, qty, side):
        req = self.MarketOrderRequest(symbol=symbol, qty=qty, side=side,
                                      time_in_force=self.TimeInForce.DAY)
        try:
            order = self.client.submit_order(req)
        except Exception as e:
            print(f"  ! Alpaca rejected {side.value} {qty} {symbol}: {e}")
            return None
        return self._wait_fill(order.id)

    def _wait_fill(self, order_id, timeout=30):
        done_bad = {self.OrderStatus.CANCELED, self.OrderStatus.EXPIRED, self.OrderStatus.REJECTED}
        deadline = time.time() + timeout
        while time.time() < deadline:
            o = self.client.get_order_by_id(order_id)
            if o.status == self.OrderStatus.FILLED:
                return float(o.filled_avg_price)
            if o.status in done_bad:
                print(f"  ! order {order_id} ended as {o.status.value}")
                return None
            time.sleep(1)
        # Don't leave a stray order behind
        try:
            self.client.cancel_order_by_id(order_id)
        except Exception:
            pass
        print(f"  ! order {order_id} not filled within {timeout}s; cancelled")
        return None

    def buy(self, symbol, qty, expected_price):
        return self._market(symbol, qty, self.OrderSide.BUY)

    def sell(self, symbol, qty, expected_price):
        return self._market(symbol, qty, self.OrderSide.SELL)

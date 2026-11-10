"""Local simulated broker. Fills at the expected price plus configurable slippage."""
import config


class SimBroker:
    name = "sim"

    def __init__(self, cash=config.STARTING_CASH):
        self._cash = float(cash)

    def cash(self):
        return self._cash

    def buy(self, symbol, qty, expected_price):
        fill = round(expected_price * (1 + config.SIM_SLIPPAGE_BPS / 10_000), 4)
        cost = fill * qty + config.SIM_COMMISSION
        if cost > self._cash:
            return None
        self._cash -= cost
        return fill

    def sell(self, symbol, qty, expected_price):
        fill = round(expected_price * (1 - config.SIM_SLIPPAGE_BPS / 10_000), 4)
        self._cash += fill * qty - config.SIM_COMMISSION
        return fill

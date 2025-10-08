import robin_stocks.robinhood as r
import os

class RobinhoodAPI:
    def __init__(self, username, password, mfa_code=None):
        self.username = username
        self.password = password
        self.mfa_code = mfa_code
        self.logged_in = False

    def login(self):
        if self.mfa_code:
            login = r.authentication.login(self.username, self.password, mfa_code=self.mfa_code)
        else:
            login = r.authentication.login(self.username, self.password)
        self.logged_in = True if login else False
        return self.logged_in

    def get_crypto_quote(self, symbol):
        return r.crypto.get_crypto_quote(symbol)

    def get_crypto_positions(self):
        return r.crypto.get_crypto_positions()

    def place_order(self, symbol, quantity, side):
        if side not in ['buy', 'sell']:
            raise ValueError("side must be 'buy' or 'sell'")
        # Market order; you can expand to support limit orders
        if side == 'buy':
            return r.orders.order_buy_crypto_by_quantity(symbol, quantity)
        else:
            return r.orders.order_sell_crypto_by_quantity(symbol, quantity)

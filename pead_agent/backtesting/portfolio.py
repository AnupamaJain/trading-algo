from datetime import date
from typing import List, Dict

class Portfolio:
    """
    Simulates a trading portfolio, tracking cash, holdings, and trade history.
    """

    def __init__(self, initial_cash: float = 100000.0):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.holdings: Dict[str, int] = {}  # Symbol -> Quantity
        self.trades: List[Dict] = []

    def record_trade(self, trade_date: date, symbol: str, quantity: int, price: float, side: str):
        """
        Records a trade and updates cash and holdings.

        Args:
            trade_date: The date of the trade.
            symbol: The stock symbol.
            quantity: The number of shares traded.
            price: The price per share.
            side: 'BUY' or 'SELL'.
        """
        if side.upper() == 'BUY':
            cost = quantity * price
            if self.cash < cost:
                print(f"WARNING: Insufficient cash to buy {quantity} of {symbol}. Trade not executed.")
                return
            self.cash -= cost
            self.holdings[symbol] = self.holdings.get(symbol, 0) + quantity
        elif side.upper() == 'SELL':
            if self.holdings.get(symbol, 0) < quantity:
                print(f"WARNING: Not enough holdings to sell {quantity} of {symbol}. Trade not executed.")
                return
            self.cash += quantity * price
            self.holdings[symbol] -= quantity
            if self.holdings[symbol] == 0:
                del self.holdings[symbol]
        else:
            raise ValueError("Side must be 'BUY' or 'SELL'")

        trade_record = {
            "date": trade_date,
            "symbol": symbol,
            "quantity": quantity,
            "price": price,
            "side": side.upper(),
        }
        self.trades.append(trade_record)
        print(f"Trade Recorded: {trade_record}")

    def get_current_value(self, current_prices: Dict[str, float]) -> float:
        """
        Calculates the total current value of the portfolio.

        Args:
            current_prices: A dictionary mapping symbols to their current prices.

        Returns:
            The total portfolio value (cash + holdings).
        """
        holdings_value = 0.0
        for symbol, quantity in self.holdings.items():
            holdings_value += quantity * current_prices.get(symbol, 0.0)
        return self.cash + holdings_value

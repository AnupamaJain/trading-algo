from brokers.core.interface import BrokerDriver


class StubBrokerDriver(BrokerDriver):
    """A stub implementation of the BrokerDriver for testing purposes."""

    def get_funds(self):
        return None

    def get_positions(self):
        return []

    def place_order(self, order_request):
        print(f"[StubBrokerDriver] Simulating order placement for: {order_request.symbol}")
        return {"s": "ok", "id": "STUB_ORDER_123"}

    # Implement other abstract methods with placeholder logic as needed
    def get_capabilities(self):
        return super().get_capabilities()

    def get_position(self, symbol: str, exchange: str | None = None):
        return None

    def cancel_order(self, order_id: str):
        return super().cancel_order(order_id)

    def modify_order(self, order_id: str, updates: dict):
        return super().modify_order(order_id, updates)

    def get_orderbook(self):
        return []

    def get_tradebook(self):
        return []

    def get_order(self, order_id: str):
        return None

    def get_quote(self, symbol: str):
        return super().get_quote(symbol)

    def get_quotes(self, symbols: list[str]):
        return {}

    def get_history(self, symbol: str, interval: str, start: str, end: str, oi: bool = False):
        return []

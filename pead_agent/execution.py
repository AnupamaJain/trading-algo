import os
from brokers.core.gateway import BrokerGateway
from brokers.core.enums import Exchange, OrderType, ProductType, TransactionType, Validity
from brokers.core.schemas import OrderRequest


class ExecutionManager:
    """
    Handles the execution of trades based on the final decision from the DecisionEngine.
    """

    def __init__(self, broker_gateway: BrokerGateway):
        """
        Initializes the ExecutionManager.

        Args:
            broker_gateway: An instance of the BrokerGateway to interact with the broker.
        """
        self.broker_gateway = broker_gateway

    def execute_trade(self, decision: dict, config: dict, trade_date=None):
        """
        Translates a decision into an order and places it via the BrokerGateway.

        Args:
            decision: A dictionary containing the final verdict and other details.
            config: A dictionary with execution-specific parameters.
            trade_date: The date of the trade (used for backtesting, ignored here).
        """
        final_verdict = decision.get("verdict")
        stock_symbol = decision.get("stock")

        if final_verdict not in ["STRONG BUY", "BUY", "SELL"]:
            print(f"[ExecutionManager] No action taken for {stock_symbol} with verdict: {final_verdict}.")
            return

        if "FYERS_CLIENT_ID" not in os.environ:
            print(f"[ExecutionManager] Fyers credentials not found in environment. Skipping live order.")
            print(f"Would have placed {final_verdict} order for {stock_symbol} using config: {config}")
            return

        transaction_type = (
            TransactionType.BUY if final_verdict in ["STRONG BUY", "BUY"] else TransactionType.SELL
        )

        # Get order parameters from the config, with sensible defaults
        quantity = config.get("order_quantity", 1)
        product_type_str = config.get("product_type", "INTRADAY").upper()
        order_type_str = config.get("order_type", "MARKET").upper()

        # Create the standardized order request using values from the config
        order_request = OrderRequest(
            symbol=stock_symbol,
            exchange=Exchange.NSE,
            quantity=int(quantity),
            order_type=OrderType[order_type_str],
            transaction_type=transaction_type,
            product_type=ProductType[product_type_str],
            validity=Validity.DAY,
        )

        try:
            print(f"[ExecutionManager] Placing {order_request.product_type.value} {order_request.order_type.value} "
                  f"{transaction_type.value} order for {order_request.quantity} share(s) of {order_request.symbol}...")

            order_response = self.broker_gateway.place_order(order_request)

            print(f"[ExecutionManager] Order Response: {order_response}")

        except Exception as e:
            print(f"[ExecutionManager] Error placing order for {stock_symbol}: {e}")

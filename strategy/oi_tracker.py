import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import yaml
import random
from logger import logger
from brokers import BrokerGateway, OrderRequest, Exchange, OrderType, TransactionType, ProductType
from tabulate import tabulate
import pandas as pd
from datetime import datetime, timedelta
from termcolor import colored

try:
    from playsound import playsound
except ImportError:
    playsound = None
class OITrackerStrategy:
    """
    OI Tracker Strategy

    This strategy tracks the change in Open Interest (OI) for ATM and 2 slightly ITM and 2 slightly OTM options
    both call and put. It creates a live table in python which updates every minute.
    """

    def __init__(self, broker, config, dispatcher):
        # Assign config values as instance variables with 'strat_var_' prefix
        for k, v in config.items():
            setattr(self, f'strat_var_{k}', v)
        # External dependencies
        self.broker = broker
        self.dispatcher = dispatcher
        self.broker.download_instruments()
        self.instruments = self.broker.get_instruments()

        # Log instruments debug info
        try:
            if hasattr(self.instruments, 'shape'):
                logger.info(f"Loaded instruments: rows={self.instruments.shape[0]}, cols={self.instruments.shape[1]}")
            else:
                logger.info(f"Loaded instruments: type={type(self.instruments)}, len={(len(self.instruments) if self.instruments is not None else 0)}")
        except Exception:
            logger.debug("Could not log instruments metadata")

        # Trading parameters - use getattr for safe fallback
        self.trading_config = getattr(self, 'strat_var_trading', {})

        self._initialize_state()

    def _initialize_state(self):
        """Initializes the state of the strategy."""
        logger.info("Initializing OI Tracker Strategy...")
        self.active_trades = set()
        self.historical_oi = {}
        self.last_run_date = None
        self.last_update_time = None

    def _generate_synthetic_oi(self, strike, minutes=180):
        """
        Generate a synthetic OI history for `minutes` minutes (one entry per minute).
        Returns a list of records with keys `ts` (unix timestamp) and `oi` (int).
        """
        now = datetime.now()
        # Base OI depends loosely on strike (closer-to-ATM -> larger OI)
        try:
            atm = self.get_atm_strike(get_nifty_price_with_fallback(self.broker, self.strat_var_index_symbol, allow_mock=True))
            distance = abs(strike - atm)
        except Exception:
            distance = 0

        # Larger base for strikes nearer the ATM, smaller for far strikes
        base = max(200, int(3000 - (distance / max(1, self.strat_var_strike_difference)) * 200))
        history = []
        for i in range(minutes):
            ts = int((now - timedelta(minutes=(minutes - i))).timestamp())
            # Simulate a small upward or downward drift + noise
            noise = int(random.gauss(0, base * 0.02))
            drift = int((i - minutes / 2) * (base * 0.0005))
            oi = max(0, base + noise + drift)
            history.append({"ts": ts, "oi": oi})
        return history

    def on_ticks_update(self, ticks):
        """
        Main strategy execution method called on each tick update
        """
        now = datetime.now()
        if self.last_update_time is None or (now - self.last_update_time).total_seconds() >= 60:
            if self.last_run_date != now.date():
                logger.info("New trading day, resetting active trades.")
                self.active_trades = set()
                self.last_run_date = now.date()

            current_price = ticks['last_price'] if 'last_price' in ticks else ticks['ltp']
            self.update_tables(current_price)
            self.last_update_time = now

    def get_atm_strike(self, current_price):
        """
        Get the current ATM strike price for NIFTY.
        """
        strike_difference = self.strat_var_strike_difference
        atm_strike = round(current_price / strike_difference) * strike_difference
        return atm_strike

    def get_strikes(self, atm_strike):
        """
        Get the 5 strike prices to track (ATM, 2 ITM, 2 OTM).
        """
        strike_difference = self.strat_var_strike_difference
        strikes = [atm_strike - 2 * strike_difference,
                   atm_strike - 1 * strike_difference,
                   atm_strike,
                   atm_strike + 1 * strike_difference,
                   atm_strike + 2 * strike_difference]
        return strikes

    def get_oi_data(self, strikes, option_type):
        """
        Fetch OI data for the given strikes and option type.
        Maintains an internal state to avoid re-fetching the entire history on each call.
        """
        oi_data = {}
        now = datetime.now()

        for strike in strikes:
            symbol = self.get_option_symbol(strike, option_type, self.strat_var_underlying)
            if symbol is not None:
                logger.debug(f"Resolved instrument symbol for strike={strike}, type={option_type}: {symbol}")
            if symbol is None:
                logger.error(f"Could not find symbol for strike {strike} and option type {option_type}")
                # populate empty structure so UI remains stable
                oi_data[strike] = {'history': [], 'current_oi': None}
                for interval in self.strat_var_intervals.keys():
                    oi_data[strike][interval] = None
                continue

            if symbol not in self.historical_oi:
                # First run for this symbol, fetch the last 3 hours
                end_date = now.strftime("%Y-%m-%d")
                start_date = (now - timedelta(hours=3)).strftime("%Y-%m-%d")
                history = self.broker.get_history(symbol, "1m", start_date, end_date, oi=True)
                if history:
                    self.historical_oi[symbol] = history
                else:
                    # If broker didn't return OI/history, optionally generate synthetic OI
                    if getattr(self, 'strat_var_use_synthetic_oi', False):
                        logger.info(f"Generating synthetic OI for {symbol} (strike={strike})")
                        synth = self._generate_synthetic_oi(strike, minutes=180)
                        self.historical_oi[symbol] = synth
            else:
                # Subsequent run, fetch only the last ~2 minutes and append
                end_date = now.strftime("%Y-%m-%d")
                start_date = (now - timedelta(minutes=2)).strftime("%Y-%m-%d")
                latest_history = self.broker.get_history(symbol, "1m", start_date, end_date, oi=True)

                if latest_history:
                    last_known_ts = self.historical_oi[symbol][-1]['ts']
                    for record in latest_history:
                        if record['ts'] > last_known_ts:
                            self.historical_oi[symbol].append(record)

                # Trim history to keep it within the last 3 hours
                three_hours_ago_ts = (now - timedelta(hours=3)).timestamp()
                self.historical_oi[symbol] = [r for r in self.historical_oi[symbol] if r['ts'] >= three_hours_ago_ts]
                history = self.historical_oi[symbol]

            if not history:
                logger.debug(f"No history returned for symbol={symbol}")
                oi_data[strike] = {'history': [], 'current_oi': None}
                for interval in self.strat_var_intervals.keys():
                    oi_data[strike][interval] = None
                continue

            # history is expected to be a list of records with 'oi' and 'ts'
            oi_data[strike] = {'history': history}
            # Get current OI from quote
            quote = self.broker.get_quote(symbol)
            oi_data[strike]['current_oi'] = quote.open_interest if quote else None

            # Calculate historical OI for different intervals
            for interval, minutes in self.strat_var_intervals.items():
                target_time = now - timedelta(minutes=minutes)
                historical_oi_val = None
                for record in reversed(history):
                    record_time = datetime.fromtimestamp(record['ts'])
                    if record_time <= target_time:
                        historical_oi_val = record['oi']
                        break
                oi_data[strike][interval] = historical_oi_val

        return oi_data

    def get_option_symbol(self, strike, option_type, underlying):
        """
        Get the option symbol for a given strike and option type.
        """
        df = self.instruments

        # Ensure strike is numeric
        try:
            strike_val = float(strike)
        except Exception:
            logger.debug(f"Invalid strike price: {strike}")
            return None

        # Find the next expiry date
        today = datetime.now().date()
        expiries = pd.to_datetime(df.get('expiry', []), errors='coerce').dropna().dt.date.unique()
        expiries = sorted([e for e in expiries if e >= today])
        if not expiries:
            logger.warning(f"No valid expiries found for {underlying}")
            return None
        next_expiry = expiries[0]

        # Normalize underlying for comparison
        underlying_norm = str(underlying).upper()

        # Try exact match first (tolerant columns)
        underlying_col = 'underlying_symbol' if 'underlying_symbol' in df.columns else (
            'underlying' if 'underlying' in df.columns else None
        )

        mask = (pd.to_datetime(df['expiry']).dt.date == next_expiry) & (df['instrument_type'] == option_type)
        if underlying_col:
            mask = mask & (df[underlying_col].astype(str).str.upper() == underlying_norm)

        # Compare strike allowing numeric types
        try:
            strikes_series = pd.to_numeric(df['strike'], errors='coerce')
        except Exception:
            strikes_series = df['strike']

        candidates = df[mask].copy()
        if not candidates.empty:
            # Try exact strike
            exact = candidates[pd.to_numeric(candidates['strike'], errors='coerce') == strike_val]
            if not exact.empty:
                return exact.iloc[0]['symbol']

        # If exact match not found, broaden search to same expiry+type and pick nearest strike
        relaxed = df[(pd.to_datetime(df['expiry']).dt.date == next_expiry) & (df['instrument_type'] == option_type)].copy()
        if relaxed.empty:
            logger.debug(f"No instruments for expiry {next_expiry} and type {option_type}")
            return None

        # Compute numeric strike differences and pick nearest
        try:
            relaxed['__strike_num'] = pd.to_numeric(relaxed['strike'], errors='coerce')
            relaxed = relaxed.dropna(subset=['__strike_num'])
            relaxed['__diff'] = (relaxed['__strike_num'] - strike_val).abs()
            relaxed = relaxed.sort_values('__diff')
            if not relaxed.empty:
                # Prefer matching underlying if available
                if underlying_col:
                    same_underlying = relaxed[relaxed[underlying_col].astype(str).str.upper() == underlying_norm]
                    if not same_underlying.empty:
                        return same_underlying.iloc[0]['symbol']
                return relaxed.iloc[0]['symbol']
        except Exception as e:
            logger.debug(f"Error while searching nearest strike: {e}")

        logger.debug(f"Could not find symbol for strike {strike}, option type {option_type}, underlying {underlying} and expiry {next_expiry}")
        return None

    def calculate_oi_change(self, current_oi, historical_oi):
        """
        Calculate the percentage and absolute change in OI.
        """
        if historical_oi is None or historical_oi == 0:
            return 0, 0

        absolute_change = current_oi - historical_oi
        percentage_change = (absolute_change / historical_oi) * 100
        return percentage_change, absolute_change

    def _check_and_place_trade(self, strike, option_type, percentage_change):
        """
        Check if the OI change crosses the threshold and place a trade.
        """
        if not self.trading_config.get('enabled', False):
            return

        trade_key = (strike, option_type)
        if trade_key in self.active_trades:
            return # A trade has already been placed for this strike and option type.

        if percentage_change > self.trading_config['trade_threshold_percent']:
            logger.info(f"OI change of {percentage_change:.2f}% for {strike} {option_type} crossed the threshold. Placing trade.")
            symbol = self.get_option_symbol(strike, option_type, self.strat_var_underlying)
            if symbol:
                self._place_order(symbol)
                self.active_trades.add(trade_key)

    def _place_order(self, symbol):
        """
        Place a trade order.
        """
        req = OrderRequest(
            symbol=symbol,
            exchange=Exchange.NFO,
            transaction_type=TransactionType.BUY, # Or SELL, based on strategy logic
            quantity=self.trading_config['quantity'],
            product_type=ProductType[self.trading_config['product_type']],
            order_type=OrderType[self.trading_config['order_type']],
            price=None, # For MARKET orders
            tag=self.trading_config['tag']
        )
        logger.info(f"Placing order: {req}")
        try:
            order_resp = self.broker.place_order(req)
            if order_resp and order_resp.order_id:
                logger.info(f"Order placed successfully, order_id: {order_resp.order_id}")
            else:
                logger.error("Order placement failed.")
        except Exception as e:
            logger.error(f"Error placing order: {e}")

    def update_tables(self, current_price):
        """
        Update the Put, Call, and NIFTY tables.
        """
        atm_strike = self.get_atm_strike(current_price)
        strikes = self.get_strikes(atm_strike)

        # Update Call and Put tables
        alert_triggered = False
        for option_type in ["CE", "PE"]:
            oi_data = self.get_oi_data(strikes, option_type)
            table_data = []
            headers = ["Strike", "Current OI"] + list(self.strat_var_intervals.keys())
            red_cell_count = 0

            for strike in strikes:
                row = [strike, oi_data.get(strike, {}).get('current_oi', 'N/A')]
                current_oi = oi_data.get(strike, {}).get('current_oi')

                for interval in self.strat_var_intervals.keys():
                    historical_oi = oi_data.get(strike, {}).get(interval)
                    if current_oi is not None and historical_oi is not None:
                        percentage_change, absolute_change = self.calculate_oi_change(current_oi, historical_oi)
                        formatted_cell, is_red = self.format_and_color_cell(percentage_change, absolute_change, interval)
                        if is_red:
                            red_cell_count += 1
                        row.append(formatted_cell)

                        # Check and place trade for the most recent interval
                        if interval == list(self.strat_var_intervals.keys())[0]:
                            self._check_and_place_trade(strike, option_type, percentage_change)
                    else:
                        row.append("N/A")
                table_data.append(row)

            print(f"\n--- {option_type} Table ---")
            print(tabulate(table_data, headers=headers))

            total_cells = len(strikes) * len(self.strat_var_intervals.keys())
            if not alert_triggered and (red_cell_count / total_cells > 0.3):
                self.trigger_alert()
                alert_triggered = True

        # Update NIFTY table
        now = datetime.now()
        nifty_table_data = []
        nifty_headers = ["", "Current Value", "3m", "5m", "10m", "15m", "30m", "3h"]

        end_date = now.strftime("%Y-%m-%d")
        start_date = (now - timedelta(hours=3)).strftime("%Y-%m-%d")
        history = self.broker.get_history(self.strat_var_index_symbol, "1m", start_date, end_date)

        if history:
            current_price = history[-1]['close']
            nifty_row = ["NIFTY", f"{current_price:.2f}"]
            for interval, minutes in self.strat_var_intervals.items():
                target_time = now - timedelta(minutes=minutes)
                historical_price = None
                for record in reversed(history):
                    record_time = datetime.fromtimestamp(record['ts'])
                    if record_time <= target_time:
                        historical_price = record['close']
                        break

                if historical_price is not None:
                    percentage_change = ((current_price - historical_price) / historical_price) * 100
                    absolute_change = current_price - historical_price
                    nifty_row.append(f"{percentage_change:.2f}% ({absolute_change:.2f})")
                else:
                    nifty_row.append("N/A")
            nifty_table_data.append(nifty_row)
        print("\n--- NIFTY Table ---")
        print(tabulate(nifty_table_data, headers=nifty_headers))


    def format_and_color_cell(self, percentage_change, absolute_change, column_name):
        """
        Formats the cell text and applies color if the threshold is met.
        """
        text = f"{percentage_change:.2f}% ({absolute_change})"
        threshold = self.strat_var_color_thresholds.get(column_name)
        if threshold and percentage_change > threshold:
            return colored(text, 'red'), True
        return text, False

    def trigger_alert(self):
        """
        Trigger an alert sound if more than 30% of the cells in any table are color-coded.
        """
        logger.info("ALERT: More than 30% of cells are color-coded!")
        try:
            playsound(self.strat_var_alert_sound_path)
        except FileNotFoundError:
            logger.error(f"Alert sound file not found at: {self.strat_var_alert_sound_path}")
        except Exception as e:
            logger.error(f"Error playing alert sound: {e}")


def get_nifty_price_with_fallback(broker, symbol, last_known_price=None, allow_mock=False):
    """
    Fetch NIFTY price with multiple fallbacks.
    If real data unavailable, use last known price or realistic mock data.
    """
    # Try live quote
    try:
        quote = broker.get_quote(symbol)
        if quote and hasattr(quote, 'last_price') and quote.last_price > 0:
            logger.debug(f"Got live quote: {quote.last_price}")
            return quote.last_price
    except Exception as e:
        logger.debug(f"Live quote failed: {e}")

    # Try historical data (BrokerGateway.get_history expects start/end YYYY-MM-DD)
    try:
        from datetime import datetime, timedelta
        end = datetime.now().strftime('%Y-%m-%d')
        start = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        history = broker.get_history(symbol, interval="1m", start=start, end=end)
        if history is not None and len(history) > 0:
            # history may be a DataFrame-like or list; handle both
            try:
                price = float(history.iloc[-1]['close'])
            except Exception:
                # assume list of dicts
                price = float(history[-1].get('close') or history[-1].get('c') or 0)
            if price > 0:
                logger.debug(f"Got price from history: {price}")
                return price
    except Exception as e:
        logger.debug(f"Historical data failed: {e}")

    # Fallback to last known price
    if last_known_price and last_known_price > 0:
        logger.info(f"Using last known price: {last_known_price}")
        return last_known_price

    # Final behavior: either return None (if mock not allowed) or a mock price
    if not allow_mock:
        logger.warning("No valid NIFTY price available and mock disabled")
        return None

    # Mock price (allowed)
    base_price = 26050  # Realistic NIFTY value
    mock_price = base_price + random.uniform(-50, 50)  # Small realistic variation
    logger.warning(f"Using mock NIFTY price for testing: {mock_price:.2f} (real data unavailable - check broker auth)")
    return mock_price


if __name__ == "__main__":
    import argparse
    import warnings
    from dotenv import load_dotenv
    from dispatcher import DataDispatcher
    from queue import Queue
    import queue
    import traceback

    load_dotenv()
    warnings.filterwarnings("ignore")

    config_file = os.path.join(os.path.dirname(__file__), "configs/oi_tracker.yml")
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)['default']

    broker = BrokerGateway.from_name(os.getenv("BROKER_NAME"))

    dispatcher = DataDispatcher()
    dispatcher.register_main_queue(Queue())

    strategy = OITrackerStrategy(broker, config, dispatcher)

    # Get update interval from config (default 60 seconds)
    update_interval = config.get('update_interval_seconds', 60)
    # Whether to allow mock NIFTY prices when real data unavailable
    allow_mock_price = config.get('use_mock_price', False)
    logger.info(f"Starting OI Tracker Strategy in polling mode (update interval: {update_interval}s)")

    # Cache for last known good price
    last_known_price = None

    try:
        last_update = 0
        last_known_price = None

        while True:
            try:
                current_time = time.time()

                # Check if it's time for an update
                if current_time - last_update >= update_interval:
                    index_symbol = config['index_symbol']

                    # Use fallback-enabled price fetcher
                    current_price = get_nifty_price_with_fallback(
                        broker, index_symbol, last_known_price, allow_mock=allow_mock_price
                    )

                    if current_price and current_price > 0:
                        last_known_price = current_price
                        logger.info(f"Using NIFTY price: {current_price:.2f}")
                        strategy.update_tables(current_price)
                        last_update = current_time
                    else:
                        logger.error("Could not determine valid NIFTY price")

                # Sleep briefly to avoid busy-waiting
                time.sleep(1)

            except KeyboardInterrupt:
                logger.info("SHUTDOWN REQUESTED - Stopping strategy...")
                break
            except Exception as error:
                logger.error(f"Error in main loop: {error}", exc_info=True)
                time.sleep(5)  # Wait before retrying
                continue

    except Exception as fatal_error:
        logger.error("FATAL ERROR in main trading loop:")
        logger.error(f"Error: {fatal_error}")
        traceback.print_exc()

    finally:
        logger.info("STRATEGY SHUTDOWN COMPLETE")

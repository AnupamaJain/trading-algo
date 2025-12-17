import os
import yaml
from logger import logger
from brokers import BrokerGateway, OrderRequest, Exchange, OrderType, TransactionType, ProductType
import pandas as pd
import pandas_ta as ta
import time
from datetime import datetime, timedelta
from termcolor import colored
import argparse
from scipy.signal import find_peaks
import numpy as np

class FVGStrategy:
    """
    FVG (Fair Value Gap) Trading Strategy
    """

    def __init__(self, broker, config, order_tracker):
        for k, v in config.items():
            setattr(self, f'strat_var_{k}', v)
        self.broker = broker
        self.order_tracker = order_tracker

        self.broker.download_instruments()
        # Prioritize symbols from config, otherwise fetch all futures symbols
        if hasattr(self, 'strat_var_symbols') and self.strat_var_symbols:
            self.symbols = self.strat_var_symbols
        else:
            self.symbols = self.broker.get_nse_futures_symbols()
        self.positions = {}
        self.order_blocks = {}

        logger.info("FVG Strategy initialized")

    def _find_swing_points(self, df):
        """Identifies swing highs and lows from historical data."""
        lookback = self.strat_var_swing_lookback

        high_peaks_indices, _ = find_peaks(df['high'], distance=lookback)
        low_peaks_indices, _ = find_peaks(-df['low'], distance=lookback)

        swing_highs = np.zeros(len(df), dtype=bool)
        swing_lows = np.zeros(len(df), dtype=bool)

        swing_highs[high_peaks_indices] = True
        swing_lows[low_peaks_indices] = True

        df['swing_high'] = swing_highs
        df['swing_low'] = swing_lows

        return df

    def run(self):
        logger.info("Running FVG Strategy")
        while True:
            now = datetime.now()
            next_run = (now - timedelta(minutes=now.minute % 15, seconds=now.second, microseconds=now.microsecond)) + timedelta(minutes=15)

            self.check_open_orders()
            self.analyze_and_trade()
            self.manage_positions()
            self.display_table()

            sleep_time = (next_run - datetime.now()).total_seconds()
            if sleep_time > 0:
                time.sleep(sleep_time)

    def check_open_orders(self):
        for symbol, pos in self.positions.items():
            if pos['status'] == 'PENDING_ENTRY':
                order_status = self.broker.get_order_status(pos['order_id'])
                if order_status == 'FILLED':
                    pos['status'] = 'OPEN'
                    self.place_exit_orders(symbol, pos)

    def place_exit_orders(self, symbol, pos):
        # Place SL order
        sl_req = OrderRequest(
            symbol=symbol.split(':')[1],
            exchange=Exchange[symbol.split(':')[0]],
            transaction_type=TransactionType.SELL if pos['type'] == 'LONG' else TransactionType.BUY,
            quantity=1,
            product_type=ProductType.MARGIN,
            order_type=OrderType.STOP,
            price=pos['stop_loss'],
            stop_price=pos['stop_loss']
        )
        sl_resp = self.broker.place_order(sl_req)
        if sl_resp.status == 'ok':
            pos['sl_order_id'] = sl_resp.order_id

        # Place Target order
        tgt_req = OrderRequest(
            symbol=symbol.split(':')[1],
            exchange=Exchange[symbol.split(':')[0]],
            transaction_type=TransactionType.SELL if pos['type'] == 'LONG' else TransactionType.BUY,
            quantity=1,
            product_type=ProductType.MARGIN,
            order_type=OrderType.LIMIT,
            price=pos['target']
        )
        tgt_resp = self.broker.place_order(tgt_req)
        if tgt_resp.status == 'ok':
            pos['target_order_id'] = tgt_resp.order_id

    def analyze_and_trade(self):
        logger.info("Analyzing for FVG patterns...")

        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        for symbol in self.symbols:
            if symbol in self.positions:
                continue

            try:
                df = pd.DataFrame(self.broker.get_history(symbol, "15m", start_date, end_date))
                if df.empty:
                    continue

                # Convert 'ts' to datetime and set as index
                df['ts'] = pd.to_datetime(df['ts'], unit='s')
                df.set_index('ts', inplace=True)

                # 1. Calculate indicators that may introduce NaNs
                df['vwap'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])
                df['ema200'] = ta.ema(df['close'], length=self.strat_var_ema_length)

                # 2. Calculate positional patterns on the full, un-cleaned data
                df['bullish_fvg'] = self.is_bullish_fvg(df)
                df['bearish_fvg'] = self.is_bearish_fvg(df)
                df = self._find_swing_points(df)

                # Store the order block based on the full history before cleaning
                self.order_blocks[symbol] = self._identify_order_block(df)

                # 3. Clean data and check if enough remains for analysis
                df.dropna(inplace=True)
                if len(df) < 3: # Need at least fvg_candle and entry_candle
                    continue

                # 4. Check entry conditions on the cleaned data
                self.check_long_entry_conditions(df, symbol)
                self.check_short_entry_conditions(df, symbol)

            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")

    def is_bullish_fvg(self, df):
        return df['low'] > df['high'].shift(2)

    def is_bearish_fvg(self, df):
        return df['high'] < df['low'].shift(2)

    def _identify_order_block(self, df):
        """Identifies the most recent order block based on swing points."""
        order_block = None
        # Find the index of the last swing high and last swing low
        last_swing_high_idx = df.index[df['swing_high']].max()
        last_swing_low_idx = df.index[df['swing_low']].max()

        if pd.isna(last_swing_high_idx) or pd.isna(last_swing_low_idx):
            return None # Not enough market structure yet

        # If the most recent swing is a high, look for a bullish order block
        if last_swing_high_idx > last_swing_low_idx:
            search_area = df.loc[:last_swing_high_idx]
            down_candles = search_area[search_area['close'] < search_area['open']]
            if not down_candles.empty:
                ob_candle = down_candles.iloc[-1]
                order_block = {'top': ob_candle['high'], 'bottom': ob_candle['low'], 'type': 'bullish'}

        # If the most recent swing is a low, look for a bearish order block
        elif last_swing_low_idx > last_swing_high_idx:
            search_area = df.loc[:last_swing_low_idx]
            up_candles = search_area[search_area['close'] > search_area['open']]
            if not up_candles.empty:
                ob_candle = up_candles.iloc[-1]
                order_block = {'top': ob_candle['high'], 'bottom': ob_candle['low'], 'type': 'bearish'}

        return order_block

    def check_long_entry_conditions(self, df, symbol):
        if len(df) < 3:
            return

        fvg_candle = df.iloc[-2]
        entry_candle = df.iloc[-1]

        # --- Diagnostic Logging ---
        log_prefix = f"DEBUG_LONG - {symbol} at {entry_candle.name}"

        # Condition 1: Is the second-to-last candle a Bullish FVG?
        is_fvg = fvg_candle['bullish_fvg']
        logger.debug(f"{log_prefix} - Cond 1 (Is Bullish FVG): {is_fvg}")

        # Condition 2: Did the FVG candle cross VWAP or EMA200?
        crossed_vwap = fvg_candle['low'] < fvg_candle['vwap'] and fvg_candle['high'] > fvg_candle['vwap']
        crossed_ema = fvg_candle['low'] < fvg_candle['ema200'] and fvg_candle['high'] > fvg_candle['ema200']
        logger.debug(f"{log_prefix} - Cond 2 (Crossed VWAP/EMA): {crossed_vwap or crossed_ema} (VWAP: {crossed_vwap}, EMA: {crossed_ema})")

        # Condition 3: Is the FVG near a bullish order block?
        order_block = self.order_blocks.get(symbol)
        near_order_block = False
        if order_block and order_block['type'] == 'bullish':
            # Check if any part of the FVG candle is within the order block
            if max(fvg_candle['low'], order_block['bottom']) <= min(fvg_candle['high'], order_block['top']):
                near_order_block = True
        logger.debug(f"{log_prefix} - Cond 3 (Near Bullish OB): {near_order_block} (OB: {order_block})")


        # Condition 4: Is the entry candle's high above the FVG candle's high?
        entry_trigger = entry_candle['high'] > fvg_candle['high']
        logger.debug(f"{log_prefix} - Cond 4 (Entry Trigger): {entry_trigger} (Entry High: {entry_candle['high']}, FVG High: {fvg_candle['high']})")

        if is_fvg and (crossed_vwap or crossed_ema) and near_order_block and entry_trigger:
            entry_price = fvg_candle['high']
            stop_loss = fvg_candle['low']
            target = entry_price + (entry_price - stop_loss) # 1:1 RR

            logger.info(f"Long entry condition met for {symbol}: Entry at {entry_price}, SL at {stop_loss}, Target at {target}")
            self._place_order(symbol, 1, TransactionType.BUY, entry_price, stop_loss, target, "LONG")

    def check_short_entry_conditions(self, df, symbol):
        if len(df) < 3:
            return

        fvg_candle = df.iloc[-2]
        entry_candle = df.iloc[-1]

        # --- Diagnostic Logging ---
        log_prefix = f"DEBUG_SHORT - {symbol} at {entry_candle.name}"

        # Condition 1: Is the second-to-last candle a Bearish FVG?
        is_fvg = fvg_candle['bearish_fvg']
        logger.debug(f"{log_prefix} - Cond 1 (Is Bearish FVG): {is_fvg}")

        # Condition 2: Did the FVG candle cross VWAP or EMA200?
        crossed_vwap = fvg_candle['low'] < fvg_candle['vwap'] and fvg_candle['high'] > fvg_candle['vwap']
        crossed_ema = fvg_candle['low'] < fvg_candle['ema200'] and fvg_candle['high'] > fvg_candle['ema200']
        logger.debug(f"{log_prefix} - Cond 2 (Crossed VWAP/EMA): {crossed_vwap or crossed_ema} (VWAP: {crossed_vwap}, EMA: {crossed_ema})")

        # Condition 3: Is the FVG near a bearish order block?
        order_block = self.order_blocks.get(symbol)
        near_order_block = False
        if order_block and order_block['type'] == 'bearish':
            if max(fvg_candle['low'], order_block['bottom']) <= min(fvg_candle['high'], order_block['top']):
                near_order_block = True
        logger.debug(f"{log_prefix} - Cond 3 (Near Bearish OB): {near_order_block} (OB: {order_block})")

        # Condition 4: Is the entry candle's low below the FVG candle's low?
        entry_trigger = entry_candle['low'] < fvg_candle['low']
        logger.debug(f"{log_prefix} - Cond 4 (Entry Trigger): {entry_trigger} (Entry Low: {entry_candle['low']}, FVG Low: {fvg_candle['low']})")

        if is_fvg and (crossed_vwap or crossed_ema) and near_order_block and entry_trigger:
            entry_price = fvg_candle['low']
            stop_loss = fvg_candle['high']
            target = entry_price - (stop_loss - entry_price) # 1:1 RR

            logger.info(f"Short entry condition met for {symbol}: Entry at {entry_price}, SL at {stop_loss}, Target at {target}")
            self._place_order(symbol, 1, TransactionType.SELL, entry_price, stop_loss, target, "SHORT")

    def _place_order(self, symbol, quantity, transaction_type, entry_price, stop_loss, target, position_type):
        exchange_str, _ = symbol.split(':')
        exchange = Exchange[exchange_str]

        # Immediately add to positions with 'ATTEMPTING' status
        self.positions[symbol] = {
            "order_id": None,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "target": target,
            "status": "ATTEMPTING",
            "type": position_type
        }

        req = OrderRequest(
            symbol=symbol.split(':')[1],
            exchange=exchange,
            transaction_type=transaction_type,
            quantity=quantity,
            product_type=ProductType.MARGIN,
            order_type=OrderType.STOP,
            price=entry_price,
            stop_price=entry_price
        )

        order_resp = self.broker.place_order(req)

        if order_resp.status == "ok":
            self.positions[symbol]['order_id'] = order_resp.order_id
            self.positions[symbol]['status'] = "PENDING_ENTRY"
            logger.info(f"Order placed for {symbol}: {order_resp.order_id}")
        else:
            self.positions[symbol]['status'] = "FAILED"
            logger.error(f"Failed to place order for {symbol}: {order_resp.message}")

    def manage_positions(self):
        for symbol, pos in list(self.positions.items()):
            if pos['status'] == "OPEN":
                quote = self.broker.get_quote(symbol)
                if pos['type'] == 'LONG':
                    if quote.last_price >= pos['entry_price'] + (pos['target'] - pos['entry_price']) / 2:
                        if pos['stop_loss'] < pos['entry_price']:
                            self.broker.cancel_order(pos['sl_order_id'])
                            self.broker.cancel_order(pos['target_order_id'])
                            pos['stop_loss'] = pos['entry_price']
                            self.place_exit_orders(symbol, pos)
                            logger.info(f"Moved SL to breakeven for {symbol}")
                else: # SHORT
                    if quote.last_price <= pos['entry_price'] - (pos['entry_price'] - pos['target']) / 2:
                        if pos['stop_loss'] > pos['entry_price']:
                            self.broker.cancel_order(pos['sl_order_id'])
                            self.broker.cancel_order(pos['target_order_id'])
                            pos['stop_loss'] = pos['entry_price']
                            self.place_exit_orders(symbol, pos)
                            logger.info(f"Moved SL to breakeven for {symbol}")

                sl_status = self.broker.get_order_status(pos['sl_order_id'])
                if sl_status == 'FILLED':
                    self.broker.cancel_order(pos['target_order_id'])
                    pos['status'] = 'CLOSED_SL'
                    logger.info(f"SL hit for {symbol}")

                tgt_status = self.broker.get_order_status(pos['target_order_id'])
                if tgt_status == 'FILLED':
                    self.broker.cancel_order(pos['sl_order_id'])
                    pos['status'] = 'CLOSED_TARGET'
                    logger.info(f"Target hit for {symbol}")

    def display_table(self):
        os.system('cls' if os.name == 'nt' else 'clear')

        table_data = []
        for symbol, pos in self.positions.items():
            quote = None
            if pos['status'] not in ["ATTEMPTING", "FAILED"]:
                quote = self.broker.get_quote(symbol)

            row = {
                "stock_name": symbol.split(':')[1],
                "symbol": symbol,
                "future_price": quote.last_price if quote else 'N/A',
                "entry_price": pos['entry_price'],
                "target_price": pos['target'],
                "stoploss_price": pos['stop_loss'],
                "order_filled": pos['status'],
                "type": pos['type']
            }
            table_data.append(row)

        df = pd.DataFrame(table_data)

        print("--- FVG Strategy Live Positions ---")
        if not df.empty:
            table_str = df.to_string()
            lines = table_str.split('\n')
            header = lines[0]
            data_lines = lines[1:]

            print(header)
            for i, line in enumerate(data_lines):
                status = df.iloc[i]['order_filled']
                if status == 'CLOSED_SL':
                    print(colored(line, 'red'))
                elif status == 'CLOSED_TARGET':
                    print(colored(line, 'green'))
                else:
                    print(line)
        else:
            print("No open positions.")
        print("-----------------------------------")


if __name__ == "__main__":
    import yaml
    import sys
    from orders import OrderTracker
    from logger import logger
    from dotenv import load_dotenv
    # Explicitly load .env from the project root
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(dotenv_path=dotenv_path)
    import logging
    logger.setLevel(logging.DEBUG)

    parser = argparse.ArgumentParser(description="FVG Strategy")
    parser.add_argument('--symbols', type=str, nargs='+', help='List of symbols to trade')
    parser.add_argument('--ema-length', type=int, help='Length for EMA calculation')
    parser.add_argument('--support-proximity-threshold', type=float, help='Proximity threshold for support zone')
    parser.add_argument('--swing-lookback', type=int, help='Lookback period for swing point detection')
    args = parser.parse_args()

    # Construct an absolute path to the config file
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_file = os.path.join(project_root, "strategy", "configs", "fvg_strategy.yml")
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)['default']

    if args.symbols:
        config['symbols'] = args.symbols
    if args.ema_length:
        config['ema_length'] = args.ema_length
    if args.support_proximity_threshold:
        config['support_proximity_threshold'] = args.support_proximity_threshold
    if args.swing_lookback:
        config['swing_lookback'] = args.swing_lookback

    broker = BrokerGateway.from_name(os.getenv("BROKER_NAME"))
    order_tracker = OrderTracker()

    strategy = FVGStrategy(broker, config, order_tracker)
    strategy.run()

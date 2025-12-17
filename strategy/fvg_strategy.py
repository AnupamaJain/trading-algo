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
    FVG (Fair Value Gap) Trading Strategy based on Smart Money Concepts.
    """
    
    def __init__(self, broker, config):
        for k, v in config.items():
            setattr(self, f'strat_var_{k}', v)
        self.broker = broker
        
        self.broker.download_instruments()
        # Fetch all F&O stock futures and GOLDM/SILVERM
        self.symbols = self._get_target_symbols()
        self.positions = {}

        logger.info("FVG Strategy initialized")

    def _get_target_symbols(self):
        """Fetches all NSE F&O stock futures, precious metals, and MCX futures."""
        all_instruments = self.broker.get_instruments()

        # 1. Create a whitelist of valid stock underlyings from the cash market segment
        stock_symbols_df = all_instruments[all_instruments['segment'] == 'NSE']
        # Extract the base symbol (e.g., 'SBIN' from 'SBIN-EQ')
        stock_underlyings = set(stock_symbols_df['symbol'].str.replace('-EQ', ''))

        # 2. Filter for NSE futures contracts that are actual stock futures and have not expired
        futures_df = all_instruments[
            (all_instruments['segment'] == 'NFO-FUT') &
            (all_instruments['expiry'] >= pd.to_datetime('today').date()) &
            (all_instruments['underlying_symbol'].isin(stock_underlyings)) # Ensure the underlying is a stock
        ].copy()

        # Find the nearest expiry for each underlying symbol
        futures_df['expiry'] = pd.to_datetime(futures_df['expiry'])
        nearest_expiry_df = futures_df.loc[futures_df.groupby('underlying_symbol')['expiry'].idxmin()]

        stock_futures = nearest_expiry_df['symbol'].tolist()

        # 3. Add Gold and Silver futures separately
        precious_metals = ["GOLDM", "SILVERM"]

        metal_futures_df = all_instruments[
            (all_instruments['underlying_symbol'].isin(precious_metals)) &
            (all_instruments['instrument_type'] == 'FUT') & # Ensure we get futures, not options
            (all_instruments['expiry'] >= pd.to_datetime('today').date())
        ].copy()

        if not metal_futures_df.empty:
            metal_futures_df['expiry'] = pd.to_datetime(metal_futures_df['expiry'])
            nearest_metal_expiry_df = metal_futures_df.loc[metal_futures_df.groupby('underlying_symbol')['expiry'].idxmin()]
            metal_symbols = nearest_metal_expiry_df['symbol'].tolist()
        else:
            metal_symbols = []

        # 4. Get all current-expiry MCX futures
        mcx_futures_df = all_instruments[
            (all_instruments['exchange'] == 'MCX') &
            (all_instruments['instrument_type'] == 'FUT') &
            (all_instruments['expiry'] >= pd.to_datetime('today').date())
        ].copy()

        if not mcx_futures_df.empty:
            mcx_futures_df['expiry'] = pd.to_datetime(mcx_futures_df['expiry'])
            nearest_mcx_expiry_df = mcx_futures_df.loc[mcx_futures_df.groupby('underlying_symbol')['expiry'].idxmin()]
            mcx_symbols = nearest_mcx_expiry_df['symbol'].tolist()
        else:
            mcx_symbols = []

        # Combine all symbols and remove duplicates
        final_symbols = list(set(stock_futures + metal_symbols + mcx_symbols))

        logger.info(f"Tracking {len(stock_futures)} stock futures, {len(metal_symbols)} specific metal futures, and {len(mcx_symbols)} other MCX futures. Total unique symbols: {len(final_symbols)}")
        return final_symbols


    def run(self):
        """Main execution loop for the strategy."""
        logger.info("Running FVG Strategy")
        while True:
            now = datetime.now()
            # Align to the next 15-minute mark
            next_run = (now - timedelta(minutes=now.minute % 15, seconds=now.second, microseconds=now.microsecond)) + timedelta(minutes=15)
            
            self.analyze_and_trade()
            self.manage_positions()
            self.display_table()
            
            sleep_time = (next_run - datetime.now()).total_seconds()
            if sleep_time > 0:
                logger.info(f"Waiting for {sleep_time:.2f} seconds until the next 15-minute candle.")
                time.sleep(sleep_time)

    def analyze_and_trade(self):
        """Fetches data, analyzes for entry conditions, and places trades."""
        logger.info("Analyzing symbols for FVG patterns...")
        
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d") # 90 days for enough data

        for symbol in self.symbols:
            if symbol in self.positions:
                continue

            try:
                df_raw = self.broker.get_history(symbol, "15", start_date, end_date)
                if not df_raw:
                    logger.warning(f"No historical data for {symbol}")
                    continue

                df = pd.DataFrame(df_raw)
                if df.empty:
                    continue

                # --- Data Preparation and Indicator Calculation ---
                df['ts'] = pd.to_datetime(df['ts'], unit='s')
                df.set_index('ts', inplace=True)
                df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)


                self.calculate_indicators(df)
                self.find_smc_patterns(df)

                # --- Entry Logic ---
                self.check_entry_conditions(df, symbol)

            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")

    def calculate_indicators(self, df):
        """Calculates all necessary technical indicators."""
        df['ema200'] = ta.ema(df['Close'], length=self.strat_var_ema_length)
        df['vwap'] = ta.vwap(df['High'], df['Low'], df['Close'], df['Volume'])
        df['atr'] = ta.atr(df['High'], df['Low'], df['Close'], length=self.strat_var_atr_length)

    def find_smc_patterns(self, df):
        """Identifies Swing Points, Order Blocks, and FVGs."""
        self.get_swing_points(df)
        self.get_order_blocks(df)
        self.get_fair_value_gaps(df)

    def get_swing_points(self, df):
        """Identifies swing highs and lows."""
        lookback = self.strat_var_swing_lookback
        # Using scipy find_peaks for more robust peak/trough detection
        high_peaks, _ = find_peaks(df['High'], distance=lookback, prominence=df['atr'].mean() * 0.5)
        low_peaks, _ = find_peaks(-df['Low'], distance=lookback, prominence=df['atr'].mean() * 0.5)
        
        df['swing_high'] = False
        df.iloc[high_peaks, df.columns.get_loc('swing_high')] = True

        df['swing_low'] = False
        df.iloc[low_peaks, df.columns.get_loc('swing_low')] = True

    def get_order_blocks(self, df):
        """Identifies bullish and bearish order blocks based on swing points."""
        df['bullish_ob'] = np.nan
        df['bearish_ob'] = np.nan

        # Find potential bullish OBs (last down candle before a swing high)
        bullish_ob_indices = df.index[df['swing_high'] & (df['Close'].shift(1) < df['Open'].shift(1))]
        for idx in bullish_ob_indices:
            ob_candle = df.loc[idx].shift(1)
            df.loc[idx, 'bullish_ob'] = ob_candle['High']

        # Find potential bearish OBs (last up candle before a swing low)
        bearish_ob_indices = df.index[df['swing_low'] & (df['Close'].shift(1) > df['Open'].shift(1))]
        for idx in bearish_ob_indices:
            ob_candle = df.loc[idx].shift(1)
            df.loc[idx, 'bearish_ob'] = ob_candle['Low']

    def get_fair_value_gaps(self, df):
        """Identifies Fair Value Gaps (FVGs) with momentum check."""
        # Calculate bar momentum and threshold
        df['bar_delta_percent'] = (df['Close'] - df['Open']) / df['Open'] * 100
        # Dynamic threshold based on cumulative average of momentum
        df['fvg_threshold'] = df['bar_delta_percent'].abs().expanding().mean() * 0.8 # 80% of average momentum

        # Bullish FVG Conditions:
        # 1. Low of current candle is higher than the high of the candle two periods ago.
        # 2. Momentum of the FVG candle (candle 2) must be positive and above the threshold.
        is_bullish_gap = df['Low'] > df['High'].shift(2)
        has_bullish_momentum = df['bar_delta_percent'].shift(1) > df['fvg_threshold'].shift(1)

        df['bullish_fvg'] = is_bullish_gap & has_bullish_momentum
        df['bullish_fvg_top'] = np.where(df['bullish_fvg'], df['Low'], np.nan)
        df['bullish_fvg_bottom'] = np.where(df['bullish_fvg'], df['High'].shift(2), np.nan)

        # Bearish FVG Conditions:
        # 1. High of current candle is lower than the low of the candle two periods ago.
        # 2. Momentum of the FVG candle (candle 2) must be negative and below the negative threshold.
        is_bearish_gap = df['High'] < df['Low'].shift(2)
        has_bearish_momentum = df['bar_delta_percent'].shift(1) < -df['fvg_threshold'].shift(1)

        df['bearish_fvg'] = is_bearish_gap & has_bearish_momentum
        df['bearish_fvg_top'] = np.where(df['bearish_fvg'], df['Low'].shift(2), np.nan)
        df['bearish_fvg_bottom'] = np.where(df['bearish_fvg'], df['High'], np.nan)

    def is_fvg_near_order_block(self, df, fvg_candle_index, is_bullish):
        """Checks if an FVG is located near a recent order block."""
        proximity_range = df['atr'].mean() * self.strat_var_order_block_proximity_percent
        fvg_candle = df.loc[fvg_candle_index]

        if is_bullish:
            # Look for a recent bullish OB before this FVG
            recent_obs = df.loc[:fvg_candle_index]['bullish_ob'].dropna()
            if recent_obs.empty:
                return False
            last_ob_level = recent_obs.iloc[-1]
            # Check if the FVG bottom is close to the OB level
            return abs(fvg_candle['bullish_fvg_bottom'] - last_ob_level) <= proximity_range
        else: # Bearish
            # Look for a recent bearish OB before this FVG
            recent_obs = df.loc[:fvg_candle_index]['bearish_ob'].dropna()
            if recent_obs.empty:
                return False
            last_ob_level = recent_obs.iloc[-1]
            # Check if the FVG top is close to the OB level
            return abs(fvg_candle['bearish_fvg_top'] - last_ob_level) <= proximity_range

    def check_entry_conditions(self, df, symbol):
        """Checks the final entry conditions and triggers trades."""
        if len(df) < 3: return

        last_candle = df.iloc[-1]
        fvg_candle = df.iloc[-2] # Entry is on the candle *after* the FVG candle

        # --- Bullish Entry ---
        if fvg_candle['bullish_fvg']:
            is_near_ob = self.is_fvg_near_order_block(df, fvg_candle.name, is_bullish=True)
            crosses_ma = fvg_candle['Close'] > fvg_candle['vwap'] or fvg_candle['Close'] > fvg_candle['ema200']
            entry_trigger = last_candle['High'] > fvg_candle['High']

            if is_near_ob and crosses_ma and entry_trigger:
                entry_price = fvg_candle['High']
                stop_loss = fvg_candle['Low']
                target = entry_price + (entry_price - stop_loss) * self.strat_var_risk_reward_ratio

                logger.info(colored(f"LONG ENTRY SIGNAL for {symbol}: Entry at {entry_price}, SL at {stop_loss}, Target at {target}", 'green'))
                self._place_basket_order(symbol, TransactionType.BUY, entry_price, stop_loss, target, "LONG")

        # --- Bearish Entry ---
        if fvg_candle['bearish_fvg']:
            is_near_ob = self.is_fvg_near_order_block(df, fvg_candle.name, is_bullish=False)
            crosses_ma = fvg_candle['Close'] < fvg_candle['vwap'] or fvg_candle['Close'] < fvg_candle['ema200']
            entry_trigger = last_candle['Low'] < fvg_candle['Low']

            if is_near_ob and crosses_ma and entry_trigger:
                entry_price = fvg_candle['Low']
                stop_loss = fvg_candle['High']
                target = entry_price - (stop_loss - entry_price) * self.strat_var_risk_reward_ratio

                logger.info(colored(f"SHORT ENTRY SIGNAL for {symbol}: Entry at {entry_price}, SL at {stop_loss}, Target at {target}", 'red'))
                self._place_basket_order(symbol, TransactionType.SELL, entry_price, stop_loss, target, "SHORT")


    def _place_basket_order(self, symbol, transaction_type, entry_price, stop_loss, target, position_type):
        """Places a basket order for entry, SL, and target."""
        if symbol in self.positions:
            return # Avoid placing duplicate orders

        exchange_str, symbol_only = symbol.split(':', 1)
        exchange = Exchange[exchange_str]
        quantity = self.strat_var_lot_size

        self.positions[symbol] = {
            "order_id": None, "sl_order_id": None, "target_order_id": None,
            "entry_price": entry_price, "stop_loss": stop_loss, "target": target,
            "status": "ATTEMPTING", "type": position_type
        }

        # 1. Entry Order (Stop Limit)
        entry_order = OrderRequest(
            symbol=symbol_only, exchange=exchange, transaction_type=transaction_type,
            quantity=quantity, product_type=ProductType.MARGIN, order_type=OrderType.STOP,
            price=entry_price, stop_price=entry_price
        )
        
        # 2. Stop Loss Order
        sl_transaction_type = TransactionType.SELL if transaction_type == TransactionType.BUY else TransactionType.BUY
        sl_order = OrderRequest(
            symbol=symbol_only, exchange=exchange, transaction_type=sl_transaction_type,
            quantity=quantity, product_type=ProductType.MARGIN, order_type=OrderType.STOP,
            price=stop_loss, stop_price=stop_loss
        )

        # 3. Target Order
        target_order = OrderRequest(
            symbol=symbol_only, exchange=exchange, transaction_type=sl_transaction_type,
            quantity=quantity, product_type=ProductType.MARGIN, order_type=OrderType.LIMIT,
            price=target
        )
        
        basket = [entry_order, sl_order, target_order]

        try:
            order_responses = self.broker.place_basket_orders(basket)

            # For simplicity, we'll assume the first order is the entry order for now
            # A more robust implementation would match response to request
            entry_resp = order_responses[0]
            if entry_resp.status == "ok":
                self.positions[symbol]['status'] = "PENDING_ENTRY"
                self.positions[symbol]['order_id'] = entry_resp.order_id
                self.positions[symbol]['sl_order_id'] = order_responses[1].order_id
                self.positions[symbol]['target_order_id'] = order_responses[2].order_id
                logger.info(f"Basket order placed for {symbol}. Entry Order ID: {entry_resp.order_id}")
            else:
                self.positions[symbol]['status'] = "FAILED"
                logger.error(f"Failed to place basket order for {symbol}: {entry_resp.message}")
        except Exception as e:
            self.positions[symbol]['status'] = "FAILED"
            logger.error(f"Exception placing basket order for {symbol}: {e}")

    def manage_positions(self):
        """Checks status of open orders and manages active positions."""
        for symbol, pos in list(self.positions.items()):
            # Check for entry order fill
            if pos['status'] == 'PENDING_ENTRY':
                entry_status = self.broker.get_order_status(pos['order_id'])
                if entry_status == 'FILLED':
                    pos['status'] = 'OPEN'
                    logger.info(colored(f"ENTRY FILLED for {symbol}", 'cyan'))
                elif entry_status in ['REJECTED', 'CANCELLED']:
                     pos['status'] = 'FAILED'
                     self.broker.cancel_order(pos['sl_order_id'])
                     self.broker.cancel_order(pos['target_order_id'])


            # Check for exit order fill
            if pos['status'] == 'OPEN':
                sl_status = self.broker.get_order_status(pos['sl_order_id'])
                if sl_status == 'FILLED':
                    pos['status'] = 'CLOSED_SL'
                    self.broker.cancel_order(pos['target_order_id']) # Cancel target
                    logger.info(colored(f"STOP-LOSS HIT for {symbol}", 'red'))
                    continue

                tgt_status = self.broker.get_order_status(pos['target_order_id'])
                if tgt_status == 'FILLED':
                    pos['status'] = 'CLOSED_TARGET'
                    self.broker.cancel_order(pos['sl_order_id']) # Cancel SL
                    logger.info(colored(f"TARGET HIT for {symbol}", 'green'))


    def display_table(self):
        """Displays a live table of all positions."""
        os.system('cls' if os.name == 'nt' else 'clear')
        
        table_data = []
        for symbol, pos in self.positions.items():
            quote = self.broker.get_quote(symbol)
            
            row = {
                "stock_name": symbol.split(':')[1],
                "type": pos['type'],
                "status": pos['status'],
                "future_price": quote.last_price if quote else 'N/A',
                "entry_price": pos['entry_price'],
                "target_price": pos['target'],
                "stoploss_price": pos['stop_loss'],
            }
            table_data.append(row)

        if not table_data:
            print("--- FVG Strategy ---")
            print("No active or attempted trades yet.")
            print("--------------------")
            return

        df = pd.DataFrame(table_data)
        
        def colorize_row(row):
            status = row['status']
            if status == 'CLOSED_SL' or status == 'FAILED':
                return [colored(val, 'red') for val in row]
            elif status == 'CLOSED_TARGET':
                return [colored(val, 'green') for val in row]
            elif status == 'OPEN':
                return [colored(val, 'cyan') for val in row]
            return [str(val) for val in row]

        df_display = df.apply(colorize_row, axis=1)
        df_display.columns = df.columns
        print(df_display.to_string())

        print("-----------------------------------")

if __name__ == "__main__":
    from dotenv import load_dotenv
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(dotenv_path=dotenv_path)
    import logging
    logger.setLevel(logging.INFO)

    parser = argparse.ArgumentParser(description="FVG Strategy")
    parser.add_argument('--config', type=str, default="fvg_strategy.yml", help='Path to the config file')
    args = parser.parse_args()
    
    config_file = os.path.join(os.path.dirname(__file__), "configs", args.config)
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)['default']

    broker = BrokerGateway.from_name(os.getenv("BROKER_NAME"))
    strategy = FVGStrategy(broker, config)
    strategy.run()

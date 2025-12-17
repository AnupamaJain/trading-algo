import unittest
import pandas as pd
from strategy.fvg_strategy import FVGStrategy
from unittest.mock import MagicMock, patch

class TestFVGStrategy(unittest.TestCase):

    @patch('strategy.fvg_strategy.FVGStrategy._get_target_symbols', return_value=[])
    def setUp(self, mock_get_symbols):
        # Mock broker and config
        self.mock_broker = MagicMock()
        self.config = {
            'ema_length': 14,
            'atr_length': 14,
            'swing_lookback': 5,
            'order_block_body_ratio': 0.5,
            'order_block_proximity_percent': 0.5,
            'fvg_atr_multiplier': 1.0,
            'risk_reward_ratio': 1.0,
            'lot_size': 1
        }
        self.strategy = FVGStrategy(self.mock_broker, self.config)

    def test_swing_points(self):
        # Create sample data with one clear swing high and one clear swing low
        data = {
            'High': [100, 105, 110, 105, 100, 98, 96, 95, 94, 93],
            'Low':  [90, 95, 100, 95, 90, 85, 80, 82, 81, 83],
            'Close':[95, 100, 105, 100, 95, 90, 82, 84, 83, 85],
            'atr': [1] * 10
        }
        df = pd.DataFrame(data)

        self.strategy.get_swing_points(df)

        # Expected high at index 2 (110)
        self.assertTrue(df.iloc[2]['swing_high'])
        # Expected low at index 6 (80)
        self.assertTrue(df.iloc[6]['swing_low'])
        # Verify no other swing points are detected
        self.assertEqual(df['swing_high'].sum(), 1)
        self.assertEqual(df['swing_low'].sum(), 1)


    def test_fvg_detection(self):
        # Data designed to create a bullish FVG at index 3
        data = {
            'High': [100, 102, 105, 112, 115],
            'Low':  [98,  100, 101, 108, 110],
            'Close': [99, 101, 104, 110, 114],
            'Open': [98, 100, 102, 109, 111]
        }
        df = pd.DataFrame(data)

        self.strategy.get_fair_value_gaps(df)

        # Expect a bullish FVG at index 3, because Low[3] (108) > High[1] (102)
        self.assertTrue(df.iloc[3]['bullish_fvg'])
        self.assertFalse(df.iloc[3]['bearish_fvg'])

if __name__ == '__main__':
    unittest.main()

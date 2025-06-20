import unittest
import pandas as pd
from src.strategies.momentum import MomentumStrategy
from src.api.alpaca_client import AlpacaClient
from unittest.mock import MagicMock


class TestMomentumStrategy(unittest.TestCase):
    def setUp(self):
        # Mock Alpaca client
        self.mock_client = MagicMock(spec=AlpacaClient)
        self.mock_client.get_historical_data.return_value = [
            {'time': '2023-01-01', 'close': 100},
            {'time': '2023-01-02', 'close': 102},
            # Add more test data
        ]

        # Mock config
        self.config = {
            'trading': {
                'symbols': ['TEST'],
                'timeframe': '15Min',
                'risk_per_trade': 0.01
            }
        }

        self.strategy = MomentumStrategy(self.mock_client, self.config)

    def test_calculate_signals(self):
        signals = self.strategy.calculate_signals('TEST')
        self.assertIsNotNone(signals)
        self.assertIn(signals['signal'], ['buy', 'sell'])

    def test_execute(self):
        trades = self.strategy.execute()
        self.assertIsInstance(trades, list)


if __name__ == '__main__':
    unittest.main()
import numpy as np
import pandas as pd
from typing import Dict, Optional
from datetime import datetime, timedelta
import logging
from ..utils.indicators import calculate_rsi, calculate_macd
from ..utils.risk_management import calculate_position_size

logger = logging.getLogger(__name__)


class MomentumStrategy:
    def __init__(self, client, config_path: str):
        self.client = client
        with open(config_path) as file:
            self.config = yaml.safe_load(file)['trading']
        self.symbols = self.config['symbols']
        self.timeframe = self.config['timeframe']
        self.risk_per_trade = self.config['risk_per_trade']
        self.account_balance = float(self.client.account.equity)
        logger.info("Momentum strategy initialized")

    def calculate_signals(self, symbol: str) -> Optional[Dict]:
        """Calculate trading signals for a symbol"""
        try:
            data = self.client.get_historical_data(symbol, self.timeframe, 100)
            if not data:
                return None

            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['time'])
            df.set_index('date', inplace=True)

            # Calculate indicators
            df['rsi'] = calculate_rsi(df['close'], 14)
            df['macd'], df['signal'] = calculate_macd(df['close'])

            # Generate signals
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2]

            signal = None
            reason = []

            # Momentum entry conditions
            if (last_row['rsi'] > 50 and prev_row['rsi'] <= 50 and
                    last_row['macd'] > last_row['signal'] and prev_row['macd'] <= prev_row['signal']):
                signal = 'buy'
                reason.append('RSI crossed above 50')
                reason.append('MACD crossed above signal line')

            elif (last_row['rsi'] < 50 and prev_row['rsi'] >= 50 and
                  last_row['macd'] < last_row['signal'] and prev_row['macd'] >= prev_row['signal']):
                signal = 'sell'
                reason.append('RSI crossed below 50')
                reason.append('MACD crossed below signal line')

            if signal:
                return {
                    'symbol': symbol,
                    'signal': signal,
                    'price': last_row['close'],
                    'time': last_row.name,
                    'reason': ', '.join(reason)
                }
            return None

        except Exception as e:
            logger.error(f"Error calculating signals for {symbol}: {e}")
            return None

    def execute(self) -> List[Dict]:
        """Execute trades based on signals"""
        trades = []
        for symbol in self.symbols:
            signal = self.calculate_signals(symbol)
            if signal:
                position_size = calculate_position_size(
                    self.account_balance,
                    self.risk_per_trade,
                    signal['price']
                )

                if position_size > 0:
                    order = self.client.submit_order(
                        symbol=signal['symbol'],
                        qty=position_size,
                        side=signal['signal']
                    )

                    if order:
                        trades.append({
                            'symbol': signal['symbol'],
                            'side': signal['signal'],
                            'price': signal['price'],
                            'quantity': position_size,
                            'time': datetime.now(),
                            'reason': signal['reason']
                        })
        return trades
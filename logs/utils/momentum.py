from typing import List
import pandas as pd
from alpaca_client import AlpacaClient
from db_models import Trade
import logging

logger = logging.getLogger(__name__)


class MomentumStrategy:
    def __init__(self, client: AlpacaClient, config: dict):
        self.client = client
        self.config = config
        self.max_positions = config.get('max_positions', 5)
        self.rsi_period = config.get('rsi_period', 14)
        self.rsi_threshold = config.get('rsi_threshold', 30)  # oversold threshold

    def calculate_rsi(self, prices: pd.Series) -> pd.Series:
        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(self.rsi_period).mean()
        avg_loss = loss.rolling(self.rsi_period).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_position_size(self, account_balance, risk_percent, entry_price, stop_loss_price):
        risk_per_share = abs(entry_price - stop_loss_price)
        risk_amount = account_balance * risk_percent
        position_size = risk_amount / risk_per_share
        return int(position_size) if position_size > 0 else 0

    def execute(self) -> List[Trade]:
        trades = []
        open_positions = self.client.get_positions()
        if len(open_positions) >= self.max_positions:
            logger.info("Max open positions reached, skipping new trades")
            return trades

        symbols = self.config.get('symbols', ['AAPL', 'MSFT', 'TSLA'])
        for symbol in symbols:
            bars = self.client.get_historical_data(symbol, timeframe='1Min', limit=100)
            df = pd.DataFrame(bars)
            if df.empty or 'close' not in df.columns:
                logger.warning(f"No price data for {symbol}")
                continue

            rsi = self.calculate_rsi(df['close'])
            latest_rsi = rsi.iloc[-1]

            if latest_rsi < self.rsi_threshold:
                account_balance = float(self.client.account.cash)
                risk_percent = self.config.get('risk_percent', 0.01)
                current_price = df['close'].iloc[-1]
                stop_loss_price = current_price * 0.98  # 2% stop loss

                position_size = self.calculate_position_size(account_balance, risk_percent, current_price,
                                                             stop_loss_price)
                if position_size <= 0:
                    logger.info(f"Position size zero or negative for {symbol}, skipping")
                    continue

                order = self.client.submit_order(symbol, qty=position_size, side='buy')
                if order:
                    logger.info(
                        f"Placed BUY order for {position_size} shares of {symbol} at approx {current_price}, RSI={latest_rsi:.2f}")
                    trade = Trade(
                        symbol=symbol,
                        price=current_price,
                        quantity=position_size,
                        entry_price=current_price,
                        strategy='momentum'
                    )
                    trades.append(trade)
                else:
                    logger.error(f"Order failed for {symbol}")

        return trades


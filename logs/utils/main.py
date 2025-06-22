import time
import logging
from typing import List, Dict, Optional
from decimal import getcontext
from datetime import datetime
import yfinance as yf
import pandas as pd

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from rich.logging import RichHandler
from rich.console import Console
from rich.table import Table

# Configure decimal precision
getcontext().prec = 6

# Setup rich console and logging
console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, markup=True)]
)
logger = logging.getLogger(__name__)

# ======= Your Alpaca API keys here =======
ALPACA_API_KEY = 'PKPWDQHHK0NELHJOGHJ4'
ALPACA_API_SECRET = 'JNdLs5ldleeNJ6Vz41ZM8S9qlspeZLJJSbxlhL61'
PAPER_TRADING = True  # Set False for live trading


class FreeDataTradingBot:
    def __init__(self, api_key: str, api_secret: str, paper: bool = True):
        self.trading_client = TradingClient(api_key, api_secret, paper=paper)
        self.data_client = StockHistoricalDataClient(api_key, api_secret) if api_key and api_secret else None
        logger.info("Initialized trading bot with free data sources")

        try:
            account = self.trading_client.get_account()
            logger.info(f"Connected to account {account.account_number} (Status: {account.status})")
        except Exception as e:
            logger.error(f"Failed to connect to Alpaca: {e}")
            raise

    def get_account_info(self) -> Dict:
        try:
            account = self.trading_client.get_account()
            return {
                'cash': float(account.cash),
                'equity': float(account.equity),
                'buying_power': float(account.buying_power),
                'portfolio_value': float(account.portfolio_value)
            }
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            return {}

    def get_positions(self) -> Dict[str, float]:
        try:
            positions = self.trading_client.get_all_positions()
            return {pos.symbol: float(pos.qty) for pos in positions}
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return {}

    def get_current_price(self, symbol: str) -> Optional[float]:
        # Try Yahoo Finance first
        try:
            stock = yf.Ticker(symbol)
            data = stock.history(period='1d')
            if not data.empty:
                return data['Close'].iloc[-1]
        except Exception as e:
            logger.warning(f"Yahoo Finance failed for {symbol}: {e}")

        # Fallback to Alpaca free data
        if self.data_client:
            try:
                request = StockBarsRequest(
                    symbol_or_symbols=symbol,
                    timeframe=TimeFrame.Minute,
                    limit=1
                )
                bars = self.data_client.get_stock_bars(request)
                if not bars.df.empty:
                    return bars.df['close'].iloc[-1]
            except Exception as e:
                logger.warning(f"Alpaca data failed for {symbol}: {e}")

        logger.error(f"All data sources failed for {symbol}")
        return None

    def submit_order(self, symbol: str, qty: float, side: str) -> bool:
        try:
            order_data = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL,
                time_in_force=TimeInForce.GTC
            )
            order = self.trading_client.submit_order(order_data)
            logger.info(f"Submitted {order.side} order for {order.qty} shares of {order.symbol}")
            return True
        except Exception as e:
            logger.error(f"Order failed for {symbol}: {e}")
            return False


class RSIStrategy:
    def __init__(self, bot: FreeDataTradingBot, config: Dict):
        self.bot = bot
        self.symbols = config['symbols']
        self.rsi_period = config['rsi_period']
        self.overbought = config['overbought']
        self.oversold = config['oversold']
        self.risk_pct = config['risk_pct']
        self.max_positions = config['max_positions']

    def calculate_rsi(self, prices: List[float]) -> float:
        if len(prices) < self.rsi_period + 1:
            logger.warning(f"Not enough data for RSI calculation (need {self.rsi_period + 1}, got {len(prices)})")
            return 50.0

        delta = pd.Series(prices).diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)

        avg_gain = gain.rolling(window=self.rsi_period, min_periods=self.rsi_period).mean().iloc[-1]
        avg_loss = loss.rolling(window=self.rsi_period, min_periods=self.rsi_period).mean().iloc[-1]

        if pd.isna(avg_gain) or pd.isna(avg_loss):
            return 50.0

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return round(rsi, 2)

    def generate_signals(self) -> Dict[str, str]:
        positions = self.bot.get_positions()
        signals = {}

        for symbol in self.symbols:
            # Fetch historical prices (1 min interval, 1 day)
            try:
                stock = yf.Ticker(symbol)
                hist = stock.history(period='1d', interval='1m')
                if hist.empty:
                    logger.warning(f"No price data for {symbol}")
                    signals[symbol] = 'hold'
                    continue
                prices = hist['Close'].tolist()
            except Exception as e:
                logger.warning(f"Failed to fetch prices for {symbol}: {e}")
                signals[symbol] = 'hold'
                continue

            rsi = self.calculate_rsi(prices)
            logger.info(f"{symbol} RSI: {rsi}")

            if rsi > self.overbought and symbol in positions:
                signals[symbol] = 'sell'
            elif rsi < self.oversold and symbol not in positions and len(positions) < self.max_positions:
                signals[symbol] = 'buy'
            else:
                signals[symbol] = 'hold'

        return signals


def print_startup_banner():
    console.rule("[bold green]24/7 RSI Trading Bot Started[/bold green]")
    console.print("[cyan]Press Ctrl+C to stop the bot at any time[/cyan]\n")


def print_signals(signals: Dict[str, str]):
    table = Table(title="Trading Signals", show_header=True, header_style="bold magenta")
    table.add_column("Symbol", style="cyan", justify="center")
    table.add_column("Signal", style="green", justify="center")

    for sym, signal in signals.items():
        color = "red" if signal == "sell" else "green" if signal == "buy" else "yellow"
        table.add_row(sym, f"[{color}]{signal.upper()}[/{color}]")

    console.print(table)


def main():
    # Configuration
    config = {
        'symbols': ['AAPL', 'MSFT', 'TSLA'],
        'rsi_period': 14,
        'overbought': 70,
        'oversold': 30,
        'risk_pct': 0.01,
        'max_positions': 3,
    }

    bot = FreeDataTradingBot(ALPACA_API_KEY, ALPACA_API_SECRET, paper=PAPER_TRADING)
    strategy = RSIStrategy(bot, config)

    print_startup_banner()

    try:
        while True:
            signals = strategy.generate_signals()
            print_signals(signals)
            # Here you can add your order execution logic based on signals
            time.sleep(60)  # Wait 1 minute before next cycle
    except KeyboardInterrupt:
        console.print("\n[bold red]Trading bot stopped by user.[/bold red]")


if __name__ == '__main__':
    main()




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

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.exc import SQLAlchemyError

# Configure decimal precision
getcontext().prec = 6

# Setup rich console and logging
console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[RichHandler(rich_tracebacks=True, markup=True)]
)
logger = logging.getLogger(__name__)

# ==== Database setup ====

Base = declarative_base()

class TradeSignal(Base):
    __tablename__ = 'trade_signals'
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False)
    signal = Column(String(10), nullable=False)  # 'buy', 'sell', 'hold'
    rsi = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False)
    side = Column(String(4), nullable=False)  # 'buy' or 'sell'
    qty = Column(Float, nullable=False)
    status = Column(String(20), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Database:
    def __init__(self, url: str):
        self.engine = create_engine(url, echo=False, pool_pre_ping=True)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        logger.info(f"Database connected: {url}")

    def get_session(self) -> Session:
        return self.SessionLocal()

    def add_trade_signals(self, signals: Dict[str, str], rsis: Dict[str, float]):
        session = self.get_session()
        try:
            for symbol, signal in signals.items():
                rsi_value = rsis.get(symbol, 0.0)
                ts = TradeSignal(symbol=symbol, signal=signal, rsi=rsi_value)
                session.add(ts)
                logger.info(f"[DB][TradeSignal] Symbol={symbol}, Signal={signal}, RSI={rsi_value:.2f}, Time={ts.timestamp}")
            session.commit()
            logger.info("[DB] Trade signals committed successfully")
        except SQLAlchemyError as e:
            logger.error(f"[DB][TradeSignal] Commit failed: {e}")
            session.rollback()
        finally:
            session.close()

    def add_orders(self, orders: List[Dict]):
        session = self.get_session()
        try:
            for order in orders:
                o = Order(
                    symbol=order['symbol'],
                    side=order['side'],
                    qty=order['qty'],
                    status=order['status']
                )
                session.add(o)
                logger.info(f"[DB][Order] Symbol={o.symbol}, Side={o.side}, Qty={o.qty}, Status={o.status}, Time={o.timestamp}")
            session.commit()
            logger.info("[DB] Orders committed successfully")
        except SQLAlchemyError as e:
            logger.error(f"[DB][Order] Commit failed: {e}")
            session.rollback()
        finally:
            session.close()

# ==== Alpaca and Trading Bot ====

ALPACA_API_KEY = "PKPWDQHHK0NELHJOGHJ4"
ALPACA_API_SECRET = "JNdLs5ldleeNJ6Vz41ZM8S9qlspeZLJJSbxlhL61"
PAPER_TRADING = True

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
                price = data['Close'].iloc[-1]
                logger.debug(f"Price for {symbol} from Yahoo: {price}")
                return price
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
                    price = bars.df['close'].iloc[-1]
                    logger.debug(f"Price for {symbol} from Alpaca: {price}")
                    return price
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
    def __init__(self, bot: FreeDataTradingBot, db: Database, config: Dict):
        self.bot = bot
        self.db = db
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
        rsis = {}

        for symbol in self.symbols:
            try:
                stock = yf.Ticker(symbol)
                hist = stock.history(period='1d', interval='1m')
                if hist.empty:
                    logger.warning(f"No price data for {symbol}")
                    signals[symbol] = 'hold'
                    rsis[symbol] = 50.0
                    continue
                prices = hist['Close'].tolist()
            except Exception as e:
                logger.warning(f"Failed to fetch prices for {symbol}: {e}")
                signals[symbol] = 'hold'
                rsis[symbol] = 50.0
                continue

            rsi = self.calculate_rsi(prices)
            rsis[symbol] = rsi
            logger.info(f"{symbol} RSI: {rsi}")

            if rsi > self.overbought and symbol in positions:
                signals[symbol] = 'sell'
            elif rsi < self.oversold and symbol not in positions and len(positions) < self.max_positions:
                signals[symbol] = 'buy'
            else:
                signals[symbol] = 'hold'

        # Log all trade signals to DB with RSI values
        self.db.add_trade_signals(signals, rsis)

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

    DB_URL = "mysql+pymysql://trading_user:your_password@localhost:3306/trading_bot"

    # Initialize database connection
    db = Database(DB_URL)

    bot = FreeDataTradingBot(ALPACA_API_KEY, ALPACA_API_SECRET, paper=PAPER_TRADING)
    strategy = RSIStrategy(bot, db, config)

    print_startup_banner()

    try:
        while True:
            signals = strategy.generate_signals()
            print_signals(signals)

            positions = bot.get_positions()
            orders_to_add = []

            for symbol, signal in signals.items():
                if signal == 'buy':
                    qty = 1  # Could be dynamic based on risk_pct and buying power
                    success = bot.submit_order(symbol, qty, 'buy')
                    status = 'submitted' if success else 'failed'
                    orders_to_add.append({'symbol': symbol, 'side': 'buy', 'qty': qty, 'status': status})
                elif signal == 'sell' and symbol in positions:
                    qty = positions[symbol]
                    success = bot.submit_order(symbol, qty, 'sell')
                    status = 'submitted' if success else 'failed'
                    orders_to_add.append({'symbol': symbol, 'side': 'sell', 'qty': qty, 'status': status})

            # Log all orders to DB once per cycle
            if orders_to_add:
                db.add_orders(orders_to_add)

            time.sleep(60)  # Wait 1 minute before next cycle

    except KeyboardInterrupt:
        console.print("\n[bold red]Trading bot stopped by user.[/bold red]")


if __name__ == '__main__':
    main()



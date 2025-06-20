import os
import sys
import time
import yaml
from logs.utils.logging_config import setup_logging
from logs.API.alpaca_client import AlpacaClient
from logs.strategy.momentum import MomentumStrategy
from logs.data.db_models import init_db
from logs.data.queries import log_trade, update_trade, get_open_trades

PROJECT_ROOT = "/Users/anjuloh/PycharmProjects/Algorithmic-trading-bot-"

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def load_config():
    config_path = os.path.join(PROJECT_ROOT, 'config', 'config.yaml')
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def main():
    logger = setup_logging()

    try:
        config = load_config()
    except FileNotFoundError as e:
        logger.error(f"Fatal error loading config: {e}")
        return

    db_session = None
    try:
        db_session = init_db(config_path=os.path.join(PROJECT_ROOT, 'config', 'config.yaml'))

        client = AlpacaClient(config_path=os.path.join(PROJECT_ROOT, 'config', 'config.yaml'))
        strategy = MomentumStrategy(client, config)

        logger.info("Starting trading bot...")

        while True:
            try:
                trades = strategy.execute()
                for trade in trades:
                    trade_id = log_trade(
                        db_session,
                        trade['symbol'],
                        trade['price'],
                        trade['quantity'],
                        'momentum'
                    )
                    logger.info(f"Logged trade {trade_id}: {trade}")

                manage_open_positions(db_session, client)
                time.sleep(900)

            except KeyboardInterrupt:
                logger.info("Shutting down...")
                break
            except Exception as e:
                logger.error(f"Error during trading loop: {e}")
                time.sleep(60)

    except Exception as e:
        logger.error(f"Failed to initialize database or Alpaca client: {e}")

    finally:
        if db_session:
            db_session.close()

def manage_open_positions(session, client):
    open_trades = get_open_trades(session)
    positions = {p.symbol: p for p in client.get_positions()}

    for trade in open_trades:
        if trade.symbol in positions:
            position = positions[trade.symbol]
            current_price = float(position.current_price)
            pnl = (current_price - trade.entry_price) * trade.quantity

            if current_price <= trade.entry_price * 0.98 or current_price >= trade.entry_price * 1.04:
                if client.close_position(trade.symbol):
                    update_trade(session, trade.id, current_price, pnl)

if __name__ == "__main__":
    main()

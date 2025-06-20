import os
import sys
import time
from datetime import datetime, timedelta

# Fix project root to one level above logs/
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from logs.config.logging_config import setup_logging
    from logs.API.alpaca_client import AlpacaClient
    from logs.strategy.momentum import MomentumStrategy
    from logs.data.db_models import init_db
    from logs.data.queries import log_trade, update_trade, get_open_trades
except ImportError as e:
    print(f"Fatal Import Error: {e}")
    print(f"Current sys.path: {sys.path}")
    print(f"PROJECT_ROOT: {PROJECT_ROOT}")
    raise


def main():
    logger = setup_logging()
    db_session = None  # Initialize early

    # Build config path early (relative to PROJECT_ROOT)
    config_path = os.path.join(PROJECT_ROOT, 'config', 'config.yaml')

    try:
        # Pass config_path to init_db so it can open config.yaml
        db_session = init_db(config_path)

        client = AlpacaClient(config_path)
        strategy = MomentumStrategy(client, config_path)

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
                time.sleep(900)  # Sleep for 15 minutes

            except KeyboardInterrupt:
                logger.info("Shutting down...")
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                time.sleep(60)  # Sleep for 1 minute before retry

    except FileNotFoundError as e:
        logger.error(f"Database connection failed: {e}")
        # Handle or exit program as needed

    finally:
        if db_session:
            db_session.close()


def manage_open_positions(session, client):
    """Check and close positions based on exit strategy"""
    open_trades = get_open_trades(session)
    positions = {p.symbol: p for p in client.get_positions()}

    for trade in open_trades:
        if trade.symbol in positions:
            position = positions[trade.symbol]
            current_price = float(position.current_price)
            pnl = (current_price - trade.entry_price) * trade.quantity

            if (current_price <= trade.entry_price * 0.98 or
                    current_price >= trade.entry_price * 1.04):
                if client.close_position(trade.symbol):
                    update_trade(session, trade.id, current_price, pnl)


if __name__ == "__main__":
    main()


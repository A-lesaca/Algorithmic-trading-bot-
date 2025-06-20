import yaml
from config.logging_config import setup_logging
from api.alpaca_client import AlpacaClient
from strategies.momentum import MomentumStrategy
from database.db_models import init_db
from database.queries import log_trade, update_trade
import time
from datetime import datetime, timedelta


def main():
    # Setup logging
    logger = setup_logging()

    try:
        # Initialize database
        db_session = init_db()

        # Load configuration
        config_path = 'config/config.yaml'

        # Initialize Alpaca client
        client = AlpacaClient(config_path)

        # Initialize strategy
        strategy = MomentumStrategy(client, config_path)

        logger.info("Starting trading bot...")

        while True:
            try:
                # Execute strategy
                trades = strategy.execute()

                # Log trades to database
                for trade in trades:
                    trade_id = log_trade(
                        db_session,
                        trade['symbol'],
                        trade['price'],
                        trade['quantity'],
                        'momentum'
                    )
                    logger.info(f"Logged trade {trade_id}: {trade}")

                # Check for open positions to close
                self.manage_open_positions(db_session, client)

                # Sleep until next interval
                time.sleep(900)  # 15 minutes

            except KeyboardInterrupt:
                logger.info("Shutting down trading bot...")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(60)

    finally:
        db_session.close()


def manage_open_positions(session, client):
    """Check open positions and close if conditions are met"""
    open_trades = get_open_trades(session)
    positions = {p.symbol: p for p in client.get_positions()}

    for trade in open_trades:
        if trade.symbol in positions:
            position = positions[trade.symbol]
            current_price = float(position.current_price)
            pnl = (current_price - trade.entry_price) * trade.quantity

            # Simple exit strategy: 2% stop loss or 4% take profit
            if (current_price <= trade.entry_price * 0.98 or
                    current_price >= trade.entry_price * 1.04):
                if client.close_position(trade.symbol):
                    update_trade(session, trade.id, current_price, pnl)


if __name__ == "__main__":
    main()
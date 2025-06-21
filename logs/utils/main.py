import os
import sys
import time
import yaml
import logging

from alpaca_client import AlpacaClient
from db_models import init_db
from momentum import MomentumStrategy

# Define project root and config path
PROJECT_ROOT = "/Users/anjuloh/PycharmProjects/Algorithmic-trading-bot-"
CONFIG_PATH = os.path.join(PROJECT_ROOT, 'config', 'config.yaml')

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def load_config(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    try:
        config = load_config(CONFIG_PATH)
    except FileNotFoundError as e:
        logger.error(f"Fatal error loading config: {e}")
        return

    db_session = None
    try:
        db_url = config['database']['url']
        db_session = init_db(db_url)

        client = AlpacaClient(config_path=CONFIG_PATH)
        strategy = MomentumStrategy(client, config['trading'])

        logger.info("Starting trading bot...")

        while True:
            try:
                trades = strategy.execute()
                for trade in trades:
                    logger.info(f"Executed trade: {trade}")
                    # db_session.add(trade)
                    # db_session.commit()

                time.sleep(60)  # 1 minute for faster testing

            except KeyboardInterrupt:
                logger.info("Shutting down trading bot.")
                break
            except Exception as e:
                logger.exception(f"Error during trading loop: {e}")
                time.sleep(60)

    except Exception as e:
        logger.exception(f"Failed to initialize database or Alpaca client: {e}")

    finally:
        if db_session:
            db_session.close()
            logger.info("Database session closed.")

if __name__ == "__main__":
    main()

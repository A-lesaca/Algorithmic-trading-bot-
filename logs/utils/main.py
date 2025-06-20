import os
import sys
import time
import yaml
import logging

from alpaca_client import AlpacaClient
from db_models import init_db
from momentum import MomentumStrategy

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
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    try:
        config = load_config()
    except FileNotFoundError as e:
        logger.error(f"Fatal error loading config: {e}")
        return

    db_session = None
    try:
        # Pass the DB URL string from config to init_db
        db_url = config['database']['url']
        db_session = init_db(db_url)

        client = AlpacaClient(config_path=os.path.join(PROJECT_ROOT, 'config', 'config.yaml'))
        strategy = MomentumStrategy(client, config)

        logger.info("Starting trading bot...")

        while True:
            try:
                trades = strategy.execute()
                for trade in trades:
                    # Replace this with your DB logging logic if needed
                    logger.info(f"Executed trade: {trade}")

                time.sleep(900)  # Sleep 15 minutes

            except KeyboardInterrupt:
                logger.info("Shutting down trading bot.")
                break
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                time.sleep(60)

    except Exception as e:
        logger.error(f"Failed to initialize database or Alpaca client: {e}")

    finally:
        if db_session:
            db_session.close()

if __name__ == "__main__":
    main()

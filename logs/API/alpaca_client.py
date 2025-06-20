import alpaca_trade_api as tradeapi
import yaml
import os
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class AlpacaClient:
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.api = tradeapi.REST(
            self.config['alpaca']['API_KEY'],
            self.config['alpaca']['SECRET_KEY'],
            base_url=self.config['alpaca']['BASE_URL'],
            api_version='v2'
        )
        self.account = self.api.get_account()
        logger.info(f"Connected to Alpaca. Account status: {self.account.status}")

    def _load_config(self, path: str) -> Dict:
        with open(path) as file:
            return yaml.safe_load(file)

    def get_historical_data(self, symbol: str, timeframe: str, limit: int = 100) -> List[Dict]:
        """Get historical bar data for a symbol"""
        bars = self.api.get_bars(
            symbol,
            tradeapi.TimeFrame.MINUTE if timeframe.endswith('Min') else tradeapi.TimeFrame.DAY,
            limit=limit
        ).df
        return bars.reset_index().to_dict('records')

    def submit_order(self, symbol: str, qty: float, side: str,
                    order_type: str = 'market', time_in_force: str = 'gtc') -> Optional[Dict]:
        """Submit an order"""
        try:
            order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side=side,
                type=order_type,
                time_in_force=time_in_force
            )
            logger.info(f"Order submitted: {order}")
            return order
        except Exception as e:
            logger.error(f"Order failed: {e}")
            return None

    def get_positions(self) -> List[Dict]:
        """Get current positions"""
        return self.api.list_positions()

    def close_position(self, symbol: str) -> bool:
        """Close a position"""
        try:
            self.api.close_position(symbol)
            logger.info(f"Closed position for {symbol}")
            return True
        except Exception as e:
            logger.error(f"Failed to close position: {e}")
            return False
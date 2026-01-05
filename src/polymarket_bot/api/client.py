"""Polymarket API client wrapper."""

import structlog
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

from polymarket_bot.config import settings

logger = structlog.get_logger(__name__)


class PolymarketClient:
    """Wrapper around Polymarket CLOB client with enhanced functionality."""

    def __init__(self) -> None:
        """Initialize the Polymarket client."""
        self.credentials = ApiCreds(
            api_key=settings.polymarket_api_key,
            api_secret=settings.polymarket_secret,
            api_passphrase=settings.polymarket_passphrase,
        )

        self.client = ClobClient(
            host="https://clob.polymarket.com",
            chain_id=settings.polymarket_chain_id,
            key=settings.polymarket_api_key,
            creds=self.credentials,
        )

        logger.info(
            "polymarket_client_initialized",
            chain_id=settings.polymarket_chain_id,
            trading_enabled=settings.enable_trading,
        )

    async def get_markets(self, **kwargs):
        """Get available markets."""
        try:
            markets = self.client.get_markets(**kwargs)
            logger.info("fetched_markets", count=len(markets) if markets else 0)
            return markets
        except Exception as e:
            logger.error("error_fetching_markets", error=str(e))
            raise

    async def get_market(self, condition_id: str):
        """Get specific market details."""
        try:
            market = self.client.get_market(condition_id)
            logger.info("fetched_market", condition_id=condition_id)
            return market
        except Exception as e:
            logger.error("error_fetching_market", condition_id=condition_id, error=str(e))
            raise

    async def get_orderbook(self, token_id: str):
        """Get orderbook for a token."""
        try:
            orderbook = self.client.get_order_book(token_id)
            logger.debug("fetched_orderbook", token_id=token_id)
            return orderbook
        except Exception as e:
            logger.error("error_fetching_orderbook", token_id=token_id, error=str(e))
            raise

    async def place_order(self, order_params: dict):
        """
        Place an order on Polymarket.

        Note: This will only execute if ENABLE_TRADING is True in settings.
        """
        if not settings.enable_trading:
            logger.warning(
                "trading_disabled",
                message="Order not placed - trading is disabled in settings",
                order_params=order_params,
            )
            return {"status": "disabled", "message": "Trading is disabled"}

        try:
            logger.info("placing_order", order_params=order_params)
            result = self.client.create_order(**order_params)
            logger.info("order_placed", result=result)
            return result
        except Exception as e:
            logger.error("error_placing_order", error=str(e), order_params=order_params)
            raise

    async def cancel_order(self, order_id: str):
        """Cancel an existing order."""
        if not settings.enable_trading:
            logger.warning("trading_disabled", message="Cancel not executed")
            return {"status": "disabled", "message": "Trading is disabled"}

        try:
            logger.info("cancelling_order", order_id=order_id)
            result = self.client.cancel(order_id)
            logger.info("order_cancelled", order_id=order_id, result=result)
            return result
        except Exception as e:
            logger.error("error_cancelling_order", order_id=order_id, error=str(e))
            raise

    async def get_positions(self):
        """Get current positions."""
        try:
            positions = self.client.get_positions()
            logger.info("fetched_positions", count=len(positions) if positions else 0)
            return positions
        except Exception as e:
            logger.error("error_fetching_positions", error=str(e))
            raise


# Singleton instance
_client: PolymarketClient | None = None


def get_client() -> PolymarketClient:
    """Get or create the singleton Polymarket client."""
    global _client
    if _client is None:
        _client = PolymarketClient()
    return _client

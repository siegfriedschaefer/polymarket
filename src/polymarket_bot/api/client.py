"""Polymarket API client wrapper."""

from typing import Optional

import structlog
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

from polymarket_bot.config import settings

logger = structlog.get_logger(__name__)


class PolymarketClient:
    """Wrapper around Polymarket CLOB client with enhanced functionality."""

    def __init__(self, enable_portfolio_tracking: bool = True) -> None:
        """
        Initialize the Polymarket client.

        Args:
            enable_portfolio_tracking: If True, enables local portfolio state tracking
        """
        self.credentials = ApiCreds(
            api_key=settings.polymarket_api_key,
            api_secret=settings.polymarket_secret,
            api_passphrase=settings.polymarket_passphrase,
        )

        # Initialize client
        # Private key is required for trading operations
        # For read-only access, credentials are sufficient
        client_kwargs = {
            "host": "https://clob.polymarket.com",
            "chain_id": settings.polymarket_chain_id,
            "creds": self.credentials,
        }

        if settings.polymarket_private_key:
            client_kwargs["key"] = settings.polymarket_private_key

        self.client = ClobClient(**client_kwargs)

        # Portfolio tracking setup
        self.portfolio_tracking_enabled = enable_portfolio_tracking
        self._portfolio_id: Optional[int] = None

        if enable_portfolio_tracking:
            try:
                from polymarket_bot.portfolio import PortfolioService, MarketType, init_db

                # Initialize database
                init_db()

                # Get or create portfolio for this account
                with PortfolioService() as ps:
                    portfolio = ps.ensure_portfolio(
                        name="polymarket_main",
                        market_type=MarketType.PREDICTION,
                        exchange="polymarket",
                        wallet_address=settings.polymarket_private_key[:10] + "..." if settings.polymarket_private_key else None,
                    )
                    self._portfolio_id = portfolio.id

                logger.info("portfolio_tracking_enabled", portfolio_id=self._portfolio_id)
            except Exception as e:
                logger.warning("portfolio_tracking_init_failed", error=str(e))
                self.portfolio_tracking_enabled = False

        logger.info(
            "polymarket_client_initialized",
            chain_id=settings.polymarket_chain_id,
            trading_enabled=settings.enable_trading,
            has_private_key=bool(settings.polymarket_private_key),
            portfolio_tracking=self.portfolio_tracking_enabled,
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
        """
        Get current positions from local portfolio database.

        This returns positions tracked in our own database, not from Polymarket API.
        To sync positions with actual Polymarket state, use sync_positions() or
        record trades via place_order().

        Returns:
            Portfolio summary with all open positions
        """
        if not self.portfolio_tracking_enabled:
            logger.warning("portfolio_tracking_disabled")
            return {"error": "Portfolio tracking is not enabled"}

        try:
            from polymarket_bot.portfolio import PortfolioService
            from polymarket_bot.portfolio.models import Portfolio

            with PortfolioService() as ps:
                portfolio = ps.db.query(Portfolio).filter(Portfolio.id == self._portfolio_id).first()
                if not portfolio:
                    logger.error("portfolio_not_found", portfolio_id=self._portfolio_id)
                    return {"error": "Portfolio not found"}

                summary = ps.get_portfolio_summary(portfolio)
                logger.info(
                    "fetched_positions",
                    count=summary.get("open_positions_count", 0),
                    total_value=summary.get("total_value", 0),
                )
                return summary

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

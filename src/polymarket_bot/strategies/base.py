"""Base strategy class for implementing trading strategies."""

from abc import ABC, abstractmethod
from typing import Any
import structlog

from polymarket_bot.api.client import PolymarketClient

logger = structlog.get_logger(__name__)


class BaseStrategy(ABC):
    """Base class for all trading strategies."""

    def __init__(self, client: PolymarketClient, name: str = "BaseStrategy"):
        """Initialize the strategy."""
        self.client = client
        self.name = name
        logger.info("strategy_initialized", strategy=self.name)

    @abstractmethod
    async def analyze(self) -> dict[str, Any]:
        """
        Analyze markets and generate trading signals.

        Returns:
            dict: Analysis results with potential trading opportunities
        """
        pass

    @abstractmethod
    async def execute(self, signals: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Execute trades based on signals.

        Args:
            signals: Trading signals from analyze()

        Returns:
            list: List of executed orders
        """
        pass

    async def run(self) -> dict[str, Any]:
        """Run the complete strategy cycle: analyze and execute."""
        logger.info("strategy_run_started", strategy=self.name)

        try:
            signals = await self.analyze()
            logger.info("analysis_complete", strategy=self.name, signals=signals)

            if signals:
                orders = await self.execute(signals)
                logger.info(
                    "execution_complete",
                    strategy=self.name,
                    orders_count=len(orders)
                )
                return {"status": "success", "signals": signals, "orders": orders}
            else:
                logger.info("no_signals_generated", strategy=self.name)
                return {"status": "no_action", "signals": signals, "orders": []}

        except Exception as e:
            logger.error("strategy_run_failed", strategy=self.name, error=str(e))
            return {"status": "error", "error": str(e)}

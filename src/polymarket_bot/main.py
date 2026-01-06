"""Main application entry point."""

import asyncio
import signal
import sys

import structlog

from polymarket_bot.api.client import get_client
from polymarket_bot.config import settings
from polymarket_bot.strategies.example import ExampleStrategy
from polymarket_bot.utils.logging import setup_logging

logger = structlog.get_logger(__name__)


class Application:
    """Main application controller."""

    def __init__(self):
        """Initialize the application."""
        self.running = False
        self.client = None
        self.strategy = None

    async def startup(self) -> None:
        """Perform startup tasks."""
        logger.info(
            "application_startup",
            environment=settings.environment,
            trading_enabled=settings.enable_trading,
        )

        self.client = get_client()
        self.strategy = ExampleStrategy(self.client)

        logger.info("application_ready")

    async def shutdown(self) -> None:
        """Perform cleanup tasks."""
        logger.info("application_shutdown")
        self.running = False

    async def run_once(self) -> None:
        """Run the strategy once."""
        if self.strategy:
            result = await self.strategy.run()
            logger.info("strategy_execution_complete", result=result)

    async def run_loop(self, interval: int = 60) -> None:
        """
        Run the strategy in a loop.

        Args:
            interval: Seconds between strategy executions
        """
        self.running = True
        logger.info("starting_main_loop", interval=interval)

        while self.running:
            try:
                await self.run_once()
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error("loop_error", error=str(e))
                await asyncio.sleep(interval)

    def handle_shutdown(self, signum, frame) -> None:
        """Handle shutdown signals."""
        logger.info("shutdown_signal_received", signal=signum)
        self.running = False


async def main() -> None:
    """Main entry point."""
    setup_logging()

    app = Application()

    signal.signal(signal.SIGINT, app.handle_shutdown)
    signal.signal(signal.SIGTERM, app.handle_shutdown)

    try:
        await app.startup()

        await app.run_once()

    except Exception as e:
        logger.error("application_error", error=str(e))
        sys.exit(1)
    finally:
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())

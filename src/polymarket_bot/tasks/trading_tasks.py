"""Celery tasks for trading operations."""

import asyncio
import structlog

from polymarket_bot.tasks.celery_app import celery_app
from polymarket_bot.api.client import get_client
from polymarket_bot.strategies.example import ExampleStrategy

logger = structlog.get_logger(__name__)


@celery_app.task(name="polymarket_bot.tasks.trading_tasks.run_strategy")
def run_strategy() -> dict:
    """
    Run the trading strategy.

    This task executes the main trading logic on a schedule.
    """
    logger.info("celery_task_started", task="run_strategy")

    try:
        client = get_client()
        strategy = ExampleStrategy(client)

        result = asyncio.run(strategy.run())

        logger.info("celery_task_completed", task="run_strategy", result=result)
        return result

    except Exception as e:
        logger.error("celery_task_failed", task="run_strategy", error=str(e))
        raise


@celery_app.task(name="polymarket_bot.tasks.trading_tasks.update_positions")
def update_positions() -> dict:
    """
    Update and monitor current positions.

    This task fetches current positions and can trigger alerts or actions.
    """
    logger.info("celery_task_started", task="update_positions")

    try:
        client = get_client()

        positions = asyncio.run(client.get_positions())

        logger.info(
            "celery_task_completed",
            task="update_positions",
            positions_count=len(positions) if positions else 0
        )

        return {
            "status": "success",
            "positions_count": len(positions) if positions else 0,
            "positions": positions
        }

    except Exception as e:
        logger.error("celery_task_failed", task="update_positions", error=str(e))
        raise


@celery_app.task(name="polymarket_bot.tasks.trading_tasks.analyze_market")
def analyze_market(condition_id: str) -> dict:
    """
    Analyze a specific market.

    Args:
        condition_id: The market condition ID to analyze
    """
    logger.info("celery_task_started", task="analyze_market", condition_id=condition_id)

    try:
        client = get_client()

        market = asyncio.run(client.get_market(condition_id))

        logger.info(
            "celery_task_completed",
            task="analyze_market",
            condition_id=condition_id
        )

        return {"status": "success", "market": market}

    except Exception as e:
        logger.error(
            "celery_task_failed",
            task="analyze_market",
            condition_id=condition_id,
            error=str(e)
        )
        raise

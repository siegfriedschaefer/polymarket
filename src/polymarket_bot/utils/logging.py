"""Logging configuration using structlog."""

import sys
import logging
from pathlib import Path
import structlog
from structlog.typing import EventDict, WrappedLogger

from polymarket_bot.config import settings


def add_app_context(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Add application context to log entries."""
    event_dict["environment"] = settings.environment
    return event_dict


def setup_logging() -> None:
    """Configure structured logging for the application."""
    log_file = Path(settings.log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(getattr(logging, settings.log_level.upper()))

    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        add_app_context,
    ]

    if settings.debug:
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    else:
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

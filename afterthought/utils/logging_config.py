"""Logging configuration for AfterThought."""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    log_file: Optional[Path] = None,
    level: int = logging.INFO,
    verbose: bool = False,
) -> logging.Logger:
    """
    Setup logging configuration for AfterThought.

    Args:
        log_file: Optional path to log file (default: ~/.afterthought/afterthought.log)
        level: Logging level (default: INFO)
        verbose: Enable verbose (DEBUG) logging

    Returns:
        Configured logger instance
    """
    if verbose:
        level = logging.DEBUG

    # Create logger
    logger = logging.getLogger("afterthought")
    logger.setLevel(level)

    # Remove existing handlers
    logger.handlers.clear()

    # Console handler (INFO and above)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO if not verbose else logging.DEBUG)
    console_formatter = logging.Formatter(
        "%(levelname)s: %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (DEBUG and above)
    if log_file is None:
        log_file = Path.home() / ".afterthought" / "afterthought.log"

    # Ensure log directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        # If file logging fails, just log to console
        logger.warning(f"Could not setup file logging: {e}")

    return logger


def get_logger(name: str = "afterthought") -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (default: "afterthought")

    Returns:
        Logger instance
    """
    return logging.getLogger(name)

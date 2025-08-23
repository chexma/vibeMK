"""
Logging configuration for vibeMK
"""

import logging
import os
import sys
from typing import List, Optional


def setup_logging(level: Optional[str] = None, debug: bool = False) -> None:
    """Setup logging configuration with optional file logging"""

    # Determine log level
    if debug:
        log_level = logging.DEBUG
    elif level:
        log_level = getattr(logging, level.upper(), logging.INFO)
    else:
        log_level = logging.INFO

    # Setup log handlers
    handlers: List[logging.Handler] = []

    # Always add stderr handler for console output
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    handlers.append(console_handler)

    # Add file handler if LOGFILE environment variable is set
    logfile = os.environ.get("LOGFILE")
    if logfile:
        try:
            # Ensure log directory exists
            log_dir = os.path.dirname(logfile)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)

            file_handler = logging.FileHandler(logfile, mode="a", encoding="utf-8")
            file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
            handlers.append(file_handler)

            # Log to console that file logging is enabled
            console_handler.emit(
                logging.LogRecord(
                    name="vibeMK.logging",
                    level=logging.INFO,
                    pathname="",
                    lineno=0,
                    msg=f"File logging enabled: {logfile}",
                    args=(),
                    exc_info=None,
                )
            )
        except Exception as e:
            # If file logging fails, log error to console and continue
            console_handler.emit(
                logging.LogRecord(
                    name="vibeMK.logging",
                    level=logging.ERROR,
                    pathname="",
                    lineno=0,
                    msg=f"Failed to setup file logging ({logfile}): {e}",
                    args=(),
                    exc_info=None,
                )
            )

    # Configure root logger with all handlers
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
        force=True,  # Force reconfiguration if already configured
    )

    # Suppress urllib3 debug logs unless in debug mode
    if not debug:
        logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get logger for specific module"""
    return logging.getLogger(name)

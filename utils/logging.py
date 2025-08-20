"""
Logging configuration for vibeMK
"""

import logging
import sys
from typing import Optional


def setup_logging(level: Optional[str] = None, debug: bool = False) -> None:
    """Setup logging configuration"""
    
    # Determine log level
    if debug:
        log_level = logging.DEBUG
    elif level:
        log_level = getattr(logging, level.upper(), logging.INFO)
    else:
        log_level = logging.INFO
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stderr)
        ]
    )
    
    # Suppress urllib3 debug logs unless in debug mode
    if not debug:
        logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get logger for specific module"""
    return logging.getLogger(name)
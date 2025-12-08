"""Shared logging configuration for all agents."""

import logging
import sys
from typing import Literal


def setup_logging(
    agent_name: str,
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO",
) -> logging.Logger:
    """
    Set up logging for an agent with proper formatting for Docker.
    
    Logs are written to stdout/stderr to be captured by Docker.
    
    Args:
        agent_name: Name of the agent for the logger
        level: Logging level
        
    Returns:
        Configured logger instance
    """
    # Create a logger for the agent
    logger = logging.getLogger(agent_name)
    logger.setLevel(getattr(logging, level))
    
    # Avoid duplicate handlers if already configured
    if logger.handlers:
        return logger
    
    # Create console handler that writes to stdout
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level))
    
    # Create a formatter with timestamp, level, agent name, and message
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    # Also configure the root logger to capture third-party library logs
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        root_handler = logging.StreamHandler(sys.stdout)
        root_handler.setLevel(logging.WARNING)
        root_handler.setFormatter(formatter)
        root_logger.addHandler(root_handler)
    
    return logger

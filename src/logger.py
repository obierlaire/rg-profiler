"""
Logging configuration for RG Profiler

This module configures the Python standard logging library for use throughout the project,
maintaining the emoji indicators from the previous print-based logging approach.
"""
import logging
import os
import sys
from pathlib import Path

# Create custom log levels
TRACE = 5  # More detailed than DEBUG

# Create logger
logger = logging.getLogger("rg-profiler")

# Default log format with emojis
DEFAULT_FORMAT = "%(message)s"
DETAILED_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

class EmojiFormatter(logging.Formatter):
    """Custom formatter that adds emojis to log messages based on level"""
    
    # Define emoji prefixes for different log levels
    EMOJIS = {
        logging.CRITICAL: "💥 ",  # Critical failures
        logging.ERROR: "❌ ",     # Errors
        logging.WARNING: "⚠️ ",   # Warnings
        logging.INFO: "",         # Regular info (emoji will be in the message)
        logging.DEBUG: "🔍 ",     # Debug info
        TRACE: "🔬 "              # Trace level (very detailed)
    }
    
    def format(self, record):
        # Skip adding emoji if already present in message
        emoji_prefixes = list(self.EMOJIS.values())
        has_emoji = any(record.msg.startswith(prefix.strip()) for prefix in emoji_prefixes if prefix.strip())
        
        # Format the message
        message = super().format(record)
        
        # Add emoji prefix if not already present
        if not has_emoji and record.levelno in self.EMOJIS:
            return f"{self.EMOJIS[record.levelno]}{message}"
        
        return message


def setup_logging(
    console_level=logging.INFO,
    file_level=None,
    log_file=None,
    detailed_format=False
):
    """
    Set up logging configuration
    
    Args:
        console_level: Logging level for console output
        file_level: Logging level for file output (None to disable file logging)
        log_file: Path to log file (None for default location)
        detailed_format: Whether to use detailed format with timestamps
    """
    # Clear any existing handlers
    logger.handlers = []
    
    # Set global log level (used for filtering)
    logger.setLevel(logging.DEBUG if console_level <= logging.DEBUG else console_level)
    
    # Configure format based on preference
    log_format = DETAILED_FORMAT if detailed_format else DEFAULT_FORMAT
    formatter = EmojiFormatter(log_format)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if enabled)
    if file_level is not None and log_file is not None:
        # Ensure directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
            
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(file_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Add custom logging methods for convenience
    add_custom_log_levels()


def add_custom_log_levels():
    """Add custom log levels and convenience methods to the logger"""
    # Add trace level
    logging.addLevelName(TRACE, "TRACE")
    
    # Add convenience methods for each emoji type
    def success(self, message, *args, **kwargs):
        """Log a success message with checkmark emoji"""
        self.info(f"✅ {message}", *args, **kwargs)
    
    def error(self, message, *args, **kwargs):
        """Log an error message"""
        self.error(message, *args, **kwargs)
    
    def warning(self, message, *args, **kwargs):
        """Log a warning message"""
        self.warning(message, *args, **kwargs)
    
    def start(self, message, *args, **kwargs):
        """Log a startup/progress message with rocket emoji"""
        self.info(f"🚀 {message}", *args, **kwargs)
    
    def finish(self, message, *args, **kwargs):
        """Log a completion message with checkmark emoji"""
        self.info(f"✅ {message}", *args, **kwargs)
    
    def trace(self, message, *args, **kwargs):
        """Log a trace message (very detailed level)"""
        if self.isEnabledFor(TRACE):
            self._log(TRACE, message, args, **kwargs)
    
    # Add custom methods to logger
    logging.Logger.success = success
    logging.Logger.start = start
    logging.Logger.finish = finish
    logging.Logger.trace = trace


# Set up default logging configuration
setup_logging()

__all__ = ["logger", "setup_logging"]
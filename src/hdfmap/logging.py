"""
Create logging objects and functions

See https://docs.python.org/3/howto/logging.html
"""

import logging

# Setup config - doesn't work properly without this
logging.basicConfig()   # setup logging

LEVELS = {
    'notset': logging.NOTSET,
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL
}


def create_logger(name: str) -> logging.Logger:
    """Create new logger instance"""
    return logging.getLogger(name)


def set_logging_levels(level: str | int):
    """
    Set logging level of all loggers
    Logging Levels
        'notset'   |  0
        'debug'    |  10
        'info'     |  20
        'warning'  |  30
        'error'    |  40
        'critical' |  50
    :param level: str level name or int level
    :return: None
    """
    try:
        level = level.lower()
        level = LEVELS[level]
    except AttributeError:
        level = int(level)

    logging_logger = logging.getLogger(__name__)
    for logger in [logging.getLogger(name) for name in logging.root.manager.loggerDict]:
        logger.setLevel(level)
    logging_logger.info(f"Logging level set to {level}")

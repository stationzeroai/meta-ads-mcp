import logging

from .config import config

logging.basicConfig(level=config.LOG_LEVEL)

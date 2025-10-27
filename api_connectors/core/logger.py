import logging
import os
from dotenv import load_dotenv

# charge immédiatement le .env
load_dotenv()

def get_logger(name: str) -> logging.Logger:
    """Configure un logger standardisé avec un niveau selon l'environnement"""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(log_level)

        # log initial pour vérifier la config
        logger.debug(f"Logger initialized for '{name}' with level={log_level}")
    return logger
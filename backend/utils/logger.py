import logging
import sys

def configure_logging(level: int = logging.INFO) -> None:
    logger = logging.getLogger()
    if logger.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)


"""Setting up a file logger for recording simple logs.

Returns a lazily initialized module logger that writes to a file
`{logging_dir}/{filename}` in the message format only, without metadata.
"""
import os
from logging import FileHandler, Formatter, getLogger, INFO
from src.app.core.config import settings

def get_logs_writer_logger(logging_dir=settings.LOG_PATH, filename='logs.log'):
    os.makedirs(logging_dir, exist_ok=True)
    log_path = os.path.join(logging_dir, filename)

    logger = getLogger(__name__)

    if logger.handlers:
        return logger

    logger.setLevel(INFO)
    logger.propagate = False

    handler = FileHandler(log_path, mode="a", encoding="utf-8", delay=True)
    handler.setFormatter(Formatter("%(message)s"))
    logger.addHandler(handler)

    return logger
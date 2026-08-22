import logging
import sys

from loguru import logger


class InterceptHandler(logging.Handler):
    """
    Перехватывает стандартные логи Python (например, от aiogram или asyncio)
    и перенаправляет их в Loguru.
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame.f_back and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logger(level: str = "INFO") -> None:
    """
    Настраивает вывод логов через Loguru и перехват стандартного logging.
    """
    logger.remove()

    logger.add(
        sys.stdout,
        level=level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)


__all__ = ["logger", "setup_logger"]

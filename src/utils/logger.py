# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 日誌配置
優先使用 Loguru，未安裝時降級為標準 logging
"""
import sys
import logging
from pathlib import Path

from src.config import LOG_DIR, LOG_LEVEL

try:
    from loguru import logger as _loguru_logger
    LOGURU_AVAILABLE = True
except ImportError:
    LOGURU_AVAILABLE = False


class _FallbackLogger:
    """Loguru 未安裝時的降級 logger，提供相容介面"""

    def __init__(self):
        self._logger = logging.getLogger("parksmart")
        self._logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(message)s",
                datefmt="%H:%M:%S",
            ))
            self._logger.addHandler(handler)

    def info(self, msg, *args, **kwargs):
        self._logger.info(msg)

    def warning(self, msg, *args, **kwargs):
        self._logger.warning(msg)

    def error(self, msg, *args, **kwargs):
        self._logger.error(msg)

    def debug(self, msg, *args, **kwargs):
        self._logger.debug(msg)

    def add(self, *args, **kwargs):
        pass  # 降級模式不支援文件輸出

    def remove(self, *args, **kwargs):
        pass


def setup_logger(name: str = "parksmart"):
    """配置日誌，返回 logger"""
    if LOGURU_AVAILABLE:
        _loguru_logger.remove()
        _loguru_logger.add(
            sys.stderr,
            level=LOG_LEVEL,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | "
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                   "<level>{message}</level>",
            colorize=True,
        )
        # 文件輸出
        try:
            log_file = LOG_DIR / f"{name}_{{time:YYYY-MM-DD}}.log"
            _loguru_logger.add(
                str(log_file),
                level="DEBUG",
                rotation="00:00",
                retention="30 days",
                compression="zip",
                encoding="utf-8",
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            )
        except Exception:
            pass
        return _loguru_logger
    else:
        return _FallbackLogger()


# 預設 logger 實例
log = setup_logger()

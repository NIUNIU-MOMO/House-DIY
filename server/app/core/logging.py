"""
@Author NIUNIU_AI
@Date 2026/05/23 16:00
@Version 1.0
@Description 应用日志配置
"""

import logging
import sys

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
QUIET_LOGGERS = ("httpx", "httpcore", "chromadb", "watchdog", "urllib3")


def setup_logging(level: int = logging.INFO) -> None:
    """
    初始化全局日志格式与级别

    @param level 根日志级别
    """
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(level=level, format=LOG_FORMAT, stream=sys.stdout)
    root.setLevel(level)
    for name in QUIET_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    获取命名 logger

    @param name logger 名称
    @return Logger 实例
    """
    return logging.getLogger(name)

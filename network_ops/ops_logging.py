"""network_ops 전용 파일 로깅 — 모든 접속 시도·에러를 network_ops.log에 남깁니다."""

from __future__ import annotations

import logging
from pathlib import Path

_LOG_PATH: Path | None = None
_CONFIGURED = False


def init_network_ops_logging(base_dir: Path) -> logging.Logger:
    """
    WHY: backup_errors.log만으로는 ‘시도’ 이력이 부족해, 단일 파일에 시간순으로 남깁니다.
    """
    global _CONFIGURED, _LOG_PATH
    log_path = base_dir / "network_ops.log"
    _LOG_PATH = log_path

    logger = logging.getLogger("network_ops")
    if _CONFIGURED:
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    fh = logging.FileHandler(log_path, encoding="utf-8", mode="a")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(sh)
    _CONFIGURED = True
    return logger


def get_ops_logger() -> logging.Logger:
    return logging.getLogger("network_ops")

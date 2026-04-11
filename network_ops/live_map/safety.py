"""
파괴적 원격 명령 차단 및 관리자 2차 확인.
WHY: reboot/delete 등은 오탐·실수로 인프라에 치명적이므로 실행 전 이중 확인합니다.
"""

from __future__ import annotations

import getpass
import os
import re
from typing import Pattern

# 대소문자 무시 매칭용 패턴 (명령어 일부만 있어도 위험으로 분류)
_DESTRUCTIVE_PATTERNS: tuple[Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\breboot\b",
        r"\bshutdown\b",
        r"\bhalt\b",
        r"\bpoweroff\b",
        r"\binit\s+0\b",
        r"\binit\s+6\b",
        r"\bdelete\b",
        r"\berase\b",
        r"\bwrite\s+erase\b",
        r"\bformat\b",
        r"\brm\s+-rf\b",
        r"\brm\s+/\b",
        r"\bdrop\s+database\b",
        r"\bmkfs\b",
        r"\bdd\s+if=",
        r":\s*!\s*format",  # 일부 장비
    )
)


def is_destructive_command(command: str) -> bool:
    """명령 문자열에 파괴적 키워드가 포함되는지 검사합니다."""
    text = (command or "").strip()
    if not text:
        return False
    return any(p.search(text) for p in _DESTRUCTIVE_PATTERNS)


def admin_two_step_confirm() -> bool:
    """
    관리자 2차 확인.
    1) 환경변수 LIVE_MAP_DESTRUCTIVE_PHRASE(기본 CONFIRM_DESTRUCTIVE)를 정확히 입력
    2) LIVE_MAP_ADMIN_PIN 이 있으면 PIN 일치, 없으면 동일 문구를 한 번 더 입력
    """
    phrase = (os.environ.get("LIVE_MAP_DESTRUCTIVE_PHRASE") or "CONFIRM_DESTRUCTIVE").strip()
    print("\n*** 위험: 파괴적·복구 어려운 명령으로 분류되었습니다. ***")
    print(f"계속하려면 다음 문구를 한 글자도 틀리지 않고 입력하세요:\n  {phrase}\n")
    first = input("1차 확인> ").strip()
    if first != phrase:
        print("1차 확인 불일치 — 취소합니다.")
        return False

    admin_pin = (os.environ.get("LIVE_MAP_ADMIN_PIN") or "").strip()
    if admin_pin:
        second = getpass.getpass("2차 확인(관리자 PIN)> ").strip()
        if second != admin_pin:
            print("PIN 불일치 — 취소합니다.")
            return False
    else:
        print("LIVE_MAP_ADMIN_PIN 미설정 — 동일 문구로 2차 확인합니다.")
        second = input("2차 확인> ").strip()
        if second != phrase:
            print("2차 확인 불일치 — 취소합니다.")
            return False

    return True

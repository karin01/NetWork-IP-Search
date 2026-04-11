"""장비별 이전 설정 백업 파일과의 차이 탐지."""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import Optional, Tuple


def read_prior_config_text(
    network_ops_dir: Path,
    device_ip: str,
    device_type: str,
    output_file: Path,
) -> Optional[str]:
    """
    이번에 덮어쓰기 전 ‘직전’ 설정 텍스트.
    같은 날짜 파일이 이미 있으면 그 내용, 없으면 가장 최근 다른 날짜 백업.
    """
    pattern = f"{device_ip}_{device_type}.cfg"
    backups_root = network_ops_dir / "backups"
    if not backups_root.is_dir():
        return None
    paths = list(backups_root.glob(f"*/{pattern}"))
    if not paths:
        return None
    paths.sort(key=lambda p: p.stat().st_mtime_ns, reverse=True)
    newest = paths[0]
    out_res = output_file.resolve()
    if output_file.is_file() and newest.resolve() == out_res:
        return output_file.read_text(encoding="utf-8", errors="ignore")
    for p in paths:
        if p.resolve() != out_res:
            return p.read_text(encoding="utf-8", errors="ignore")
    return None


def diff_summary(prev_text: str, new_text: str, max_lines: int = 80) -> Tuple[bool, str]:
    """
    내용이 동일하면 (False, "").
    다르면 (True, unified diff 앞부분 문자열).
    """
    if prev_text == new_text:
        return False, ""
    prev_lines = prev_text.splitlines()
    new_lines = new_text.splitlines()
    diff = difflib.unified_diff(
        prev_lines,
        new_lines,
        fromfile="이전",
        tofile="현재",
        lineterm="",
    )
    lines = list(diff)
    if len(lines) > max_lines:
        tail = f"\n... ({len(lines) - max_lines}줄 생략)"
        excerpt = "\n".join(lines[:max_lines]) + tail
    else:
        excerpt = "\n".join(lines)
    return True, excerpt

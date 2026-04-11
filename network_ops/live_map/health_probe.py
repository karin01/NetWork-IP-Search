"""Ping 및 TCP 서비스 포트 체크 (OS 공통)."""

from __future__ import annotations

import platform
import socket
import subprocess
from typing import Dict, List


def ping_host(ip_address: str, timeout_ms: int = 800) -> bool:
    """ICMP ping 1회 (Windows/Linux)."""
    try:
        is_windows = platform.system().lower().startswith("win")
        if is_windows:
            cmd = ["ping", "-n", "1", "-w", str(timeout_ms), ip_address]
        else:
            sec = max(1, int(timeout_ms / 1000))
            cmd = ["ping", "-c", "1", "-W", str(sec), ip_address]
        r = subprocess.run(cmd, capture_output=True, timeout=timeout_ms / 1000 + 5, check=False)
        return r.returncode == 0
    except Exception:
        return False


def probe_tcp_port(host: str, port: int, timeout_sec: float = 0.5) -> bool:
    """TCP 연결 시도로 포트 개방 여부."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout_sec)
    try:
        return sock.connect_ex((host, int(port))) == 0
    except OSError:
        return False
    finally:
        sock.close()


def check_service_ports(host: str, ports: List[int]) -> Dict[str, bool]:
    """포트 번호별 열림 여부."""
    out: Dict[str, bool] = {}
    for p in ports:
        try:
            pi = int(p)
        except (TypeError, ValueError):
            continue
        out[str(pi)] = probe_tcp_port(host, pi)
    return out

"""hosts.yaml 인벤토리 로드."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml


def load_inventory(path: Path) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    WHY: 서버(WinRM/SSH)와 네트워크(Netmiko)를 구분해 로드합니다.
    반환: (servers, network_devices)
    """
    if not path.is_file():
        raise FileNotFoundError(f"인벤토리 파일이 없습니다: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    servers = raw.get("servers") or []
    network_devices = raw.get("network_devices") or []
    if not isinstance(servers, list):
        raise ValueError("hosts.yaml: servers 는 리스트여야 합니다.")
    if not isinstance(network_devices, list):
        raise ValueError("hosts.yaml: network_devices 는 리스트여야 합니다.")

    for idx, row in enumerate(servers):
        if not isinstance(row, dict) or not row.get("id") or not row.get("hostname"):
            raise ValueError(f"servers[{idx}]: id, hostname 필수")
        ot = (row.get("os_type") or "").lower()
        if ot not in ("linux", "windows"):
            raise ValueError(f"servers[{idx}]: os_type 은 linux 또는 windows")

    for idx, row in enumerate(network_devices):
        if not isinstance(row, dict) or not row.get("id") or not row.get("hostname"):
            raise ValueError(f"network_devices[{idx}]: id, hostname 필수")
        if not row.get("netmiko_device_type"):
            raise ValueError(f"network_devices[{idx}]: netmiko_device_type 필수")

    return servers, network_devices

"""
생존 지도 스캔 파이프라인: Ping·서비스 포트·원격 읽기 전용 명령.
WHY: 장비 수가 많을 수 있어 ThreadPoolExecutor 로 동시 10대 제한 병렬 처리합니다.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .health_probe import check_service_ports, ping_host
from .inventory_loader import load_inventory
from .remote_exec import collect_network_status, collect_server_status

# 동시 접속 상한 (요구사항: 10)
MAX_WORKERS = 10


def _health_tier(ping_ok: bool, ports_ok: bool, remote_ok: bool) -> str:
    """생존 지도 색상용: up(전부) / degraded(일부) / down(icmp 불가)."""
    if not ping_ok:
        return "down"
    if ports_ok and remote_ok:
        return "up"
    return "degraded"


def _scan_server_row(entry: Dict[str, Any]) -> Dict[str, Any]:
    host = entry["hostname"]
    ports_cfg = entry.get("check_ports") or []
    ports = [int(p) for p in ports_cfg if str(p).isdigit()]

    ping_ok = ping_host(host)
    port_results = check_service_ports(host, ports) if ports else {}
    ports_ok = all(port_results.values()) if port_results else ping_ok

    remote_ok = False
    remote_detail = ""
    if ping_ok:
        ok, msg = collect_server_status(entry)
        remote_ok = ok
        remote_detail = msg
    else:
        remote_detail = "ping 실패로 원격 명령 생략"

    tier = _health_tier(ping_ok, ports_ok, remote_ok)
    return {
        "category": "server",
        "id": entry["id"],
        "hostname": host,
        "role": entry.get("role") or "",
        "os_type": entry.get("os_type") or "",
        "ping": ping_ok,
        "ports": port_results,
        "ports_all_open": ports_ok,
        "remote_ok": remote_ok,
        "remote_snippet": remote_detail[:500],
        "health_tier": tier,
        "alive": tier == "up",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def _scan_network_row(entry: Dict[str, Any]) -> Dict[str, Any]:
    host = entry["hostname"]
    ports_cfg = entry.get("check_ports") or [22]
    ports = [int(p) for p in ports_cfg if str(p).isdigit()]

    ping_ok = ping_host(host)
    port_results = check_service_ports(host, ports) if ports else {}
    ports_ok = all(port_results.values()) if port_results else ping_ok

    remote_ok = False
    remote_detail = ""
    if ping_ok:
        ok, msg = collect_network_status(entry)
        remote_ok = ok
        remote_detail = msg
    else:
        remote_detail = "ping 실패로 Netmiko 생략"

    tier = _health_tier(ping_ok, ports_ok, remote_ok)
    return {
        "category": "network",
        "id": entry["id"],
        "hostname": host,
        "role": entry.get("role") or "",
        "device_type": entry.get("netmiko_device_type") or "",
        "ping": ping_ok,
        "ports": port_results,
        "ports_all_open": ports_ok,
        "remote_ok": remote_ok,
        "remote_snippet": remote_detail[:500],
        "health_tier": tier,
        "alive": tier == "up",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def run_live_map_scan(inventory_path: Path) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    인벤토리를 로드한 뒤 서버·네트워크 각 행을 병렬 스캔합니다.
    반환: (server_results, network_results)
    """
    servers, network_devices = load_inventory(inventory_path)

    tasks: List[Tuple[str, Dict[str, Any]]] = []
    for s in servers:
        tasks.append(("server", s))
    for n in network_devices:
        tasks.append(("network", n))

    server_results: List[Dict[str, Any]] = []
    network_results: List[Dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_map = {}
        for kind, row in tasks:
            if kind == "server":
                fut = executor.submit(_scan_server_row, row)
            else:
                fut = executor.submit(_scan_network_row, row)
            future_map[fut] = kind

        for fut in as_completed(future_map):
            kind = future_map[fut]
            try:
                result = fut.result()
            except Exception as e:
                result = {
                    "category": kind,
                    "id": "?",
                    "hostname": "?",
                    "role": "",
                    "os_type": "",
                    "device_type": "",
                    "ping": False,
                    "ports": {},
                    "ports_all_open": False,
                    "remote_ok": False,
                    "remote_snippet": str(e)[:500],
                    "health_tier": "down",
                    "alive": False,
                    "error": str(e),
                    "checked_at": datetime.now(timezone.utc).isoformat(),
                }
            if kind == "server":
                server_results.append(result)
            else:
                network_results.append(result)

    server_results.sort(key=lambda r: r.get("id") or "")
    network_results.sort(key=lambda r: r.get("id") or "")
    return server_results, network_results


def default_inventory_path() -> Path:
    return Path(__file__).resolve().parent / "hosts.yaml"

import ipaddress
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List

from fastapi import FastAPI, Query

try:
    import nmap
except Exception:  # pragma: no cover
    nmap = None

app = FastAPI(title="IP Scan API", version="1.0.0")


def calculate_subnet_info(cidr: str) -> Dict:
    """CIDR 기준 네트워크 대역 정보를 계산합니다."""
    network_obj = ipaddress.ip_network(cidr, strict=False)
    host_count = max(0, network_obj.num_addresses - 2) if network_obj.version == 4 else network_obj.num_addresses
    return {
        "cidr": cidr,
        "network_address": str(network_obj.network_address),
        "broadcast_address": str(network_obj.broadcast_address) if network_obj.version == 4 else "-",
        "netmask": str(network_obj.netmask) if network_obj.version == 4 else "-",
        "prefix_length": network_obj.prefixlen,
        "total_addresses": network_obj.num_addresses,
        "usable_hosts": host_count,
    }


def _resolve_hostname(ip_address: str) -> str:
    try:
        host_name, _, _ = socket.gethostbyaddr(ip_address)
        return host_name
    except Exception:
        return "알 수 없음"


def _ping_host(ip_address: str, timeout_ms: int = 400) -> bool:
    command = ["ping", "-n", "1", "-w", str(timeout_ms), ip_address]
    result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    return result.returncode == 0


def _scan_with_nmap(ip_address: str) -> bool:
    if nmap is None:
        return False
    try:
        scanner = nmap.PortScanner()
        scanner.scan(hosts=ip_address, arguments="-sn -n")
        return ip_address in scanner.all_hosts()
    except Exception:
        return False


def scan_network_hosts(cidr: str) -> Dict:
    network_obj = ipaddress.ip_network(cidr, strict=False)
    ip_list = [str(host_ip) for host_ip in network_obj.hosts()]

    devices: List[Dict] = []
    with ThreadPoolExecutor(max_workers=min(128, max(1, len(ip_list)))) as executor:
        future_map = {executor.submit(_ping_host, ip_address): ip_address for ip_address in ip_list}
        for future in as_completed(future_map):
            ip_address = future_map[future]
            is_online = future.result()
            if not is_online:
                # WHY: ping 실패 장비는 nmap 호스트 디스커버리로 한 번 더 보완 시도합니다.
                is_online = _scan_with_nmap(ip_address)
            status_text = "사용 중" if is_online else "비어 있음"
            devices.append(
                {
                    "ip": ip_address,
                    "status": status_text,
                    "color": "red" if is_online else "green",
                    "hostname": _resolve_hostname(ip_address) if is_online else "-",
                }
            )

    devices.sort(key=lambda row: tuple(int(part) for part in row["ip"].split(".")))
    return {
        "cidr": cidr,
        "last_scan_time": datetime.now().isoformat(timespec="seconds"),
        "devices": devices,
    }


@app.get("/scan")
def scan_endpoint(cidr: str = Query("192.168.1.0/24", description="스캔할 CIDR 대역")):
    return scan_network_hosts(cidr)


@app.get("/subnet/calc")
def subnet_calc_endpoint(cidr: str = Query("192.168.1.0/24", description="계산할 CIDR 대역")):
    return calculate_subnet_info(cidr)

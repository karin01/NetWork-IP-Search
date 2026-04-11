import ipaddress
import platform
import subprocess
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import psutil
from scapy.all import ARP, Ether, srp


# WHY: 오프라인 환경에서도 기본적인 제조사 구분이 가능하도록 대표 OUI를 내장합니다.
OUI_VENDOR_MAP: Dict[str, str] = {
    "00:50:56": "VMware",
    "08:00:27": "Oracle VirtualBox",
    "00:1C:42": "Parallels",
    "B8:27:EB": "Raspberry Pi",
    "DC:A6:32": "Raspberry Pi",
    "3C:5A:B4": "Google",
    "F4:F5:D8": "Google",
    "28:6D:97": "Apple",
    "F0:18:98": "Apple",
    "FC:FB:FB": "Facebook/Meta",
    "00:1A:11": "Google Nest",
    "18:B4:30": "Nest Labs",
    "E4:5F:01": "Samsung",
    "60:57:18": "Xiaomi",
    "50:02:91": "Xiaomi",
    "A4:2B:B0": "TP-Link",
    "C0:25:E9": "TP-Link",
}

COMMON_PORTS: List[int] = [21, 22, 23, 53, 80, 110, 139, 143, 443, 445, 3389, 8080]


def _find_private_ipv4_network() -> Tuple[str, str]:
    """현재 장치의 사설 IPv4와 네트워크 CIDR을 추출합니다."""
    private_network = None
    current_ip = None

    for interface_name, interface_addresses in psutil.net_if_addrs().items():
        for address in interface_addresses:
            if getattr(address, "family", None) != socket.AF_INET:
                continue

            ip_address = address.address
            netmask = address.netmask
            if not ip_address or not netmask:
                continue

            try:
                ip_obj = ipaddress.ip_address(ip_address)
            except ValueError:
                continue

            # WHY: 사설망이 아닌 주소(예: 공인 IP, 루프백)는 LAN 스캔 대상에서 제외합니다.
            if not ip_obj.is_private:
                continue

            network = ipaddress.ip_network(f"{ip_address}/{netmask}", strict=False)
            current_ip = ip_address
            private_network = str(network)
            break

        if private_network:
            break

    if not private_network or not current_ip:
        raise RuntimeError("사설 IPv4 네트워크를 찾지 못했습니다. 네트워크 연결 상태를 확인해주세요.")

    return current_ip, private_network


def _resolve_hostname(ip_address: str) -> str:
    """IP의 호스트명을 안전하게 조회합니다."""
    try:
        hostname, _, _ = socket.gethostbyaddr(ip_address)
        return hostname
    except (socket.herror, socket.gaierror, TimeoutError, OSError):
        return "알 수 없음"


def _resolve_vendor(mac_address: str) -> str:
    """MAC 주소의 OUI(앞 3바이트)로 제조사를 추정합니다."""
    if not mac_address or mac_address == "알 수 없음":
        return "알 수 없음"

    normalized_mac = mac_address.upper().replace("-", ":")
    oui_prefix = ":".join(normalized_mac.split(":")[:3])
    return OUI_VENDOR_MAP.get(oui_prefix, "알 수 없음")


class NetworkScanner:
    """Scapy 기반 장치 스캐너 (연결 상태 추적 포함)."""

    def __init__(self) -> None:
        # WHY: 스캔 사이클 간 상태 비교를 위해 마지막 탐지 시각을 저장합니다.
        self.last_seen_map: Dict[str, datetime] = {}
        self.offline_grace_seconds = 60
        self.scan_history: List[Dict[str, int | str]] = []
        self.max_history_points = 30
        self.last_scan_result: Dict = {}
        self.max_ping_hosts = 254
        self.ping_workers = 64
        self.port_scan_timeout_seconds = 0.2
        self.port_scan_workers = 32
        self.port_scan_cache_seconds = 60
        self.max_port_scan_devices = 30
        self.port_cache_map: Dict[str, Dict] = {}

    def _is_scapy_layer2_unavailable(self, error: Exception) -> bool:
        """Scapy의 L2 스캔 불가 오류인지 판별합니다."""
        message = str(error).lower()
        error_keywords = [
            "winpcap is not installed",
            "npcap",
            "libpcap",
            "layer 2",
            "sniffing and sending packets is not available",
        ]
        return any(keyword in message for keyword in error_keywords)

    def _ping_single_host(self, ip_address: str, timeout_ms: int = 300) -> bool:
        """단일 호스트에 ping을 보내 응답 여부를 확인합니다."""
        try:
            is_windows = platform.system().lower().startswith("win")
            if is_windows:
                command = ["ping", "-n", "1", "-w", str(timeout_ms), ip_address]
            else:
                timeout_seconds = max(1, int(timeout_ms / 1000))
                command = ["ping", "-c", "1", "-W", str(timeout_seconds), ip_address]

            completed = subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            return completed.returncode == 0
        except Exception:
            return False

    def _fallback_ping_scan(self, network_cidr: str, current_ip: str, scanned_at: datetime) -> Tuple[List[Dict], str]:
        """Scapy 사용 불가 시 ping 기반으로 제한 스캔을 수행합니다."""
        network_object = ipaddress.ip_network(network_cidr, strict=False)
        # WHY: 다른 서브넷을 스캔할 때 로컬 IP가 대역 밖이면 자기 자신 제외가 무의미하므로 생략합니다.
        exclude_ip = None
        try:
            if current_ip and ipaddress.ip_address(current_ip) in network_object:
                exclude_ip = current_ip
        except ValueError:
            exclude_ip = None
        candidate_ips = [
            str(host_ip) for host_ip in network_object.hosts() if exclude_ip is None or str(host_ip) != exclude_ip
        ]

        warning_message = ""
        if len(candidate_ips) > self.max_ping_hosts:
            candidate_ips = candidate_ips[: self.max_ping_hosts]
            warning_message = (
                "Npcap/WinPcap 미설치로 ping 기반 제한 스캔으로 전환되었습니다. "
                f"성능 보호를 위해 상위 {self.max_ping_hosts}개 IP만 검사했습니다."
            )
        else:
            warning_message = (
                "Npcap/WinPcap 미설치로 ping 기반 스캔으로 전환되었습니다. "
                "정확한 ARP 스캔을 원하면 Npcap 설치 후 관리자 권한으로 실행해주세요."
            )

        online_devices: List[Dict] = []
        currently_seen_ips = set()

        with ThreadPoolExecutor(max_workers=self.ping_workers) as executor:
            future_by_ip = {
                executor.submit(self._ping_single_host, ip): ip for ip in candidate_ips
            }
            for future in as_completed(future_by_ip):
                ip_address = future_by_ip[future]
                is_online = future.result()
                if not is_online:
                    continue

                currently_seen_ips.add(ip_address)
                self.last_seen_map[ip_address] = scanned_at
                online_devices.append(
                    {
                        "ip": ip_address,
                        "mac": "알 수 없음",
                        "vendor": "알 수 없음",
                        "open_ports": [],
                        "hostname": _resolve_hostname(ip_address),
                        "status": "online",
                        "last_seen": scanned_at.isoformat(timespec="seconds"),
                    }
                )

        return online_devices, warning_message

    def _probe_single_port(self, ip_address: str, port: int) -> bool:
        """TCP 포트 하나에 접속 시도해 개방 여부를 확인합니다."""
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.settimeout(self.port_scan_timeout_seconds)
        try:
            return test_socket.connect_ex((ip_address, port)) == 0
        except OSError:
            return False
        finally:
            test_socket.close()

    def _scan_open_ports(self, ip_address: str, scanned_at: datetime) -> List[int]:
        """주요 포트 목록에서 열린 포트를 수집합니다(캐시 포함)."""
        cached_result = self.port_cache_map.get(ip_address)
        if cached_result:
            checked_at = cached_result.get("checked_at")
            open_ports = cached_result.get("open_ports")
            if isinstance(checked_at, datetime) and isinstance(open_ports, list):
                if (scanned_at - checked_at).total_seconds() <= self.port_scan_cache_seconds:
                    return open_ports

        open_ports: List[int] = []
        with ThreadPoolExecutor(max_workers=self.port_scan_workers) as executor:
            future_by_port = {
                executor.submit(self._probe_single_port, ip_address, port): port for port in COMMON_PORTS
            }
            for future in as_completed(future_by_port):
                port_number = future_by_port[future]
                is_open = future.result()
                if is_open:
                    open_ports.append(port_number)

        open_ports.sort()
        self.port_cache_map[ip_address] = {"checked_at": scanned_at, "open_ports": open_ports}
        return open_ports

    def _apply_open_ports(self, online_devices: List[Dict], scanned_at: datetime) -> None:
        """온라인 장치에 열린 포트 정보를 채웁니다."""
        if not online_devices:
            return

        # WHY: 장치가 매우 많을 때도 주기 스캔 성능을 보호하기 위해 상한을 둡니다.
        target_devices = online_devices[: self.max_port_scan_devices]
        for device in target_devices:
            device["open_ports"] = self._scan_open_ports(device["ip"], scanned_at)

        for device in online_devices[self.max_port_scan_devices :]:
            device["open_ports"] = []

    def scan(self, timeout_seconds: int = 2, network_cidr_override: Optional[str] = None) -> Dict:
        current_ip, auto_cidr = _find_private_ipv4_network()
        network_cidr = auto_cidr
        if network_cidr_override and str(network_cidr_override).strip():
            try:
                network_cidr = str(ipaddress.ip_network(str(network_cidr_override).strip(), strict=False))
            except ValueError as error:
                raise ValueError(f"잘못된 CIDR입니다: {network_cidr_override}") from error
        scanned_at = datetime.now()

        online_devices: List[Dict] = []
        currently_seen_ips = set()
        warning_message = ""
        scan_mode = "arp"

        try:
            arp_request = ARP(pdst=network_cidr)
            ethernet_frame = Ether(dst="ff:ff:ff:ff:ff:ff")
            packet = ethernet_frame / arp_request
            answered, _ = srp(packet, timeout=timeout_seconds, verbose=False)

            for _, received in answered:
                device_ip = received.psrc
                device_mac = received.hwsrc
                currently_seen_ips.add(device_ip)
                self.last_seen_map[device_ip] = scanned_at

                online_devices.append(
                    {
                        "ip": device_ip,
                        "mac": device_mac,
                        "vendor": _resolve_vendor(device_mac),
                        "open_ports": [],
                        "hostname": _resolve_hostname(device_ip),
                        "status": "online",
                        "last_seen": scanned_at.isoformat(timespec="seconds"),
                    }
                )
        except Exception as error:
            if isinstance(error, PermissionError):
                raise

            if not self._is_scapy_layer2_unavailable(error):
                raise

            scan_mode = "ping_fallback"
            online_devices, warning_message = self._fallback_ping_scan(
                network_cidr=network_cidr,
                current_ip=current_ip,
                scanned_at=scanned_at,
            )
            currently_seen_ips = {device["ip"] for device in online_devices}

        offline_devices: List[Dict] = []
        offline_threshold = scanned_at - timedelta(seconds=self.offline_grace_seconds)

        for remembered_ip, last_seen_time in list(self.last_seen_map.items()):
            if remembered_ip in currently_seen_ips:
                continue

            if last_seen_time >= offline_threshold:
                # WHY: 일시적인 패킷 손실로 인한 오탐을 줄이기 위해 유예 시간을 둡니다.
                continue

            offline_devices.append(
                {
                    "ip": remembered_ip,
                    "mac": "알 수 없음",
                    "vendor": "알 수 없음",
                    "open_ports": [],
                    "hostname": _resolve_hostname(remembered_ip),
                    "status": "offline",
                    "last_seen": last_seen_time.isoformat(timespec="seconds"),
                }
            )

        self._apply_open_ports(online_devices, scanned_at)

        devices = sorted(
            online_devices + offline_devices,
            key=lambda device: tuple(int(part) for part in device["ip"].split(".")),
        )

        online_count = len(online_devices)
        offline_count = len(offline_devices)
        total_count = len(devices)

        history_point = {
            "time": scanned_at.strftime("%H:%M:%S"),
            "online": online_count,
            "offline": offline_count,
            "total": total_count,
        }
        self.scan_history.append(history_point)
        if len(self.scan_history) > self.max_history_points:
            self.scan_history = self.scan_history[-self.max_history_points :]

        result = {
            "network": network_cidr,
            "current_host_ip": current_ip,
            "scanned_at": scanned_at.isoformat(timespec="seconds"),
            "devices": devices,
            "scan_mode": scan_mode,
            "warning_message": warning_message,
            "summary": {
                "online_count": online_count,
                "offline_count": offline_count,
                "total_count": total_count,
            },
            "history": self.scan_history,
        }
        self.last_scan_result = result
        return result

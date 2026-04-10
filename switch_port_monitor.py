"""
스위치 포트 상태 모니터링 모듈
WHY: SNMP IF-MIB 워크를 통해 스위치 각 포트의 UP/DOWN 상태를 수집합니다.
     기존 device_fingerprint.py의 SNMP 패턴을 포트 테이블 워크에 맞게 확장합니다.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List, Optional

import yaml

# SNMP IF-MIB OID 정의
# WHY: IF-MIB는 모든 벤더 스위치가 공통으로 지원하는 표준 MIB입니다.
OID_IF_DESCR        = "1.3.6.1.2.1.2.2.1.2"   # 포트 이름 (e.g. GigabitEthernet0/1)
OID_IF_OPER_STATUS  = "1.3.6.1.2.1.2.2.1.8"   # 실제 상태  (1=up, 2=down)
OID_IF_ADMIN_STATUS = "1.3.6.1.2.1.2.2.1.7"   # 설정 상태  (1=up, 2=down)
OID_IF_SPEED        = "1.3.6.1.2.1.2.2.1.5"   # 속도 (bps)
OID_IF_IN_OCTETS    = "1.3.6.1.2.1.2.2.1.10"  # 수신 바이트
OID_IF_OUT_OCTETS   = "1.3.6.1.2.1.2.2.1.16"  # 송신 바이트

# OPER_STATUS 코드 → 사람이 읽을 수 있는 문자열
OPER_STATUS_MAP = {
    "1": "up",
    "2": "down",
    "3": "testing",
    "4": "unknown",
    "5": "dormant",
    "6": "notPresent",
    "7": "lowerLayerDown",
}

try:
    from netmiko import ConnectHandler
except Exception:
    ConnectHandler = None

try:
    from pysnmp.hlapi import (
        CommunityData,
        ContextData,
        ObjectIdentity,
        ObjectType,
        SnmpEngine,
        UdpTransportTarget,
        UsmUserData,
        nextCmd,
        usmAesCfb128Protocol,
        usmDESPrivProtocol,
        usmHMACMD5AuthProtocol,
        usmHMACSHAAuthProtocol,
    )
    SNMP_AVAILABLE = True
except Exception:
    SNMP_AVAILABLE = False
    nextCmd = None


def _walk_snmp_table(ip: str, auth_data, base_oid: str, timeout: int = 3) -> Dict[str, str]:
    """
    SNMP Walk로 테이블 OID 전체를 읽어 {포트인덱스: 값} 딕셔너리를 반환합니다.
    WHY: getCmd는 단일 OID용이고, 포트 목록 전체를 가져오려면 nextCmd(Walk)가 필요합니다.
    """
    if not SNMP_AVAILABLE or nextCmd is None:
        return {}

    result: Dict[str, str] = {}
    try:
        for err_ind, err_status, _, var_binds in nextCmd(
            SnmpEngine(),
            auth_data,
            UdpTransportTarget((ip, 161), timeout=timeout, retries=0),
            ContextData(),
            ObjectType(ObjectIdentity(base_oid)),
            lexicographicMode=False,    # WHY: base_oid 범위를 벗어나면 중단
        ):
            if err_ind or err_status:
                break
            for name, val in var_binds:
                # OID 마지막 숫자가 포트 인덱스입니다 (e.g. .2.2.1.2.3 → "3")
                index = str(name).split(".")[-1]
                result[index] = str(val)
    except Exception:
        pass
    return result


def _build_auth(snmp_cfg: dict):
    """devices.yaml의 snmp 설정에서 pysnmp 인증 객체를 생성합니다."""
    if not SNMP_AVAILABLE:
        return None
    # SNMPv3 우선
    username = snmp_cfg.get("v3_username", "")
    auth_key = snmp_cfg.get("v3_auth_key", "")
    if username and auth_key:
        priv_key = snmp_cfg.get("v3_priv_key", "")
        auth_proto = (
            usmHMACMD5AuthProtocol
            if str(snmp_cfg.get("v3_auth_protocol", "sha")).lower() == "md5"
            else usmHMACSHAAuthProtocol
        )
        priv_proto = (
            usmDESPrivProtocol
            if str(snmp_cfg.get("v3_priv_protocol", "aes")).lower() == "des"
            else usmAesCfb128Protocol
        )
        if priv_key:
            return UsmUserData(username, auth_key, priv_key,
                               authProtocol=auth_proto, privProtocol=priv_proto)
        return UsmUserData(username, auth_key, authProtocol=auth_proto)
    # SNMPv2c 폴백
    community = snmp_cfg.get("community", "")
    if community:
        return CommunityData(community, mpModel=1)
    return None


def _parse_cisco_show_interfaces_status(device: Dict) -> Optional[List[Dict]]:
    """
    SNMP 실패 시 Cisco IOS에서 show interfaces status 결과를 파싱합니다.
    WHY: Netmiko + TextFSM(ntc-templates)로 표 형식을 구조화합니다.
    """
    if ConnectHandler is None:
        return None
    ssh_cfg = device.get("ssh") or {}
    username = ssh_cfg.get("username") or device.get("username", "")
    password = ssh_cfg.get("password") or device.get("password", "")
    switch_ip = device.get("ip", "")
    if not (username and password and switch_ip):
        return None
    try:
        connection = ConnectHandler(
            device_type="cisco_ios",
            host=switch_ip,
            username=username,
            password=password,
            timeout=15,
            conn_timeout=15,
        )
        try:
            parsed = connection.send_command(
                "show interfaces status",
                use_textfsm=True,
                read_timeout=120,
            )
        finally:
            connection.disconnect()
    except Exception:
        return None

    if not isinstance(parsed, list):
        return None

    ports: List[Dict] = []
    for row_index, row in enumerate(parsed, start=1):
        if not isinstance(row, dict):
            continue
        port_name = (
            row.get("PORT")
            or row.get("port")
            or row.get("interface")
            or ""
        )
        port_name = str(port_name).strip()
        if not port_name:
            continue
        status_text = str(
            row.get("STATUS") or row.get("status") or row.get("state") or ""
        ).lower()

        lower_name = port_name.lower()
        if any(kw in lower_name for kw in ("vlan", "loopback", "tunnel", "port-channel")):
            continue

        if status_text in ("connected", "up", "monitoring"):
            oper_status = "up"
        elif status_text in ("notconnect", "down", "inactive", "err-disabled", "suspended"):
            oper_status = "down"
        elif status_text == "disabled":
            oper_status = "down"
        else:
            oper_status = "unknown"

        admin_status = "down" if status_text == "disabled" else "up"

        speed_raw = str(row.get("SPEED") or row.get("speed") or "")
        speed_mbps = 0
        if "1000" in speed_raw or "1g" in speed_raw.lower() or "a-1000" in speed_raw.lower():
            speed_mbps = 1000
        elif "100" in speed_raw:
            speed_mbps = 100
        elif "10" in speed_raw:
            speed_mbps = 10

        ports.append(
            {
                "index": str(row_index),
                "name": port_name,
                "oper_status": oper_status,
                "admin_status": admin_status,
                "speed_mbps": speed_mbps,
            }
        )

    return ports if ports else None


def _build_port_result(switch_ip: str, ports: List[Dict], error: Optional[str], source: str) -> Dict:
    up_count = sum(1 for p in ports if p["oper_status"] == "up")
    down_count = sum(1 for p in ports if p["oper_status"] == "down")
    return {
        "switch_ip": switch_ip,
        "error": error,
        "ports": ports,
        "summary": {"total": len(ports), "up": up_count, "down": down_count},
        "collected_at": datetime.now().isoformat(timespec="seconds"),
        "source": source,
    }


def _collect_ports_for_switch(device: Dict) -> Dict:
    """
    단일 스위치의 모든 포트 상태를 수집합니다.
    반환: { switch_ip, ports, summary, source }
    """
    switch_ip = device.get("ip", "")
    snmp_cfg = device.get("snmp", {}) or {}
    vendor = str(device.get("vendor", "")).lower()

    auth = _build_auth(snmp_cfg)
    if auth is not None:
        descr_map = _walk_snmp_table(switch_ip, auth, OID_IF_DESCR)
        oper_map = _walk_snmp_table(switch_ip, auth, OID_IF_OPER_STATUS)
        admin_map = _walk_snmp_table(switch_ip, auth, OID_IF_ADMIN_STATUS)
        speed_map = _walk_snmp_table(switch_ip, auth, OID_IF_SPEED)

        if descr_map:
            ports: List[Dict] = []
            for idx in sorted(descr_map.keys(), key=lambda x: int(x) if x.isdigit() else 0):
                name = descr_map.get(idx, f"ifIndex.{idx}")
                oper_raw = oper_map.get(idx, "4")
                admin_raw = admin_map.get(idx, "4")
                speed_bps = int(speed_map.get(idx, 0) or 0)
                speed_mbps = speed_bps // 1_000_000 if speed_bps else 0

                lower_name = name.lower()
                if any(
                    kw in lower_name
                    for kw in (
                        "loopback",
                        "loop",
                        "tunnel",
                        "vlan",
                        "null",
                        "mgmt",
                        "software",
                        "async",
                        "virtual",
                        "aggregate",
                    )
                ):
                    continue

                ports.append(
                    {
                        "index": idx,
                        "name": name,
                        "oper_status": OPER_STATUS_MAP.get(oper_raw, "unknown"),
                        "admin_status": OPER_STATUS_MAP.get(admin_raw, "unknown"),
                        "speed_mbps": speed_mbps,
                    }
                )

            return _build_port_result(switch_ip, ports, None, "snmp")

    # SNMP 불가 또는 응답 없음 → Cisco면 SSH 보조
    if "cisco" in vendor:
        ssh_ports = _parse_cisco_show_interfaces_status(device)
        if ssh_ports:
            return _build_port_result(switch_ip, ssh_ports, None, "ssh_cisco")

    err_msg = "SNMP 응답 없음 또는 인증 실패"
    if auth is None:
        err_msg = "SNMP 인증 설정 없음 (community 또는 v3)"
    elif "cisco" not in vendor:
        err_msg += " (비-Cisco는 SSH 포트 파싱 미지원, SNMP 설정 필요)"

    return _build_port_result(switch_ip, [], err_msg, "none")


class SwitchPortMonitor:
    """스위치 목록을 병렬로 폴링해 포트 상태를 반환합니다."""

    def __init__(self, inventory_path: Optional[str] = None) -> None:
        self.inventory_path = inventory_path

    def _load_switches(self) -> List[Dict]:
        """devices.yaml에서 스위치 목록을 읽습니다."""
        if not self.inventory_path:
            return []
        try:
            with open(self.inventory_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return data.get("devices", [])
        except Exception:
            return []

    def poll(self, inventory_path: Optional[str] = None) -> List[Dict]:
        """
        모든 스위치의 포트 상태를 병렬로 수집합니다.
        WHY: 스위치마다 SNMP Walk가 수초 걸리므로 ThreadPoolExecutor로 병렬 실행합니다.
        """
        path = inventory_path or self.inventory_path
        if not path:
            return []
        try:
            with open(path, "r", encoding="utf-8") as yaml_file:
                data = yaml.safe_load(yaml_file) or {}
            switches = data.get("devices", [])
        except Exception:
            return []

        if not switches:
            return []

        results = []
        with ThreadPoolExecutor(max_workers=min(8, len(switches))) as executor:
            futures = {
                executor.submit(_collect_ports_for_switch, sw): sw
                for sw in switches
                if sw.get("ip")
            }
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as exc:
                    sw = futures[future]
                    results.append({
                        "switch_ip": sw.get("ip", "unknown"),
                        "error": str(exc),
                        "ports": [],
                        "summary": {"total": 0, "up": 0, "down": 0},
                        "source": "error",
                    })

        # IP 순서로 정렬
        results.sort(key=lambda r: tuple(
            int(p) for p in r["switch_ip"].split(".") if p.isdigit()
        ))
        return results

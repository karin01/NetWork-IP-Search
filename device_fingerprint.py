import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import yaml

try:
    import paramiko
except Exception:  # pragma: no cover
    paramiko = None

try:
    from pysnmp.hlapi import (
        CommunityData,
        ContextData,
        ObjectIdentity,
        ObjectType,
        SnmpEngine,
        UdpTransportTarget,
        UsmUserData,
        getCmd,
        usmAesCfb128Protocol,
        usmDESPrivProtocol,
        usmHMACMD5AuthProtocol,
        usmHMACSHAAuthProtocol,
    )
except Exception:  # pragma: no cover
    getCmd = None
    SnmpEngine = None
    CommunityData = None
    UdpTransportTarget = None
    ContextData = None
    ObjectType = None
    ObjectIdentity = None
    UsmUserData = None
    usmAesCfb128Protocol = None
    usmDESPrivProtocol = None
    usmHMACMD5AuthProtocol = None
    usmHMACSHAAuthProtocol = None


VENDOR_COMMAND_TEMPLATES: Dict[str, List[str]] = {
    "cisco": ["show version", "show inventory"],
    "juniper": ["show chassis hardware", "show version"],
    "hpe": ["display version", "display device manuinfo"],
    "generic": ["show version", "show inventory", "display version"],
}

SNMP_OID_SYSDESCR = "1.3.6.1.2.1.1.1.0"
SNMP_OID_ENT_SERIAL = "1.3.6.1.2.1.47.1.1.1.1.11.1"
SNMP_OID_ENT_MODEL = "1.3.6.1.2.1.47.1.1.1.1.13.1"


class DeviceFingerprintCollector:
    """L2/L3 장비 모델/시리얼 수집기 (SNMPv3 우선, 벤더별 SSH 파서 보조)."""

    def __init__(self) -> None:
        self.cache_seconds = 300
        self.cache_map: Dict[str, Dict] = {}

    def _read_inventory(self, inventory_path: str) -> Dict[str, Dict]:
        with open(inventory_path, "r", encoding="utf-8") as inventory_file:
            data = yaml.safe_load(inventory_file) or {}
        device_list = data.get("devices", [])
        return {str(device.get("ip", "")): device for device in device_list if device.get("ip")}

    def _normalize_vendor(self, vendor_name: str) -> str:
        normalized = (vendor_name or "").strip().lower()
        if "cisco" in normalized:
            return "cisco"
        if "juniper" in normalized or "junos" in normalized:
            return "juniper"
        if normalized in {"hpe", "hp", "aruba"}:
            return "hpe"
        return "generic"

    def _build_empty_result(self, device: Dict, reason: str) -> Dict:
        return {
            **device,
            "model": "알 수 없음",
            "serial_number": "알 수 없음",
            "fingerprint_source": "unknown",
            "fingerprint_status": "failed",
            "fingerprint_reason": reason,
        }

    def _snmp_get(self, ip_address: str, auth_data, oid: str, timeout_seconds: int = 2) -> str:
        if getCmd is None:
            return ""
        try:
            iterator = getCmd(
                SnmpEngine(),
                auth_data,
                UdpTransportTarget((ip_address, 161), timeout=timeout_seconds, retries=0),
                ContextData(),
                ObjectType(ObjectIdentity(oid)),
            )
            error_indication, error_status, _, var_binds = next(iterator)
            if error_indication or error_status:
                return ""
            for _, value in var_binds:
                return str(value).strip()
            return ""
        except Exception:
            return ""

    def _snmp_v3_auth_data(self, snmp_config: Dict):
        if UsmUserData is None:
            return None
        username = snmp_config.get("v3_username", "")
        auth_key = snmp_config.get("v3_auth_key", "")
        priv_key = snmp_config.get("v3_priv_key", "")
        auth_proto_raw = str(snmp_config.get("v3_auth_protocol", "sha")).lower()
        priv_proto_raw = str(snmp_config.get("v3_priv_protocol", "aes")).lower()
        if not username or not auth_key:
            return None

        auth_protocol = usmHMACSHAAuthProtocol if auth_proto_raw == "sha" else usmHMACMD5AuthProtocol
        priv_protocol = usmAesCfb128Protocol if priv_proto_raw == "aes" else usmDESPrivProtocol

        if priv_key:
            return UsmUserData(username, auth_key, priv_key, authProtocol=auth_protocol, privProtocol=priv_protocol)
        return UsmUserData(username, auth_key, authProtocol=auth_protocol)

    def _collect_via_snmp(self, ip_address: str, device_config: Dict) -> Tuple[Dict, str]:
        snmp_config = device_config.get("snmp", {})
        # WHY: 운영 환경 보안 강화를 위해 v3를 우선 시도하고 v2c를 보조로 사용합니다.
        v3_auth = self._snmp_v3_auth_data(snmp_config)
        if v3_auth:
            model_value = self._snmp_get(ip_address, v3_auth, SNMP_OID_ENT_MODEL) or self._snmp_get(
                ip_address, v3_auth, SNMP_OID_SYSDESCR
            )
            serial_value = self._snmp_get(ip_address, v3_auth, SNMP_OID_ENT_SERIAL)
            if model_value or serial_value:
                return (
                    {
                        "model": model_value or "알 수 없음",
                        "serial_number": serial_value or "알 수 없음",
                        "source": "snmp_v3",
                    },
                    "",
                )

        community = snmp_config.get("community", "")
        if community and CommunityData is not None:
            v2_auth = CommunityData(community, mpModel=1)
            model_value = self._snmp_get(ip_address, v2_auth, SNMP_OID_ENT_MODEL) or self._snmp_get(
                ip_address, v2_auth, SNMP_OID_SYSDESCR
            )
            serial_value = self._snmp_get(ip_address, v2_auth, SNMP_OID_ENT_SERIAL)
            if model_value or serial_value:
                return (
                    {
                        "model": model_value or "알 수 없음",
                        "serial_number": serial_value or "알 수 없음",
                        "source": "snmp_v2c",
                    },
                    "",
                )

        return {}, "snmp_unreachable_or_auth_failed"

    def _run_ssh_command(self, ip_address: str, username: str, password: str, command: str) -> str:
        if paramiko is None:
            return ""
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh_client.connect(
                hostname=ip_address,
                username=username,
                password=password,
                timeout=5,
                look_for_keys=False,
                allow_agent=False,
            )
            _, stdout, _ = ssh_client.exec_command(command, timeout=10)
            return stdout.read().decode("utf-8", errors="ignore")
        except Exception:
            return ""
        finally:
            ssh_client.close()

    def _parse_vendor_output(self, vendor_key: str, joined_output: str) -> Dict:
        if vendor_key == "cisco":
            model_match = re.search(r"PID:\s*([A-Za-z0-9._-]+)", joined_output, re.IGNORECASE)
            if not model_match:
                model_match = re.search(r"cisco\s+([A-Za-z0-9._-]+)", joined_output, re.IGNORECASE)
            serial_match = re.search(r"SN:\s*([A-Za-z0-9._-]+)", joined_output, re.IGNORECASE)
        elif vendor_key == "juniper":
            model_match = re.search(r"Model:\s*([A-Za-z0-9._-]+)", joined_output, re.IGNORECASE)
            serial_match = re.search(r"Serial\s+number:\s*([A-Za-z0-9._-]+)", joined_output, re.IGNORECASE)
        elif vendor_key == "hpe":
            model_match = re.search(r"DEVICE\s+MODEL\s*:\s*([A-Za-z0-9._-]+)", joined_output, re.IGNORECASE)
            if not model_match:
                model_match = re.search(r"HP[E]?\s+([A-Za-z0-9._-]+)", joined_output, re.IGNORECASE)
            serial_match = re.search(r"Serial\s+Number\s*:\s*([A-Za-z0-9._-]+)", joined_output, re.IGNORECASE)
        else:
            model_match = re.search(
                r"(?:Model(?: number)?|PID)\s*[:#]?\s*([A-Za-z0-9._-]+)",
                joined_output,
                re.IGNORECASE,
            )
            serial_match = re.search(
                r"(?:Serial(?: number)?|SN)\s*[:#]?\s*([A-Za-z0-9._-]+)",
                joined_output,
                re.IGNORECASE,
            )
        return {
            "model": model_match.group(1) if model_match else "알 수 없음",
            "serial_number": serial_match.group(1) if serial_match else "알 수 없음",
        }

    def _collect_via_ssh(self, ip_address: str, device_config: Dict, vendor_key: str) -> Tuple[Dict, str]:
        ssh_config = device_config.get("ssh", {})
        username = ssh_config.get("username", device_config.get("username", ""))
        password = ssh_config.get("password", device_config.get("password", ""))
        if not username or not password:
            return {}, "ssh_credentials_missing"

        command_outputs = []
        command_list = VENDOR_COMMAND_TEMPLATES.get(vendor_key, VENDOR_COMMAND_TEMPLATES["generic"])
        for command in command_list:
            output_text = self._run_ssh_command(ip_address, username, password, command)
            if output_text:
                command_outputs.append(output_text)

        joined_output = "\n".join(command_outputs)
        if not joined_output:
            return {}, "ssh_connection_or_command_failed"

        parsed_result = self._parse_vendor_output(vendor_key, joined_output)
        if parsed_result["model"] == "알 수 없음" and parsed_result["serial_number"] == "알 수 없음":
            return {}, "ssh_parse_failed"
        return ({**parsed_result, "source": f"ssh_{vendor_key}"}, "")

    def _collect_single_device(self, device: Dict, inventory_map: Dict[str, Dict]) -> Dict:
        ip_address = device.get("ip", "")
        if not ip_address:
            return self._build_empty_result(device, "ip_missing")

        cached = self.cache_map.get(ip_address)
        if cached:
            cached_at = cached.get("cached_at")
            if isinstance(cached_at, datetime) and datetime.now() - cached_at <= timedelta(seconds=self.cache_seconds):
                return {
                    **device,
                    "model": cached.get("model", "알 수 없음"),
                    "serial_number": cached.get("serial_number", "알 수 없음"),
                    "fingerprint_source": cached.get("source", "cache"),
                    "fingerprint_status": cached.get("fingerprint_status", "success"),
                    "fingerprint_reason": cached.get("fingerprint_reason", ""),
                }

        device_config = inventory_map.get(ip_address, {})
        vendor_key = self._normalize_vendor(device_config.get("vendor", device.get("vendor", "")))

        snmp_result, snmp_reason = self._collect_via_snmp(ip_address, device_config)
        if snmp_result:
            final_result = {
                "model": snmp_result["model"],
                "serial_number": snmp_result["serial_number"],
                "source": snmp_result["source"],
                "fingerprint_status": "success",
                "fingerprint_reason": "",
            }
            self.cache_map[ip_address] = {**final_result, "cached_at": datetime.now()}
            return {**device, **final_result, "fingerprint_source": final_result["source"]}

        ssh_result, ssh_reason = self._collect_via_ssh(ip_address, device_config, vendor_key)
        if ssh_result:
            final_result = {
                "model": ssh_result["model"],
                "serial_number": ssh_result["serial_number"],
                "source": ssh_result["source"],
                "fingerprint_status": "success",
                "fingerprint_reason": "",
            }
            self.cache_map[ip_address] = {**final_result, "cached_at": datetime.now()}
            return {**device, **final_result, "fingerprint_source": final_result["source"]}

        failure_reason = ssh_reason or snmp_reason or "unknown_failure"
        failed_result = self._build_empty_result(device, failure_reason)
        failed_result["fingerprint_source"] = "unknown"
        self.cache_map[ip_address] = {
            "model": failed_result["model"],
            "serial_number": failed_result["serial_number"],
            "source": failed_result["fingerprint_source"],
            "fingerprint_status": failed_result["fingerprint_status"],
            "fingerprint_reason": failed_result["fingerprint_reason"],
            "cached_at": datetime.now(),
        }
        return failed_result

    def _build_summary(self, online_devices: List[Dict], enriched_online_devices: List[Dict]) -> Dict:
        total_targets = len(online_devices)
        success_count = sum(1 for device in enriched_online_devices if device.get("fingerprint_status") == "success")
        failure_count = max(0, total_targets - success_count)
        success_rate = round((success_count / total_targets) * 100, 1) if total_targets else 0.0
        reason_counter = Counter(
            device.get("fingerprint_reason", "")
            for device in enriched_online_devices
            if device.get("fingerprint_status") != "success"
        )
        return {
            "target_online_devices": total_targets,
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate_percent": success_rate,
            "failure_reasons": dict(reason_counter),
        }

    def enrich_devices(self, devices: List[Dict], inventory_path: Optional[str] = None) -> Dict:
        inventory_map: Dict[str, Dict] = {}
        if inventory_path:
            try:
                inventory_map = self._read_inventory(inventory_path)
            except Exception:
                inventory_map = {}

        online_devices = [device for device in devices if device.get("status") == "online"]
        offline_devices = [device for device in devices if device.get("status") != "online"]

        enriched_online_devices: List[Dict] = []
        with ThreadPoolExecutor(max_workers=min(12, max(1, len(online_devices)))) as executor:
            future_list = [executor.submit(self._collect_single_device, device, inventory_map) for device in online_devices]
            for future in as_completed(future_list):
                enriched_online_devices.append(future.result())

        summary = self._build_summary(online_devices, enriched_online_devices)
        enriched_devices = sorted(
            enriched_online_devices
            + [
                {
                    **device,
                    "model": "-",
                    "serial_number": "-",
                    "fingerprint_source": "-",
                    "fingerprint_status": "skipped",
                    "fingerprint_reason": "offline_device",
                }
                for device in offline_devices
            ],
            key=lambda device: tuple(int(part) for part in device["ip"].split(".")),
        )
        return {
            "devices": enriched_devices,
            "summary": summary,
            "collected_at": datetime.now().isoformat(timespec="seconds"),
        }

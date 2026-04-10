"""
Wi-Fi 링크 정보 및 (선택) 처리량 측정.
WHY: ARP/RARP는 대역폭 측정에 부적합하므로, OS가 제공하는 협상 링크 속도(netsh)와
     선택적 iperf3로 실제 처리량을 분리해 제공합니다.
"""

import json
import platform
import re
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional


def _normalize_key(raw_key: str) -> str:
    """라벨을 비교하기 쉽게 정규화합니다."""
    key = raw_key.strip().lower()
    key = re.sub(r"[\s\(\)]", "", key)
    return key


def _parse_interface_block(block: str) -> Dict[str, str]:
    """netsh 한 블록에서 key: value 추출."""
    result: Dict[str, str] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        # 앞쪽 공백(들여쓰기) 제거 후 첫 ':' 기준 분리
        stripped = line.strip()
        key_part, _, val_part = stripped.partition(":")
        nk = _normalize_key(key_part)
        if nk:
            result[nk] = val_part.strip()
    return result


def _block_to_interface(kv: Dict[str, str]) -> Dict[str, Any]:
    """정규화된 키에서 UI용 필드 매핑 (영문/한글 netsh 대응)."""
    def pick(*labels: str) -> str:
        """WHY: kv 키는 _parse_interface_block에서 이미 정규화되어 있으므로 정확 일치를 우선합니다."""
        for label in labels:
            needle = _normalize_key(label)
            if needle in kv:
                return kv[needle]
        return ""

    ssid = pick("SSID")
    state = pick("State", "상태")
    signal = pick("Signal", "신호")
    receive = pick(
        "Receive rate (Mbps)",
        "Receive rate",
        "수신 속도 (Mbps)",
        "수신 속도(Mbps)",
        "수신 속도",
    )
    transmit = pick(
        "Transmit rate (Mbps)",
        "Transmit rate",
        "송신 속도 (Mbps)",
        "송신 속도(Mbps)",
        "송신 속도",
    )
    radio = pick("Radio type", "무선 종류", "라디오 종류")
    channel = pick("Channel", "채널")
    auth = pick("Authentication", "인증")
    profile = pick("Profile", "프로필")
    name = pick("Name", "이름")

    def parse_mbps(text: str) -> Optional[float]:
        if not text:
            return None
        m = re.search(r"([\d.]+)", text.replace(",", ""))
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                return None
        return None

    def parse_signal(text: str) -> Optional[int]:
        if not text:
            return None
        m = re.search(r"(\d+)\s*%", text)
        if m:
            return int(m.group(1))
        m = re.search(r"(\d+)", text)
        if m:
            return int(m.group(1))
        return None

    return {
        "adapter_name": name or "Wi-Fi",
        "ssid": ssid or "—",
        "state": state or "—",
        "signal_percent": parse_signal(signal),
        "receive_mbps": parse_mbps(receive),
        "transmit_mbps": parse_mbps(transmit),
        "radio_type": radio or "—",
        "channel": channel or "—",
        "authentication": auth or "—",
        "profile": profile or "—",
        "raw_signal": signal,
        "raw_receive": receive,
        "raw_transmit": transmit,
    }


def _split_netsh_blocks(text: str) -> List[str]:
    """여러 무선 인터페이스 블록으로 분리."""
    lines = text.replace("\r\n", "\n").split("\n")
    blocks: List[List[str]] = []
    current: List[str] = []

    def is_adapter_start(stripped_line: str) -> bool:
        return bool(
            re.match(r"^Name\s*:", stripped_line, re.I)
            or re.match(r"^이름\s*:", stripped_line)
        )

    for line in lines:
        stripped = line.strip()
        if is_adapter_start(stripped):
            if current:
                blocks.append(current)
            current = [line]
        elif current:
            current.append(line)
    if current:
        blocks.append(current)
    if not blocks and lines:
        return ["\n".join(lines)]
    return ["\n".join(b) for b in blocks]


def get_windows_wifi_status() -> Dict[str, Any]:
    """Windows netsh wlan show interfaces 출력을 파싱합니다."""
    if platform.system().lower() != "windows":
        return {
            "ok": False,
            "platform": platform.system(),
            "message": "Wi-Fi 링크 정보는 현재 Windows(netsh)만 지원합니다.",
            "interfaces": [],
            "measured_at": datetime.now().isoformat(timespec="seconds"),
        }

    try:
        completed = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True,
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
    except FileNotFoundError:
        return {
            "ok": False,
            "platform": "windows",
            "message": "netsh 명령을 실행할 수 없습니다.",
            "interfaces": [],
            "measured_at": datetime.now().isoformat(timespec="seconds"),
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "platform": "windows",
            "message": "netsh 실행 시간 초과.",
            "interfaces": [],
            "measured_at": datetime.now().isoformat(timespec="seconds"),
        }

    raw_out = completed.stdout or b""
    for encoding in ("utf-8", "cp949", "mbcs"):
        try:
            text = raw_out.decode(encoding)
            break
        except UnicodeDecodeError:
            text = raw_out.decode("utf-8", errors="replace")
    else:
        text = raw_out.decode("utf-8", errors="replace")

    if completed.returncode != 0:
        err = (completed.stderr or b"").decode("utf-8", errors="replace")
        return {
            "ok": False,
            "platform": "windows",
            "message": f"netsh 실패: {err or text[:200]}",
            "interfaces": [],
            "raw_preview": text[:500],
            "measured_at": datetime.now().isoformat(timespec="seconds"),
        }

    # 무선 어댑터 없음
    if re.search(r"no wireless interface|무선.*없|there is no wireless", text, re.I):
        return {
            "ok": True,
            "platform": "windows",
            "message": "무선 LAN 인터페이스가 없거나 사용 안 함입니다.",
            "interfaces": [],
            "measured_at": datetime.now().isoformat(timespec="seconds"),
        }

    blocks = _split_netsh_blocks(text)
    interfaces: List[Dict[str, Any]] = []
    for block in blocks:
        kv = _parse_interface_block(block)
        if not kv:
            continue
        keys_set = set(kv.keys())
        has_ssid = "ssid" in keys_set
        has_name = "name" in keys_set
        has_state = "state" in keys_set or "상태" in keys_set
        has_signal = "signal" in keys_set or "신호" in keys_set
        if not (has_ssid or (has_name and has_signal) or (has_name and has_state)):
            continue
        interfaces.append(_block_to_interface(kv))

    if not interfaces:
        # 폴백: 전체를 한 덩어리 파싱
        kv = _parse_interface_block(text)
        if kv:
            interfaces.append(_block_to_interface(kv))

    return {
        "ok": True,
        "platform": "windows",
        "message": "",
        "interfaces": interfaces,
        "note": "수신/송신 Mbps는 AP와의 협상 링크 속도(참고)이며, 실제 인터넷 속도와 다를 수 있습니다. 실제 처리량은 iperf3로 측정하세요.",
        "measured_at": datetime.now().isoformat(timespec="seconds"),
    }


def run_iperf3_client(
    host: str,
    port: int = 5201,
    duration_seconds: int = 5,
) -> Dict[str, Any]:
    """
    iperf3로 TCP 처리량을 측정합니다. iperf3가 PATH에 있어야 합니다.
    서버 측: iperf3 -s
    """
    host = (host or "").strip()
    if not host:
        return {"ok": False, "error": "호스트 IP가 비어 있습니다."}

    duration_seconds = max(2, min(60, int(duration_seconds)))
    port = int(port) if port else 5201

    try:
        completed = subprocess.run(
            [
                "iperf3",
                "-c",
                host,
                "-p",
                str(port),
                "-t",
                str(duration_seconds),
                "-f",
                "m",
                "-J",
            ],
            capture_output=True,
            text=True,
            timeout=duration_seconds + 30,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
    except FileNotFoundError:
        return {
            "ok": False,
            "error": "iperf3가 설치되어 있지 않거나 PATH에 없습니다. https://iperf.fr 에서 설치하세요.",
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "iperf3 실행 시간 초과."}

    if completed.returncode != 0:
        return {
            "ok": False,
            "error": completed.stderr or completed.stdout or "iperf3 실패",
        }

    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "error": "iperf3 JSON 파싱 실패", "raw": completed.stdout[:400]}

    end = data.get("end", {}) or {}
    sent = end.get("sum_sent", {}) or {}
    received = end.get("sum_received", {}) or {}
    send_bps = float(sent.get("bits_per_second", 0) or 0)
    recv_bps = float(received.get("bits_per_second", 0) or 0)

    return {
        "ok": True,
        "host": host,
        "port": port,
        "duration_seconds": duration_seconds,
        "send_mbps": round(send_bps / 1_000_000, 2),
        "receive_mbps": round(recv_bps / 1_000_000, 2),
        "measured_at": datetime.now().isoformat(timespec="seconds"),
    }


def get_wifi_status() -> Dict[str, Any]:
    """플랫폼별 Wi-Fi 상태 진입점."""
    return get_windows_wifi_status()

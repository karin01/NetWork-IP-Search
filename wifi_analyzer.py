"""
주변 Wi-Fi AP 스캔 및 채널·신호 기반 분석 (Wi-Fi Analyzer 스타일).
WHY: Windows는 사용자 모드에서 패킷 캡처 없이 netsh로 BSSID/채널/신호를 얻을 수 있어,
     동일 대역 혼잡도·2.4GHz 비중첩 채널(1/6/11) 힌트를 제공합니다.
"""

from __future__ import annotations

import platform
import re
import subprocess
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


def _normalize_key(raw_key: str) -> str:
    """wifi_metrics와 동일 규칙으로 라벨 정규화."""
    key = raw_key.strip().lower()
    key = re.sub(r"[\s\(\)]", "", key)
    return key


def _decode_netsh_stdout(raw: bytes) -> str:
    """netsh stdout 바이트를 문자열로 복원합니다."""
    for encoding in ("utf-8", "cp949", "mbcs"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _run_netsh_wlan(args: List[str], timeout: float) -> Tuple[int, str, str]:
    """netsh wlan 하위 명령 실행."""
    creationflags = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        creationflags = subprocess.CREATE_NO_WINDOW
    completed = subprocess.run(
        ["netsh", "wlan", *args],
        capture_output=True,
        timeout=timeout,
        creationflags=creationflags,
    )
    out = _decode_netsh_stdout(completed.stdout or b"")
    err = _decode_netsh_stdout(completed.stderr or b"")
    return completed.returncode, out, err


def _parse_line_kv(line: str) -> Optional[Tuple[str, str]]:
    """들여쓰기 있는 netsh 줄에서 key: value 추출."""
    if ":" not in line:
        return None
    stripped = line.strip()
    key_part, _, val_part = stripped.partition(":")
    key_part = key_part.strip()
    val_part = val_part.strip()
    if not key_part:
        return None
    return _normalize_key(key_part), val_part


def _parse_signal_percent(text: str) -> Optional[int]:
    if not text:
        return None
    m = re.search(r"(\d+)\s*%", text)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)", text)
    if m:
        return int(m.group(1))
    return None


def _parse_channel_int(text: str) -> Optional[int]:
    if not text:
        return None
    m = re.search(r"(\d+)", text)
    if m:
        return int(m.group(1))
    return None


def _pick_from_kv(kv: Dict[str, str], *label_variants: str) -> str:
    for label in label_variants:
        nk = _normalize_key(label)
        if nk in kv:
            return kv[nk]
    return ""


def _infer_band_from_channel(ch: Optional[int]) -> Optional[str]:
    if ch is None:
        return None
    if 1 <= ch <= 14:
        return "2.4"
    if 32 <= ch <= 177:
        return "5"
    if ch >= 1:  # 6GHz 등
        return "6+"
    return None


def _band_label(band_raw: str, channel_int: Optional[int]) -> str:
    s = (band_raw or "").replace(" ", "").lower()
    if "2.4" in s:
        return "2.4 GHz"
    if "5" in s and "2.4" not in s:
        return "5 GHz"
    if "6" in s and "802" not in s:
        return "6 GHz"
    inferred = _infer_band_from_channel(channel_int)
    if inferred == "2.4":
        return "2.4 GHz"
    if inferred == "5":
        return "5 GHz"
    return band_raw or "—"


def _materialize_ap(
    interface: Optional[str],
    ssid: str,
    network_kv: Dict[str, str],
    bssid_mac: str,
    ap_kv: Dict[str, str],
) -> Dict[str, Any]:
    """한 BSSID 행을 UI/JSON용 dict로 만듭니다."""
    signal_raw = _pick_from_kv(ap_kv, "Signal", "신호")
    channel_raw = _pick_from_kv(ap_kv, "Channel", "채널")
    band_raw = _pick_from_kv(ap_kv, "Band", "밴드")
    radio_raw = _pick_from_kv(ap_kv, "Radio type", "무선 수신/송신 장치 형식", "무선 종류")

    ch = _parse_channel_int(channel_raw)
    sig = _parse_signal_percent(signal_raw)

    util_raw = _pick_from_kv(ap_kv, "Channel Utilization", "채널 사용률")
    util_pct = _parse_signal_percent(util_raw)

    return {
        "interface": interface or "—",
        "ssid": ssid or "(숨김 SSID)",
        "bssid": bssid_mac,
        "signal_percent": sig,
        "channel": channel_raw or "—",
        "channel_int": ch,
        "band": _band_label(band_raw, ch),
        "radio_type": radio_raw or "—",
        "authentication": _pick_from_kv(network_kv, "Authentication", "인증"),
        "encryption": _pick_from_kv(network_kv, "Encryption", "암호화"),
        "network_type": _pick_from_kv(network_kv, "Network type", "네트워크 종류"),
        "channel_utilization_percent": util_pct,
        "raw_signal": signal_raw,
        "raw_channel": channel_raw,
    }


def _parse_bssid_dump(text: str) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    """
    netsh wlan show networks mode=bssid 전체 텍스트 파싱.
    반환: (오류 메시지 또는 None, AP 목록)
    """
    if re.search(r"no wireless interface|무선.*없|there is no wireless", text, re.I):
        return "무선 LAN 인터페이스가 없습니다.", []

    if re.search(r"0 networks currently visible|0개의.*네트워크|현재 0개", text, re.I):
        return None, []

    interface: Optional[str] = None
    current_ssid: Optional[str] = None
    network_kv: Dict[str, str] = {}
    bssid_mac: Optional[str] = None
    ap_kv: Dict[str, str] = {}
    aps: List[Dict[str, Any]] = []

    def flush_ap() -> None:
        nonlocal bssid_mac, ap_kv
        if bssid_mac and current_ssid is not None:
            aps.append(
                _materialize_ap(interface, current_ssid, network_kv, bssid_mac, ap_kv.copy())
            )
        bssid_mac = None
        ap_kv = {}

    for line in text.replace("\r\n", "\n").split("\n"):
        stripped = line.strip()
        if not stripped:
            continue

        if re.match(r"^Interface name\s*:", stripped, re.I) or re.match(
            r"^인터페이스\s*이름\s*:", stripped.strip()
        ):
            flush_ap()
            _, _, rest = stripped.partition(":")
            interface = rest.strip() or interface
            current_ssid = None
            network_kv = {}
            continue

        m_ssid = re.match(r"^SSID\s+\d+\s*:\s*(.*)$", stripped, re.I)
        if m_ssid:
            flush_ap()
            current_ssid = m_ssid.group(1).strip() or "(숨김 SSID)"
            network_kv = {}
            continue

        m_bss = re.match(r"^BSSID\s+\d+\s*:\s*(.+)$", stripped, re.I)
        if m_bss:
            flush_ap()
            bssid_mac = m_bss.group(1).strip().lower()
            ap_kv = {}
            continue

        parsed = _parse_line_kv(line)
        if not parsed:
            continue
        nk, val = parsed
        # Bss Load 하위 줄(Connected Stations 등)도 ap_kv에 들어가지만 materialize에서 미사용
        if bssid_mac:
            ap_kv[nk] = val
        elif current_ssid is not None:
            network_kv[nk] = val

    flush_ap()
    return None, aps


def _overlap_weight(center: int, other: int) -> float:
    """20MHz 근사: 이웃 채널이면 간섭 가중."""
    d = abs(center - other)
    if d <= 2:
        return 1.0
    if d <= 4:
        return 0.35
    return 0.0


def _build_analysis(access_points: List[Dict[str, Any]]) -> Dict[str, Any]:
    """채널별 집계·2.4GHz 1/6/11 힌트·최강 신호 AP."""
    by_channel: Dict[str, int] = defaultdict(int)
    band_counts: Dict[str, int] = defaultdict(int)
    for ap in access_points:
        ch = ap.get("channel_int")
        if ch is not None:
            by_channel[str(ch)] += 1
        band = ap.get("band") or ""
        if "2.4" in band:
            band_counts["2.4 GHz"] += 1
        elif "5" in band:
            band_counts["5 GHz"] += 1
        elif "6" in band:
            band_counts["6 GHz"] += 1
        else:
            band_counts["기타"] += 1

    channels_24 = [ap["channel_int"] for ap in access_points if ap.get("channel_int") is not None and 1 <= ap["channel_int"] <= 14]

    recommendation_24: List[Dict[str, Any]] = []
    if channels_24:
        ap_by_ch = defaultdict(list)
        for ap in access_points:
            c = ap.get("channel_int")
            if c is not None and 1 <= c <= 14:
                ap_by_ch[c].append(ap)
        for candidate in (1, 6, 11):
            score = 0.0
            for ch, lst in ap_by_ch.items():
                w = _overlap_weight(candidate, ch)
                score += w * len(lst)
            recommendation_24.append(
                {
                    "channel": candidate,
                    "overlap_score": round(score, 2),
                    "note": "2.4GHz에서 1·6·11은 서로 겹침이 적은 대표 채널입니다. 점수는 이웃 채널 AP 수 가중 합(근사)입니다.",
                }
            )
        recommendation_24.sort(key=lambda x: x["overlap_score"])

    strongest: Optional[Dict[str, Any]] = None
    for ap in access_points:
        s = ap.get("signal_percent")
        if s is None:
            continue
        if strongest is None or s > strongest.get("signal_percent", -1):
            strongest = {
                "ssid": ap.get("ssid"),
                "bssid": ap.get("bssid"),
                "signal_percent": s,
                "channel_int": ap.get("channel_int"),
                "band": ap.get("band"),
            }

    # 덜 붐비는 채널(관측된 채널 중 AP 수 최소)
    sorted_channels = sorted(by_channel.items(), key=lambda kv: kv[1])
    least_loaded = [{"channel": int(k), "ap_count": v} for k, v in sorted_channels[:8]]

    return {
        "total_aps": len(access_points),
        "by_channel": dict(sorted(by_channel.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 999)),
        "by_band": dict(band_counts),
        "strongest_ap": strongest,
        "recommended_24ghz_channels": recommendation_24,
        "least_loaded_observed_channels": least_loaded,
        "disclaimer": "AP 배치·대역폭(20/40/80MHz)·DFS 등은 단순화되어 있어 공유기 설정 시 참고용으로만 사용하세요.",
    }


def scan_wifi_surroundings(
    refresh_scan: bool = False,
    merge_current_link: bool = False,
) -> Dict[str, Any]:
    """
    Windows: netsh로 주변 AP 목록을 읽고 분석 dict를 반환합니다.
    refresh_scan=True 이면 먼저 `netsh wlan refresh` 시도(환경에 따라 실패할 수 있음).
    """
    if platform.system().lower() != "windows":
        return {
            "ok": False,
            "message": "Wi-Fi 분석 스캔은 현재 Windows(netsh)만 지원합니다.",
            "access_points": [],
            "analysis": {},
            "measured_at": datetime.now().isoformat(timespec="seconds"),
        }

    if refresh_scan:
        try:
            _run_netsh_wlan(["refresh"], timeout=12.0)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    try:
        code, out, err = _run_netsh_wlan(["show", "networks", "mode=bssid"], timeout=35.0)
    except FileNotFoundError:
        return {
            "ok": False,
            "message": "netsh를 실행할 수 없습니다.",
            "access_points": [],
            "analysis": {},
            "measured_at": datetime.now().isoformat(timespec="seconds"),
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "message": "netsh 스캔 시간 초과.",
            "access_points": [],
            "analysis": {},
            "measured_at": datetime.now().isoformat(timespec="seconds"),
        }

    if code != 0:
        return {
            "ok": False,
            "message": (err or out or "netsh 실패")[:400],
            "access_points": [],
            "analysis": {},
            "measured_at": datetime.now().isoformat(timespec="seconds"),
        }

    err_msg, aps = _parse_bssid_dump(out)
    if err_msg:
        return {
            "ok": True,
            "message": err_msg,
            "access_points": [],
            "analysis": _build_analysis([]),
            "measured_at": datetime.now().isoformat(timespec="seconds"),
        }

    aps.sort(key=lambda x: (-(x.get("signal_percent") or -1), x.get("ssid") or ""))
    analysis = _build_analysis(aps)
    result: Dict[str, Any] = {
        "ok": True,
        "message": "",
        "access_points": aps,
        "analysis": analysis,
        "measured_at": datetime.now().isoformat(timespec="seconds"),
        "note": "목록은 OS가 스캔한 순간의 스냅샷입니다. 숨김 SSID는 이름이 비어 있을 수 있습니다.",
    }

    if merge_current_link:
        from wifi_metrics import get_wifi_status

        link = get_wifi_status()
        result["current_link"] = link
        if link.get("ok") and link.get("interfaces"):
            iface0 = link["interfaces"][0]
            my_ssid = (iface0.get("ssid") or "").strip()
            my_ch_raw = iface0.get("channel")
            my_ch: Optional[int] = None
            if my_ch_raw and str(my_ch_raw).strip() != "—":
                m = re.search(r"(\d+)", str(my_ch_raw))
                if m:
                    my_ch = int(m.group(1))
            same_chan_count = 0
            if my_ch is not None:
                same_chan_count = sum(1 for ap in aps if ap.get("channel_int") == my_ch)
            result["connected_hint"] = {
                "ssid": my_ssid or "—",
                "channel_int": my_ch,
                "access_points_on_same_channel": same_chan_count,
                "hint": (
                    "같은 채널에 보이는 AP가 많으면 간섭이 커질 수 있습니다. "
                    "유선으로 공유기 관리 페이지에서 덜 붐빈 채널(특히 2.4GHz는 1·6·11)을 검토하세요."
                    if same_chan_count >= 4
                    else ""
                ),
            }

    return result


"""
사용자 설정(JSON 파일).
WHY: 인벤토리·스캔 주기·이력·알림·프로필을 웹에서 바꿔도 저장소에 커밋되지 않게 로컬 파일에만 기록합니다.
"""

import json
import os
from typing import Any, Dict, List, Optional

DEFAULTS: Dict[str, Any] = {
    "inventory_path": "devices.example.yaml",
    "scan_interval_seconds": 10,
    # SQLite 스캔 이력
    "history_enabled": True,
    "history_max_snapshots": 200,
    "history_min_interval_seconds": 60,
    # Webhook (비어 있으면 전송 안 함)
    "alert_webhook_url": "",
    "alert_on_new_mac": False,
    "alert_on_mac_gone": False,
    # 스캔 프로필: [{"id":"lab","name":"랩","network_cidr":"10.0.0.0/24"}] — cidr 빈 문자열이면 자동 탐지
    "scan_profiles": [],
    "active_profile_id": "",
}


def settings_path(base_dir: str) -> str:
    return os.path.join(base_dir, "user_settings.json")


def _coerce_profiles(raw: Any) -> List[Dict[str, str]]:
    if not isinstance(raw, list):
        return []
    out: List[Dict[str, str]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        pid = str(item.get("id") or "").strip() or f"p{index}"
        name = str(item.get("name") or pid).strip()
        cidr = str(item.get("network_cidr") or "").strip()
        out.append({"id": pid[:64], "name": name[:128], "network_cidr": cidr[:80]})
    return out[:40]


def _normalize_loaded(base: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(DEFAULTS)
    for key in DEFAULTS:
        if key in base:
            out[key] = base[key]
    out["scan_interval_seconds"] = max(5, min(3600, int(out["scan_interval_seconds"])))
    inv = str(out.get("inventory_path") or "").strip()
    out["inventory_path"] = inv if inv else DEFAULTS["inventory_path"]
    out["history_enabled"] = bool(out["history_enabled"])
    out["history_max_snapshots"] = max(10, min(5000, int(out["history_max_snapshots"])))
    out["history_min_interval_seconds"] = max(10, min(86400, int(out["history_min_interval_seconds"])))
    out["alert_webhook_url"] = str(out.get("alert_webhook_url") or "").strip()[:2000]
    out["alert_on_new_mac"] = bool(out["alert_on_new_mac"])
    out["alert_on_mac_gone"] = bool(out["alert_on_mac_gone"])
    out["scan_profiles"] = _coerce_profiles(out.get("scan_profiles"))
    out["active_profile_id"] = str(out.get("active_profile_id") or "").strip()[:64]
    return out


def load_settings(base_dir: str) -> Dict[str, Any]:
    path = settings_path(base_dir)
    if not os.path.isfile(path):
        return dict(DEFAULTS)
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            return dict(DEFAULTS)
        merged = {**DEFAULTS, **{k: data[k] for k in data if k in DEFAULTS}}
        return _normalize_loaded(merged)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return dict(DEFAULTS)


def save_settings(
    base_dir: str,
    *,
    inventory_path: Optional[str] = None,
    scan_interval_seconds: Optional[int] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """extra: DEFAULTS 키만 병합(인벤토리·주기는 명시 인자가 우선)."""
    cur = load_settings(base_dir)
    if inventory_path is not None:
        s = inventory_path.strip()
        cur["inventory_path"] = s if s else DEFAULTS["inventory_path"]
    if scan_interval_seconds is not None:
        cur["scan_interval_seconds"] = max(5, min(3600, int(scan_interval_seconds)))
    if extra:
        for key, val in extra.items():
            if key not in DEFAULTS or key in ("inventory_path", "scan_interval_seconds"):
                continue
            if key == "scan_profiles":
                cur[key] = _coerce_profiles(val)
            elif key == "history_enabled":
                cur[key] = bool(val)
            elif key == "history_max_snapshots":
                cur[key] = max(10, min(5000, int(val)))
            elif key == "history_min_interval_seconds":
                cur[key] = max(10, min(86400, int(val)))
            elif key == "alert_webhook_url":
                cur[key] = str(val or "").strip()[:2000]
            elif key in ("alert_on_new_mac", "alert_on_mac_gone"):
                cur[key] = bool(val)
            elif key == "active_profile_id":
                cur[key] = str(val or "").strip()[:64]
            else:
                cur[key] = val
    cur = _normalize_loaded(cur)
    path = settings_path(base_dir)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(cur, handle, ensure_ascii=False, indent=2)
    return cur

"""
스캔 스냅샷 SQLite 저장 및 MAC/IP 기준 diff.
WHY: 브라우저를 닫아도 과거 대비 신규·오프라인 변화를 추적합니다.
"""

import json
import os
import sqlite3
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

_lock = threading.Lock()


def history_db_path(base_dir: str) -> str:
    return os.path.join(base_dir, "scan_history.sqlite")


def _connect(base_dir: str) -> sqlite3.Connection:
    path = history_db_path(base_dir)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_db(base_dir: str) -> None:
    """테이블 생성(멱등)."""
    with _lock:
        conn = _connect(base_dir)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scanned_at TEXT NOT NULL,
                    network TEXT NOT NULL,
                    scan_mode TEXT NOT NULL,
                    summary_json TEXT NOT NULL,
                    devices_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_scanned_at ON snapshots (scanned_at)")
            conn.commit()
        finally:
            conn.close()


def _normalize_mac(mac: Optional[str]) -> str:
    if not mac or mac == "알 수 없음":
        return ""
    return mac.upper().replace("-", ":")


def device_stable_key(device: Dict[str, Any]) -> Optional[str]:
    """온라인 장치 식별키: MAC 우선, 없으면 IP(폴백 스캔)."""
    if (device.get("status") or "") != "online":
        return None
    mac_norm = _normalize_mac(device.get("mac"))
    if mac_norm:
        return f"mac:{mac_norm}"
    ip_val = (device.get("ip") or "").strip()
    if ip_val:
        return f"ip:{ip_val}"
    return None


def online_key_set(devices: List[Dict[str, Any]]) -> Set[str]:
    keys: Set[str] = set()
    for dev in devices:
        key = device_stable_key(dev)
        if key:
            keys.add(key)
    return keys


def _row_to_meta(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "scanned_at": row["scanned_at"],
        "network": row["network"],
        "scan_mode": row["scan_mode"],
        "summary": json.loads(row["summary_json"]),
    }


def list_snapshots(base_dir: str, *, limit: int = 50) -> List[Dict[str, Any]]:
    ensure_db(base_dir)
    limit = max(1, min(500, int(limit)))
    with _lock:
        conn = _connect(base_dir)
        try:
            rows = conn.execute(
                "SELECT id, scanned_at, network, scan_mode, summary_json FROM snapshots ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [_row_to_meta(row) for row in rows]
        finally:
            conn.close()


def get_snapshot_devices(base_dir: str, snapshot_id: int) -> Optional[Tuple[Dict[str, Any], List[Dict[str, Any]]]]:
    ensure_db(base_dir)
    with _lock:
        conn = _connect(base_dir)
        try:
            row = conn.execute(
                "SELECT id, scanned_at, network, scan_mode, summary_json, devices_json FROM snapshots WHERE id = ?",
                (int(snapshot_id),),
            ).fetchone()
            if not row:
                return None
            meta = _row_to_meta(row)
            devices = json.loads(row["devices_json"])
            if not isinstance(devices, list):
                devices = []
            return meta, devices
        finally:
            conn.close()


def _parse_iso(ts: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return None


def should_append_snapshot(
    base_dir: str, min_interval_seconds: int, scanned_at_iso: str
) -> bool:
    """최소 간격 이내면 저장 생략(알림은 별도 로직에서 처리)."""
    ensure_db(base_dir)
    min_interval_seconds = max(10, min(86400, int(min_interval_seconds)))
    with _lock:
        conn = _connect(base_dir)
        try:
            row = conn.execute(
                "SELECT scanned_at FROM snapshots ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if not row:
                return True
            last = _parse_iso(row["scanned_at"])
            now = _parse_iso(scanned_at_iso)
            if not last or not now:
                return True
            return (now - last).total_seconds() >= min_interval_seconds
        finally:
            conn.close()


def append_snapshot(base_dir: str, scan_result: Dict[str, Any]) -> Optional[int]:
    """스캔 결과 한 건 저장. devices는 경량 복사본만 JSON으로."""
    ensure_db(base_dir)
    devices = scan_result.get("devices") or []
    slim: List[Dict[str, Any]] = []
    for dev in devices:
        if not isinstance(dev, dict):
            continue
        slim.append(
            {
                "ip": dev.get("ip"),
                "mac": dev.get("mac"),
                "vendor": dev.get("vendor"),
                "hostname": dev.get("hostname"),
                "status": dev.get("status"),
                "last_seen": dev.get("last_seen"),
            }
        )
    summary = scan_result.get("summary") or {}
    payload = {
        "scanned_at": scan_result.get("scanned_at"),
        "current_host_ip": scan_result.get("current_host_ip"),
        "scan_mode": scan_result.get("scan_mode"),
        "warning_message": (scan_result.get("warning_message") or "")[:400],
    }
    summary_json = json.dumps(summary, ensure_ascii=False)
    devices_json = json.dumps(slim, ensure_ascii=False)
    scanned_at = str(scan_result.get("scanned_at") or datetime.now().isoformat(timespec="seconds"))
    network = str(scan_result.get("network") or "")
    scan_mode = str(scan_result.get("scan_mode") or "")
    with _lock:
        conn = _connect(base_dir)
        try:
            cur = conn.execute(
                """
                INSERT INTO snapshots (scanned_at, network, scan_mode, summary_json, devices_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (scanned_at, network, scan_mode, summary_json, devices_json),
            )
            conn.commit()
            return int(cur.lastrowid)
        finally:
            conn.close()


def prune_old_snapshots(base_dir: str, keep_max: int) -> None:
    keep_max = max(10, min(5000, int(keep_max)))
    ensure_db(base_dir)
    with _lock:
        conn = _connect(base_dir)
        try:
            row = conn.execute("SELECT id FROM snapshots ORDER BY id DESC LIMIT 1 OFFSET ?", (keep_max - 1,)).fetchone()
            if not row:
                return
            cutoff_id = int(row["id"])
            conn.execute("DELETE FROM snapshots WHERE id < ?", (cutoff_id,))
            conn.commit()
        finally:
            conn.close()


def diff_online_sets(
    prev_online: Set[str], curr_online: Set[str]
) -> Tuple[List[str], List[str]]:
    added = sorted(curr_online - prev_online)
    removed = sorted(prev_online - curr_online)
    return added, removed


def build_diff_detail(
    added_keys: List[str],
    removed_keys: List[str],
    current_devices: List[Dict[str, Any]],
    old_devices: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """키 목록을 사람이 읽기 쉬운 요약으로."""
    key_to_row: Dict[str, Dict[str, Any]] = {}
    for dev in current_devices:
        if not isinstance(dev, dict):
            continue
        k = device_stable_key(dev)
        if k:
            key_to_row[k] = dev

    old_map: Dict[str, Dict[str, Any]] = {}
    if old_devices:
        for dev in old_devices:
            if not isinstance(dev, dict):
                continue
            k = device_stable_key(dev)
            if k:
                old_map[k] = dev

    def brief_from_key(key: str, source_map: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        row = source_map.get(key) or {}
        return {
            "key": key,
            "ip": row.get("ip"),
            "mac": row.get("mac"),
            "vendor": row.get("vendor"),
            "hostname": row.get("hostname"),
        }

    return {
        "online_new": [brief_from_key(k, key_to_row) for k in added_keys],
        "online_gone": [brief_from_key(k, old_map) for k in removed_keys],
    }


def diff_snapshot_to_current(
    base_dir: str, from_snapshot_id: int, current_result: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    loaded = get_snapshot_devices(base_dir, from_snapshot_id)
    if not loaded:
        return None
    meta, old_devices = loaded
    old_online = online_key_set(old_devices)
    curr_devices = current_result.get("devices") or []
    curr_online = online_key_set(curr_devices if isinstance(curr_devices, list) else [])
    added_keys, removed_keys = diff_online_sets(old_online, curr_online)
    detail = build_diff_detail(
        added_keys,
        removed_keys,
        curr_devices if isinstance(curr_devices, list) else [],
        old_devices,
    )
    return {
        "ok": True,
        "from_snapshot": meta,
        "current_scanned_at": current_result.get("scanned_at"),
        "current_network": current_result.get("network"),
        "counts": {
            "online_new": len(added_keys),
            "online_gone": len(removed_keys),
        },
        **detail,
    }


def diff_two_snapshots(base_dir: str, from_id: int, to_id: int) -> Optional[Dict[str, Any]]:
    a = get_snapshot_devices(base_dir, from_id)
    b = get_snapshot_devices(base_dir, to_id)
    if not a or not b:
        return None
    meta_a, dev_a = a
    meta_b, dev_b = b
    old_online = online_key_set(dev_a)
    new_online = online_key_set(dev_b)
    added_keys, removed_keys = diff_online_sets(old_online, new_online)
    detail = build_diff_detail(added_keys, removed_keys, dev_b, dev_a)
    return {
        "ok": True,
        "from_snapshot": meta_a,
        "to_snapshot": {"id": meta_b["id"], "scanned_at": meta_b["scanned_at"], "network": meta_b["network"]},
        "counts": {
            "online_new": len(added_keys),
            "online_gone": len(removed_keys),
        },
        **detail,
    }

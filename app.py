import csv
import io
import os
import platform
import subprocess
import time
from datetime import datetime
from typing import Optional, Set

from flask import Flask, Response, jsonify, make_response, render_template, request

from alert_webhook import post_json_webhook
from app_settings import load_settings, save_settings
from device_automation import run_automation
from device_fingerprint import DeviceFingerprintCollector
from log_lab import analyze_log_file
import scan_history_store
from scanner import NetworkScanner
from switch_port_monitor import SwitchPortMonitor
from wifi_analyzer import scan_wifi_surroundings
from wifi_metrics import get_wifi_status, run_iperf3_client

# WHY: 작업 디렉터리와 무관하게 항상 이 app.py 옆 templates/static만 사용 (다른 복사본 혼동 방지)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_TAG = "wifi17"

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)
scanner = NetworkScanner()
fingerprint_collector = DeviceFingerprintCollector()
switch_monitor = SwitchPortMonitor()
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# WHY: 선택적 접근 제어 — 환경변수가 없으면 기존과 동일(인증 없음)
_ACCESS_TOKEN = (os.environ.get("NETWORK_IP_SEARCH_TOKEN") or "").strip()

# WHY: 연속 스캔 간 온라인 집합 비교로 Webhook 알림(첫 스캔은 기준 없음)
_previous_online_keys: Optional[Set[str]] = None

_SETTINGS_PATCH_KEYS = frozenset(
    {
        "history_enabled",
        "history_max_snapshots",
        "history_min_interval_seconds",
        "alert_webhook_url",
        "alert_on_new_mac",
        "alert_on_mac_gone",
        "scan_profiles",
        "active_profile_id",
    }
)


def _abs_inventory_path(relative_or_abs: str) -> str:
    return (
        relative_or_abs
        if os.path.isabs(relative_or_abs)
        else os.path.join(BASE_DIR, relative_or_abs)
    )


def _effective_inventory_path(explicit: Optional[str]) -> str:
    """API/폼에서 넘긴 경로가 없으면 user_settings.json 기본값 사용."""
    if explicit and str(explicit).strip():
        return str(explicit).strip()
    return load_settings(BASE_DIR)["inventory_path"]


def _npcap_present():
    """Windows 에서만 레지스트리로 Npcap 설치 여부 추정."""
    if platform.system().lower() != "windows":
        return None
    try:
        r = subprocess.run(
            ["reg", "query", "HKLM\\SOFTWARE\\Npcap"],
            capture_output=True,
            timeout=5,
            check=False,
        )
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _effective_scan_cidr(settings: dict) -> Optional[str]:
    """활성 프로필의 CIDR이 있으면 사용, 없으면 None(스캐너 자동 탐지)."""
    active = (settings.get("active_profile_id") or "").strip()
    if not active:
        return None
    for profile in settings.get("scan_profiles") or []:
        if not isinstance(profile, dict):
            continue
        if (profile.get("id") or "").strip() != active:
            continue
        cidr = (profile.get("network_cidr") or "").strip()
        return cidr if cidr else None
    return None


def _active_profile_label(settings: dict) -> str:
    active = (settings.get("active_profile_id") or "").strip()
    if not active:
        return "자동"
    for profile in settings.get("scan_profiles") or []:
        if isinstance(profile, dict) and (profile.get("id") or "").strip() == active:
            return str(profile.get("name") or active).strip() or active
    return active


def _send_alerts_if_needed(settings: dict, prev_online: Set[str], curr_online: Set[str], result: dict) -> None:
    url = (settings.get("alert_webhook_url") or "").strip()
    if not url:
        return
    added, removed = scan_history_store.diff_online_sets(prev_online, curr_online)
    events = []
    if settings.get("alert_on_new_mac") and added:
        events.append({"type": "online_new", "keys": added})
    if settings.get("alert_on_mac_gone") and removed:
        events.append({"type": "online_gone", "keys": removed})
    if not events:
        return
    payload = {
        "source": "network-ip-search",
        "scanned_at": result.get("scanned_at"),
        "network": result.get("network"),
        "events": events,
    }
    post_json_webhook(url, payload)


def run_network_scan(timeout_seconds: int = 2) -> dict:
    """스캔 + 이력 저장 + Webhook 알림을 한 경로에서 처리합니다."""
    global _previous_online_keys
    st = load_settings(BASE_DIR)
    override_cidr = _effective_scan_cidr(st)
    started = time.perf_counter()
    result = scanner.scan(timeout_seconds=timeout_seconds, network_cidr_override=override_cidr)
    result["scan_duration_ms"] = int((time.perf_counter() - started) * 1000)

    devices = result.get("devices") or []
    curr_keys = scan_history_store.online_key_set(devices if isinstance(devices, list) else [])

    if _previous_online_keys is not None:
        _send_alerts_if_needed(st, _previous_online_keys, curr_keys, result)
    _previous_online_keys = set(curr_keys)

    if st.get("history_enabled"):
        scanned_at = str(result.get("scanned_at") or "")
        if scanned_at and scan_history_store.should_append_snapshot(
            BASE_DIR, int(st["history_min_interval_seconds"]), scanned_at
        ):
            scan_history_store.append_snapshot(BASE_DIR, result)
            scan_history_store.prune_old_snapshots(BASE_DIR, int(st["history_max_snapshots"]))

    return result


@app.before_request
def _optional_access_token():
    """NETWORK_IP_SEARCH_TOKEN 설정 시 API·페이지 접근에 토큰 필요."""
    if not _ACCESS_TOKEN:
        return None
    path = request.path or ""
    if path == "/api/health" or path.startswith("/api/health/"):
        return None
    if path.startswith("/api/build-info") or path == "/build-info" or path.startswith("/api/nwip-"):
        return None
    if path.startswith("/static"):
        return None
    provided = (request.headers.get("X-NetWork-IP-Token") or "").strip()
    if not provided:
        provided = (request.args.get("token") or "").strip()
    if provided == _ACCESS_TOKEN:
        return None
    if path.startswith("/api/"):
        return (
            jsonify(
                {"ok": False, "error": "인증이 필요합니다. X-NetWork-IP-Token 헤더 또는 token 쿼리."}
            ),
            401,
        )
    return Response(
        "인증이 필요합니다. 주소에 ?token=비밀값 을 붙이거나 문서를 참고하세요.",
        status=401,
        mimetype="text/plain; charset=utf-8",
    )


@app.after_request
def _disable_cache_for_dashboard(response):
    """WHY: 브라우저·중간 캐시가 예전 dashboard.html/CSS/JS를 붙잡는 경우가 많아 Wi-Fi 섹션이 안 보이는 것처럼 보입니다."""
    path = request.path or ""
    if (
        path == "/"
        or path == "/wifi"
        or path == "/settings"
        or path.startswith("/api/build-info")
        or path == "/build-info"
        or path.startswith("/api/nwip-")
        or path.startswith("/api/history")
        or path.endswith("dashboard.css")
        or path.endswith("dashboard.js")
    ):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


@app.get("/")
def dashboard():
    """대시보드 페이지를 렌더링합니다."""
    response = make_response(render_template("dashboard.html"))
    response.headers["X-NetWork-IP-Build"] = BUILD_TAG
    return response


@app.get("/wifi")
def wifi_tools_page():
    """Wi-Fi 링크·iperf·주변 AP 분석 전용 페이지."""
    response = make_response(render_template("wifi_dashboard.html"))
    response.headers["X-NetWork-IP-Build"] = BUILD_TAG
    return response


@app.route("/api/build-info", methods=["GET"])
@app.route("/build-info", methods=["GET"])
def build_info():
    """실행 중인 Flask가 읽는 파일 경로·Wi-Fi 템플릿 포함 여부(원인 조사용)."""
    template_path = os.path.join(BASE_DIR, "templates", "dashboard.html")
    wifi_panels_path = os.path.join(BASE_DIR, "templates", "_wifi_panels.html")
    ok_file = os.path.isfile(template_path)
    ok_wifi_panels = os.path.isfile(wifi_panels_path)
    has_wifi = False
    snippet = ""
    mtime = None
    if ok_file:
        mtime = datetime.fromtimestamp(os.path.getmtime(template_path)).isoformat(timespec="seconds")
        try:
            with open(template_path, encoding="utf-8") as handle:
                raw = handle.read()
            # WHY: 소스에는 url_for('wifi_tools_page')가 있어 렌더 결과와 달리 /wifi 문자열이 없을 수 있음
            has_wifi = "card-wifi" in raw and "wifi-refresh-button" in raw and "wifi_tools_page" in raw
            snippet = raw[:180].replace("\n", " ")
        except OSError as error:
            snippet = f"read_error:{error}"
    has_wifi_panels = False
    if ok_wifi_panels:
        try:
            with open(wifi_panels_path, encoding="utf-8") as handle:
                has_wifi_panels = "card-wifi-analyzer" in handle.read()
        except OSError:
            pass
    return jsonify(
        {
            "ok": True,
            "build_tag": BUILD_TAG,
            "app_py": os.path.abspath(__file__),
            "base_dir": BASE_DIR,
            "dashboard_template_path": template_path,
            "dashboard_template_exists": ok_file,
            "dashboard_template_mtime": mtime,
            "template_has_wifi_cta": has_wifi,
            "wifi_panels_path": wifi_panels_path,
            "wifi_panels_has_analyzer": has_wifi_panels,
            "template_preview_start": snippet,
            "diagnose_urls": [
                "/api/nwip-whoami",
                "/api/build-info",
                "/build-info",
                "/api/health",
            ],
        }
    )


@app.route("/api/nwip-whoami", methods=["GET"])
def nwip_whoami():
    """다른 Flask 앱과 구분용 최소 JSON(경로 짧고 고유)."""
    return jsonify(
        ok=True,
        service="network-ip-search",
        build_tag=BUILD_TAG,
        app_py=os.path.abspath(__file__),
    )


@app.get("/api/health")
def api_health():
    """로드밸런서·스크립트용 최소 헬스 체크(토큰이 있어도 인증 없이 허용)."""
    return jsonify(
        {
            "ok": True,
            "service": "network-ip-search",
            "time": datetime.now().isoformat(timespec="seconds"),
        }
    )


@app.get("/api/dashboard-summary")
def dashboard_summary():
    """대시보드 상단 요약 카드용: Npcap·인벤토리·마지막 스캔·토큰 설정 여부."""
    st = load_settings(BASE_DIR)
    inv = _effective_inventory_path(None)
    abs_inv = _abs_inventory_path(inv)
    last = scanner.last_scan_result or {}
    summary = last.get("summary") or {}
    scan_history_store.ensure_db(BASE_DIR)
    hist_meta = scan_history_store.list_snapshots(BASE_DIR, limit=1)
    hist_last = hist_meta[0] if hist_meta else None
    return jsonify(
        {
            "ok": True,
            "build_tag": BUILD_TAG,
            "npcap_installed": _npcap_present(),
            "inventory_path": inv,
            "inventory_exists": os.path.isfile(abs_inv),
            "access_token_configured": bool(_ACCESS_TOKEN),
            "last_scan_at": last.get("scanned_at"),
            "last_scan_online": summary.get("online_count"),
            "last_scan_total": summary.get("total_count"),
            "last_scan_duration_ms": last.get("scan_duration_ms"),
            "scan_interval_seconds": st["scan_interval_seconds"],
            "warning_from_last_scan": (last.get("warning_message") or "")[:500],
            "history_enabled": bool(st.get("history_enabled")),
            "history_last_snapshot_at": (hist_last or {}).get("scanned_at"),
            "active_profile_label": _active_profile_label(st),
        }
    )


@app.get("/api/settings")
def api_settings_get():
    return jsonify({"ok": True, "data": load_settings(BASE_DIR)})


@app.post("/api/settings")
def api_settings_post():
    payload = request.get_json(silent=True) or {}
    try:
        interval = payload.get("scan_interval_seconds")
        interval_int = int(interval) if interval is not None else None
    except (TypeError, ValueError):
        interval_int = None
    patch = {key: payload[key] for key in _SETTINGS_PATCH_KEYS if key in payload}
    save_settings(
        BASE_DIR,
        inventory_path=payload.get("inventory_path"),
        scan_interval_seconds=interval_int,
        extra=patch if patch else None,
    )
    return jsonify({"ok": True, "data": load_settings(BASE_DIR)})


@app.get("/settings")
def settings_page():
    """인벤토리 경로·스캔 주기 설정(로컬 JSON 저장)."""
    return render_template("settings.html")


@app.get("/api/scan")
def scan_network():
    """네트워크 장치 목록을 JSON으로 반환합니다."""
    try:
        result = run_network_scan(timeout_seconds=2)
        return jsonify({"ok": True, "data": result})
    except ValueError as error:
        return jsonify({"ok": False, "error": str(error)}), 400
    except PermissionError:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "권한 오류: 관리자 권한(또는 sudo)으로 실행해야 Scapy 스캔이 가능합니다.",
                }
            ),
            403,
        )
    except Exception as error:
        return jsonify({"ok": False, "error": f"스캔 실패: {str(error)}"}), 500


@app.get("/api/export/csv")
def export_csv():
    """가장 최근 스캔 결과를 CSV로 내보냅니다."""
    try:
        if not scanner.last_scan_result:
            run_network_scan(timeout_seconds=2)

        result = scanner.last_scan_result
        csv_stream = io.StringIO()
        csv_writer = csv.writer(csv_stream)
        csv_writer.writerow(
            [
                "status",
                "ip",
                "mac",
                "vendor",
                "open_ports",
                "model",
                "serial_number",
                "hostname",
                "last_seen",
            ]
        )

        for device in result.get("devices", []):
            csv_writer.writerow(
                [
                    device.get("status", ""),
                    device.get("ip", ""),
                    device.get("mac", ""),
                    device.get("vendor", ""),
                    ",".join(str(port) for port in device.get("open_ports", [])),
                    device.get("model", ""),
                    device.get("serial_number", ""),
                    device.get("hostname", ""),
                    device.get("last_seen", ""),
                ]
            )

        csv_content = csv_stream.getvalue()
        filename = f"network_scan_{result.get('scanned_at', 'unknown').replace(':', '-')}.csv"
        return Response(
            csv_content,
            mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ValueError as error:
        return jsonify({"ok": False, "error": str(error)}), 400
    except PermissionError:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "권한 오류: 관리자 권한(또는 sudo)으로 실행해야 CSV 내보내기 스캔이 가능합니다.",
                }
            ),
            403,
        )
    except Exception as error:
        return jsonify({"ok": False, "error": f"CSV 내보내기 실패: {str(error)}"}), 500


@app.post("/api/log/analyze")
def analyze_log():
    """업로드된 로그를 AI 분석 친화 포맷으로 가공합니다."""
    try:
        uploaded_file = request.files.get("log_file")
        if uploaded_file is None or not uploaded_file.filename:
            return jsonify({"ok": False, "error": "로그 파일이 업로드되지 않았습니다."}), 400

        safe_name = uploaded_file.filename.replace("..", "_").replace("/", "_").replace("\\", "_")
        timestamp_prefix = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_path = os.path.join(UPLOAD_DIR, f"{timestamp_prefix}_{safe_name}")
        uploaded_file.save(saved_path)

        output_directory = os.path.join(OUTPUT_DIR, f"log_{timestamp_prefix}")
        result = analyze_log_file(saved_path, output_directory)
        return jsonify({"ok": True, "data": result})
    except Exception as error:
        return jsonify({"ok": False, "error": f"로그 분석 실패: {str(error)}"}), 500


@app.post("/api/automation/run")
def run_device_automation():
    """자연어 지시 기반 다중 장비 자동화를 실행합니다."""
    try:
        payload = request.get_json(silent=True) or {}
        instruction_text = payload.get("instruction", "").strip()
        if not instruction_text:
            return jsonify({"ok": False, "error": "instruction 값이 비어 있습니다."}), 400

        inventory_path = _effective_inventory_path(payload.get("inventory_path"))
        absolute_inventory_path = _abs_inventory_path(inventory_path)
        if not os.path.exists(absolute_inventory_path):
            return jsonify(
                {
                    "ok": False,
                    "error": f"인벤토리 파일을 찾지 못했습니다: {absolute_inventory_path}",
                }
            ), 400

        dry_run = bool(payload.get("dry_run", True))
        timestamp_prefix = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_directory = os.path.join(OUTPUT_DIR, f"automation_{timestamp_prefix}")
        result = run_automation(
            instruction_text=instruction_text,
            inventory_path=absolute_inventory_path,
            output_directory=output_directory,
            dry_run=dry_run,
        )
        return jsonify({"ok": True, "data": result})
    except Exception as error:
        return jsonify({"ok": False, "error": f"자동화 실행 실패: {str(error)}"}), 500


@app.post("/api/device/fingerprint")
def collect_device_fingerprint():
    """온라인 장비의 모델/시리얼 정보를 수집합니다."""
    try:
        payload = request.get_json(silent=True) or {}
        inventory_path = _effective_inventory_path(payload.get("inventory_path"))
        absolute_inventory_path = _abs_inventory_path(inventory_path)
        if not os.path.exists(absolute_inventory_path):
            absolute_inventory_path = None

        scan_result = run_network_scan(timeout_seconds=2)
        enrichment_result = fingerprint_collector.enrich_devices(
            devices=scan_result.get("devices", []),
            inventory_path=absolute_inventory_path,
        )
        scan_result["devices"] = enrichment_result["devices"]
        scan_result["fingerprint_collected_at"] = enrichment_result["collected_at"]
        scan_result["fingerprint_summary"] = enrichment_result.get("summary", {})
        return jsonify({"ok": True, "data": scan_result})
    except ValueError as error:
        return jsonify({"ok": False, "error": str(error)}), 400
    except Exception as error:
        return jsonify({"ok": False, "error": f"장비 정보 수집 실패: {str(error)}"}), 500


@app.get("/api/history/snapshots")
def history_snapshots_list():
    """저장된 스캔 스냅샷 메타 목록."""
    try:
        limit = request.args.get("limit", default=50, type=int)
        rows = scan_history_store.list_snapshots(BASE_DIR, limit=limit or 50)
        return jsonify({"ok": True, "data": rows})
    except Exception as error:
        return jsonify({"ok": False, "error": f"이력 조회 실패: {str(error)}"}), 500


@app.get("/api/history/diff")
def history_diff():
    """
    스냅샷 간 또는 스냅샷 vs 현재 마지막 스캔 결과 diff.
    Query: from_id (필수), to_id (선택 — 없으면 scanner.last_scan_result 와 비교)
    """
    from_id = request.args.get("from_id", type=int)
    if not from_id:
        return jsonify({"ok": False, "error": "from_id 쿼리가 필요합니다."}), 400
    to_id = request.args.get("to_id", type=int)
    try:
        if to_id:
            data = scan_history_store.diff_two_snapshots(BASE_DIR, from_id, to_id)
        else:
            if not scanner.last_scan_result:
                return (
                    jsonify(
                        {
                            "ok": False,
                            "error": "현재 스캔 결과가 없습니다. 대시보드에서 스캔 후 다시 시도하세요.",
                        }
                    ),
                    400,
                )
            data = scan_history_store.diff_snapshot_to_current(
                BASE_DIR, from_id, scanner.last_scan_result
            )
        if not data:
            return jsonify({"ok": False, "error": "스냅샷을 찾을 수 없습니다."}), 404
        return jsonify({"ok": True, "data": data})
    except Exception as error:
        return jsonify({"ok": False, "error": f"diff 실패: {str(error)}"}), 500


@app.get("/api/wifi/status")
def wifi_status():
    """Windows netsh 기반 Wi-Fi 링크(협상 속도) 상태를 반환합니다."""
    try:
        data = get_wifi_status()
        return jsonify({"ok": True, "data": data})
    except Exception as error:
        return jsonify({"ok": False, "error": f"Wi-Fi 상태 조회 실패: {str(error)}"}), 500


@app.get("/api/wifi/analyze")
def wifi_analyze():
    """
    주변 AP(BSSID) 스캔 + 채널·밴드 집계 (Wi-Fi Analyzer 스타일).
    Query: refresh=1 → netsh wlan refresh 시도, merge=1 → 현재 연결 정보·동일 채널 AP 수 힌트 포함.
    """
    try:
        refresh = str(request.args.get("refresh", "0")).lower() in ("1", "true", "yes")
        merge = str(request.args.get("merge", "1")).lower() in ("1", "true", "yes")
        data = scan_wifi_surroundings(refresh_scan=refresh, merge_current_link=merge)
        return jsonify({"ok": True, "data": data})
    except Exception as error:
        return jsonify({"ok": False, "error": f"Wi-Fi 분석 실패: {str(error)}"}), 500


@app.post("/api/wifi/iperf")
def wifi_iperf():
    """선택적 iperf3 클라이언트 측정(서버에 iperf3 -s 필요)."""
    try:
        payload = request.get_json(silent=True) or {}
        host = (payload.get("host") or "").strip()
        port_raw = payload.get("port", 5201)
        duration_raw = payload.get("duration_seconds", 5)
        try:
            port_value = int(port_raw)
        except (TypeError, ValueError):
            port_value = 5201
        try:
            duration_value = int(duration_raw)
        except (TypeError, ValueError):
            duration_value = 5

        result = run_iperf3_client(host, port_value, duration_value)
        if not result.get("ok"):
            return (
                jsonify({"ok": False, "error": result.get("error", "iperf3 실패")}),
                400,
            )
        return jsonify({"ok": True, "data": result})
    except Exception as error:
        return jsonify({"ok": False, "error": f"iperf3 요청 실패: {str(error)}"}), 500


@app.get("/api/switch/ports")
def get_switch_ports():
    """스위치 포트 UP/DOWN 상태를 SNMP Walk로 수집해 반환합니다."""
    try:
        inventory_path = _effective_inventory_path(request.args.get("inventory_path"))
        absolute_path = _abs_inventory_path(inventory_path)
        if not os.path.exists(absolute_path):
            return jsonify({"ok": False, "error": f"인벤토리 파일 없음: {absolute_path}"}), 400

        results = switch_monitor.poll(inventory_path=absolute_path)
        return jsonify({"ok": True, "data": results})
    except Exception as error:
        return jsonify({"ok": False, "error": f"포트 조회 실패: {str(error)}"}), 500


if __name__ == "__main__":
    # WHY: debug=False로 설정해 운영 환경에서 디버거 노출을 차단합니다.
    # WHY: PaaS(Railway 등)는 PORT 를 주고, 로컬은 NETWORK_IP_SEARCH_PORT 우선
    _port = int(os.environ.get("NETWORK_IP_SEARCH_PORT") or os.environ.get("PORT") or "8500")
    _tpl = os.path.join(BASE_DIR, "templates", "dashboard.html")
    print(f"[NetWork-IP Search] BUILD={BUILD_TAG}")
    print(f"[NetWork-IP Search] app.py = {os.path.abspath(__file__)}")
    print(f"[NetWork-IP Search] dashboard.html = {_tpl}")
    print(f"[NetWork-IP Search] 템플릿 존재 = {os.path.isfile(_tpl)}")
    if os.path.isfile(_tpl):
        with open(_tpl, encoding="utf-8") as _f:
            _s = _f.read()
        # WHY: 메인 / 에서는 Wi-Fi 카드를 뺐고 /wifi + _wifi_panels.html 로만 제공합니다(False 가 정상).
        _wifi_analyzer_in_main = "card-wifi-analyzer" in _s
        print(
            f"[NetWork-IP Search] 메인 dashboard.html 안에 Wi-Fi 분석기 카드 = {_wifi_analyzer_in_main} "
            f"(False면 정상 — Wi-Fi 도구: http://127.0.0.1:{_port}/wifi)"
        )
    print(
        f"[NetWork-IP Search] 수신 포트 = {_port} (NETWORK_IP_SEARCH_PORT 또는 표준 PORT 환경변수)"
    )
    print(
        f"[NetWork-IP Search] 진단 JSON: http://127.0.0.1:{_port}/api/nwip-whoami "
        f"(404면 {_port} 포트에 이 app.py가 아닌 다른 서버가 떠 있습니다)"
    )
    _diag = [r.rule for r in app.url_map.iter_rules() if "nwip" in r.rule or r.rule.endswith("build-info")]
    print(f"[NetWork-IP Search] 등록된 진단 경로: {_diag}")
    if _ACCESS_TOKEN:
        print("[NetWork-IP Search] 접근 토큰 사용 중 — API 헤더 X-NetWork-IP-Token 또는 ?token= 필요")
    app.run(host="0.0.0.0", port=_port, debug=False, use_reloader=False)

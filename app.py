import csv
import io
import os
from datetime import datetime

from flask import Flask, Response, jsonify, make_response, render_template, request

from device_automation import run_automation
from device_fingerprint import DeviceFingerprintCollector
from log_lab import analyze_log_file
from scanner import NetworkScanner
from switch_port_monitor import SwitchPortMonitor
from wifi_analyzer import scan_wifi_surroundings
from wifi_metrics import get_wifi_status, run_iperf3_client

# WHY: 작업 디렉터리와 무관하게 항상 이 app.py 옆 templates/static만 사용 (다른 복사본 혼동 방지)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_TAG = "wifi8"

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


@app.after_request
def _disable_cache_for_dashboard(response):
    """WHY: 브라우저·중간 캐시가 예전 dashboard.html/CSS/JS를 붙잡는 경우가 많아 Wi-Fi 섹션이 안 보이는 것처럼 보입니다."""
    path = request.path or ""
    if (
        path == "/"
        or path == "/wifi"
        or path.startswith("/api/build-info")
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


@app.get("/api/build-info")
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
            has_wifi = "card-wifi-cta" in raw and "wifi_tools_page" in raw
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
        }
    )


@app.get("/api/scan")
def scan_network():
    """네트워크 장치 목록을 JSON으로 반환합니다."""
    try:
        result = scanner.scan(timeout_seconds=2)
        return jsonify({"ok": True, "data": result})
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
            scanner.scan(timeout_seconds=2)

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

        inventory_path = payload.get("inventory_path", "devices.example.yaml")
        absolute_inventory_path = (
            inventory_path
            if os.path.isabs(inventory_path)
            else os.path.join(BASE_DIR, inventory_path)
        )
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
        inventory_path = payload.get("inventory_path", "devices.example.yaml")
        absolute_inventory_path = (
            inventory_path
            if os.path.isabs(inventory_path)
            else os.path.join(BASE_DIR, inventory_path)
        )
        if not os.path.exists(absolute_inventory_path):
            absolute_inventory_path = None

        scan_result = scanner.scan(timeout_seconds=2)
        enrichment_result = fingerprint_collector.enrich_devices(
            devices=scan_result.get("devices", []),
            inventory_path=absolute_inventory_path,
        )
        scan_result["devices"] = enrichment_result["devices"]
        scan_result["fingerprint_collected_at"] = enrichment_result["collected_at"]
        scan_result["fingerprint_summary"] = enrichment_result.get("summary", {})
        return jsonify({"ok": True, "data": scan_result})
    except Exception as error:
        return jsonify({"ok": False, "error": f"장비 정보 수집 실패: {str(error)}"}), 500


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
        inventory_path = request.args.get("inventory_path", "devices.example.yaml")
        absolute_path = (
            inventory_path
            if os.path.isabs(inventory_path)
            else os.path.join(BASE_DIR, inventory_path)
        )
        if not os.path.exists(absolute_path):
            return jsonify({"ok": False, "error": f"인벤토리 파일 없음: {absolute_path}"}), 400

        results = switch_monitor.poll(inventory_path=absolute_path)
        return jsonify({"ok": True, "data": results})
    except Exception as error:
        return jsonify({"ok": False, "error": f"포트 조회 실패: {str(error)}"}), 500


if __name__ == "__main__":
    # WHY: debug=False로 설정해 운영 환경에서 디버거 노출을 차단합니다.
    _tpl = os.path.join(BASE_DIR, "templates", "dashboard.html")
    print(f"[NetWork-IP Search] BUILD={BUILD_TAG}")
    print(f"[NetWork-IP Search] app.py = {os.path.abspath(__file__)}")
    print(f"[NetWork-IP Search] dashboard.html = {_tpl}")
    print(f"[NetWork-IP Search] 템플릿 존재 = {os.path.isfile(_tpl)}")
    if os.path.isfile(_tpl):
        with open(_tpl, encoding="utf-8") as _f:
            _s = _f.read()
        print(f"[NetWork-IP Search] Wi-Fi 분석기 섹션 포함 = {'card-wifi-analyzer' in _s}")
    _port = int(os.environ.get("NETWORK_IP_SEARCH_PORT", "5000"))
    print(f"[NetWork-IP Search] 수신 포트 = {_port} (환경변수 NETWORK_IP_SEARCH_PORT 로 변경 가능)")
    app.run(host="0.0.0.0", port=_port, debug=False, use_reloader=False)

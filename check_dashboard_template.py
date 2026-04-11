"""
로컬 disk에 있는 템플릿이 메인 대시보드 + Wi-Fi 패널 구조를 만족하는지 검사합니다.
WHY: 구글 드라이브 동기화·다른 복사본 실행 시 패널이 빠질 수 있습니다.
"""
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
DASHBOARD = os.path.join(BASE, "templates", "dashboard.html")
PANELS = os.path.join(BASE, "templates", "_wifi_panels.html")
WIFI_PAGE = os.path.join(BASE, "templates", "wifi_dashboard.html")


def main() -> int:
    print(f"[check] 폴더: {BASE}")
    errors = []

    if not os.path.isfile(DASHBOARD):
        errors.append("dashboard.html 없음")
    else:
        with open(DASHBOARD, encoding="utf-8") as handle:
            dash = handle.read()
        if '_wifi_panels.html' not in dash:
            errors.append('dashboard.html 에 {% include "_wifi_panels.html" %} 없음')
        if "wifi_tools_page" not in dash:
            errors.append("dashboard.html 에 url_for('wifi_tools_page') 없음")
        if "card-scan-history" not in dash:
            errors.append("dashboard.html 에 스캔 이력 카드(card-scan-history) 없음")

    if not os.path.isfile(PANELS):
        errors.append("_wifi_panels.html 없음")
    else:
        with open(PANELS, encoding="utf-8") as handle:
            pan = handle.read()
        if "card-wifi-analyzer" not in pan:
            errors.append("_wifi_panels.html 에 card-wifi-analyzer 없음")
        if "wifi-iperf-button" not in pan:
            errors.append("_wifi_panels.html 에 iperf3 버튼 없음")

    if not os.path.isfile(WIFI_PAGE):
        errors.append("wifi_dashboard.html 없음")

    if errors:
        for line in errors:
            print(f"[check] 오류: {line}")
        return 2
    print("[check] OK: 메인 include Wi-Fi 패널 + wifi_dashboard 존재")
    return 0


if __name__ == "__main__":
    sys.exit(main())

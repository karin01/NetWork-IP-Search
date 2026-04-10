"""
로컬 disk에 있는 템플릿이 Wi-Fi 분리 구조(wifi8)를 만족하는지 검사합니다.
WHY: 구글 드라이브 동기화·다른 복사본 실행 시 패널/CTA가 빠질 수 있습니다.
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
        if "card-wifi-cta" not in dash:
            errors.append("dashboard.html 에 Wi-Fi CTA(card-wifi-cta) 없음")
        if "wifi_tools_page" not in dash:
            errors.append("dashboard.html 에 url_for('wifi_tools_page') 없음")
        if "card-wifi-analyzer" in dash:
            errors.append("dashboard.html 에 옛 Wi-Fi 분석기가 남아 있음(별도 페이지로 옮겨야 함)")

    if not os.path.isfile(PANELS):
        errors.append("_wifi_panels.html 없음")
    else:
        with open(PANELS, encoding="utf-8") as handle:
            pan = handle.read()
        if "card-wifi-analyzer" not in pan:
            errors.append("_wifi_panels.html 에 card-wifi-analyzer 없음")

    if not os.path.isfile(WIFI_PAGE):
        errors.append("wifi_dashboard.html 없음")

    if errors:
        for line in errors:
            print(f"[check] 오류: {line}")
        return 2
    print("[check] OK: 메인 CTA + _wifi_panels + wifi_dashboard 존재")
    return 0


if __name__ == "__main__":
    sys.exit(main())

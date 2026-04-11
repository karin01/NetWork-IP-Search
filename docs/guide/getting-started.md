# 시작하기

::: tip Pages 구조와 로컬 대시보드
**GitHub Pages 루트**(`…/NetWork-IP-Search/`)는 소개용 웹 페이지이고, **지금 읽는 곳**은 **문서**(`/manual/`)입니다. 장치 목록·그래프·Wi‑Fi 화면은 **자기 PC에서 서버**를 실행한 뒤 `http://127.0.0.1:5000` 으로 접속하세요.
:::

**서버 실행만 따로 보기:** [Flask 서버 실행하기 (대시보드)](/guide/flask-server) — 배치 파일, 수동 명령, 포트 변경, 오류 대응까지 모아 두었습니다.  
**스위치 포트:** [스위치 포트 (벤더별)](/guide/switch-ports) — Cisco·Juniper·HPE·유비쿼티·다산·Dovado/다보링크 등 SNMP 요약.

## 0. 한 번에 열기 (Windows)

프로젝트 폴더에서 **`run_dashboard.bat`** 또는 **`대시보드 열기.bat`** 을 실행합니다.  
검은 창에 Flask가 뜨면 브라우저에서 **http://127.0.0.1:5000** 을 엽니다. Wi‑Fi 전용은 **http://127.0.0.1:5000/wifi** 입니다.

## 1. 설치

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 2. 서버 실행

```bash
python app.py
```

## 3. 대시보드 접속

- 이 PC: `http://127.0.0.1:5000`
- 같은 Wi‑Fi의 휴대폰 등: `http://<이 PC의 IPv4>:5000` (방화벽에서 포트 허용 필요할 수 있음)

## 4. 권장 사항

- Windows에서 ARP 정밀 스캔: [Npcap](https://npcap.com/) 설치 + 필요 시 관리자 실행

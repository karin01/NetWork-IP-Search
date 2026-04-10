# 네트워크 스캐너 작업 기록

## 2026-04-10

- Scapy 기반 LAN 장치 스캐너(`scanner.py`) 구현
- Flask API/대시보드(`app.py`, `templates/dashboard.html`, `static/*`) 구현
- 장치 상태(online/offline) 판별 및 유예 시간 로직 적용
- 실행/설치 문서(`README.md`) 작성
- OUI 기반 벤더 추정 기능 추가
- CSV 내보내기 API(`/api/export/csv`) 추가
- 접속 이력 그래프(온라인/오프라인/총량) 추가
- Npcap/WinPcap 미설치 시 ping 폴백 스캔 추가
- 폴백 모드 안내용 경고 메시지 UI 추가
- 장치별 열린 포트 스캔/표시 기능 추가(주요 포트 + 캐시)
- 로그 분석 모듈(`log_lab.py`) 추가: txt/csv/pcap -> JSONL/summary 가공
- 자연어 기반 다중 장비 자동화 모듈(`device_automation.py`) 추가
- 대시보드에 로그 분석/자동화 실행 UI 추가
- VitePress 기반 기술 문서 사이트(`docs/`) 구성
- 장비 모델/시리얼 수집 모듈(`device_fingerprint.py`) 추가
- SNMP/SSH 기반 장비 식별 API(`/api/device/fingerprint`) 추가
- 대시보드에 모델/시리얼 컬럼 및 수집 버튼 추가
- SNMPv3 우선 수집 + SNMPv2c 보조 로직 확장
- Cisco/Juniper/HPE 벤더별 SSH 명령 템플릿 및 정밀 파서 추가
- 수집 성공률/실패 사유 집계 및 대시보드 카드 추가
- Netmiko 기반 장비 설정 백업/보안 감사 도구(`network_ops/backup_configs.py`) 추가
- FastAPI + Streamlit 기반 CIDR IP 스캔 대시보드(`network_ops/scan_api.py`, `network_ops/scan_dashboard.py`) 추가
- CIDR 네트워크 대역 계산 API/대시보드 기능(`/subnet/calc`) 추가
- `대시보드 열기.bat` CMD 인코딩/주석 파싱 오류 수정(chcp 65001, ASCII REM, 관리자 재실행 PowerShell 안정화)
- 스위치 포트 모니터(`switch_port_monitor.py`): `poll()` 인벤토리 로딩 단순화, SNMP 실패 시 Cisco SSH(`show interfaces status`+TextFSM) 보조, 수집 소스(snmp/ssh) 표시

## 2026-04-11

- Wi-Fi 링크 정보 모듈(`wifi_metrics.py`): Windows `netsh wlan show interfaces` 파싱(UTF-8/cp949 디코딩, 다중 어댑터 블록 분리), 선택적 `iperf3 -c ... -J` 처리량 요약
- Flask API: `GET /api/wifi/status`, `POST /api/wifi/iperf`
- 대시보드: `Wi-Fi 링크 · 처리량` 카드(수동 새로고침, iperf3 IP/포트/시간 입력), 그리드 영역 `wifi` 추가 및 반응형(1100px 이하)에 `switch` 행 보강
- `README.md` Wi-Fi/iperf3 API 섹션(기존 9~10번 절 번호 조정)
- Wi-Fi 분석기(`wifi_analyzer.py`): `netsh wlan show networks mode=bssid` 파싱·채널/밴드 집계·2.4GHz 1·6·11 혼잡도 점수(근사), 현재 연결 SSID/채널과 동일 채널 AP 수 힌트(`merge=1`)
- API `GET /api/wifi/analyze`, 대시보드 카드 `Wi-Fi 분석기`(주변 AP 스캔, 선택 `refresh`), 그리드 영역 `wifian`
- Wi-Fi 카드가 안 보이는 현상 대응: `dashboard.css` 그리드에서 고정 `grid-template-rows` 제거·`grid-auto-rows` 지정, 정적 파일 `?v=wifi2` 캐시 무효화, 상단 바 `Wi-Fi` / `Wi-Fi 분석` 앵커 링크 추가
- Wi-Fi 분석기: 채널별 AP 수 막대 그래프(`canvas` + DPR 대응), SSID 부분 일치 필터·지우기·`<datalist>` 자동완성, 창 리사이즈 시 차트 재그리기 (`?v=wifi3`)
- Wi-Fi 분석기 확장: 2.4/5 GHz **분리 차트**, **밴드·BSSID 필터**, **테이블 열 클릭 정렬**, **필터 결과 CSV**, 필터 초기화 일괄 적용 (`?v=wifi4`)
- Wi-Fi 분석기 추가: **스캔 후 필터 유지** 체크, **연결 SSID로** 빠른 필터(merge 응답), 표 **신호 막대**, 차트 **가로 눈금·막대 개수 라벨**, **필터 결과 JSON**·**표 복사(TSV)**·토스트 안내 (`?v=wifi5`)
- 예전 화면만 보이는 문제 대응: Flask `after_request`로 `/`·`dashboard.css`·`dashboard.js` **Cache-Control: no-store**, HTML meta no-cache, 부제 **빌드 Wi-Fi+wifi6** 표시, `대시보드 열기.bat`에서 Flask를 **별도 cmd 창**으로 실행(포트 충돌 확인)·안내 문구·`?nocache=1`로 브라우저 열기 (`?v=wifi6`)
- 추가 진단: `Flask` **절대 경로** `template_folder`/`static_folder`, `GET /api/build-info`, 시작 시 콘솔 로그, `check_dashboard_template.py`, 배치에서 검사 후 실행·**venv python 우선**, `BUILD_TAG=wifi7`·`X-NetWork-IP-Build` 헤더, 포트 `NETWORK_IP_SEARCH_PORT` 환경변수
- **Wi-Fi 별도 페이지** (`wifi8`): 메인 `/` 에서 Wi-Fi 카드 제거 → 전폭 CTA + 상단 **Wi-Fi 도구** 링크, `GET /wifi`·`templates/wifi_dashboard.html`·`templates/_wifi_panels.html` include, `/wifi`도 no-store 캐시, `dashboard.js`는 `/wifi`에서 장치 스캔 폴링 미실행, `build-info`에 `template_has_wifi_cta`·`wifi_panels_has_analyzer` 필드
- `대시보드 열기.bat` 안내 `echo` 줄에 **ASCII 큰따옴표**(`"Wi-Fi …"`)가 들어가 CMD가 문자열을 잘못 닫아 **이후 줄 전체가 파싱 오류**(`http:`·`Wi-Fi`를 명령으로 인식 등)로 깨짐 → 안내 문구에서 따옴표 제거로 수정
- UAC 재실행: `powershell -Command "Start-Process -Verb RunAs …"` 는 환경에 따라 CMD가 `Start`/`Process`로 **토큰 분리**(`Process`는 내부 또는 외부 명령 아님, `full was unexpected` 등) → **임시 VBS + ShellExecute runas**로 변경; Npcap 안내 문구의 `for full scan` 제거(괄호 블록 안 `for`/`full` 파싱 리스크); `start` 창 제목의 `:5000` 콜론 제거
- CMD는 **`chcp 65001`보다 먼저** 배치 소스를 **시스템 기본 ANSI 코드페이지**로 읽습니다. UTF-8(또는 한글)이 섞인 `.bat`은 한 글자씩 잘려 `'M'`, `'f'`, 깨진 한글 명령·Flask `No such command`까지 유발 → **`대시보드 열기.bat`는 ASCII 전용**으로 통일(안내는 영문; 한글 안내는 README/옵시디언 참고)
- `The system cannot find the path specified` 두 번: (1) 구글 드라이브 등 **폴더 미동기화**로 `cd` 실패 (2) **`call .venv\Scripts\activate.bat`** 가 설치 당시 절대 경로로 `cd` 재시도 → **`activate.bat` 호출 제거**, `cd` 후 **`PROJROOT=%CD%`** 로 `start`/`python` 인용부호 깨짐(`\"`) 방지, `app.py` 없으면 안내 후 종료
- 한글 파일명 `대시보드 열기.bat` + 구글 드라이브 한글 경로: CMD가 **본문을 UTF-8로 잘못 읽으면** `setlocal`→`tlocal`, UAC는 **경로 깨짐** → 실제 로직은 **`run_dashboard.bat`(ASCII 이름)** 로 분리, UAC는 **`%%~sI` 짧은 경로**로 `ShellExecute`, 한글 배치는 `call "%~dp0run_dashboard.bat"` 3줄만 유지(본문 전부 ASCII)
- VBS `ShellExecute` + 한글 경로는 여전히 **경로 깨짐**(run_dashboard.bat 찾을 수 없음) → **`run_dashboard.bat`에서 자동 관리자 승격 제거**, ARP 필요 시 **우클릭 관리자 실행** 안내; `대시보드 열기.bat`은 **`pushd "%~dp0"` 후 `call run_dashboard.bat`**(상대 경로만 넘김)
- `. was unexpected at this time`: `if (...)` **괄호 블록 안의 `echo` 문에 리터럴 `(` `)`** 가 있으면 CMD가 블록을 중간에 끊음 → `(folder ...)` 등은 **`^(` `^)`** 로 이스케이프
- `python: can't open file 'G:\\내'`: 한글·공백 경로에서 `start cmd /k "cd ... && python ...\app.py"` **중첩 따옴표가 깨져** 스크립트 경로가 `G:\내` 로 잘림 → **`start /D "%PROJROOT%" cmd /k ""%PYEXE%" app.py"`** (작업 폴더만 지정, `app.py`는 상대 경로)
- GitHub Pages: VitePress `docs/` 배포 — 처음은 `upload-pages-artifact`+`deploy-pages`+Pages 소스 *GitHub Actions* 조합에서 404 다수 → **`peaceiris/actions-gh-pages` 로 `gh-pages` 브랜치 푸시**로 변경; Settings → Pages → **Deploy from branch → gh-pages / (root)**; `config.mjs` 의 `base` 는 `GITHUB_ACTIONS` 일 때만 `/NetWork-IP-Search/`

## 운영 메모

- 관리자 권한 부족 시 `/api/scan`에서 권한 오류를 반환하도록 처리함
- 일부 장치는 ARP 응답이 없을 수 있어 탐지 누락 가능성이 있음

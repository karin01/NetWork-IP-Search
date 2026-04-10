# NetWork-IP Search

Scapy를 사용해 현재 네트워크의 장치를 탐지하고, IP/연결 상태를 대시보드로 보여주는 Python 앱입니다.

## 1) 설치

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 2) 실행

```bash
python app.py
```

브라우저에서 `http://127.0.0.1:5000` 접속

## 3) 주요 기능

- 현재 네트워크 CIDR 자동 식별
- Scapy ARP 스캔으로 장치 탐지
- 장치별 IP / MAC / 벤더(OUI 기반) / 열린 포트 / 모델 / 시리얼 / 호스트명 표시
- 온라인/오프라인 상태 표시(유예 시간 기반)
- 10초 주기 자동 갱신 + 수동 새로고침 버튼
- 스캔 결과 CSV 다운로드
- 온라인/오프라인/총 장치 수 접속 이력 그래프
- Npcap 미설치 환경에서 ping 기반 폴백 스캔(경고 메시지 표시)
- 주요 포트(예: 22, 80, 443, 3389 등) 개방 여부 표시 및 CSV 포함
- Wireshark/텍스트/CSV 로그를 AI 분석 친화 포맷(JSONL)으로 가공
- 자연어 기반 다중 장비 자동화(기본 드라이런)
- VitePress 기반 기술 매뉴얼 사이트(`docs/`)
- 스위치 **물리 포트 UP/DOWN**: 대시보드 하단「스위치 포트 현황」→ `포트 조회` (SNMP IF-MIB, Cisco는 SNMP 실패 시 SSH 보조)
- **Wi-Fi**: Windows `netsh wlan show interfaces`로 협상 링크 속도(참고) 표시, 선택적으로 `iperf3` 실측 (`Wi-Fi 링크 · 처리량` 카드)
- **Wi-Fi 분석기**: `netsh` BSSID 스캔으로 주변 AP·채널 혼잡도 요약 (Wi-Fi Analyzer 유사, `Wi-Fi 분석기` 카드) — 2.4/5 GHz 분리 차트·눈금·막대 값, SSID·밴드·BSSID 필터·연결 SSID 단축·스캔 후 필터 유지, 표 정렬·신호 막대, CSV/JSON/클립보드(TSV)

## 4) 주의사항

- Windows에서는 관리자 권한 터미널에서 실행해야 스캔이 정상 동작할 수 있습니다.
- 방화벽/네트워크 정책에 따라 일부 장치는 응답하지 않을 수 있습니다.
- ARP 정밀 스캔을 원하면 Npcap 설치가 필요합니다: [Npcap 다운로드](https://npcap.com/#download)

## 5) 로그 분석 API

- `POST /api/log/analyze`
- form-data 키: `log_file`
- 결과: 요약 통계 + `ai_ready.jsonl`, `summary.json` 출력 파일 경로

## 6) 장비 자동화 API

- `POST /api/automation/run`
- JSON 예시:

```json
{
  "instruction": "모든 장비에서 최근 로그를 수집해줘",
  "inventory_path": "devices.example.yaml",
  "dry_run": true
}
```

## 7) 장비 모델/시리얼 수집 API

- `POST /api/device/fingerprint`
- JSON 예시:

```json
{
  "inventory_path": "devices.example.yaml"
}
```
- 동작 방식: SNMPv3 우선, v2c 보조, 실패 시 SSH CLI 파싱 보조
- 벤더별 SSH 템플릿/정밀 파서 지원: Cisco / Juniper / HPE
- 응답에 수집 성공률/실패 사유 집계(`fingerprint_summary`) 포함
- 주의: 실제 장비 정보 수집을 위해 `devices.example.yaml`에 SNMP/SSH 자격 정보가 필요합니다.

## 8) 스위치 포트 UP/DOWN API

- `GET /api/switch/ports?inventory_path=devices.example.yaml`
- 인벤토리의 각 장비 IP에 대해 SNMP(IF-MIB)로 포트별 `oper_status` / `admin_status` 수집
- `vendor`에 `cisco`가 포함되면 SNMP 실패 시 SSH로 `show interfaces status`(TextFSM) 보조
- 응답 항목에 `source`: `snmp` | `ssh_cisco` | `none`

## 9) Wi-Fi 링크 / iperf3 API

- `GET /api/wifi/status` — Windows에서 `netsh`로 무선 인터페이스별 SSID·신호·수신/송신 협상 Mbps 등 반환(실제 인터넷 속도와 다를 수 있음).
- `POST /api/wifi/iperf` — JSON 예시:

```json
{
  "host": "192.168.0.10",
  "port": 5201,
  "duration_seconds": 5
}
```

- 대상 PC에 `iperf3`가 PATH에 있어야 하며, 측정 서버에서 `iperf3 -s` 실행이 필요합니다. 설치: [iperf.fr](https://iperf.fr)

- `GET /api/wifi/analyze?refresh=0&merge=1` — `netsh wlan show networks mode=bssid`로 주변 AP(SSId·BSSID·신호·채널·밴드) 목록과 채널/밴드 집계, 2.4GHz 1·6·11 기준 혼잡도 점수(참고). `refresh=1`이면 스캔 전 `netsh wlan refresh` 시도.

## 10) 문서 사이트(VitePress)

```bash
cd docs
npm install
npm run docs:dev
```

## 11) Netmiko 백업 + FastAPI/Streamlit 스캔 도구

- 위치: `network_ops/`
- 장비 백업/감사:
  - `python network_ops/backup_configs.py`
- 스캔 API:
  - `uvicorn network_ops.scan_api:app --host 0.0.0.0 --port 8000 --reload`
- 스캔 대시보드:
  - `streamlit run network_ops/scan_dashboard.py`

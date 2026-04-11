# NetWork-IP Search

Scapy를 사용해 현재 네트워크의 장치를 탐지하고, IP/연결 상태를 대시보드로 보여주는 Python 앱입니다.

### GitHub Pages가 README만 보일 때 — 1분 체크리스트

`https://karin01.github.io/NetWork-IP-Search/` 에 **README·Jekyll 페이지**만 보이면, 아래를 순서대로 확인하세요.

- [ ] 저장소 **Settings → Pages** 로 이동
- [ ] **Build and deployment → Source** 가 **Deploy from a branch** 인지 확인 (`GitHub Actions` 전용이 아님)
- [ ] **Branch:** **`gh-pages`** · **Folder:** **`/(root)`** 선택 후 **Save**
- [ ] **Actions** 탭 → 워크플로 **Deploy docs to GitHub Pages** 가 최근 커밋에서 **성공(초록)** 인지 확인
- [ ] 1~2분 후 브라우저에서 **강력 새로고침**(Ctrl+F5) 후 같은 주소로 다시 열기
- [ ] (선택) 페이지에서 **소스 보기**: `generator" content="Jekyll"` 이 보이면 아직 **`main` 브랜치**로 올라가 있는 것 — **`gh-pages`** 로 바꿔야 랜딩·`/manual/` 이 보입니다.

> **GitHub Pages** 루트는 **소개 웹 페이지**(`site-landing/`), 상세 **기술 문서**는 **`/manual/`** 경로(VitePress)입니다. 그래프·스캔 대시보드는 `python app.py`(또는 배치 파일) 실행 후 **`http://127.0.0.1:5000`** 에서 엽니다.

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

### 접근 토큰·웹 설정·민감 파일 (선택)

- **`NETWORK_IP_SEARCH_TOKEN`** — 환경 변수로 설정하면 API·HTML 페이지 접근에 토큰이 필요합니다. 브라우저는 처음 `http://127.0.0.1:5000/?token=값` 으로 열거나, API 호출 시 헤더 `X-NetWork-IP-Token` 을 붙입니다. (`/api/health`, `/api/build-info`, 정적 `/static` 은 예외)
- **`/settings`** (또는 `GET/POST /api/settings`) — 기본 인벤토리 YAML 경로·스캔 주기(초)를 저장합니다. 저장 파일은 프로젝트 루트의 **`user_settings.json`** (Git 제외).
- **`devices.secret.yaml`** — 실제 SNMP/SSH 비밀번호가 들어가는 인벤토리는 예시(`devices.secret.yaml.example`)를 복사해 쓰고, `.gitignore` 로 커밋에서 제외하세요.

### 스모크 테스트·Docker

```bash
pip install -r requirements-dev.txt
python -m pytest tests/test_smoke.py -v
```

- **`Dockerfile`** — Linux 컨테이너에서 Flask UI만 띄우는 참고용입니다. **Windows 전용 기능**(Npcap ARP, `netsh` Wi‑Fi 등)은 컨테이너·클라우드 VM에서 기대하지 마세요. 상세는 문서 `docs/guide/cloud-deploy.md`.
- **포트** — 로컬은 `NETWORK_IP_SEARCH_PORT`, 일부 PaaS는 **`PORT`** 환경 변수를 씁니다. 둘 중 설정된 값이 사용됩니다(`NETWORK_IP_SEARCH_PORT` 우선).

## 2-1) GitHub Pages (소개 페이지 + 기술 문서)

Flask 대시보드는 서버가 필요해 Pages에 호스팅할 수 없습니다. 대신 Actions가 다음을 한 번에 배포합니다.

- **루트** `https://karin01.github.io/NetWork-IP-Search/` — `site-landing/` 단독 HTML 랜딩(Portfolio 느낌)
- **문서** `https://karin01.github.io/NetWork-IP-Search/manual/` — `docs/` VitePress 빌드

1. GitHub 저장소 **Settings → Pages → Build and deployment**  
2. **Source** 를 **Deploy from a branch** 로 두고, **Branch** 는 **`gh-pages`** / **`/(root)`** 선택 후 Save  
   - `main` 또는 `master`에 푸시되면 Actions가 **`gh-pages` 브랜치**를 자동 생성·갱신합니다.  
3. 1~2분 뒤 위 주소로 접속  
   - **Actions** 탭에서 **Deploy docs to GitHub Pages** 워크플로가 성공(초록)인지 확인하세요.

### ⚠️ 다른 PC에서 안 열리거나, README만 보일 때 (가장 흔한 원인)

1. **Pages 소스가 `main`으로 되어 있는 경우**  
   저장소 **Settings → Pages**에서 **Branch가 `gh-pages`**, 폴더 **`/(root)`** 인지 꼭 확인하세요.  
   `main` / `(root)`로 두면 GitHub가 **Jekyll로 README만 웹에 올립니다.** 이때 소스 보기에 `generator" content="Jekyll"` 이 보이면 **아직 커스텀 랜딩이 아닙니다.**

2. **`127.0.0.1` 또는 `localhost`로 다른 PC에서 접속한 경우**  
   `127.0.0.1`은 **그 PC 자기 자신**만 가리킵니다. 다른 컴퓨터에서는 **`https://karin01.github.io/NetWork-IP-Search/`** 처럼 **공개 주소**를 써야 하고, **대시보드(Flask)** 는 서버를 켠 PC의 **`http://그PC의내부IP:5000`** 으로 접속해야 합니다.

3. **회사·학교망에서 `*.github.io` 차단**  
   방화벽 정책으로 GitHub Pages가 막히면 연결이 안 됩니다. 휴대폰 LTE 등 다른 네트워크로 시험해 보세요.

4. **주소 오타**  
   저장소 이름과 동일하게 하이픈 포함: `NetWork-IP-Search` (공백 없음).

## 2-2) 해결책 정리 — “메뉴얼만 보인다” vs “대시보드를 웹에서 보고 싶다”

| 하고 싶은 것 | 해결책 |
| --- | --- |
| **github.io에 README만 나와서 속상하다** | **Settings → Pages → Branch `gh-pages` / `(root)`** 로 바꾸기. 그러면 소개 랜딩 + `/manual/` 문서가 의도대로 나옵니다. (대시보드는 여전히 Pages에 없음) |
| **같은 집·사무실 Wi‑Fi에서 휴대폰으로 대시보드** | 대시보드를 켠 PC의 **사설 IP**로 접속: `http://192.168.x.x:5000` . Windows **방화벽에서 포트 5000 인바운드 허용**이 필요할 수 있습니다. 앱은 이미 `host=0.0.0.0` 으로 떠서 같은 망 접속이 가능합니다. |
| **인터넷 어디서나 브라우저로 대시보드 (임시)** | [ngrok](https://ngrok.com/) 등으로 `ngrok http 5000` → 발급된 **https URL**을 다른 PC에 입력. (보안·노출 주의, 테스트용에 적합) |
| **인터넷에서 상시 서비스** | **Railway**, **Render**, **Fly.io** 같은 PaaS에 Flask 앱을 배포하거나, 자신의 **VPS**에 올립니다. 저장소·환경 변수·스캔 권한(Npcap 등)은 클라우드 OS에 맞게 다시 설계해야 합니다. |

**한 줄 요약:** [GitHub Pages](https://pages.github.com/)는 **정적 사이트 전용**이라 **Flask 대시보드를 그 주소에 올릴 “기술적 해결”은 없습니다.** 대시보드는 **로컬·망 내 IP·터널·클라우드** 중 하나로 열어야 합니다.

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

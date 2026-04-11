# Network Ops 도구 모음

## 1. `backup_configs.py` — 장비 설정 백업·감사

- `devices.csv`를 읽어 장비에 순차 SSH 접속 후 `show run` 백업을 `backups/YYYY-MM-DD/`에 저장합니다.
- 보안 감사 규칙 검사 후 같은 폴더에 `report.txt`를 만듭니다.
- **모든 SSH 접속 시도·성공·실패·종료와 에러 스택**은 `network_ops/network_ops.log`에 **시간 순으로 누적**됩니다. (일별 `backup_errors.log`는 사용하지 않습니다.)
- **비밀번호는 소스 코드에 넣지 않습니다.** CSV의 `pw`를 비우고 아래 중 하나로만 주입합니다.
  - **`secrets.enc`** 암호화 파일 (`encrypt_secrets.py`로 생성)
  - 실행 시 터미널 **`getpass`** 입력 (암호화 파일 복호화 마스터 비밀번호, 장비 SSH 비밀번호)
  - **환경 변수** (SMTP·텔레그램·Fernet 키 등, 아래 표 참고)
- **설정 백업이 이전 파일과 다를 때**(같은 날 재실행 포함) `secrets`에 `notify_on_config_change: true` 이고 메일·텔레그램 중 설정된 채널로 **diff 요약**을 보냅니다. 최초 백업(비교 대상 없음)은 알림하지 않습니다.

### 비밀 정보 준비

1. `secrets.plain.example.yaml`을 복사해 `secrets.plain.yaml`을 만든 뒤 값을 채웁니다. (이 파일은 Git에 넣지 마세요.)
2. 암호화:

   ```bash
   cd network_ops
   python encrypt_secrets.py secrets.plain.yaml secrets.enc
   ```

3. 실행 시 마스터 비밀번호를 입력하거나, 비대화식으로 `NETWORK_OPS_MASTER_PASSWORD` 또는 `NETWORK_OPS_FERNET_KEY`를 설정합니다.

### 주요 환경 변수 (암호화 파일 내용을 덮어씀)

| 변수 | 설명 |
|------|------|
| `NETWORK_OPS_SECRETS_ENC` | 암호화 파일 경로 (기본: `network_ops/secrets.enc`) |
| `NETWORK_OPS_FERNET_KEY` | Fernet 키(base64). 있으면 `secrets.enc` 전체를 순수 Fernet 토큰으로 해석 |
| `NETWORK_OPS_MASTER_PASSWORD` | salt+PBKDF2 형식 `secrets.enc` 복호화용 |
| `NETWORK_OPS_SMTP_HOST` / `_PORT` / `_USER` / `_PASSWORD` / `_FROM` / `_TO` | 메일 (수신은 쉼표 구분) |
| `NETWORK_OPS_TELEGRAM_BOT_TOKEN` / `NETWORK_OPS_TELEGRAM_CHAT_ID` | 텔레그램 |
| `NETWORK_OPS_NOTIFY_ON_CHANGE` | `1` / `true` 이면 설정 변경 알림 켜기 |

### `devices.csv`

- `pw`를 **비우면** `secrets.enc`의 `device_passwords` 또는 터미널에서 해당 IP 비밀번호를 묻습니다.
- 평문 비밀번호를 CSV에 두는 것은 피하는 것이 좋습니다.

```bash
python network_ops/backup_configs.py
```

실행 시 작업 디렉터리가 `network_ops`가 아니어도, 스크립트 위치 기준으로 모듈을 불러옵니다.

---

## 인프라 생존 지도 (Live Map)

기존 **Ping·서비스 포트 체크** 개념을 확장해, 서버·네트워크 장비를 한 화면에서 **생존 상태(up / degraded / down)** 로 모읍니다.

| 구성요소 | 설명 |
|----------|------|
| 인벤토리 | `live_map/hosts.yaml` — `servers` / `network_devices` 분리 (`hosts.example.yaml` 복사) |
| 병렬 | `ThreadPoolExecutor(max_workers=10)` — 동시 최대 10대 |
| 점검 | ICMP ping → `check_ports` TCP → 읽기 전용 `status_command` (Linux SSH / Windows WinRM / Netmiko) |
| 비밀번호 | YAML에 평문 금지 — `ssh_password_env` / `winrm_password_env` 에 적은 **이름**으로 OS 환경 변수 설정 |
| Streamlit | `streamlit run live_map_dashboard.py` — **서버** / **네트워크** 탭 + 산점도 요약 지도 |
| 통합 프롬프트 | `python run_live_map_prompt.py` — `help`, `list`, `scan`, `status <id>`, `exec <id> "<명령>"` |
| 안전장치 | `live_map/safety.py` — reboot/delete 등은 **확인 문구 + PIN** 2단계 (`LIVE_MAP_DESTRUCTIVE_PHRASE`, `LIVE_MAP_ADMIN_PIN`). 웹 탭의 파괴적 명령은 **PIN 환경 변수 필수** |

```bash
cd network_ops
copy live_map\hosts.example.yaml live_map\hosts.yaml   # Windows
python run_live_map_prompt.py
streamlit run live_map_dashboard.py
```

---

## 2. `scan_api.py` + `scan_dashboard.py`

- FastAPI 백엔드가 CIDR 대역 IP 활성 상태를 스캔
- Streamlit 대시보드에서 테이블로 표시
- CIDR 네트워크 대역 계산 기능 제공(네트워크/브로드캐스트/호스트 수)
- 상태 색상: 사용 중 = Red, 비어 있음 = Green

```bash
uvicorn network_ops.scan_api:app --host 0.0.0.0 --port 8000 --reload
streamlit run network_ops/scan_dashboard.py
```

## API 참고

- `GET /scan?cidr=192.168.1.0/24`
- `GET /subnet/calc?cidr=192.168.1.0/24`

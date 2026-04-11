# 트러블슈팅 허브

증상별로 빠르게 점검할 항목을 모았습니다.

## GitHub Pages / github.io

- [README 체크리스트](https://github.com/karin01/NetWork-IP-Search/blob/main/README.md) — **`gh-pages` / (root)** 인지 확인.  
- 소스에 `Jekyll` 이 보이면 **`main` 브랜치**로만 올라가 있는 상태입니다.

## 대시보드가 안 열림

| 증상 | 조치 |
| --- | --- |
| 연결 거부 | `python app.py` 또는 배치 파일로 서버가 떠 있는지, 포트 `NETWORK_IP_SEARCH_PORT` 확인 |
| 401 텍스트 | `NETWORK_IP_SEARCH_TOKEN` 설정됨 → URL에 `?token=값` 또는 API 헤더 `X-NetWork-IP-Token` |
| 다른 PC에서 안 됨 | `127.0.0.1` 대신 서버 PC의 `192.168.x.x:5000`, Windows 방화벽 인바운드 |

## 스캔 / 권한

- **Scapy 권한 오류** — Windows는 **관리자** CMD/PowerShell에서 실행.  
- **Npcap** — ARP 정밀 스캔용. 없으면 ping 폴백(경고 표시). [Npcap](https://npcap.com/)  
- **Google Drive 동기** — 폴더가 “오프라인 사용 가능”인지, 동기 완료 후 배치 재실행.

## SNMP / 스위치

- UDP **161** 방화벽, community / SNMPv3, 장비 ACL.  
- 비-Cisco는 **SSH 폴백 없음** → SNMP 필수. [스위치 포트](/guide/switch-ports)

## Wi‑Fi (Windows)

- `netsh` 실패 — 무선 드라이버·어댑터 상태 확인.  
- iperf3 — 서버에 `iperf3 -s`, 클라이언트 PATH.

## 설정 파일

- **`user_settings.json`** — 웹 `/settings` 에서 저장. Git 제외.  
- **`devices.secret.yaml`** — 실제 비밀번호. `.gitignore` 처리. `devices.secret.yaml.example` 복사.

## 자동 점검 (개발)

```bash
pip install -r requirements-dev.txt
python -m pytest tests/test_smoke.py -v
```

관련: [시리얼 콘솔](/guide/serial-console) · [API](/reference/api)

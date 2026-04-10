# Network Ops 도구 모음

이 폴더는 아래 2가지 실무 도구를 제공합니다.

1. `backup_configs.py`
- `devices.csv`를 읽어 장비에 순차 SSH 접속
- `show run` 백업을 `backups/YYYY-MM-DD`에 저장
- 보안 감사 규칙 검사 후 `report.txt` 생성
- 오류는 `backup_errors.log`에 남기고 다음 장비로 진행

2. `scan_api.py` + `scan_dashboard.py`
- FastAPI 백엔드가 CIDR 대역 IP 활성 상태를 스캔
- Streamlit 대시보드에서 테이블로 표시
- CIDR 네트워크 대역 계산 기능 제공(네트워크/브로드캐스트/호스트 수)
- 상태 색상:
  - 사용 중 = Red
  - 비어 있음 = Green

## 실행 방법

```bash
# 1) 백업/감사 실행
python network_ops/backup_configs.py

# 2) 스캔 API 실행
uvicorn network_ops.scan_api:app --host 0.0.0.0 --port 8000 --reload

# 3) Streamlit 실행
streamlit run network_ops/scan_dashboard.py
```

## API 참고

- `GET /scan?cidr=192.168.1.0/24`
- `GET /subnet/calc?cidr=192.168.1.0/24`

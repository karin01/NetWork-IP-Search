# API 레퍼런스

## GET /api/switch/ports

인벤토리 YAML에 정의된 스위치들의 **포트 UP/DOWN**(IF-MIB)을 반환합니다. Cisco는 SNMP 실패 시 SSH 보조 가능.

- 쿼리: `inventory_path` — 예: `devices.yaml` (프로젝트 루트 기준 경로)
- 상세·벤더별 SNMP 설정: [스위치 포트 가이드](../guide/switch-ports)

## GET /api/scan

네트워크 스캔 결과를 반환합니다.

## GET /api/export/csv

최근 스캔 결과를 CSV로 다운로드합니다.

## POST /api/log/analyze

업로드한 로그 파일을 분석해 요약/JSONL 출력물을 생성합니다.

## POST /api/automation/run

자연어 지시와 인벤토리를 받아 다중 장비 자동화를 실행합니다.

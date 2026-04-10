# NetWork-IP Search 기술 매뉴얼

네트워크 장치 스캔, 로그 분석, 다중 장비 자동화를 한 곳에서 운영하기 위한 문서입니다.

::: tip 온라인 문서 (GitHub Pages)
저장소 **main** 브랜치에 푸시하면 GitHub Actions가 이 매뉴얼을 배포합니다.  
주소: **https://karin01.github.io/NetWork-IP-Search/** (저장소 설정에서 Pages 소스가 *GitHub Actions* 여야 합니다.)

**Flask 대시보드·Wi‑Fi 도구**는 Python 서버가 필요해 GitHub Pages에 올릴 수 없습니다. PC에서 `python app.py` 또는 `run_dashboard.bat` 으로 실행하세요.
:::

## 빠른 시작

- 대시보드 실행: `python app.py`
- 문서 사이트 실행:
  1. `cd docs`
  2. `npm install`
  3. `npm run docs:dev`

## 핵심 기능

- 네트워크 장치/IP/포트/상태 대시보드
- 로그 파일 AI 친화 가공(JSONL + 요약 통계)
- 자연어 기반 다중 장비 자동화(드라이런 기본)

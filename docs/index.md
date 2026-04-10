# NetWork-IP Search 기술 매뉴얼

::: danger 여기(karin01.github.io)에는「대시보드 웹앱」이 없습니다
**지금 보시는 페이지는 설치·API 안내용 매뉴얼입니다.** 장치 스캔·그래프·Wi‑Fi 분석 화면은 **Python(Flask) 서버**가 돌아가야 해서 GitHub Pages에는 올릴 수 없습니다.

**실제 대시보드를 보려면 (같은 Windows PC에서):**

1. 프로젝트 폴더에서 **`run_dashboard.bat`** 실행 (또는 터미널에서 `python app.py`)
2. 브라우저에서 **`http://127.0.0.1:5000`** 열기 — Wi‑Fi 도구는 **`http://127.0.0.1:5000/wifi`**

휴대폰 등 **다른 기기**에서는 PC의 Wi‑Fi IP로 `http://192.168.x.x:5000` 형태로 접속합니다.
:::

네트워크 장치 스캔, 로그 분석, 다중 장비 자동화를 한 곳에서 운영하기 위한 문서입니다.

::: tip 온라인 문서 (GitHub Pages)
**main**에 푸시하면 Actions가 **`gh-pages` 브랜치**에 빌드 결과를 올립니다.  
저장소 **Settings → Pages** 에서 소스를 **Deploy from a branch → `gh-pages` / (root)** 로 지정한 뒤,  
**https://karin01.github.io/NetWork-IP-Search/** 로 접속하세요.

**Flask 대시보드·Wi‑Fi 도구**는 Python 서버가 필요해 Pages에 올릴 수 없습니다. PC에서 `python app.py` 또는 `run_dashboard.bat` 으로 실행하세요.
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

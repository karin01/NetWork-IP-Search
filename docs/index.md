---
layout: home

hero:
  name: NetWork-IP Search
  text: LAN 스캔 · Wi‑Fi 분석 · 장비 자동화
  tagline: |
    기술 문서(가이드·API) 영역입니다. Portfolio처럼 보이는 소개 웹 페이지는 저장소 Pages 루트에서 열립니다.
    실시간 대시보드는 PC에서 서버 실행 후 http://127.0.0.1:5000 으로 접속하세요.
  image:
    src: /favicon.svg
    alt: NetWork-IP Search
  actions:
    - theme: brand
      text: 시작하기 (설치·실행)
      link: /guide/getting-started
    - theme: alt
      text: 프로젝트 웹 홈
      link: https://karin01.github.io/NetWork-IP-Search/

features:
  - icon: 🖥️
    title: 대시보드는 로컬에서
    details: run_dashboard.bat 또는 python app.py 실행 후 http://127.0.0.1:5000 — 같은 Wi‑Fi의 다른 기기는 PC의 192.168.x.x:5000
  - icon: 📶
    title: Wi‑Fi 도구
    details: /wifi 에서 netsh 링크·iperf3·주변 AP·채널 차트. Windows + 로컬 서버 필요
  - icon: 📚
    title: 이 경로는 문서(/manual/)
    details: API·로그 랩·SNMP·배포 안내. 정적 호스팅이라 Python 백엔드는 돌리지 않습니다.
---

<div class="vp-doc home-after">

### 빠른 링크

| 할 일 | 주소 / 방법 |
| --- | --- |
| **실시간 대시보드** | PC에서 서버 실행 → `http://127.0.0.1:5000` |
| **Wi‑Fi 전용 페이지** | 서버 실행 후 `http://127.0.0.1:5000/wifi` |
| **REST API 설명** | [API 레퍼런스](/reference/api) |

</div>

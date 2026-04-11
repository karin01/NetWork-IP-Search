---
layout: home

hero:
  name: NetWork-IP Search
  text: LAN 스캔 · Wi‑Fi 분석 · 장비 자동화
  tagline: |
    기술 문서(가이드·API) 영역입니다. Portfolio처럼 보이는 소개 웹 페이지는 저장소 Pages 루트에서 열립니다.
    실시간 대시보드는 PC에서 서버 실행 후 http://127.0.0.1:8500 으로 접속하세요.
  image:
    src: /favicon.svg
    alt: NetWork-IP Search
  actions:
    - theme: brand
      text: 5분 안에 실행
      link: /guide/quickstart-5min
    - theme: brand
      text: Flask 서버 켜기 (대시보드)
      link: /guide/flask-server
    - theme: alt
      text: 시작하기 (개요)
      link: /guide/getting-started
    - theme: alt
      text: 스위치 포트 가이드
      link: /guide/switch-ports
    - theme: alt
      text: 프로젝트 웹 홈
      link: https://karin01.github.io/NetWork-IP-Search/

features:
  - icon: 🖥️
    title: Flask 서버 → 대시보드
    details: 가이드「Flask 서버 실행」에 배치 파일·수동 명령·포트 변경·방화벽·Wi‑Fi 접속까지 정리. 실행 후 127.0.0.1:8500
  - icon: 📶
    title: Wi‑Fi 도구
    details: /wifi 에서 netsh 링크·iperf3·주변 AP·채널 차트. Windows + 로컬 서버 필요
  - icon: 🔌
    title: 스위치 포트
    details: IF-MIB SNMP + Cisco SSH 보조. 벤더별 설정은「스위치 포트」가이드 참고
  - icon: 📚
    title: 이 경로는 문서(/manual/)
    details: API·로그 랩·SNMP·배포 안내. 정적 호스팅이라 Python 백엔드는 돌리지 않습니다.
---

<div class="vp-doc home-after">

### 빠른 링크

| 할 일 | 주소 / 방법 |
| --- | --- |
| **실시간 대시보드** | [Flask 서버 실행 가이드](/guide/flask-server) → `http://127.0.0.1:8500` |
| **Wi‑Fi 전용 페이지** | 서버 실행 후 `http://127.0.0.1:8500/wifi` |
| **스위치 포트 (Cisco·Juniper 등)** | [벤더별 가이드](/guide/switch-ports) |
| **시리얼(콘솔) 접속** | [장비별 Baud·명령](/guide/serial-console) |
| **REST API 설명** | [API 레퍼런스](/reference/api) |

</div>

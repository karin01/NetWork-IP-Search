# 클라우드 배포 (참고)

이 프로젝트는 **Windows 데스크톱에서 LAN 스캔·netsh Wi‑Fi** 를 전제로 한 부분이 많습니다. **클라우드 VM/Linux 컨테이너**에 그대로 올리면 **기능 대부분이 동작하지 않거나 의미가 달라질 수 있습니다.**

## 언제 의미가 있나

- **정적 매뉴얼만** — 이미 [GitHub Pages](https://pages.github.com/) 로 충분합니다.  
- **API 일부만** — 스캔 없이 내부망 전용 프록시를 붙이는 식의 **맞춤 설계**가 필요합니다.  
- **Docker** — 루트의 `Dockerfile` 은 **Linux에서 Flask UI를 띄우는 최소 예시**입니다. Npcap·Wi‑Fi는 기대하지 마세요.

## Railway / Render / Fly.io 등

1. **런타임** — Python, 시작 명령 `python app.py`, 포트는 플랫폼이 주는 `PORT` 환경 변수에 맞추려면 코드에서 `NETWORK_IP_SEARCH_PORT` 와 동일하게 매핑하는 편이 안전합니다(플랫폼별 문서 확인).  
2. **시크릿** — `NETWORK_IP_SEARCH_TOKEN` 으로 무분별 접속을 줄이세요.  
3. **스캔** — 클라우드 인스턴스의 NIC는 사용자 집 LAN이 아니므로 **ARP 스캔 결과가 쓸모없을 수 있습니다.**

## 한 줄 결론

**“집·사무실 네트워크 도구”로 쓰려면 로컬 PC(또는 같은 LAN의 Windows 서버) 실행이 정답에 가깝고**, 클라우드는 **문서·데모·부분 API** 용으로만 검토하세요.

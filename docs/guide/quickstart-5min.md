# 5분 안에 돌려 보기

1. **저장소 받기** — ZIP 다운로드 또는 `git clone` 후 폴더를 연다.  
2. **Python** — 3.10+ 권장. 터미널에서 `python --version` 확인.  
3. **의존성** — 프로젝트 루트에서:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
4. **서버 실행** — **`run_dashboard.bat`** 또는 `python app.py`  
5. **브라우저** — [http://127.0.0.1:5000](http://127.0.0.1:5000)  
6. **Wi‑Fi 도구** — [http://127.0.0.1:5000/wifi](http://127.0.0.1:5000/wifi) (Windows)

**스위치·SNMP** — `devices.example.yaml` 을 복사해 경로를 맞춘 뒤 [스위치 포트](/guide/switch-ports) 참고.

**접근 토큰(선택)** — 같은 망에 열 때:
```powershell
$env:NETWORK_IP_SEARCH_TOKEN = "임의의_긴_문자열"
python app.py
```
브라우저는 `http://127.0.0.1:5000/?token=임의의_긴_문자열` 로 처음 연다.

다음: [Flask 서버 상세](/guide/flask-server) · [트러블슈팅](/guide/troubleshooting) · [클라우드 배포 참고](/guide/cloud-deploy)

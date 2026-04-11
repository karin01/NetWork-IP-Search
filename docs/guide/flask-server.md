# Flask 서버 실행하기 (대시보드)

::: warning 이 문서 사이트에서는 서버가 돌아가지 않습니다
지금 보시는 페이지는 **GitHub Pages에 올라간 정적 매뉴얼**입니다. **Flask는 여기서 실행할 수 없고**, 반드시 **프로젝트를 받아 둔 자신의 Windows PC**에서 아래 순서대로 실행합니다.  
코드 블록 우측의 **복사** 버튼으로 명령을 붙여 넣을 수 있습니다.
:::

## 1. 준비물

- Windows PC (대시보드·Wi‑Fi 도구는 Windows 전제)
- [Python 3](https://www.python.org/downloads/) 설치 (`python`이 터미널에서 인식되어야 함)
- 이 저장소 폴더 전체 (클론 또는 ZIP 해제)

선택:

- ARP 정밀 스캔: [Npcap](https://npcap.com/)
- 가상환경 권장: 아래 `venv` 단계

## 2. 가장 빠른 방법 (배치 파일)

저장소 **루트 폴더**에서 다음 중 하나를 더블클릭하거나 실행합니다.

| 파일 | 설명 |
| --- | --- |
| **`run_dashboard.bat`** | 경로·한글 폴더·venv 자동 처리, Flask용 CMD 창 + 브라우저 자동 실행 |
| **`대시보드 열기.bat`** | 위 파일을 `pushd`로 호출 (같은 동작) |

실행 후:

1. 제목이 **`NetWork-IP Flask 8500`** 인 검은 CMD 창이 떠 있어야 합니다. **이 창을 닫으면 서버가 꺼집니다.**
2. 브라우저에서 **`http://127.0.0.1:8500`**  
3. Wi‑Fi 전용 화면: **`http://127.0.0.1:8500/wifi`**

배치 파일 시작 시 콘솔에 **같은 Wi‑Fi용 `http://<IPv4>:8500`** 주소가 함께 출력됩니다. 휴대폰 등에서 쓰려면 Windows **방화벽에서 포트 8500 인바운드 허용**이 필요할 수 있습니다.

## 3. 수동 실행 (터미널)

프로젝트 루트에서:

### 3-1) 가상환경 + 의존성 (최초 1회)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3-2) 서버 기동

```bash
.venv\Scripts\activate
python app.py
```

또는 venv 없이 전역 Python만 쓰는 경우:

```bash
pip install -r requirements.txt
python app.py
```

정상 기동 시 터미널에 Flask가 리스닝한다는 메시지가 나오고, 브라우저로 **`http://127.0.0.1:8500`** 을 엽니다.

## 4. 포트 바꾸기

기본 포트는 **8500** 입니다. 다른 포트를 쓰려면 환경 변수를 설정한 뒤 `app.py`를 실행합니다.

**PowerShell 예시:**

```powershell
$env:NETWORK_IP_SEARCH_PORT = "8080"
python app.py
```

**CMD 예시:**

```bat
set NETWORK_IP_SEARCH_PORT=8080
python app.py
```

그다음 브라우저에서는 `http://127.0.0.1:8080` 으로 접속합니다.

## 5. 자주 나오는 문제

### `python`을 찾을 수 없음

- Python 설치 시 **“Add python.exe to PATH”** 옵션을 켰는지 확인하거나, **시작 메뉴 → Python**에서 “Python 3.x” 경로를 확인해 전체 경로로 실행합니다.

### `Address already in use` / 포트 충돌

- 다른 프로그램이 8500을 쓰 중입니다. 위 **4. 포트 바꾸기**로 다른 포트를 지정하거나, 기존에 떠 있는 Flask/CMD 창을 종료합니다.

### 배치 파일은 되는데 `python app.py`만 실패

- 현재 폴더가 **프로젝트 루트**( `app.py`가 있는 곳)인지 확인합니다.
- Google Drive 동기화 중이면 **동기 완료·오프라인 사용 가능**으로 만든 뒤 다시 시도합니다.

### 같은 Wi‑Fi 휴대폰에서 안 열림

- PC 방화벽 **인바운드 규칙**에서 TCP **8500**(또는 바꾼 포트) 허용
- 주소는 **`http://127.0.0.1`** 이 아니라 PC의 **`http://192.168.x.x:8500`** (배치 파일 출력 또는 `ipconfig`로 확인)

## 6. 다음 단계

- 기능 개요·주의사항: [시작하기](./getting-started)
- 스위치 포트(IF-MIB·Cisco SSH 보조): [스위치 포트 가이드](./switch-ports)
- REST API: [API 레퍼런스](../reference/api)

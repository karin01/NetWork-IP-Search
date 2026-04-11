# 스위치 포트 모니터링 (벤더별 가이드)

대시보드 하단 **「스위치 포트 현황」** 에서 인벤토리에 등록된 L2/L3 스위치의 **포트 UP/DOWN** 을 모읍니다.  
백엔드는 `switch_port_monitor.py` 에서 **IF-MIB(SNMP)** 를 우선 사용하고, **Cisco** 만 SNMP 실패 시 **SSH** 로 `show interfaces status` 를 보조 파싱합니다.

::: tip 전제
스위치 기능을 쓰려면 **Flask 서버가 실행 중**이어야 합니다. [Flask 서버 실행](./flask-server)을 먼저 완료하세요.
:::

## 1. 인벤토리 파일 (공통)

프로젝트 루트의 **`devices.example.yaml`** 을 복사해 예를 들어 `devices.yaml` 로 두고, 실제 IP·계정으로 수정합니다.

```yaml
devices:
  - ip: "192.168.0.10"
    vendor: "cisco"
    snmp:
      v3_username: "snmpuser"
      v3_auth_key: "실제_인증키"
      v3_auth_protocol: "sha" # sha | md5
      v3_priv_key: "실제_암호키"
      v3_priv_protocol: "aes" # aes | des
      community: "public" # v2c (보조)
    ssh:
      username: "admin"
      password: "실제_비밀번호"
```

- **`ip`**: 스위치 관리 IP (SNMP/SSH 도달 가능해야 함).
- **`vendor`**: 문자열에 **`cisco`** 가 포함되면 SSH 보조 경로가 활성화됩니다 (대소문자 무관).
- **`snmp`**: **SNMPv3** (`v3_username` + `v3_auth_key`) 우선, 없으면 **v2c** `community`.
- **`ssh`**: Cisco 전용 폴백용 (Netmiko `cisco_ios`).

대시보드에서 인벤토리 경로를 지정하거나, API 호출 시 쿼리로 넘깁니다.

## 2. API

```http
GET /api/switch/ports?inventory_path=devices.yaml
```

응답의 **`source`** 필드:

| 값 | 의미 |
| --- | --- |
| `snmp` | IF-MIB 워크로 수집 성공 |
| `ssh_cisco` | SNMP 실패 후 Cisco IOS SSH 파싱 성공 |
| `none` | 수집 실패 (오류 메시지는 `error` 참고) |

## 3. Cisco

**권장:** SNMP(IF-MIB)가 가장 안정적입니다. 스위치에서 SNMP view/ACL 이 `1.3.6.1.2.1.2.2` (IF-MIB) 를 포함하는지 확인하세요.

**SNMP가 안 될 때:** `vendor` 에 `cisco` 가 들어가 있고 `ssh` 계정이 맞으면, 앱이 **`show interfaces status`** (TextFSM) 로 포트 목록을 채웁니다.

**필요 패키지:** `requirements.txt` 의 Netmiko·TextFSM(ntc-templates) 등. SSH는 **enable 비밀번호**가 따로 필요한 환경이면 Netmiko 설정을 추가로 맞춰야 할 수 있습니다(기본 예제는 로그인만).

## 4. Juniper

**SNMP(IF-MIB)만 지원됩니다.** 코드에 Juniper 전용 SSH 파싱은 없습니다.

- JunOS 에서 **SNMP v2/v3** 활성화 및 클라이언트(대시보드 PC) IP 허용.
- `vendor: "juniper"` 로 두어도 되고, SNMP만 살아 있으면 벤더 문자열과 무관하게 **`snmp`** 경로로 수집됩니다.
- 인터페이스 이름이 `ge-0/0/0` 형태로 `ifDescr` 에 나오면 그대로 표에 표시됩니다.

## 5. HPE / Aruba / 기타 벤더

표준 **IF-MIB** 를 SNMP로 응답하는 스위치라면 **벤더 공통 경로(`snmp`)** 로 동작합니다.

- **Comware / Aruba AOS-S** 등: 관리 가이드에 따라 SNMP community 또는 v3 사용자를 열고, 동일한 YAML `snmp` 블록을 채웁니다.
- SSH 폴백은 **Cisco IOS 전용**이므로, HPE 등에서는 **SNMP 설정이 필수**에 가깝습니다.

## 6. Ubiquiti (유비쿼티)

UniFi·UISP·에지맥스 등 라인업마다 관리 방식이 다릅니다. 이 앱이 읽는 것은 **표준 IF-MIB(SNMP)** 뿐이므로, **장비/펌웨어에서 SNMP 에이전트가 켜져 있고 `ifDescr`·`ifOperStatus` 가 응답**해야 합니다.

| 계열 | 참고 |
| --- | --- |
| **UniFi 스위치 (USW 등)** | 컨트롤러(또는 UniFi OS)에서 **SNMP** 를 활성화하고, **스위치 관리 IP**(또는 게이트웨이가 중계하는 경우 해당 문서 확인)로 UDP **161** 이 대시보드 PC까지 열려 있는지 확인합니다. 펌웨어·모델에 따라 SNMP 가 제한되거나 커뮤니티만 지원하는 경우가 있어 **v2c `community`** 로 먼저 시험해 보는 것이 빠른 경우가 많습니다. |
| **EdgeRouter / EdgeSwitch** | 전통적인 **snmp community / v3** 설정 후, 인벤토리의 `ip` 에 **해당 장비 L3 관리 주소**를 넣습니다. |
| **에어맥스 등 브리지** | 무선 링크용 장비는 **이더넷 포트 IF-MIB** 가 기대와 다르게 보이거나 항목이 적을 수 있습니다. |

`vendor` 필드에는 예를 들어 `ubiquiti` 처럼 적어도 되고, **SNMP만 성공하면 벤더 문자열과 무관**하게 `snmp` 소스로 수집됩니다. SSH 폴백은 없습니다.

## 7. Dasan (다산)

다산네트웍스 스위치·라우터는 제품군별로 **SNMP v2c / v3** 설정 메뉴 이름이 다를 수 있으나, **IF-MIB 를 응답**하면 이 프로젝트와 호환됩니다.

- 관리 GUI/CLI에서 **SNMP agent 활성화**, **community 또는 SNMPv3 사용자** 생성.
- **접속 허용 IP**(ACL·호스트)에 **Flask를 실행하는 PC**(또는 스캔 서버) 주소를 넣습니다.
- 방화벽·중간 L3 에서 **UDP 161** 이 막히지 않았는지 확인합니다.
- 인벤토리 예: `vendor: "dasan"` (임의 문자열 가능), `snmp` 블록에 실제 community 또는 v3 키 입력.

제품 매뉴얼의 「SNMP」「NMS」 절을 따르는 것이 가장 정확합니다.

## 8. Dovado / 다보링크 (SOHO·랜 카피 장비)

**Dovado** 는 주로 **LTE/유선 공유기·미니 라우터** 라인입니다. **다보링크** 등 국내 유통 SOHO 브랜드도 기기마다 SNMP 지원 여부가 크게 다릅니다.

| 경우 | 설명 |
| --- | --- |
| **SNMP + IF-MIB 제공** | 관리 페이지에서 SNMP 를 켠 뒤, 위와 동일하게 `devices.yaml` 의 `ip`·`snmp` 만 맞추면 포트(인터페이스) 목록이 잡힐 수 있습니다. |
| **SNMP 없음·WAN 통계만** | **포트별 UP/DOWN 테이블** 을 기대하기 어렵습니다. 이 앱의 스위치 포트 기능은 **사용할 수 없을 수 있습니다.** |
| **광단말(ONT)·랜 카피 일체형** | 물리 포트가 적고 브리지 위주인 경우 **의미 있는 포트 리스트** 가 나오지 않을 수 있습니다. |

이 계열은 **Cisco SSH 폴백이 없으므로** 반드시 **SNMP로 IF-MIB 응답**이 나오는지, 운영 PC에서 `snmpwalk` 등으로 먼저 확인하는 것을 권장합니다.

## 9. 자주 나는 오류

| 증상 | 점검 |
| --- | --- |
| `SNMP 인증 설정 없음` | `community` 또는 v3 `v3_username`/`v3_auth_key` 누락 |
| `SNMP 응답 없음 또는 인증 실패` | 방화벽 UDP **161**, 커뮤니티/v3 암호·엔진ID, ACL |
| 비-Cisco에서 빈 목록 | SSH 폴백 없음 → SNMP를 반드시 성공시켜야 함 |
| Cisco만 SSH로 된다 | TextFSM 파싱 실패 시 `pip` 로 `ntc-templates` 설치 여부 확인 |

## 10. 관련 코드

- `switch_port_monitor.py` — SNMP 워크, Cisco SSH 파싱
- `devices.example.yaml` — 샘플 인벤토리

다음 단계: [API 레퍼런스](../reference/api) · [시작하기](./getting-started)

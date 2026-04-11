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

## 6. 자주 나는 오류

| 증상 | 점검 |
| --- | --- |
| `SNMP 인증 설정 없음` | `community` 또는 v3 `v3_username`/`v3_auth_key` 누락 |
| `SNMP 응답 없음 또는 인증 실패` | 방화벽 UDP **161**, 커뮤니티/v3 암호·엔진ID, ACL |
| 비-Cisco에서 빈 목록 | SSH 폴백 없음 → SNMP를 반드시 성공시켜야 함 |
| Cisco만 SSH로 된다 | TextFSM 파싱 실패 시 `pip` 로 `ntc-templates` 설치 여부 확인 |

## 7. 관련 코드

- `switch_port_monitor.py` — SNMP 워크, Cisco SSH 파싱
- `devices.example.yaml` — 샘플 인벤토리

다음 단계: [API 레퍼런스](../reference/api) · [시작하기](./getting-started)

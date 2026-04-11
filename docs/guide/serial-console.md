# 시리얼(콘솔) 포트 접속 — 장비별 참고

USB–시리얼 변환기·롤오버(RJ45–RS232) 케이블 등으로 **장비 콘솔 포트**에 연결했을 때, 터미널 프로그램 설정과 **자주 쓰는 CLI 명령**을 정리했습니다.  
이 앱의 **대시보드·SNMP 수집과는 별개**이며, **초기 IP/SNMP 설정·트러블슈팅**할 때 참고용입니다.

::: tip 관련 문서
원격으로 포트 상태를 보려면 [스위치 포트 (SNMP)](./switch-ports) 를 설정하세요.
:::

## 0. Windows에서 공통으로 할 일

1. 케이블 연결 후 **장치 관리자**에서 **COM 번호**(예: `COM3`) 확인.
2. 터미널: [PuTTY](https://www.putty.org/) · Tera Term · Windows Terminal + `mode` 등.
3. 기본적으로 **8 데이터 비트 · 패리티 없음 · 1 스톱 비트 (8N1)** 를 먼저 시도합니다.
4. **흐름 제어(Flow control)** 는 장비마다 다릅니다. 응답이 깨지면 **None** ↔ **XON/XOFF** 를 바꿔 봅니다.

---

## 1. Cisco (IOS / IOS-XE)

| 항목 | 일반값 |
| --- | --- |
| 속도(Baud) | **9600** (구형·스위치 많음), 일부 **115200** |
| 데이터 | 8 · 패리티 없음 · 스톱 1 |
| 흐름 제어 | **없음(None)** 이 흔함 |

부팅 직후 아무 것도 안 보이면 **Enter** 몇 번, 또는 속도를 **115200** 으로 바꿔 봅니다.

**포트·링크 상태 확인 (대시보드 SNMP와 대조할 때 유용)**

```text
show interfaces status
show ip interface brief
show version
```

**SNMP 켜기 (예시 — 모델·IOS 버전에 따라 다름)**

```text
configure terminal
snmp-server community YOURCOMMUNITY RO
! 또는 snmp-server user ... v3
end
write memory
```

---

## 2. Cisco NX-OS (Nexus)

콘솔은 보통 **9600 8N1**. 명령 체계가 IOS와 다릅니다.

```text
show interface brief
show port-channel summary
show version
```

SNMP 예시는 해당 NX-OS 문서를 따르세요.

---

## 3. Juniper (JunOS)

| 항목 | 일반값 |
| --- | --- |
| 속도 | **9600** 또는 **57600 / 115200** (제품·펌웨어 확인) |

```text
show interfaces terse
show interfaces descriptions
show snmp
```

SNMP 활성화는 JunOS `snmp` 스탠자 설정이 필요합니다(제품 매뉴얼 참고).

---

## 4. Ubiquiti — EdgeRouter / EdgeMAX (Vyatta 계열)

| 항목 | 일반값 |
| --- | --- |
| 속도 | **115200** 8N1 이 흔함 (펌웨어에 따라 57600) |

```text
show interfaces
show interfaces ethernet eth0
show configuration
```

UniFi 스위치 **전용 콘솔이 없고 컨트롤러만 있는 경우**는 시리얼 대신 **웹/UniFi** 로 설정합니다.

---

## 5. HPE — Comware (H3C 계열)

| 항목 | 일반값 |
| --- | --- |
| 속도 | **9600** 8N1 이 많음 |

```text
display interface brief
display snmp-agent sys-info
display version
```

---

## 6. Aruba (AOS-Switch, 예: ProCurve 계열)

콘솔 **9600 8N1** 이 일반적입니다.

```text
show interfaces status
show snmp-server
show version
```

---

## 7. Dasan (다산)

제품·펌웨어마다 CLI가 **Cisco 유사** 또는 **전용 명령**입니다. **해당 모델 사용자 매뉴얼의「콘솔」「터미널」** 절에서 **Baud rate** 를 확인하세요.

**흔한 패턴 (참고용 — 반드시 매뉴얼 대조)**

```text
show interface status
show system
show snmp
! 또는 display ... 계열
```

SNMP·포트 표시 명령은 **모델별 PDF**가 가장 정확합니다.

---

## 8. Dovado / 다보링크 등 SOHO

- **Dovado** 일부 모델은 **미니 USB 콘솔** 또는 **Telnet/SSH만** 제공합니다. 시리얼이 있어도 **단순 부팅 로그** 수준이라 스위치식 `show port` 가 없을 수 있습니다.
- **다보링크** 등 국내 SOHO는 **웹 관리만**인 경우가 많습니다. 시리얼이 있다면 제조사 안내서의 **통신 속도**를 따르세요.

---

## 9. 정리

| 벤더 | 시리얼 속도(먼저 시도) | 포트 상태 확인 예시 |
| --- | --- | --- |
| Cisco IOS | 9600 → 115200 | `show interfaces status` |
| Cisco NX-OS | 9600 | `show interface brief` |
| Juniper | 9600 / 57600 / 115200 | `show interfaces terse` |
| Ubiquiti Edge | 115200 | `show interfaces` |
| HPE Comware | 9600 | `display interface brief` |
| Aruba AOS-S | 9600 | `show interfaces status` |
| 다산 | 매뉴얼 확인 | 모델별 `show` / `display` |
| SOHO | 매뉴얼·미지원 다수 | 웹만 가능한 경우 많음 |

다음: [스위치 포트 (SNMP)](./switch-ports) · [시작하기](./getting-started)

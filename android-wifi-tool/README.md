# Wi‑Fi 도구 (안드로이드 단독)

PC의 Flask/Windows `netsh` 프로젝트와 **별도**인, 안드로이드 폰에서만 동작하는 Wi‑Fi 정보·주변 AP 스캔 앱입니다.

## 기능

- 현재 연결 Wi‑Fi: SSID, BSSID, 주파수, RSSI, 협상 링크 속도, (Android 11+) 표준(802.11n/ac/ax 등)
- 주변 AP 스캔: 신호 세기·주파수·보안 요약(기기/OS에 따라 BSSID 등이 제한될 수 있음)

## 요구 사항

- Android **10 (API 29)** 이상 (스캔 콜백·Executor API 정렬)
- **Android Studio** Koala(2024.x) 등 최신 버전 + **JDK 17**
- 첫 빌드 전 `local.properties`에 SDK 경로가 있어야 합니다. (Android Studio에서 폴더를 열면 자동 생성되는 경우가 많습니다.)

```properties
sdk.dir=C\:\\Users\\이름\\AppData\\Local\\Android\\Sdk
```

## 빌드 (APK)

프로젝트 루트 `android-wifi-tool`에서:

```bat
gradlew.bat assembleDebug
```

생성 APK 경로:

`app\build\outputs\apk\debug\app-debug.apk`

릴리스 서명 APK는 Android Studio **Build → Generate Signed Bundle / APK** 로 만드는 것이 일반적입니다.

## 권한 안내

- **정확한 위치**, **Android 13+ 근처 Wi‑Fi 기기**: SSID 표시와 스캔에 시스템 정책상 필요합니다. 앱은 위치를 서버로 보내지 않습니다.
- 일부 제조사 ROM에서는 **위치 스위치 ON**이어야 SSID가 보입니다.

## 한계 (PC 버전과의 차이)

- Windows `iperf3`·`netsh` 기반 처리량 측정은 **포함하지 않습니다**. (별도 iperf3 클라이언트 앱 조합은 가능)
- 스캔 횟수는 OS가 **스로틀**할 수 있습니다.

## 패키지 ID

`com.networkip.wifitool` — 스토어 배포 시 원하면 변경하세요.

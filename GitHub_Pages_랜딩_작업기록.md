# NetWork-IP Search — GitHub Pages 랜딩 작업 기록

**최종 갱신:** 2026-04-11

## 목적

[Portfolio](https://karin01.github.io/Portfolio/)처럼 **`https://karin01.github.io/NetWork-IP-Search/`** 를 열면 **문서(VitePress)가 아니라 일반 웹 랜딩 페이지**가 보이게 함.

## 배포 구조 (WHY)

- 사용자 요청: “메뉴얼이 먼저 열리지 말고 Portfolio 같은 웹 페이지”.
- VitePress는 기본적으로 **문서 사이트 UI**라 루트만으로는 Portfolio와 같은 인상이 나기 어렵습니다.
- 따라서 **루트는 순수 정적 HTML**(`site-landing/`), **문서는 하위 경로**(`/manual/`)로 분리했습니다.

## 경로 정리

| URL | 내용 |
| --- | --- |
| `…/NetWork-IP-Search/` | `site-landing/index.html` (히어로·내비·실행 안내) |
| `…/NetWork-IP-Search/manual/` | VitePress (`docs/` 빌드, `base: /NetWork-IP-Search/manual/`) |

## 관련 파일

- `site-landing/` — `index.html`, `styles.css`, `favicon.svg`
- `.github/workflows/deploy-pages.yml` — VitePress 빌드 후 `_site`에 랜딩 + `manual/` 복사 → `gh-pages` 푸시
- `docs/.vitepress/config.mjs` — Actions 시 `base` = `/NetWork-IP-Search/manual/`, 네비에 **프로젝트 홈** 링크

## 제약

GitHub Pages는 **정적 파일만** 서빙합니다. Flask 대시보드는 **로컬**(또는 PaaS)에서 실행합니다.

## 로컬 빌드 참고

`docs` 가 Google Drive 동기 경로에 있으면 `npm install` 이 실패할 수 있어, CI 빌드를 기준으로 두는 것이 안전합니다.

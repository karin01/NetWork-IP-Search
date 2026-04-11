// 로컬 `npm run docs:dev` 는 `/` . Actions 빌드는 루트에 단독 랜딩(site-landing)을 두고, VitePress만 `/manual/` 에 배포
const base = process.env.GITHUB_ACTIONS ? "/NetWork-IP-Search/manual/" : "/";

export default {
  base,
  title: "NetWork-IP Search",
  description: "LAN 장치 스캔, Wi‑Fi 분석, 로그·자동화 — 로컬 대시보드와 기술 문서",
  lang: "ko-KR",
  appearance: "dark",
  head: [
    ["link", { rel: "icon", href: `${base}favicon.svg`, type: "image/svg+xml" }],
  ],
  themeConfig: {
    logo: "/favicon.svg",
    nav: [
      {
        text: "프로젝트 홈",
        link: "https://karin01.github.io/NetWork-IP-Search/",
      },
      { text: "시작하기", link: "/guide/getting-started" },
      { text: "Flask 실행", link: "/guide/flask-server" },
      { text: "스위치 포트", link: "/guide/switch-ports" },
      { text: "레퍼런스", link: "/reference/api" },
      { text: "GitHub", link: "https://github.com/karin01/NetWork-IP-Search" },
    ],
    sidebar: [
      {
        text: "가이드",
        items: [
          { text: "시작하기", link: "/guide/getting-started" },
          { text: "Flask 서버 실행 (대시보드)", link: "/guide/flask-server" },
          { text: "스위치 포트 (Cisco·Juniper·기타)", link: "/guide/switch-ports" },
          { text: "로그 분석 랩", link: "/guide/log-lab" },
          { text: "장비 자동화", link: "/guide/automation" }
        ]
      },
      {
        text: "레퍼런스",
        items: [{ text: "API", link: "/reference/api" }]
      }
    ],
    socialLinks: [
      { icon: "github", link: "https://github.com/karin01/NetWork-IP-Search" },
    ],
    footer: {
      message: "소개 페이지: 사이트 루트 · 이곳은 상세 문서(/manual/)",
      copyright: "NetWork-IP Search",
    },
  },
};

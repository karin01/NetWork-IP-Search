// 로컬 `npm run docs:dev` 는 `/` , GitHub Actions 빌드는 `GITHUB_ACTIONS` 로 서브경로 배포
const base = process.env.GITHUB_ACTIONS ? "/NetWork-IP-Search/" : "/";

export default {
  base,
  title: "NetWork-IP Search 매뉴얼",
  description: "로그 분석, 장비 자동화, 네트워크 대시보드 운영 문서",
  themeConfig: {
    nav: [
      { text: "홈", link: "/" },
      { text: "가이드", link: "/guide/getting-started" },
      { text: "레퍼런스", link: "/reference/api" }
    ],
    sidebar: [
      {
        text: "가이드",
        items: [
          { text: "시작하기", link: "/guide/getting-started" },
          { text: "로그 분석 랩", link: "/guide/log-lab" },
          { text: "장비 자동화", link: "/guide/automation" }
        ]
      },
      {
        text: "레퍼런스",
        items: [{ text: "API", link: "/reference/api" }]
      }
    ]
  }
};

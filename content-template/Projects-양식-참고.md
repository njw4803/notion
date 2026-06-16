# Projects MD 양식 참고 (Notion 동기화 대상 아님)

아래 frontmatter·본문을 `content/Projects/본인프로젝트.md` 로 복사해 사용하세요.

```markdown
---
notion_section: project
layout: description
duties_label: true
project_name: (프로젝트명)
affiliation: (소속)
period_start: "YYYY-MM-DD"
period_end: null
one_liner: (한 줄 소개)
role:
  - Back-End Developer
skills: []
team_members: ""
---

Project Description
(프로젝트 개요)

담당 업무

### 프로젝트 상세 내용

**사용 기술 및 솔루션**

### 프로젝트를 통해 얻은 것
```

git 자동 갱신은 `git_projects.yaml` 의 `md` 경로와 `if_missing: create` 로도 생성할 수 있습니다 (가이드 §2-1, §3).

`update` 필드 요약: `always`(현재·주간) | `manual`(`--all`만) | `never`(git 미반영)

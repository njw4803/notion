---
notion_section: project
project_name: 현대 카드 DR 프로젝트
layout: description
duties_label: true
affiliation: 한솔인티큐브
period_start: "2025-02-03"
period_end: "2025-12-12"
team_members: CTI, IVR, PBX, 통계 팀
role:
  - Back-End & Front-End Developer
  - Project Leader
one_liner: 카드/캐피탈/커머셜 이중화 DR 센터 구성
skills:
  - Java
  - Spring Boot
  - Redis
  - Spring Security
  - Mybatis
  - Oracle
  - CentOs
  - React
project_learnings: ""
---

Project Description
한솔 통합 통계 솔루션(ISAC_STAT)을 기반으로 고도화 진행
파주 센터 증설로 인한 영등포/파주 통계 서버 사중화 구성 (영등포/파주 센터 이중화 DR 센터 구성)

담당 업무
- ICON DB → 통계 DB 콜 데이터 적재 15분 배치 PROCEDURE 개발 및 스케줄링 처리
- AS_IS 데이터 비교 검증 및 신규 CTI 구축으로 인한 콜 인입 데이터 검증
- React AG GRID를 활용한 통계보고서 비정형 페이지 개발
- 웹 전광판, vtp(IVR 채널 점유 현황 용) CTI Stat-Server 연동 Demon Application 개발
- PL 업무 - 보안 심의, 공용 계정 신청 및 방화벽 오픈 신청, 통계 DB 아카이브 용량 확인, 통계 운영 서버 CPU 점유율 확인 및 조치, 산출물(시스템 구성도, 테이블 정의서, 단위 테스트, 통합 테스트 등) 작성
- 운영 서버 Redis(Master, Slave) 구성 - 파주, 영등포(통계 서버1,통계 서버2, ap 서버) 총 6대로 master 파주 ap 서버, sentinel 그 외 5개 서버로 구성
- 로그인 otp, mpass 인증 연동 개발
- 현대 카드 통합 관리 시스템 연동 및 계정 동기화 처리

### 프로젝트 상세 내용

**사용 기술 및 솔루션**
- 언어: Java11, React
- 프레임워크: Spring Boot 3.2.3
- 라이브러리 및 기타 솔루션
  - ag-grid
  - TypeScript
- 서버: CentOS 7
- DB: Oracle 19, Redis
- 기타 협업 관리 도구
  - SVN

### 프로젝트를 통해 얻은 것

**PL의 담당 업무와 중요성
기존 프로젝트에서 PL을 담당하시던 선임 개발자의 갑작스러운 철수로 인해,
오픈을 세 달 앞둔 시점에서 PL 역할을 맡게 되었습니다.**
4명이 진행하던 프로젝트를 PL이였던 선임 개발자의 부재로 3명이 진행하게 되었고 주간 보고, 단위·통합 테스트, 보안 심의 문서 작성 등 다양한 PL 업무를 기존 개발 업무와 병행하면서 한동안 업무 과부하를 겪기도 했습니다.
사전에 PL 역할에 충분히 대비하지 못한 점에 대한 아쉬움도 컸습니다.
그럼에도 불구하고 매일 야근을 하더라도 무사히 오픈 해야겠다는 책임감으로 문제 없이 오픈을 완료했으며,
이 과정을 통해 값진 경험과 성장의 기회를 얻을 수 있었습니다.
---
**분석/설계 단계에서 더 집중을 하자!
그동안 개발 단계에만 집중해 왔으며, 분석·설계 단계에는 상대적으로 큰 비중을 두지 못했습니다. 이는 주로 선임 개발자의 지시에 따라 업무를 수행해 온 영향이 컸던 것 같습니다.**
하지만 이번 경험을 통해, 연차가 쌓일수록 단순한 개발 역할을 넘어 PL 역할 수행까지
함께 고민해야 한다는 점을 다시 한번 깊이 느끼게 되었습니다.
앞으로는 선임 개발자의 지시를 기다리는 데 그치지 않고,
스스로 고민하며 능동적으로 업무를 수행할 수 있는 개발자로 성장하고자 합니다.

---
affiliation: (주)도로시
duties_label: true
layout: description
notion_section: project
one_liner: (주)도로시 엔터프라이즈 데이터 플랫폼 SyncBox — 백엔드 API·Spark 파이프라인·사용자 매뉴얼 자동화
period_end: null
period_start: '2026-03-03'
project_learnings: ''
project_name: (주)도로시 Solution SyncBox
role:
- Back-End Developer
skills:
- Java
- Spring Boot
- Spring Security
- Mybatis
- Gradle
- PostgreSQL
- Redis
- Docker
- Git
- GitHub
- GitHub Actions
- Python
- Playwright
- Apache Spark
- Hadoop
team_members: 개발자 4명
---

Project Description
(주)도로시에서 개발 중인 SyncBox는 데이터 수집·가공·리포팅을 하나의 플랫폼으로 제공하는 B2B 솔루션입니다. 백엔드 API, 대용량 Import, Spark 기반 프로젝트 파이프라인, 외부 Embed 연동, CI 기반 사용자 매뉴얼 자동화를 담당했습니다.

담당 업무
- GitHub Actions BE 자동 배포(develop-main push): bootJar 빌드 → SCP 전송 → syncbox.properties·log4j 설정 동기화 → stop/start/restart 기반 재기동, 배포 결과 Naver Bot 알림
- FE 기능 문서(MD) 기반 Playwright 화면 캡처·vLLM AI 슬라이드 생성·PPTX 조립 파이프라인 설계 및 구축 (Figma page-* 템플릿·표지·목차·개정이력·CRUD 배치 캡처, BE·FE 동일 SemVer tag 게이트)
- ReportCacheService·EmbedTokenService 인터페이스 분리 — syncbox.redis.enabled 로 Redis/InMemory 구현체 선택, Connection·Published·Draft 리포트 metadata·chart Redis 캐싱(TTL) 및 CRUD evict
- 외부 Embed iframe columns API X-Embed-Token 인증, Draft auto_refresh 및 Connections 최신 데이터셋 정책 API
- TABLE_CHART headerGroups·pivotColumn·Numbers 설정 DTO, 차트 필터 BASIC/ADVANCED/RANGE 처리, 필터·데이터셋 오류 i18n 메시지 반환, JwtAuthorizationFilter downstream 예외 전파 수정
- Excel 2003 XML Spreadsheet(.xls) SAX 파서 기반 미리보기·반입, JDBC Import alias·MariaDB 메타데이터 버그 수정
- Spark 3.5 stage-job 매핑 수정, Chart Spark pending 로그 보강, APF/SFTP 운영 이슈 대응

### 프로젝트 상세 내용

**사용 기술 및 솔루션**
<!-- AUTO:stack -->
- 언어: Java 11 (릴리스 tag v1.0.0)
- 프레임워크: Spring Boot, Spring Security, MyBatis
- 서버/인프라: Docker, PostgreSQL, Redis, Apache Spark 3.5.0, Hadoop(HDFS)
- CI/자동화: GitHub Actions, Python, Playwright, Notion API
- Spring Boot 2.7.6 + MyBatis + PostgreSQL 레이어드 아키텍처
- Redis: syncbox.redis.enabled=false — true 시 Report·Embed 토큰 Redis, false 시 인메모리 구현체 선택
<!-- /AUTO:stack -->

### 프로젝트를 통해 얻은 것

<!-- AUTO:learnings -->
**SyncBox 백엔드·플랫폼 개발**
develop-main push 기반 GitHub Actions 자동 배포와 FE·BE SemVer tag 연동 매뉴얼 자동화를 구축해, 코드 변경부터 배포·사용자 문서 반영까지 end-to-end 흐름을 연결하는 방법을 익혔습니다. 리포트·Embed 도메인에서 Redis TTL 캐싱·환경별 빈 분리, 외부 Embed 인증, 차트 필터·i18n 오류 응답을 설계·운영했고, JWT 필터가 비즈니스 예외를 401로 오인하던 운영 장애처럼 증상과 원인이 어긋나는 이슈를 추적·해결하는 경험을 쌓았습니다. Excel SAX 스트리밍 Import, JDBC 다중 DB 연동, Spark stage-job 매핑 등 대용량 데이터 수집·가공 파이프라인을 운영하며 성능·안정성·로그 가시성을 함께 맞추는 법을 배웠습니다.
<!-- /AUTO:learnings -->
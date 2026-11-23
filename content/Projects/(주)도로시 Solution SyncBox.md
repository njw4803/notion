---
affiliation: (주)도로시
duties_label: true
layout: description
notion_section: project
one_liner: (주)도로시 엔터프라이즈 데이터 플랫폼 SyncBox — AI 어시스턴트·시스템 모니터링·리포트 Embed 서버·데이터 파이프라인
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
- FastAPI
- Playwright
- Apache Spark
- Hadoop
- Prometheus
- React
- TypeScript
team_members: 개발자 4명
---

Project Description
(주)도로시에서 개발 중인 SyncBox는 데이터 수집·가공·리포팅을 하나의 플랫폼으로 제공하는 B2B 솔루션입니다. 백엔드를 중심으로 프론트엔드와 인프라까지 맡아 AI 어시스턴트, 시스템 모니터링, 리포트 Embed 서버 분리, 데이터 파이프라인 안정화, 배포·매뉴얼 자동화를 개발했습니다.

담당 업무
- **AI 어시스턴트 — 사내 구축 LLM(Gemma) 연동 대화형 데이터 전처리**
  - 자연어 요청을 전처리 Step 20여 종(행 제거·계산 컬럼·집계·조인·피벗 등)으로 제안하고 승인 카드로 적용
  - SQL 을 붙이면 데이터셋과 Step 으로 변환(WITH·서브쿼리·윈도 함수, 7개 DB 방언)하고 같은 결과 SQL 추천
  - 요청 분류 → 기능별 프롬프트·스키마의 2단 호출 구조 설계, 실제 모델 평가 세트로 회귀 검증
  - 사용법 안내, 참고 문서 기반 답변, 인사이트 요약, FLOW 결과 검사와 실패 원인 설명
- **사용자 정의 함수 · 파이썬 실행 환경**
  - 수식 사용자 정의 함수 — 생성·버전 고정·공유, Step 과 리포트 계산 필드에서 사용, 말로 요청하면 AI 가 작성
  - 파이썬 실행 사이드카(FastAPI) — 격리된 프로세스에서 사용자 코드 실행, Spark DataFrame 을 Apache Arrow 로 전달
  - 파이썬 변환 Step·수식 안 파이썬 함수, scipy·statsmodels·scikit-learn 분석, Spark MLlib 군집 Step
- **시스템 모니터링 구축**
  - Prometheus·Alertmanager·exporter 스택(Docker Compose) — 알림 규칙 40여 개와 규칙 테스트, 메신저 봇·메일 알림 중계, 폐쇄망용 설치 번들
  - 애플리케이션 커스텀 지표(Actuator·Micrometer)와 상태·알림·추이·원인 분석 API, 웹소켓 실시간 전송
  - React 모니터링 화면 — 서비스별 상태 카드, 추이 그래프, 알림 대응 이력·알림 끄기
- **리포트 Embed 서버 분리 · 외부 임베드 연동**
  - 외부 시스템용 Connection Report API — API key·Embed 토큰(JWT) 인증, 허용 IP·Origin 검증, 고객별 데이터 범위 필터
  - 리포트 캐시·Embed 세션을 공유 저장소(Redis/JDBC)로 이전, 캐시 사전 적재·만료 전 자동 갱신
  - Spark·Hadoop 의존을 뗀 조회 전용 Embed 서버로 분리(jar 445MB → 52MB)
- **리포트 · 차트 API**
  - 차트 집계 확장 — COUNT_DISTINCT·FIRST, 전체 대비 비율(Quick Table Calculation), Summary Card, 계산 필드(Compute)
  - 리포트 버전 관리 — Draft 복사, 최신 데이터 자동 반영(auto_refresh), Connection 고정 버전·최신 버전 반영
- **데이터 파이프라인(FLOW·Spark) 안정화 · 성능 개선**
  - FLOW 실행 고착(RUNNING)·동시 실행 캐시 충돌·스케줄 중복 실행·발행 실패 등 운영 장애의 원인 추적과 수정
  - Spark 세션 자동 재생성, Spark 3.5 호환, FLOW·Spark 전용 로그 분리
  - 대용량 업로드·미리보기·엑셀 파싱·Step 처리 속도 개선, Excel 2003 XML(.xls) 반입·Oracle Export 보강
- **CI/CD · 배포 자동화**
  - GitHub Actions 로 백엔드·프론트엔드·Embed·모니터링 스택 자동 배포, 기동 확인 실패 시 자동 롤백
  - 배포 키·시크릿 정리, 주기 헬스체크, 배포 결과 메신저 봇 알림
- **사용자 매뉴얼 자동화**
  - Playwright 화면 캡처 → PPTX 매뉴얼 조립, 릴리스 tag(SemVer) 단위로 생성
  - 캡처 위 번호 표시, 메뉴 순서 목차, 지난 버전 대비 개정 이력·NEW 표시 자동화

### 프로젝트 상세 내용

**사용 기술 및 솔루션**
<!-- AUTO:stack -->
- 언어: Java 11, Python 3.11, TypeScript
- 프레임워크: Spring Boot 2.7.6, Spring Security, MyBatis, React 18, FastAPI
- 데이터·인프라: PostgreSQL, Redis, Apache Spark 3.5.0, Hadoop(HDFS), Docker
- AI: 사내 구축 LLM(Gemma) — Ollama·llama-server(OpenAI 호환 API)
- 모니터링: Prometheus, Alertmanager, Micrometer·Actuator, exporter(node·postgres·blackbox·process·nginx)
- CI/자동화: GitHub Actions, Playwright, python-pptx
- 릴리스: v1.1.0
<!-- /AUTO:stack -->

### 프로젝트를 통해 얻은 것

<!-- AUTO:learnings -->
**LLM 을 제품 기능으로 만드는 방법**
모델이 그럴듯한 답을 지어내지 않도록 요청 분류 → 기능별 프롬프트·스키마 → 서버 검증 순서로 단계를 나누고, 실제 모델 평가 세트로 회귀를 확인하며 기능을 넓히는 방식을 익혔습니다.
**장애를 먼저 알아채는 운영 체계**
지표 수집·알림 규칙·대응 절차를 하나의 흐름으로 설계하고 감시 도구 자체의 장애까지 감시하면서, 운영 중인 서비스를 숫자로 보고 판단하는 법을 배웠습니다.
**대용량 파이프라인의 문제를 추적하는 경험**
Spark 기반 실행이 멈추거나 캐시가 충돌하는 문제처럼 증상과 원인이 어긋나는 이슈를 로그와 상태 전이로 추적해 재현·수정했고, 배포 자동화와 롤백으로 변경을 안전하게 내보내는 흐름을 만들었습니다.
<!-- /AUTO:learnings -->
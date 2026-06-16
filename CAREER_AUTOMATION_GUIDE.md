# 노션 경력기술서 자동화 — 설치·사용 가이드

> **이 문서 하나만 읽으면 됩니다.**  
> 동료에게는 **스크립트 + `content/` 기본 틀 + `config.example.env` + `git_projects.example.yaml` + 이 가이드**를 전달하세요.

---

## 0. 처음 설치 (권장 순서)

> `setup.sh` → `.env`·`git_projects.yaml` 수정 → `content/` 채우기 → 7단계 수동 확인 → **8~9단계 주간 자동 실행 등록·검증**.

```bash
# 1) 도구 배치 (notion/ 을 git 저장소 루트에 둠)
./notion/setup.sh

# 2) 개인 설정
cp notion/config.example.env notion/.env              # Notion 토큰·DB ID 입력
cp notion/git_projects.example.yaml notion/git_projects.yaml  # repo·브랜치·md 수정
# NOTION_PROJECTS_DB_ID 모르면: cd notion && . .venv/bin/activate && python3 sync_to_notion.py --discover

# 3) Python 환경
cd notion && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt && cd ..

# 4) git exclude (각자 1회)
echo 'notion/' >> .git/info/exclude

# 5) content/ 플레이스홀더를 본인 정보로 수정 (Contact, Introduce, Skills 등)
#    첫 Notion 반영: ./notion/run_sync.sh

# 6) Projects MD 준비 (Projects/ 가 비어 있으면)
cd notion && python3 sync_to_notion.py --import   # Notion에 경력 있을 때
# 또는 git_projects.yaml 에 if_missing: create

# 7) git 자동 갱신 (수동 1회 — 동작 확인)
git checkout develop-main   # yaml 의 branch 와 일치하는 브랜치
./notion/update_detail_on_tag.sh --rebuild-compressed --dry-run   # 미리보기
./notion/update_detail_on_tag.sh --rebuild-compressed             # 반영 + Notion

# 8) 주간 자동 실행 등록 (macOS — 매주 월 10:30 + 로그인 시 catch-up)
./notion/install_launchd.sh
launchctl list | grep dorosee.syncbox-notion   # 에이전트 2개 보이면 등록 OK

# 9) 자동 실행 동작 확인 (등록 직후 1회 테스트)
./notion/run_scheduled_update.sh calendar        # 정기 스케줄과 동일 로직 즉시 실행
tail -30 /tmp/notion-update.log                  # [launchd] done exit=0 확인
cat notion/.launchd_state.json                   # last_success_at 시각 확인

# (선택) catch-up 에이전트만 따로 테스트
# launchctl kickstart -k gui/$(id -u)/com.dorosee.syncbox-notion-update-catchup
# tail -10 /tmp/notion-update.log
```

과거 프로젝트 일괄 반영: yaml에 `update: manual` 등록 후  
`./notion/update_detail_on_tag.sh --all --rebuild-compressed` (§3 참고)

**7단계** = 수동 갱신 확인. **8~9단계** = 매주 자동 갱신 등록 + **실제로 한 번 돌아가는지** 확인.  
Windows/Linux는 launchd 미지원 → 7·9단계의 `run_scheduled_update.sh`를 cron 등으로 스케줄.

| 9단계 정상 신호 | 의미 |
|-----------------|------|
| 로그에 `[launchd] done exit=0` | 스케줄 스크립트 정상 종료 |
| `.launchd_state.json`의 `last_success_at` | 이번 주 실행 이력 저장됨 |
| `변경 없음`만 나와도 OK | 커밋이 없어서 MD 안 바뀐 것 — 스케줄 자체는 정상 |

---

## 1. 무엇을 하는 도구인가

로컬 `notion/content/` MD를 **본인 Notion 경력기술서**와 동기화하고, **본인 git 커밋**을 읽어 프로젝트 MD의 담당 업무·배운 점을 자동 정리합니다.

```
git 커밋 (git_projects.yaml 에 등록된 repo·branch)
    → update_from_git.py (주제별 압축)
    → content/Projects/*.md
    → sync_to_notion.py
    → Notion
```

**비유:** `git_projects.yaml` = “이 브랜치 checkout 시 어느 MD를 채울지” 적어 둔 목록.

| 구분 | 설명 |
|------|------|
| `git_projects.yaml` | 브랜치 · repo 경로 · MD 경로 매핑 (**필수**) |
| `.env` | Notion 토큰·페이지 ID·DB ID |
| `content/` | 본인 경력 MD 전체 |
| `.update_state.json` | git → MD 마지막 처리 커밋 (프로젝트별) |
| `.sync_state.json` | MD → Notion 페이지 ID 캐시 |

`notion/` 폴더는 **git에 올리지 않습니다** (`.git/info/exclude`에 `notion/` 추가).

---

## 2. 동료에게 줄 것 / 주지 말 것

### 줄 것 (도구 + 기본 틀)

`update_from_git.py`, `sync_to_notion.py`, `scheduled_update.py`, `*.sh`, `requirements.txt`, `config.example.env`, `git_projects.example.yaml`, `githooks/`, `launchd/`, **`content/` (플레이스홀더 MD)**, **이 가이드**

배포 zip의 `content/`는 **본인 정보 없는 기본 틀**입니다. Contact·Introduce·Skills 등을 본인 내용으로 바꾼 뒤 사용하세요.

### 주지 말 것 (개인)

| 파일 | 이유 |
|------|------|
| `.env` | Notion 토큰 (비밀) |
| `git_projects.yaml` | 본인 로컬 repo 경로 |
| **채워진 `content/`** | 본인 경력 본문이 들어간 폴더 전체 |
| `.sync_state.json` | 본인 Notion 페이지 ID — **넘기면 남의 Notion과 섞임** |
| `.update_state.json` | 처리 이력 |
| `.venv/` | PC마다 재생성 |

받은 사람은 `.sync_state.json`·`.update_state.json` **삭제 후** 새로 시작하는 것을 권장합니다.

배포 zip에는 **`content/` 기본 틀**(Contact·Skills 등 플레이스홀더)이 포함됩니다. `content/Projects/` 는 비어 있고, 프로젝트 MD는 `--import`·`if_missing: create`·직접 작성으로 추가합니다.

---

## 2-1. content/ — 기본 틀과 Projects

### 배포본에 포함되는 `content/` (플레이스홀더)

| 파일 | 용도 |
|------|------|
| `Contact.md`, `Channel.md` | 연락처·링크 |
| `Introduce.md` | 자기소개 |
| `Skills.md` | 스킬 (카테고리별 heading) |
| `Education.md`, `Certifications.md`, `Etc.md` | 학력·자격·기타 |
| `Projects-양식-참고.md` | 프로젝트 MD 작성 예시 (**동기화 안 됨**) |
| `Projects/` | 비어 있음 — 프로젝트 MD는 각자 추가 |

zip 풀고 **플레이스홀더를 본인 정보로 수정**한 뒤 `./notion/run_sync.sh` 로 Notion에 첫 반영할 수 있습니다.

### Projects MD — git 자동 갱신용

yaml `update` 로 **계속 갱신할지 / 1회만 / 안 할지** 구분합니다 (§3).

| 방법 | 언제 | 명령/설정 |
|------|------|-----------|
| Notion 가져오기 | Notion에 이미 프로젝트 경력이 있을 때 | `python3 sync_to_notion.py --import` |
| 자동 골격 생성 | 새 프로젝트, MD가 아직 없을 때 | `if_missing: create` + `project_name`, `period_start` 등 |
| 직접 작성 | 소개 문단 등을 손으로 쓸 때 | `content/Projects/프로젝트명.md` 생성 |
| 과거 1회 반영 | 옛 repo 커밋으로 담당 업무만 채우기 | `update: manual` + `--all --rebuild-compressed` |
| git 미반영 | import·수동 MD 유지 | `update: never` |

`if_missing: skip`(기본)이면 MD가 없을 때 **에러 없이 건너뜁니다** (`건너뜀 — MD 없음` 로그). “안 돌아간다”고 느끼면 위 방법으로 MD를 먼저 준비하세요.

### `if_missing: create` 로 만들어지는 MD 골격

frontmatter 예시:

```yaml
notion_section: project
layout: description
duties_label: true
project_name: (yaml project_name 또는 파일명)
affiliation: (yaml)
period_start: "2025-01-01"
role: [Back-End Developer]
one_liner: (yaml one_liner 또는 project_name)
```

본문 골격:

```markdown
Project Description
(한 줄 소개)

담당 업무

### 프로젝트 상세 내용

**사용 기술 및 솔루션**

### 프로젝트를 통해 얻은 것
```

생성 직후 담당 업무·스택·배운 점은 비어 있습니다. 같은 실행에서 `--rebuild-compressed` 등으로 커밋이 있으면 자동으로 채워집니다.

### 권장 순서 (처음 받은 동료)

```bash
# 1) Notion에 경력이 이미 있음
cd notion && python3 sync_to_notion.py --import

# 2) git_projects.yaml 작성 후
./notion/update_detail_on_tag.sh --rebuild-compressed --dry-run
./notion/update_detail_on_tag.sh --rebuild-compressed
```

---

## 3. git_projects.yaml (핵심)

```bash
cp notion/git_projects.example.yaml notion/git_projects.yaml
```

```yaml
projects:
  # 현재 프로젝트 — 주간·일반 실행에 포함
  - branch: develop-main
    repo: ..
    md: content/Projects/(주)도로시 Solution SyncBox.md
    template: syncbox
    update: always          # 기본값 (생략 가능)
    if_missing: skip

  # 과거 프로젝트 — --all 할 때만 git 반영 (주간 스케줄 제외)
  - branches: [main, develop]
    repo: /path/to/nexus-repo
    md: content/Projects/Nexus Solution 고도화 작업.md
    template: generic
    update: manual
    if_missing: skip

  # git으로 덮어쓰지 않음 (Notion import·수동 MD만)
  # - repo: /path/to/old-repo
  #   md: content/Projects/옛 프로젝트.md
  #   update: never
  #   if_missing: skip

  # MD 없을 때 새로 만들기
  # - branch: feature/new
  #   repo: /path/to/repo
  #   md: content/Projects/신규 프로젝트.md
  #   update: always
  #   if_missing: create
  #   project_name: 신규 프로젝트
  #   period_start: "2025-01-01"
  #   template: generic
```

| 필드 | 설명 |
|------|------|
| `branch` / `branches` | 커밋을 읽을 브랜치 ref |
| `repo` | git 저장소 경로 (`..` = notion 상위 폴더) |
| `md` | 갱신할 MD (`content/Projects/...`) |
| `template` | `syncbox` \| `generic` |
| `if_missing` | MD **없을 때**: `skip`(기본) \| `create`(골격 생성) |
| `update` | MD **있을 때** git 갱신 여부 (아래 표) |

### `update` — 언제 git으로 MD를 갱신할까

| 값 | 일반 실행 (`update_detail_on_tag.sh`) | `--all` 실행 | 용도 |
|----|--------------------------------------|--------------|------|
| `always` (기본) | checkout 브랜치 일치 시 ✅ | ✅ | **현재** 프로젝트 |
| `manual` | ❌ 건너뜀 | ✅ | **과거** 프로젝트 1회성 일괄 반영 |
| `never` | ❌ | ❌ | Notion·수동 MD만 (git 미반영) |

**비유:** `if_missing` = “파일이 없으면 어떻게 할까”, `update` = “파일이 있어도 자동으로 계속 고칠까”.

### 과거 프로젝트 일괄 반영 순서

1. `content/Projects/`에 MD 준비 (`--import` 또는 직접 작성, `period_start`/`period_end` 권장)
2. 그때 쓰던 repo를 PC에 clone
3. yaml에 항목 추가 — **`update: manual`**, `repo`, `md`, `branches`
4. 미리보기: `./notion/update_detail_on_tag.sh --all --rebuild-compressed --dry-run`
5. 반영: `./notion/update_detail_on_tag.sh --all --rebuild-compressed`

이후 **주간 launchd**는 `update: always`인 현재 프로젝트만 갱신합니다. 과거 항목은 다시 `--all`을 실행할 때만 바뀝니다.

### 실행 모드

| 명령 | 동작 |
|------|------|
| `update_detail_on_tag.sh` | `update: always` + checkout 브랜치 **매칭**만 |
| `... --rebuild-compressed` | 위 대상의 커밋 전체 **다시 압축** |
| `... --all --rebuild-compressed` | `update: manual`·`always` **전체** (과거 일괄) |
| `... --dry-run` | 미리보기만 |

---

## 4. Notion 최초 설정

### 4-1. Integration 토큰

1. Notion → Settings → Integrations → 새 internal integration
2. 경력기술서 **루트 페이지**에 integration 연결(공유)
3. `.env`에 저장:

```bash
NOTION_TOKEN=secret_또는_ntn_본인토큰
```

### 4-2. 페이지 ID · DB ID

```bash
NOTION_RESUME_PAGE_ID=경력기술서_루트_페이지_UUID   # URL 에서 32자리
```

```bash
cd notion && . .venv/bin/activate
python3 sync_to_notion.py --discover
# 출력된 Projects DB id → .env
NOTION_PROJECTS_DB_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

`multiple data sources` 오류 시:

```bash
NOTION_PROJECTS_DB_ID=데이터소스_ID
NOTION_PROJECTS_PARENT_TYPE=data_source
```

### 4-3. Projects DB 컬럼 (권장)

Notion 테이블 title 컬럼명을 **`프로젝트 명`**으로 맞춥니다 (기본 `이름` → 변경).

| Notion 속성 | `.env` 변수 |
|-------------|-------------|
| 프로젝트 명 (Title) | `NOTION_PROP_PROJECT_NAME=프로젝트 명` |
| 진행 기간 (Date) | `NOTION_PROP_PERIOD=진행 기간` |
| 역할 | `NOTION_PROP_ROLE=역할` |
| Skills | `NOTION_PROP_SKILLS=Skills` |

전체 예시는 `config.example.env` 참고.

### 4-4. 경력 MD 준비

배포본 `content/`에 **섹션 기본 틀**이 있습니다. Contact·Introduce 등을 본인 내용으로 수정하세요.

Notion에 이미 경력이 있으면 프로젝트는 가져오기가 편합니다:

```bash
cd notion && python3 sync_to_notion.py --import
```

→ `content/Projects/*.md` 가 생성됩니다. 없으면 직접 만들거나 `if_missing: create` 사용.

---

## 5. .env — 본인만 바꾸는 값

```bash
cp notion/config.example.env notion/.env
```

| 변수 | 필수 | 설명 |
|------|------|------|
| `NOTION_TOKEN` | ✅ | Integration 토큰 |
| `NOTION_RESUME_PAGE_ID` | ✅ | 경력 루트 페이지 |
| `NOTION_PROJECTS_DB_ID` | ✅ | Projects DB ID |
| `NOTION_GIT_AUTHOR_EMAIL` | 권장 | 본인 git commit author |

```bash
git log --author="본인@email.com" --oneline -n 5   # 커밋 나오는지 확인
```

---

## 6. git → MD — 무엇이 바뀌나

### 포함·제외 커밋

- **포함:** `feat/fix/refactor`, "개발·배포·자동화·연동" 등
- **제외:** merge, `chore(ci): v* 재생성`, comment 추가 등

### MD 섹션

| 섹션 | 자동 갱신 |
|------|-----------|
| 담당 업무 | 커밋 → **주제별 bullet** (최대 12개, 커밋 나열 아님) |
| 상세 스택 | `<!-- AUTO:stack -->` (build.gradle 등) |
| 배운 점 | `<!-- AUTO:learnings -->` **callout 1개** |

`template: generic` 은 범용 주제 압축, `syncbox` 는 SyncBox 전용 문구.

### 첫 실행 vs 전체 재구성

- **첫 실행:** HEAD만 저장, MD 안 바꿈 (안전)
- **전체 재구성:** `--rebuild-compressed`

---

## 7. MD → Notion

```bash
./notion/run_sync.sh                    # MD 수정 후 Notion만
./notion/update_detail_on_tag.sh        # git → MD → Notion 한 번에
```

- **방향:** 로컬 MD → Notion (덮어씀)
- **가져오기:** `python3 sync_to_notion.py --import` (복원용만)

### `.sync_state.json`

MD 파일명 ↔ Notion 페이지 UUID 매핑. 없으면 이름으로 찾거나 새로 만듦. **남에게 주지 마세요.**

---

## 8. 주간 자동 실행 (macOS launchd)

**처음 설치 시 §0 8~9단계**에서 등록·동작 확인. 아래는 상세·문제 해결용입니다.

> 예전에 **crontab**을 썼다면 launchd로 옮긴 뒤 crontab 잔여 항목을 확인하세요. 이 도구는 **launchd 기준**입니다.

### 8-1. 설치

```bash
./notion/install_launchd.sh
```

| LaunchAgent | 역할 |
|-------------|------|
| `com.dorosee.syncbox-notion-update` | 매주 월 10:30 정기 실행 |
| `com.dorosee.syncbox-notion-update-catchup` | 로그인·부팅 시 놓친 주 보완 (`RunAtLoad`) |

경로는 `~/Documents/` 밖(예: `~/Developer/...`) 권장. 경로 바꾼 뒤에는 `install_launchd.sh` 다시 실행.

### 8-2. crontab 확인 (예전 설정 잔여)

```bash
crontab -l                    # 등록된 cron 목록 (없으면 "no crontab")
crontab -l 2>/dev/null | grep -i notion   # notion 관련만
```

`update_detail_on_tag` 가 보이면 **구 crontab이 남은 것**입니다. launchd와 **중복 실행**될 수 있으니 제거하세요.

```bash
# install_launchd.sh 가 notion cron 을 지우며 재등록
REMOVE_CRON=1 ./notion/install_launchd.sh

# 또는 수동 편집
crontab -e   # notion / update_detail_on_tag 줄 삭제
```

### 8-3. launchd 등록·동작 확인

```bash
# 등록 여부 (0 또는 - 가 정상)
launchctl list | grep dorosee.syncbox-notion

# 상세 상태
launchctl print gui/$(id -u)/com.dorosee.syncbox-notion-update | head -25
launchctl print gui/$(id -u)/com.dorosee.syncbox-notion-update-catchup | head -15

# 실행 로그
tail -50 /tmp/notion-update.log

# 이번 주 실행 이력 (notion/.launchd_state.json)
cat notion/.launchd_state.json
```

| 확인 항목 | 정상일 때 |
|-----------|-----------|
| `launchctl list \| grep dorosee` | 에이전트 2개 표시 |
| `/tmp/notion-update.log` | `[launchd]`·`[notion-update]` 로그 |
| `.launchd_state.json` | `last_success_at` 최근 시각 |

### 8-4. 수동으로 다시 실행 (스케줄과 동일)

```bash
# 주간 정기 실행과 동일 (즉시 git → MD → Notion)
./notion/update_detail_on_tag.sh

# launchd 가 호출하는 래퍼 (정기 스케줄과 동일 로직)
./notion/run_scheduled_update.sh calendar

# catch-up만 테스트 (이번 주 월 10:30 이후 & 아직 안 돌았을 때만 실행)
./notion/run_scheduled_update.sh load

# catch-up 에이전트 즉시 트리거 (등록 후 테스트)
launchctl kickstart -k gui/$(id -u)/com.dorosee.syncbox-notion-update-catchup
```

### 8-5. 제거·재설치

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.dorosee.syncbox-notion-update.plist
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.dorosee.syncbox-notion-update-catchup.plist

# 이후 다시 설치
./notion/install_launchd.sh
```

### 8-6. 맥 잠자기와 스케줄

| 상황 | 동작 |
|------|------|
| 잠금 화면 (로그인 유지) | 월 10:30 정기 실행 유지 |
| 잠자기 중 10:30 경과 | 정기 실행 **스킵** |
| 깨운 뒤 / 재로그인 | catch-up이 “이번 주 아직 안 돌았으면” **보완 실행** |

---

## 9. Projects MD 양식 (요약)

```markdown
---
layout: description
project_name: 프로젝트명
period_start: "2024-11-01"
period_end: "2024-12-31"
---

Project Description
한 줄 소개

담당 업무
- bullet

### 프로젝트 상세 내용
**사용 기술 및 솔루션**

### 프로젝트를 통해 얻은 것
```

상세·배운 점 빈 섹션은 Notion 기존 본문 유지 — 의도 없이 비우지 마세요.

---

## 10. 자주 쓰는 명령어

```bash
# git → MD → Notion
./notion/update_detail_on_tag.sh --dry-run
./notion/update_detail_on_tag.sh --rebuild-compressed
./notion/update_detail_on_tag.sh --all --rebuild-compressed

# MD → Notion만
./notion/run_sync.sh

# launchd (§8 참고)
./notion/install_launchd.sh
REMOVE_CRON=1 ./notion/install_launchd.sh          # crontab 잔여 제거 + 재등록
./notion/run_scheduled_update.sh calendar        # 정기와 동일 즉시 실행
./notion/run_scheduled_update.sh load            # catch-up 테스트
launchctl list | grep dorosee.syncbox-notion     # 등록 확인
tail -50 /tmp/notion-update.log                  # 실행 로그
```

---

## 11. 설치 후 체크리스트

```bash
cd notion && . .venv/bin/activate
python3 -c "import frontmatter, requests, yaml; print('deps-ok')"
python3 sync_to_notion.py --discover
test -f git_projects.yaml && echo 'yaml-ok'
cd .. && git log --author="$(git config user.email)" --oneline -n 5
./notion/update_detail_on_tag.sh --dry-run --rebuild-compressed
./notion/install_launchd.sh
launchctl list | grep dorosee.syncbox-notion
./notion/run_scheduled_update.sh calendar
grep -E 'done exit=0|failed exit=' /tmp/notion-update.log | tail -3
cat notion/.launchd_state.json
```

---

## 12. 문제 해결

| 증상 | 처리 |
|------|------|
| `bad interpreter` (`.venv`) | `cd notion && python3 -m venv --clear .venv && pip install -r requirements.txt` |
| `git_projects.yaml 이 없습니다` | `cp git_projects.example.yaml git_projects.yaml` |
| `git 저장소 아님` | yaml `repo` 경로 확인 |
| `브랜치 불일치` | `git checkout` 또는 yaml `branch` 수정 |
| `MD 없음` | `--import` 또는 `if_missing: create` |
| 과거 프로젝트가 안 돌아감 | yaml에 `update: manual` + `--all` 사용, `repo` clone·`period_start/end` 확인 |
| `--all` 해도 1개만 처리됨 | yaml에 과거 항목이 등록됐는지 확인 |
| `update=manual (--all 일 때만)` 로그 | 정상 — 일반 실행에서는 과거 프로젝트 건너뜀 |
| 새 커밋 없음 | `--rebuild-compressed` 또는 `.update_state.json` 삭제 |
| `프로젝트 명` 속성 없음 | Notion title 컬럼명 → `프로젝트 명` |
| `multiple data sources` | data source ID + `NOTION_PROJECTS_PARENT_TYPE=data_source` |
| Notion에 남의 페이지 수정됨 | `.env`·`.sync_state.json` 본인 것인지 확인 |
| 주간 실행이 안 됨 | `launchctl list \| grep dorosee`, `/tmp/notion-update.log` 확인 |
| crontab·launchd 중복 실행 | `crontab -l \| grep notion` 후 `REMOVE_CRON=1 ./notion/install_launchd.sh` |
| 이번 주만 수동 반영 | `./notion/run_scheduled_update.sh calendar` 또는 `update_detail_on_tag.sh` |

---

## 13. 다른 PC로 옮기기

1. `notion/` 복사 (도구 + 본인 `content/` + `.env`)
2. `.git/info/exclude`에 `notion/`
3. `git_projects.yaml` repo 경로 수정
4. `./notion/setup.sh` + venv 재생성 + `install_launchd.sh`

git 자동 갱신은 yaml에 적은 **각 repo가 그 PC에 clone** 되어 있어야 합니다.

---

## 부록: 폴더 구조

```
notion/
├── CAREER_AUTOMATION_GUIDE.md
├── content-template/            ← 배포 시 content/ 로 복사 (로컬 개발용 원본)
├── content/                     (개인 경력 MD — 배포본은 플레이스홀더)
│   ├── Contact.md … Etc.md
│   ├── Projects-양식-참고.md
│   └── Projects/
├── config.example.env
├── git_projects.example.yaml
├── git_projects.yaml            (개인)
├── update_from_git.py
├── sync_to_notion.py
├── .env                         (개인)
└── .venv/
```

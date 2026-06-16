#!/usr/bin/env python3
"""
git 저장소 커밋을 읽어 경력 MD(Projects)를 갱신합니다.

- git_projects.yaml 에 프로젝트·저장소 경로 등록 (과거 프로젝트는 update: manual)
- 대상 브랜치: 각 저장소의 현재 checkout 브랜치 (--all 시 branches 규칙)
- --all --rebuild-compressed 로 update=manual·always 프로젝트 일괄 압축
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import frontmatter

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
STATE_FILE = ROOT / ".update_state.json"
GIT_PROJECTS_FILE = ROOT / "git_projects.yaml"
DEFAULT_BRANCH = "develop-main"
MAX_BULLET_LEN = 160
MAX_DUTY_TOPICS = 12

SKIP_SUBJECT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^merge\b", re.I),
    re.compile(r"comment 추가\s*$", re.I),
    re.compile(r"분석 내용 comment", re.I),
    re.compile(r"^api 임시", re.I),
    re.compile(r"^외부 호출용 api test\s*$", re.I),
    re.compile(r"^chore\(ci\):\s*v[\d.]+\s", re.I),
    re.compile(r"재생성\s*$", re.I),
    re.compile(r"재테스트\s*$", re.I),
]

TOPIC_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"github actions|deploy|배포|bootjar|scp|restart\.sh|workflow", re.I), "CI/CD·자동 배포"),
    (re.compile(r"playwright|매뉴얼|notion|vllm|pptx|figma|automation|release_tag|capture", re.I), "사용자 매뉴얼 자동화"),
    (re.compile(r"redis|캐시|cache|evict|embedtoken|reportcache", re.I), "Report·Embed Redis 캐싱"),
    (re.compile(r"embed|x-embed-token|iframe", re.I), "Embed 외부 연동"),
    (re.compile(r"chart|table_chart|pivot|filter|report", re.I), "리포트·차트 API"),
    (re.compile(r"import|excel|xls|jdbc|alias|mariadb", re.I), "데이터 Import·미리보기"),
    (re.compile(r"spark|stage|job|yarn|apf|sftp", re.I), "Spark·프로젝트 파이프라인"),
    (re.compile(r"security|jwt|oauth|saml", re.I), "인증·보안"),
    (re.compile(r"mybatis|postgresql|docker|gradle", re.I), "백엔드 아키텍처·인프라"),
    (re.compile(r"thymeleaf|jquery|javascript|react|vue|frontend", re.I), "프론트엔드"),
    (re.compile(r"sse|pub/sub|websocket|알림", re.I), "실시간 알림·메시징"),
    (re.compile(r"legacy|upgrade|마이그레이션|migration|고도화", re.I), "레거시 고도화"),
]

TOPIC_DUTY_SUMMARIES: dict[str, str] = {
    "CI/CD·자동 배포": (
        "GitHub Actions BE 자동 배포({branch} push): bootJar 빌드 → SCP 전송 → "
        "syncbox.properties·log4j 설정 동기화 → stop/start/restart 기반 재기동, 배포 결과 Naver Bot 알림"
    ),
    "사용자 매뉴얼 자동화": (
        "FE 기능 문서(MD) 기반 Playwright 화면 캡처·vLLM AI 슬라이드 생성·PPTX 조립 파이프라인 설계 및 구축 "
        "(Figma page-* 템플릿·표지·목차·개정이력·CRUD 배치 캡처, BE·FE 동일 SemVer tag 게이트)"
    ),
    "Report·Embed Redis 캐싱": (
        "ReportCacheService·EmbedTokenService 인터페이스 분리 — syncbox.redis.enabled 로 "
        "Redis/InMemory 구현체 선택, Connection·Published·Draft 리포트 metadata·chart Redis 캐싱(TTL) 및 CRUD evict"
    ),
    "Embed 외부 연동": (
        "외부 Embed iframe columns API X-Embed-Token 인증, Draft auto_refresh 및 Connections 최신 데이터셋 정책 API"
    ),
    "리포트·차트 API": (
        "TABLE_CHART headerGroups·pivotColumn·Numbers 설정 DTO, 차트 필터 BASIC/ADVANCED/RANGE 처리, "
        "필터·데이터셋 오류 i18n 메시지 반환, JwtAuthorizationFilter downstream 예외 전파 수정"
    ),
    "데이터 Import·미리보기": (
        "Excel 2003 XML Spreadsheet(.xls) SAX 파서 기반 미리보기·반입, JDBC Import alias·MariaDB 메타데이터 버그 수정"
    ),
    "Spark·프로젝트 파이프라인": (
        "Spark 3.5 stage-job 매핑 수정, Chart Spark pending 로그 보강, APF/SFTP 운영 이슈 대응"
    ),
    "인증·보안": (
        "JwtAuthorizationFilter downstream 예외 전파 수정 — 비즈니스 오류가 JWT 401로 오인되어 FE 로그아웃되지 않도록 개선"
    ),
    "백엔드 아키텍처·인프라": (
        "Spring Boot + MyBatis + PostgreSQL 레이어드 아키텍처 기반 리포트·라이브러리·프로젝트(APF)·Spark 실행 도메인 API 운영"
    ),
}

TOPIC_ORDER = list(TOPIC_DUTY_SUMMARIES.keys())

# active_topics 에 맞춰 '프로젝트를 통해 얻은 것' 단일 callout 문단 생성 (--- 구분 없음)
LEARNING_SECTIONS: list[tuple[frozenset[str], str]] = [
    (
        frozenset({"CI/CD·자동 배포", "사용자 매뉴얼 자동화"}),
        "{branch} push 기반 GitHub Actions 자동 배포와 FE·BE SemVer tag 연동 매뉴얼 자동화를 구축해, "
        "코드 변경부터 배포·사용자 문서 반영까지 end-to-end 흐름을 연결하는 방법을 익혔습니다.",
    ),
    (
        frozenset({"Report·Embed Redis 캐싱", "Embed 외부 연동", "리포트·차트 API", "인증·보안"}),
        "리포트·Embed 도메인에서 Redis TTL 캐싱·환경별 빈 분리, 외부 Embed 인증, 차트 필터·i18n 오류 응답을 설계·운영했고, "
        "JWT 필터가 비즈니스 예외를 401로 오인하던 운영 장애처럼 증상과 원인이 어긋나는 이슈를 추적·해결하는 경험을 쌓았습니다.",
    ),
    (
        frozenset({"데이터 Import·미리보기", "Spark·프로젝트 파이프라인"}),
        "Excel SAX 스트리밍 Import, JDBC 다중 DB 연동, Spark stage-job 매핑 등 대용량 데이터 수집·가공 파이프라인을 "
        "운영하며 성능·안정성·로그 가시성을 함께 맞추는 법을 배웠습니다.",
    ),
    (
        frozenset({"백엔드 아키텍처·인프라"}),
        "Spring Boot + MyBatis + PostgreSQL 레이어드 구조와 ResultException 기반 i18n 패턴으로 "
        "도메인 API를 일관되게 확장하는 백엔드 설계 역량을 키웠습니다.",
    ),
]

LEARNING_TITLE = "SyncBox 백엔드·플랫폼 개발"


@dataclass
class ProjectGitConfig:
    md_path: Path
    repo_root: Path
    branch: str
    template: str
    since: str
    until: str
    project_name: str
    if_missing: str
    entry: dict[str, Any]


def resolve_repo_path(repo: str) -> Path:
    if repo in (".", ".."):
        return (ROOT / repo).resolve()
    return Path(repo).expanduser().resolve()


def project_state_key(md_path: Path) -> str:
    try:
        return str(md_path.relative_to(ROOT))
    except ValueError:
        return str(md_path)


def load_git_projects_yaml() -> list[dict[str, Any]]:
    if not GIT_PROJECTS_FILE.is_file():
        return []
    if yaml is None:
        raise RuntimeError("PyYAML 필요: pip install pyyaml")
    data = yaml.safe_load(GIT_PROJECTS_FILE.read_text(encoding="utf-8")) or {}
    return list(data.get("projects") or [])


def entry_branches(entry: dict[str, Any]) -> list[str]:
    if entry.get("branches"):
        return [str(b).strip() for b in entry["branches"] if str(b).strip()]
    branch = entry.get("branch")
    return [str(branch).strip()] if branch else []


def entry_update_mode(entry: dict[str, Any]) -> str:
    """always=주간·일반 실행 포함, manual=--all 일 때만, never=git 갱신 안 함."""
    raw = str(entry.get("update") or "always").strip().lower()
    aliases = {
        "active": "always",
        "auto": "always",
        "past": "manual",
        "once": "manual",
        "on_demand": "manual",
        "off": "never",
        "none": "never",
        "never": "never",
    }
    mode = aliases.get(raw, raw)
    if mode not in ("always", "manual", "never"):
        print(
            f"[notion-update] 알 수 없는 update={raw!r} — always 로 처리: {entry.get('md')}",
            file=sys.stderr,
        )
        return "always"
    return mode


def should_include_for_run(entry: dict[str, Any], process_all: bool) -> bool:
    mode = entry_update_mode(entry)
    if mode == "never":
        print(f"[notion-update] 건너뜀 — update=never (git 자동 갱신 제외): {entry.get('md')}")
        return False
    if mode == "manual" and not process_all:
        print(
            f"[notion-update] 건너뜀 — update=manual (--all 일 때만 처리): {entry.get('md')}"
        )
        return False
    return True


def resolve_project_md(entry: dict[str, Any]) -> Path:
    md = entry["md"]
    return ROOT / md if not str(md).startswith("/") else Path(md)


def create_project_md(md_path: Path, entry: dict[str, Any]) -> None:
    name = str(entry.get("project_name") or md_path.stem)
    role = entry.get("role") or ["Back-End Developer"]
    if isinstance(role, str):
        role = [role]
    skills = entry.get("skills") or []
    if isinstance(skills, str):
        skills = [skills]
    affiliation = entry.get("affiliation") or ""
    meta: dict[str, Any] = {
        "notion_section": "project",
        "project_name": name,
        "layout": "description",
        "duties_label": True,
        "affiliation": affiliation,
        "period_start": entry.get("period_start") or "",
        "period_end": entry.get("period_end"),
        "one_liner": entry.get("one_liner") or name,
        "role": role,
        "skills": skills,
        "team_members": entry.get("team_members") or "",
        "project_learnings": "",
    }
    desc = entry.get("description") or meta["one_liner"]
    body = (
        "Project Description\n"
        f"{desc}\n\n"
        "담당 업무\n\n"
        "### 프로젝트 상세 내용\n\n"
        "**사용 기술 및 솔루션**\n\n"
        "### 프로젝트를 통해 얻은 것\n"
    )
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(frontmatter.dumps(frontmatter.Post(body, **meta)), encoding="utf-8")


def resolve_branch_rule(entry: dict[str, Any], repo_root: Path, process_all: bool) -> str | None:
    branches = entry_branches(entry)
    checkout = checkout_branch(repo_root)
    if not branches:
        return checkout if process_all else None
    if process_all:
        return checkout if checkout in branches else branches[0]
    return checkout if checkout in branches else None


def ensure_project_md(entry: dict[str, Any], dry_run: bool) -> Path | None:
    md_path = resolve_project_md(entry)
    if md_path.is_file():
        return md_path
    if_missing = str(entry.get("if_missing") or "skip").lower()
    if if_missing != "create":
        print(
            f"[notion-update] 건너뜀 — MD 없음 (if_missing={if_missing}): {entry['md']}",
            file=sys.stderr,
        )
        return None
    if dry_run:
        print(f"[notion-update] (dry-run) MD 생성 예정: {entry['md']}")
        return md_path
    create_project_md(md_path, entry)
    print(f"[notion-update] MD 생성: {entry['md']}")
    return md_path


def build_project_configs(process_all: bool, dry_run: bool = False) -> list[ProjectGitConfig]:
    entries = load_git_projects_yaml()
    if not entries:
        raise FileNotFoundError(
            "git_projects.yaml 이 없습니다.\n"
            "  cp notion/git_projects.example.yaml notion/git_projects.yaml\n"
            "  브랜치·repo·md 매핑 후 다시 실행하세요."
        )

    configs: list[ProjectGitConfig] = []
    for entry in entries:
        if not should_include_for_run(entry, process_all):
            continue

        repo_root = resolve_repo_path(str(entry.get("repo", "..")))
        if not (repo_root / ".git").is_dir():
            print(f"[notion-update] 건너뜀 — git 저장소 아님: {repo_root}", file=sys.stderr)
            continue

        log_branch = resolve_branch_rule(entry, repo_root, process_all)
        if not log_branch:
            branches = entry_branches(entry)
            checkout = checkout_branch(repo_root)
            print(
                f"[notion-update] 건너뜀 — 브랜치 불일치 "
                f"(checkout={checkout}, 규칙={branches or '없음'}): {entry.get('md')}"
            )
            continue

        md_path = ensure_project_md(entry, dry_run)
        if md_path is None:
            continue
        if md_path.is_file():
            meta = frontmatter.load(md_path).metadata
            project_name = str(meta.get("project_name") or md_path.stem)
            since = str(entry.get("since") or meta.get("period_start") or "").strip()
            until = str(entry.get("until") or meta.get("period_end") or "").strip()
        else:
            project_name = str(entry.get("project_name") or md_path.stem)
            since = str(entry.get("since") or entry.get("period_start") or "").strip()
            until = str(entry.get("until") or entry.get("period_end") or "").strip()

        configs.append(
            ProjectGitConfig(
                md_path=md_path,
                repo_root=repo_root,
                branch=log_branch,
                template=str(entry.get("template") or "generic").lower(),
                since=since,
                until=until,
                project_name=project_name,
                if_missing=str(entry.get("if_missing") or "skip").lower(),
                entry=entry,
            )
        )
    return configs


def git_until_exclusive(period_end: str) -> str:
    if not period_end:
        return ""
    try:
        end = datetime.strptime(str(period_end)[:10], "%Y-%m-%d")
        return (end + timedelta(days=1)).strftime("%Y-%m-%d")
    except ValueError:
        return str(period_end)


def get_project_state(state: dict, key: str) -> dict:
    projects = state.get("projects")
    if isinstance(projects, dict) and key in projects:
        return projects[key]
    if key.endswith("SyncBox.md") and "last_processed_commit" in state and not projects:
        return state
    return {}


def set_project_state(state: dict, key: str, proj_state: dict) -> dict:
    if "projects" not in state or not isinstance(state.get("projects"), dict):
        state = {"projects": {}}
    state["projects"][key] = proj_state
    return state


def run_git(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        ["git", "-C", str(cwd or REPO_ROOT), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git failed: {' '.join(args)}")
    return result.stdout.strip()


def load_env() -> None:
    env_file = ROOT / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def git_author(repo_root: Path | None = None) -> str:
    email = os.environ.get("NOTION_GIT_AUTHOR_EMAIL", "").strip()
    name = os.environ.get("NOTION_GIT_AUTHOR_NAME", "").strip()
    if email:
        return email
    if name:
        return name
    cwd = repo_root or REPO_ROOT
    try:
        return run_git("config", "user.email", cwd=cwd)
    except RuntimeError:
        return run_git("config", "user.name", cwd=cwd)


def normalize_text(text: str) -> str:
    text = re.sub(r"[^\w\s가-힣]", " ", text.lower())
    return " ".join(text.split())


def similar(a: str, b: str, threshold: float = 0.58) -> bool:
    if not a.strip() or not b.strip():
        return False
    na, nb = normalize_text(a), normalize_text(b)
    if na in nb or nb in na:
        return True
    return SequenceMatcher(None, na, nb).ratio() >= threshold


def topic_for_text(text: str) -> str:
    for pattern, title in TOPIC_RULES:
        if pattern.search(text):
            return title
    return "백엔드 아키텍처·인프라"


def latest_semver_tag(repo_root: Path) -> str:
    try:
        run_git("fetch", "--tags", "--quiet", cwd=repo_root)
    except RuntimeError:
        pass
    tags = run_git("tag", "--list", "v*", "--sort=-v:refname", cwd=repo_root)
    for tag in tags.splitlines():
        tag = tag.strip()
        if re.fullmatch(r"v\d+\.\d+\.\d+", tag):
            return tag
    return ""


def read_state() -> dict:
    if STATE_FILE.is_file():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def write_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def truncate(text: str, limit: int = MAX_BULLET_LEN) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def should_include_commit(subject: str) -> bool:
    first_line = subject.splitlines()[0].strip()
    if not first_line:
        return False
    if any(pattern.search(first_line) for pattern in SKIP_SUBJECT_PATTERNS):
        return False
    if re.match(r"^(feat|fix|refactor|perf)\(", first_line, re.I):
        return True
    if "분석" in first_line or "주석 내용 수정" in first_line:
        return False
    if re.search(r"(개발|구현|도입|연동|자동화|배포|캐싱|캐시|버그|오류)", first_line):
        return True
    return False


def parse_conventional_commit(subject: str) -> str:
    first_line = subject.splitlines()[0].strip()
    match = re.match(r"^(?:feat|fix|refactor|chore|docs|perf|test)\(([^)]+)\):\s*(.+)$", first_line)
    if match:
        return truncate(match.group(2).strip())
    return truncate(first_line)


def list_commits(
    last_commit: str,
    author: str,
    branch: str,
    repo_root: Path,
    full: bool = False,
    since: str = "",
    until: str = "",
) -> list[dict]:
    args = ["log", f"--author={author}", "--pretty=format:---%n%H%n%s", "--name-only"]
    if since:
        args.append(f"--since={since}")
    until_ex = git_until_exclusive(until) if until else ""
    if until_ex:
        args.append(f"--until={until_ex}")
    if full or not last_commit:
        args.append(branch)
    else:
        args.append(f"{last_commit}..{branch}")
    raw = run_git(*args, cwd=repo_root)
    if not raw:
        return []

    commits: list[dict] = []
    for chunk in raw.split("---"):
        chunk = chunk.strip()
        if not chunk:
            continue
        lines = [line.strip() for line in chunk.splitlines() if line.strip()]
        if len(lines) < 2:
            continue
        sha, subject = lines[0], lines[1]
        if not should_include_commit(subject):
            continue
        files = lines[2:]
        commits.append({"sha": sha, "subject": subject, "files": files})
    commits.reverse()
    return commits


def group_commits_by_topic(commits: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for item in commits:
        text = item["subject"] + " " + " ".join(item.get("files", []))
        topic = topic_for_text(text)
        groups.setdefault(topic, []).append(item)
    return groups


def compress_duty_bullets(
    commits: list[dict], manual_bullets: list[str] | None = None, branch: str = DEFAULT_BRANCH
) -> list[str]:
    groups = group_commits_by_topic(commits)
    duties: list[str] = []

    for topic in TOPIC_ORDER:
        if topic not in groups:
            continue
        summary = TOPIC_DUTY_SUMMARIES.get(topic)
        if summary:
            duties.append(summary.format(branch=branch))
        else:
            sample = parse_conventional_commit(groups[topic][0]["subject"])
            duties.append(f"{topic}: {sample} 등 {len(groups[topic])}건")

    for topic, items in groups.items():
        if topic in TOPIC_ORDER:
            continue
        sample = parse_conventional_commit(items[0]["subject"])
        duties.append(truncate(f"{topic}: {sample} 등 {len(items)}건"))

    if manual_bullets:
        for bullet in manual_bullets:
            if not any(similar(bullet, duty, 0.72) for duty in duties):
                duties.append(bullet)

    deduped: list[str] = []
    for duty in duties:
        if not any(similar(duty, kept, 0.68) for kept in deduped):
            deduped.append(duty)
    return deduped[:MAX_DUTY_TOPICS]


def compress_duty_bullets_generic(commits: list[dict], manual_bullets: list[str] | None = None) -> list[str]:
    groups = group_commits_by_topic(commits)
    duties: list[str] = []
    for topic, items in sorted(groups.items(), key=lambda item: -len(item[1])):
        sample = parse_conventional_commit(items[0]["subject"])
        if len(items) == 1:
            duties.append(truncate(f"{topic}: {sample}"))
        else:
            duties.append(truncate(f"{topic}: {sample} 외 {len(items) - 1}건"))
    if manual_bullets:
        for bullet in manual_bullets:
            if not any(similar(bullet, duty, 0.72) for duty in duties):
                duties.append(bullet)
    return duties[:MAX_DUTY_TOPICS]


def extract_stack_from_gradle(repo_root: Path, syncbox: bool) -> list[str] | None:
    gradle_path = repo_root / "build.gradle"
    if not gradle_path.is_file():
        return None
    gradle = gradle_path.read_text(encoding="utf-8")
    tag = latest_semver_tag(repo_root)
    tag_note = f" (릴리스 tag {tag})" if tag else ""
    spring = re.search(r"id\s+'org\.springframework\.boot'\s+version\s+'([^']+)'", gradle)
    spring_ver = spring.group(1) if spring else "2.7.x"
    java_ver = "11"
    toolchain = re.search(r"jvmToolchain\((\d+)\)", gradle)
    if toolchain:
        java_ver = toolchain.group(1)
    lines = [
        f"- 언어: Java {java_ver}{tag_note}",
        "- 프레임워크: Spring Boot, Spring Security, MyBatis",
        f"- Spring Boot {spring_ver} + MyBatis + PostgreSQL 레이어드 아키텍처",
    ]
    if syncbox:
        spark = re.search(r"spark-core_2\.12',\s+version:\s+'([^']+)'", gradle)
        spark_ver = spark.group(1) if spark else "3.5.x"
        redis_enabled = "false"
        props_dir = repo_root / "src/main/resources"
        if props_dir.is_dir():
            for props in props_dir.glob("application*.properties"):
                text = props.read_text(encoding="utf-8", errors="ignore")
                match = re.search(r"syncbox\.redis\.enabled\s*=\s*(\w+)", text)
                if match:
                    redis_enabled = match.group(1)
                    break
        lines[1:1] = [f"- 서버/인프라: Docker, PostgreSQL, Redis, Apache Spark {spark_ver}, Hadoop(HDFS)"]
        lines.append("- CI/자동화: GitHub Actions, Python, Playwright, Notion API")
        lines.append(
            f"- Redis: syncbox.redis.enabled={redis_enabled} — "
            "true 시 Report·Embed 토큰 Redis, false 시 인메모리 구현체 선택"
        )
    return lines


def extract_stack_lines(repo_root: Path, template: str, fallback: list[str]) -> list[str]:
    syncbox = template == "syncbox"
    from_gradle = extract_stack_from_gradle(repo_root, syncbox)
    if from_gradle:
        return from_gradle
    if fallback:
        return [line if line.startswith("- ") else f"- {line}" for line in fallback]
    return ["- (git 저장소에서 스택 정보를 찾지 못함 — 상세 수동 항목 유지)"]


def duties_to_learnings(
    _duties: list[str], active_topics: set[str], branch: str = DEFAULT_BRANCH, project_name: str = ""
) -> list[str]:
    sentences: list[str] = []
    for topics, template in LEARNING_SECTIONS:
        if topics & active_topics:
            sentences.append(template.format(branch=branch))
    if not sentences:
        return []
    title = project_name or LEARNING_TITLE
    return [f"**{title}**", " ".join(sentences)]


def generic_learnings(project_name: str, groups: dict[str, list[dict]]) -> list[str]:
    if not groups:
        return []
    top = sorted(groups.items(), key=lambda item: -len(item[1]))[:4]
    parts = [f"{topic}({len(items)}건)" for topic, items in top]
    body = (
        f"{project_name} 기간 동안 {', '.join(parts)} 영역에서 개발·개선·운영 이슈 대응을 수행했습니다. "
        "구체적 성과와 기술 스택은 담당 업무·상세 내용을 참고하세요."
    )
    return [f"**{project_name}**", body]


def get_auto_block(content: str, name: str) -> str | None:
    pattern = re.compile(
        rf"<!-- AUTO:{re.escape(name)} -->\s*(.*?)\s*<!-- /AUTO:{re.escape(name)} -->",
        re.S,
    )
    match = pattern.search(content)
    return match.group(1).strip() if match else None


def set_auto_block(content: str, name: str, body: str, insert_after: str | None = None) -> str:
    start = f"<!-- AUTO:{name} -->"
    end = f"<!-- /AUTO:{name} -->"
    block = f"{start}\n{body.rstrip()}\n{end}"
    pattern = re.compile(rf"{re.escape(start)}[\s\S]*?{re.escape(end)}")
    if pattern.search(content):
        return pattern.sub(block, content, count=1)
    if insert_after and insert_after in content:
        return content.replace(insert_after, f"{insert_after}\n\n{block}", 1)
    return content.rstrip() + "\n\n" + block + "\n"


def ensure_auto_markers(body: str) -> str:
    if "<!-- AUTO:stack -->" in body:
        return body

    lines = body.splitlines()
    out: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        out.append(line)
        if line.strip() == "**사용 기술 및 솔루션**":
            index += 1
            stack_lines = []
            while index < len(lines):
                candidate = lines[index]
                if candidate.strip().startswith("- "):
                    stack_lines.append(candidate)
                    index += 1
                    continue
                break
            stack_body = "\n".join(stack_lines) if stack_lines else "- (스택 정보 자동 갱신)"
            out.append("<!-- AUTO:stack -->")
            out.extend(stack_body.splitlines())
            out.append("<!-- /AUTO:stack -->")
            continue
        if line.strip().startswith("### 프로젝트를 통해 얻은 것"):
            index += 1
            rest = lines[index:]
            learning_lines = []
            for rest_line in rest:
                if rest_line.strip().startswith("### "):
                    break
                learning_lines.append(rest_line)
            if learning_lines and "<!-- AUTO:learnings -->" not in "\n".join(learning_lines):
                out.append("<!-- AUTO:learnings -->")
                out.extend(learning_lines)
                out.append("<!-- /AUTO:learnings -->")
                index += len(learning_lines)
                continue
        index += 1

    return "\n".join(out)


def rebuild_body(
    layout: str,
    intro: list[str],
    bullets: list[str],
    detail_manual: list[str],
    stack_lines: list[str],
    learning_lines: list[str],
) -> str:
    parts: list[str] = []
    if layout == "description":
        parts.append("Project Description")
    parts.extend(intro)
    parts.append("")
    parts.append("담당 업무")
    parts.extend(f"- {bullet.lstrip('- ').strip()}" for bullet in bullets if bullet.strip())
    parts.append("")
    parts.append("### 프로젝트 상세 내용")
    parts.append("")
    parts.append("**사용 기술 및 솔루션**")
    parts.append("<!-- AUTO:stack -->")
    parts.extend(stack_lines)
    parts.append("<!-- /AUTO:stack -->")
    for line in detail_manual:
        if line.strip():
            parts.append(line.rstrip())
    parts.append("")
    parts.append("### 프로젝트를 통해 얻은 것")
    parts.append("")
    parts.append("<!-- AUTO:learnings -->")
    parts.extend(learning_lines)
    parts.append("<!-- /AUTO:learnings -->")
    return "\n".join(parts).rstrip() + "\n"


def parse_sections_from_body(body: str) -> tuple[str, list[str], list[str], list[str], list[str]]:
    layout = "description"
    intro: list[str] = []
    bullets: list[str] = []
    detail: list[str] = []
    learnings: list[str] = []
    section = "intro"
    in_auto_stack = False
    in_auto_learnings = False

    for line in body.splitlines():
        stripped = line.strip()
        if stripped == "<!-- AUTO:stack -->":
            in_auto_stack = True
            continue
        if stripped == "<!-- /AUTO:stack -->":
            in_auto_stack = False
            continue
        if stripped == "<!-- AUTO:learnings -->":
            in_auto_learnings = True
            continue
        if stripped == "<!-- /AUTO:learnings -->":
            in_auto_learnings = False
            continue
        if stripped.startswith("<!-- AUTO:") or stripped.startswith("<!-- /AUTO:"):
            continue
        if not stripped and section not in ("detail", "learnings"):
            continue
        if stripped == "Project Description":
            layout = "description"
            continue
        if stripped in ("담당 업무", "## 담당 업무"):
            section = "bullets"
            continue
        if stripped.startswith("### 프로젝트 상세 내용"):
            section = "detail"
            continue
        if stripped.startswith("### 프로젝트를 통해 얻은 것"):
            section = "learnings"
            continue
        if stripped.startswith("### ") or stripped.startswith("## "):
            continue
        if in_auto_stack or in_auto_learnings:
            continue
        if line.lstrip().startswith("- "):
            text = line.lstrip()[2:].strip()
            if section == "detail":
                detail.append(line.rstrip())
            elif section == "learnings":
                learnings.append(line.rstrip())
            else:
                bullets.append(text)
        elif section == "intro":
            intro.append(stripped)
        elif section == "detail":
            if stripped and not stripped.startswith("**사용 기술"):
                detail.append(line.rstrip())
        elif section == "learnings":
            learnings.append(line.rstrip())

    return layout, intro, bullets, detail, learnings


def manual_detail_lines(detail_lines: list[str]) -> list[str]:
    manual: list[str] = []
    for line in detail_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("<!--") or stripped.startswith("- "):
            continue
        if stripped == "**사용 기술 및 솔루션**":
            continue
        manual.append(line)
    return manual


def checkout_branch(repo_root: Path) -> str:
    try:
        branch = run_git("branch", "--show-current", cwd=repo_root)
        if branch:
            return branch
    except RuntimeError:
        pass
    return "HEAD"


def existing_stack_fallback(detail_lines: list[str]) -> list[str]:
    stack: list[str] = []
    in_stack = False
    for line in detail_lines:
        stripped = line.strip()
        if stripped == "**사용 기술 및 솔루션**":
            in_stack = True
            continue
        if stripped.startswith("<!--"):
            continue
        if in_stack and stripped.startswith("- "):
            stack.append(stripped)
        elif in_stack and stripped and not stripped.startswith("- "):
            break
    return stack


def update_one_project(
    config: ProjectGitConfig,
    state: dict,
    author: str,
    rebuild: bool,
    dry_run: bool,
) -> tuple[dict, bool]:
    key = project_state_key(config.md_path)
    proj_state = get_project_state(state, key)
    branch = config.branch
    head = run_git("rev-parse", branch, cwd=config.repo_root)
    tag = latest_semver_tag(config.repo_root)

    if not proj_state and not rebuild:
        state = set_project_state(
            state,
            key,
            {
                "branch": branch,
                "last_processed_commit": head,
                "last_tag": tag,
                "author": author,
                "initialized_at": run_git("log", "-1", "--format=%ci", cwd=config.repo_root),
            },
        )
        print(f"[notion-update] 최초 실행 — {config.project_name} ({branch}, {head[:8]})")
        return state, False

    last_commit = "" if rebuild else proj_state.get("last_processed_commit", "")
    if not rebuild and proj_state.get("branch") and proj_state.get("branch") != branch:
        print(f"[notion-update] {config.project_name}: 브랜치 변경 → incremental 초기화")
        last_commit = ""

    commits = list_commits(
        last_commit, author, branch, config.repo_root, full=rebuild,
        since=config.since, until=config.until,
    )
    tag_changed = tag and tag != proj_state.get("last_tag", "")

    if not commits and not tag_changed and not rebuild:
        print(f"[notion-update] {config.project_name}: 새 커밋 없음 ({branch}, {head[:8]})")
        return state, False

    if config.md_path.is_file():
        post = frontmatter.load(config.md_path)
        body = ensure_auto_markers(post.content)
        layout, intro, existing_bullets, detail_lines, _ = parse_sections_from_body(body)
    else:
        post = None
        layout = "description"
        intro = [str(config.entry.get("description") or config.project_name)]
        existing_bullets, detail_lines = [], []
    detail_manual = manual_detail_lines(detail_lines)
    stack_fallback = existing_stack_fallback(detail_lines)

    manual_keep = [] if rebuild else existing_bullets
    all_commits = list_commits(
        "", author, branch, config.repo_root, full=True,
        since=config.since, until=config.until,
    )
    groups = group_commits_by_topic(all_commits)
    active_topics = set(groups.keys())

    if config.template == "syncbox":
        if not rebuild:
            manual_keep = [
                b for b in existing_bullets
                if not any(
                    similar(b, TOPIC_DUTY_SUMMARIES.get(t, "").format(branch=branch), 0.65)
                    for t in TOPIC_ORDER
                )
            ]
        bullets = compress_duty_bullets(all_commits, manual_keep, branch=branch)
        learning_lines = duties_to_learnings(
            bullets, active_topics, branch=branch, project_name=config.project_name
        )
    else:
        bullets = compress_duty_bullets_generic(all_commits, manual_keep if not rebuild else [])
        learning_lines = generic_learnings(config.project_name, groups)

    stack_lines = extract_stack_lines(config.repo_root, config.template, stack_fallback)
    new_body = rebuild_body(layout, intro, bullets, detail_manual, stack_lines, learning_lines)

    period = ""
    if config.since or config.until:
        period = f", 기간={config.since or '…'}~{config.until or '…'}"
    print(
        f"[notion-update] {config.project_name}: commits={len(all_commits)}, "
        f"duties={len(bullets)}, repo={config.repo_root.name}{period}"
    )

    if dry_run:
        return state, True

    if post is None:
        create_project_md(config.md_path, config.entry)
        post = frontmatter.load(config.md_path)
    post.content = new_body
    config.md_path.write_text(frontmatter.dumps(post), encoding="utf-8")
    state = set_project_state(
        state,
        key,
        {
            "branch": branch,
            "last_processed_commit": head,
            "last_tag": tag,
            "author": author,
            "updated_at": run_git("log", "-1", "--format=%ci", cwd=config.repo_root),
        },
    )
    print(f"[notion-update] {config.project_name}: MD 저장 완료")
    return state, True


def main() -> int:
    parser = argparse.ArgumentParser(description="git 커밋 기반 경력 MD 갱신 (프로젝트별·주제별 압축)")
    parser.add_argument(
        "--rebuild-compressed",
        action="store_true",
        help="상태 무시, 본인 커밋 전체를 주제별로 압축해 MD 재구성",
    )
    parser.add_argument("--backfill", action="store_true", help="--rebuild-compressed 와 동일 (하위 호환)")
    parser.add_argument(
        "--all",
        action="store_true",
        help="브랜치 매칭 무시, git_projects.yaml 전체 항목 처리 (update=manual 포함)",
    )
    parser.add_argument("--dry-run", action="store_true", help="MD·state 저장 없이 변경 요약만 출력")
    parser.add_argument("--no-sync", action="store_true", help="갱신 후 Notion 동기화 생략")
    args = parser.parse_args()

    rebuild = args.rebuild_compressed or args.backfill
    load_env()

    try:
        configs = build_project_configs(process_all=args.all, dry_run=args.dry_run)
    except FileNotFoundError as exc:
        print(f"[notion-update] {exc}", file=sys.stderr)
        return 1
    if not configs:
        print("[notion-update] 처리할 프로젝트가 없습니다. git_projects.yaml 을 확인하세요.", file=sys.stderr)
        return 1

    state = read_state()
    updated = 0
    for config in configs:
        author = git_author(config.repo_root)
        try:
            state, changed = update_one_project(config, state, author, rebuild, args.dry_run)
            if changed:
                updated += 1
        except Exception as exc:
            print(f"[notion-update] {config.project_name} 오류: {exc}", file=sys.stderr)

    if not args.dry_run:
        write_state(state)

    if updated == 0:
        print(f"[notion-update] 변경 없음 (대상 {len(configs)}개 프로젝트)")
        return 0

    print(f"[notion-update] 완료 — {updated}/{len(configs)}개 프로젝트 갱신")

    if args.no_sync or not os.environ.get("NOTION_TOKEN"):
        if not os.environ.get("NOTION_TOKEN"):
            print("[notion-update] NOTION_TOKEN 없음 — Notion 동기화 생략")
        return 0

    sync_script = ROOT / "run_sync.sh"
    if sync_script.is_file():
        subprocess.run([str(sync_script)], cwd=str(ROOT), check=False)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"[notion-update] 오류: {exc}", file=sys.stderr)
        sys.exit(1)

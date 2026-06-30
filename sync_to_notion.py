#!/usr/bin/env python3
"""노션 경력기술서 MD → Notion 동기화."""
from __future__ import annotations

import argparse
from typing import Optional
import json
import os
import sys
import time
from pathlib import Path

import frontmatter
import requests

ROOT = Path(__file__).resolve().parent
CONTENT_DIR = ROOT / "content"
STATE_FILE = ROOT / ".sync_state.json"
NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
NOTION_VERSION_VIEWS = "2025-09-03"

SECTION_ORDER = [
    "contact",
    "channel",
    "introduce",
    "project",
    "skills",
    "education",
    "certifications",
    "etc",
]


def load_env(required: bool = True) -> bool:
    env_path = ROOT / ".env"
    if not env_path.exists():
        if required:
            print("오류: notion/.env 가 없습니다. config.example.env 를 복사하세요.", file=sys.stderr)
            sys.exit(1)
        return False
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())
    return True


def headers():
    return {
        "Authorization": f"Bearer {os.environ['NOTION_TOKEN']}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


# 일시적 네트워크 지연(ReadTimeout)·429·5xx에 한 번의 실패로 동기화가 깨지지 않도록 재시도한다.
NOTION_TIMEOUT = 120
NOTION_MAX_RETRIES = 3
NOTION_RETRY_BACKOFF = 2  # 초 (지수 백오프 기준)


def _notion_request(method, path, request_headers, **kwargs):
    last_error = None
    for attempt in range(1, NOTION_MAX_RETRIES + 1):
        try:
            response = requests.request(
                method, f"{NOTION_API}{path}", headers=request_headers, timeout=NOTION_TIMEOUT, **kwargs
            )
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            last_error = exc
            if attempt < NOTION_MAX_RETRIES:
                wait = NOTION_RETRY_BACKOFF * (2 ** (attempt - 1))
                print(f"[notion] {method} {path} 네트워크 오류({exc.__class__.__name__}) — {wait}s 후 재시도 {attempt}/{NOTION_MAX_RETRIES - 1}")
                time.sleep(wait)
                continue
            raise
        # 429(rate limit)/5xx는 재시도
        if response.status_code == 429 or response.status_code >= 500:
            if attempt < NOTION_MAX_RETRIES:
                retry_after = response.headers.get("Retry-After")
                wait = float(retry_after) if retry_after else NOTION_RETRY_BACKOFF * (2 ** (attempt - 1))
                print(f"[notion] {method} {path} → {response.status_code} — {wait}s 후 재시도 {attempt}/{NOTION_MAX_RETRIES - 1}")
                time.sleep(wait)
                continue
        if not response.ok:
            raise RuntimeError(f"Notion API {method} {path} → {response.status_code}: {response.text}")
        return response.json() if response.text else {}
    raise last_error if last_error else RuntimeError(f"Notion API {method} {path} 재시도 실패")


def notion_request(method, path, **kwargs):
    return _notion_request(method, path, headers(), **kwargs)


def notion_request_version(method, path, version: str, **kwargs):
    request_headers = headers()
    request_headers["Notion-Version"] = version
    return _notion_request(method, path, request_headers, **kwargs)


def format_uuid(page_id: str) -> str:
    raw = page_id.replace("-", "")
    if len(raw) != 32:
        return page_id
    return f"{raw[:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:]}"


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def rich_text(text: str):
    if not text:
        return []
    return [{"type": "text", "text": {"content": text[:2000]}}]


def paragraph_block(text: str):
    return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": rich_text(text)}}


def bullet_block(text: str):
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": rich_text(text)},
    }


def heading1_block(text: str):
    return {"object": "block", "type": "heading_1", "heading_1": {"rich_text": rich_text(text)}}


def heading3_block(text: str, children: Optional[list] = None):
    block = {"object": "block", "type": "heading_3", "heading_3": {"rich_text": rich_text(text)}}
    if children:
        block["children"] = children
    return block


def colored_paragraph_block(text: str, color: str):
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{
                "type": "text",
                "text": {"content": text[:2000]},
                "annotations": {"color": color},
            }],
        },
    }


def blue_paragraph_block(text: str):
    return colored_paragraph_block(text, "blue")


def callout_block_titled(title: str, children: list, color: str = "default", icon_name: Optional[str] = "wrench"):
    callout = {
        "rich_text": [{
            "type": "text",
            "text": {"content": title[:2000]},
            "annotations": {"bold": True},
        }] if title else [],
        "color": color,
    }
    if icon_name == "wrench":
        callout["icon"] = {"type": "icon", "icon": {"name": "wrench", "color": "gray"}}
    elif icon_name == "bulb":
        callout["icon"] = {"type": "emoji", "emoji": "💡"}
    block = {"object": "block", "type": "callout", "callout": callout}
    if children:
        block["children"] = children
    return block


def callout_to_md_lines(block: dict) -> list[str]:
    callout = block.get("callout", {})
    title = "".join(item.get("plain_text", "") for item in callout.get("rich_text", []))
    lines = []
    if title:
        title_lines = title.split("\n")
        if len(title_lines) == 1:
            lines.append(f"**{title}**")
        else:
            lines.append(f"**{title_lines[0]}")
            lines.extend(title_lines[1:-1])
            lines.append(f"{title_lines[-1]}**")
    if block.get("has_children"):
        lines.extend(blocks_tree_to_md_lines(list_child_blocks(block["id"])))
    return lines


def split_callout_title(lines: list[str], default_title: str = "사용 기술 및 솔루션") -> tuple[str, list[str]]:
    body = list(lines)
    title = default_title
    if not body:
        return title, body
    first = body[0].strip()
    if not first.startswith("**"):
        return title, body
    if first.endswith("**") and first.count("**") == 2:
        return first[2:-2].strip(), body[1:]
    collected = []
    index = 0
    while index < len(body):
        collected.append(body[index])
        if body[index].strip().endswith("**"):
            index += 1
            break
        index += 1
    raw = "\n".join(collected).strip()
    if raw.startswith("**"):
        raw = raw[2:]
    if raw.endswith("**"):
        raw = raw[:-2]
    return raw.strip(), body[index:]


def md_lines_to_detail_callout(lines: list[str]):
    title, body = split_callout_title(lines, "사용 기술 및 솔루션")
    content = md_lines_to_mixed_blocks(body)
    if not content:
        return None
    return callout_block_titled(title, content, "default", "wrench")


def paragraph_annotation_color(block: dict) -> str:
    if block.get("type") != "paragraph":
        return ""
    rich_text_items = block.get("paragraph", {}).get("rich_text", [])
    if not rich_text_items:
        return ""
    return rich_text_items[0].get("annotations", {}).get("color", "default")


def blocks_tree_to_md_lines(blocks: list, depth: int = 0) -> list[str]:
    lines = []
    indent = "  " * depth
    for block in blocks:
        block_type = block.get("type")
        text = block_plain_text(block)
        if block_type == "bulleted_list_item" and text:
            lines.append(f"{indent}- {text}")
            if block.get("has_children"):
                lines.extend(blocks_tree_to_md_lines(list_child_blocks(block["id"]), depth + 1))
        elif block_type == "paragraph" and text:
            lines.append(text)
        elif block_type == "callout" and block.get("has_children"):
            lines.extend(blocks_tree_to_md_lines(list_child_blocks(block["id"]), depth))
    return lines


def heading_children_to_md_lines(block: dict, split_callouts: bool = False) -> list[str]:
    if not block.get("has_children"):
        return []
    lines = []
    for child in list_child_blocks(block["id"]):
        if child.get("type") == "callout":
            if split_callouts and lines:
                lines.append("---")
            lines.extend(callout_to_md_lines(child))
        else:
            lines.extend(blocks_tree_to_md_lines([child]))
    return lines


def md_lines_to_bullet_blocks(lines: list[str]) -> list:
    roots = []
    stack = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped == "---" or not line.lstrip().startswith("- "):
            continue
        indent = len(line) - len(line.lstrip())
        text = line.lstrip()[2:].strip()
        node = bullet_block(text)
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if stack:
            parent = stack[-1][1]
            parent.setdefault("children", []).append(node)
        else:
            roots.append(node)
        stack.append((indent, node))
    return roots


def md_lines_to_mixed_blocks(lines: list[str]) -> list:
    blocks = []
    bullet_buffer = []

    def flush_bullets():
        nonlocal bullet_buffer
        if bullet_buffer:
            blocks.extend(md_lines_to_bullet_blocks(bullet_buffer))
            bullet_buffer = []

    for line in lines:
        if line.strip() == "---":
            flush_bullets()
            continue
        if not line.strip() or line.strip().startswith("<!--"):
            continue
        if line.lstrip().startswith("- "):
            bullet_buffer.append(line.rstrip())
        else:
            flush_bullets()
            blocks.append(paragraph_block(line.strip()))
    flush_bullets()
    return blocks


def is_md_callout_title_line(line: str) -> bool:
    """한 줄 또는 여러 줄 callout 제목의 첫 줄 (**로 시작)."""
    stripped = line.strip()
    return bool(stripped.startswith("**"))


def md_lines_to_learning_callouts(lines: list[str]) -> list:
    groups = []
    current = []
    for line in lines:
        stripped = line.strip()
        if stripped == "---":
            if current:
                groups.append(current)
                current = []
            continue
        if stripped and is_md_callout_title_line(stripped) and current:
            groups.append(current)
            current = [line.rstrip()]
            continue
        if stripped:
            current.append(line.rstrip())
    if current:
        groups.append(current)

    callouts = []
    for group in groups:
        title, body = split_callout_title(group, "")
        content = md_lines_to_mixed_blocks(body)
        if title or content:
            callouts.append(callout_block_titled(title, content, "gray_background", "bulb"))
    return callouts


def section_lines_to_md(lines: list[str]) -> list[str]:
    md_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("<!--"):
            continue
        md_lines.append(line.rstrip() if line.lstrip().startswith("- ") else stripped)
    return md_lines


def section_siblings_to_md_lines(
    blocks: list,
    start_index: int,
    stop_headings: set,
    split_callouts: bool = False,
) -> tuple[list[str], int]:
    lines = []
    index = start_index
    while index < len(blocks):
        block = blocks[index]
        block_type = block.get("type")
        text = block_plain_text(block)
        if block_type == "heading_3" and text in stop_headings:
            break
        if block_type == "heading_3":
            break
        if block_type == "callout":
            if split_callouts and lines:
                lines.append("---")
            lines.extend(callout_to_md_lines(block))
        elif block_type in ("paragraph", "bulleted_list_item"):
            lines.extend(blocks_tree_to_md_lines([block]))
        index += 1
    return lines, index


def extract_project_sections_from_notion(page_id: str) -> dict:
    blocks = list_child_blocks(page_id)
    detail = []
    learnings = []

    for index, block in enumerate(blocks):
        text = block_plain_text(block)
        if block.get("type") == "heading_3" and text == "프로젝트 상세 내용":
            nested = heading_children_to_md_lines(block)
            if nested:
                detail = nested
            else:
                detail, _ = section_siblings_to_md_lines(
                    blocks, index + 1, {"프로젝트를 통해 얻은 것"}, split_callouts=False,
                )
        if block.get("type") == "heading_3" and text == "프로젝트를 통해 얻은 것":
            nested = heading_children_to_md_lines(block, split_callouts=True)
            if nested:
                learnings = nested
            else:
                learnings, _ = section_siblings_to_md_lines(blocks, index + 1, set(), split_callouts=True)

    return {"detail": detail, "learnings": learnings}


def column_list_block_nested(left_blocks: list, right_blocks: list):
    return {
        "object": "block",
        "type": "column_list",
        "column_list": {
            "children": [
                {"object": "block", "type": "column", "column": {"children": left_blocks}},
                {"object": "block", "type": "column", "column": {"children": right_blocks or [paragraph_block("")]}},
            ],
        },
    }


def callout_block(text: str):
    return {
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": rich_text(text),
            "icon": {"type": "emoji", "emoji": "📌"},
        },
    }


def list_child_blocks(block_id: str) -> list:
    block_id = format_uuid(block_id)
    blocks = []
    cursor = None
    while True:
        params = {"page_size": 100}
        if cursor:
            params["start_cursor"] = cursor
        data = notion_request("GET", f"/blocks/{block_id}/children", params=params)
        blocks.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return blocks


def delete_blocks(block_ids: list):
    for block_id in block_ids:
        notion_request("DELETE", f"/blocks/{block_id}")


def block_plain_text(block: dict) -> str:
    block_type = block.get("type", "")
    if block_type in ("paragraph", "heading_1", "heading_2", "heading_3", "bulleted_list_item"):
        return "".join(item.get("plain_text", "") for item in block.get(block_type, {}).get("rich_text", []))
    return ""


def append_single_block(parent_id: str, block: dict):
    payload = {key: value for key, value in block.items() if key != "children"}
    children = block.get("children") or []
    created = notion_request(
        "PATCH",
        f"/blocks/{format_uuid(parent_id)}/children",
        json={"children": [payload]},
    )
    block_id = created["results"][0]["id"]
    for child in children:
        append_single_block(block_id, child)


def _append_payload_batch(parent_id: str, payloads: list):
    # Notion children append는 호출당 최대 100개. 요청 수를 줄여 타임아웃 노출을 낮춘다.
    for i in range(0, len(payloads), 100):
        chunk = payloads[i:i + 100]
        notion_request(
            "PATCH",
            f"/blocks/{format_uuid(parent_id)}/children",
            json={"children": chunk},
        )


def append_blocks(parent_id: str, blocks: list):
    # children 없는 블록은 100개씩 배치로, children 있는 블록은 개별(재귀)로 추가한다(순서 보존).
    buffer = []
    for block in blocks:
        if block.get("children"):
            if buffer:
                _append_payload_batch(parent_id, buffer)
                buffer = []
            append_single_block(parent_id, block)
        else:
            buffer.append({key: value for key, value in block.items() if key != "children"})
    if buffer:
        _append_payload_batch(parent_id, buffer)


def replace_child_blocks(parent_id: str, blocks: list):
    # 새 블록이 비정상적으로 비어 있으면 기존 페이지 내용을 보호하기 위해 아무것도 하지 않는다.
    if not blocks:
        print(f"[notion] replace_child_blocks skip — 새 블록이 비어 있어 기존 내용 보존: {parent_id}")
        return

    existing = list_child_blocks(parent_id)

    # append-후-delete 순서: 새 블록을 먼저 추가하고 성공하면 기존 블록을 삭제한다.
    # 이렇게 하면 추가 중 실패(예: Notion API 타임아웃)해도 기존 내용이 사라지지 않는다.
    # (실패 시 최악의 경우 기존+신규가 잠시 공존할 수 있으나 데이터 유실은 없음)
    append_blocks(parent_id, blocks)
    delete_blocks([block["id"] for block in existing])


def discover_databases():
    page_id = resume_page_id()
    print(f"루트 페이지 하위 DB 조회: {page_id}\n")
    for block in list_child_blocks(page_id):
        if block.get("type") == "child_database":
            title = block.get("child_database", {}).get("title", "")
            print(f"  [DB] {title or '(제목 없음)'}")
            print(f"       id: {block['id']}\n")


def resume_page_id() -> str:
    return format_uuid(os.environ["NOTION_RESUME_PAGE_ID"])


def projects_db_id() -> str:
    return (
        os.environ.get("NOTION_PROJECTS_DB_ID", "").strip()
        or os.environ.get("NOTION_WORK_EXPERIENCE_DB_ID", "").strip()
    )


def parse_project_markdown(content: str, meta: dict):
    layout = (meta.get("layout") or "description").strip()
    intro = []
    bullets = []
    detail = []
    learnings = []
    section = "intro"

    for line in (content or "").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("<!--"):
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
        if stripped == "---" and section in ("detail", "learnings"):
            if section == "detail":
                detail.append("---")
            else:
                learnings.append("---")
            continue
        if line.lstrip().startswith("- "):
            bullet_line = line.rstrip()
            if section == "detail":
                detail.append(bullet_line)
            elif section == "learnings":
                learnings.append(bullet_line)
            else:
                bullets.append(bullet_line.lstrip()[2:].strip())
        elif section == "intro":
            intro.append(stripped)
        elif section == "detail":
            detail.append(stripped)
        elif section == "learnings":
            learnings.append(stripped)

    return layout, intro, bullets, detail, learnings


def build_project_blocks(layout: str, intro: list, bullets: list, detail: list, learnings: list, meta: dict) -> list:
    one_liner = (meta.get("one_liner") or "").strip()
    project_name = (meta.get("project_name") or "").strip()
    blocks = []

    blocks.append(blue_paragraph_block("Project Description"))
    if intro:
        blocks.extend(paragraph_block(paragraph) for paragraph in intro)
    else:
        blocks.append(paragraph_block(one_liner or project_name))
    blocks.append(paragraph_block(""))
    blocks.append(blue_paragraph_block("담당 업무"))
    blocks.extend(bullet_block(bullet) for bullet in bullets)

    detail_callout = md_lines_to_detail_callout(detail)
    learning_callouts = md_lines_to_learning_callouts(learnings)

    blocks.append(heading3_block("프로젝트 상세 내용"))
    if detail_callout:
        blocks.append(detail_callout)
    blocks.append(heading3_block("프로젝트를 통해 얻은 것"))
    blocks.extend(learning_callouts)
    return blocks[:100]


def project_content_to_blocks(content: str, meta: dict) -> list:
    layout, intro, bullets, detail, learnings = parse_project_markdown(content, meta)
    return build_project_blocks(layout, intro, bullets, detail, learnings, meta)


def ensure_project_view_sort():
    db_id = projects_db_id()
    if not db_id:
        return
    views = notion_request_version(
        "GET",
        "/views",
        NOTION_VERSION_VIEWS,
        params={"database_id": format_uuid(db_id)},
    ).get("results", [])
    sorts = [{"property": os.environ.get("NOTION_PROP_PERIOD", "진행 기간"), "direction": "descending"}]
    for view in views:
        notion_request_version(
            "PATCH",
            f"/views/{view['id']}",
            NOTION_VERSION_VIEWS,
            json={"sorts": sorts},
        )
    if views:
        print(f"[notion] Projects 뷰 {len(views)}개 — 진행 기간 내림차순 정렬")


def _affiliation_options(meta: dict) -> list[str]:
    raw = meta.get("affiliation") or meta.get("team") or ""
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    if raw:
        return [str(raw).strip()]
    return []


def build_project_properties(meta: dict):
    project_name = meta.get("project_name") or meta.get("company", "")
    period = meta.get("period_label") or ""
    period_start = meta.get("period_start")
    period_end = meta.get("period_end")
    role = meta.get("role", "")
    if isinstance(role, list):
        roles = [str(item).strip() for item in role if str(item).strip()]
    else:
        roles = [str(role).strip()] if role else []
    team_members = meta.get("team_members")
    team_size = meta.get("team_size")
    affiliations = _affiliation_options(meta)
    one_liner = meta.get("one_liner", "")
    skills = meta.get("skills") or []
    learnings = meta.get("project_learnings") or ""

    title_prop = os.environ.get("NOTION_PROP_PROJECT_NAME") or os.environ.get("NOTION_PROP_COMPANY", "프로젝트 명")
    props = {title_prop: {"title": rich_text(project_name)}}

    period_prop = os.environ.get("NOTION_PROP_PERIOD", "기간")
    if os.environ.get("NOTION_PROP_PERIOD_TYPE") == "date" and period_start:
        date_val = {"start": period_start}
        if period_end:
            date_val["end"] = period_end
        props[period_prop] = {"date": date_val}
    else:
        props[period_prop] = {"rich_text": rich_text(period)}

    role_prop = os.environ.get("NOTION_PROP_ROLE", "역할")
    if os.environ.get("NOTION_PROP_ROLE_TYPE") == "multi_select":
        props[role_prop] = {"multi_select": [{"name": role_name} for role_name in roles]}
    else:
        props[role_prop] = {"rich_text": rich_text(", ".join(roles))}

    team_prop = os.environ.get("NOTION_PROP_TEAM", "Team Members")
    if team_members:
        team_text = str(team_members)
    elif team_size:
        team_text = f"개발자 {team_size}명"
    else:
        team_text = ""
    props[team_prop] = {"rich_text": rich_text(team_text)}

    aff_prop = os.environ.get("NOTION_PROP_AFFILIATION", "소속").strip()
    if aff_prop and affiliations:
        props[aff_prop] = {"multi_select": [{"name": name} for name in affiliations]}

    one_liner_prop = os.environ.get("NOTION_PROP_ONE_LINER", "한줄소개")
    props[one_liner_prop] = {"rich_text": rich_text(one_liner)}

    skills_prop = os.environ.get("NOTION_PROP_SKILLS", "Skills")
    props[skills_prop] = {"multi_select": [{"name": skill} for skill in skills]}

    learnings_prop = os.environ.get("NOTION_PROP_LEARNINGS", "").strip()
    if learnings_prop and learnings:
        props[learnings_prop] = {"rich_text": rich_text(learnings)}

    return props


def find_existing_page(db_id: str, project_name: str):
    title_prop = os.environ.get("NOTION_PROP_PROJECT_NAME") or os.environ.get("NOTION_PROP_COMPANY", "프로젝트 명")
    data = notion_request("POST", f"/databases/{format_uuid(db_id)}/query", json={
        "filter": {"property": title_prop, "title": {"equals": project_name}},
        "sorts": [{"property": os.environ.get("NOTION_PROP_PERIOD", "진행 기간"), "direction": "descending"}],
    })
    results = data.get("results", [])
    return results[0]["id"] if results else None


def sync_project_file(path: Path, state: dict):
    db_id = projects_db_id()
    if not db_id:
        print("경고: NOTION_PROJECTS_DB_ID 미설정 — --discover 로 확인하세요.", file=sys.stderr)
        return

    post = frontmatter.load(path)
    if post.metadata.get("notion_section") != "project":
        return

    project_name = post.metadata.get("project_name") or path.stem
    properties = build_project_properties(post.metadata)
    layout, intro, bullets, detail, learnings = parse_project_markdown(post.content, post.metadata)
    key = f"project:{project_name}"

    page_id = state.get(key) or state.get(f"work:{project_name}") or find_existing_page(db_id, project_name)
    if page_id and (not detail or not learnings):
        preserved = extract_project_sections_from_notion(page_id)
        kept = []
        if not detail and preserved["detail"]:
            detail = preserved["detail"]
            kept.append("상세")
        if not learnings and preserved["learnings"]:
            learnings = preserved["learnings"]
            kept.append("배운 점")
        if kept:
            print(f"[notion] {project_name} — MD 비어 있어 Notion {'·'.join(kept)} 본문 유지")

    body_blocks = build_project_blocks(layout, intro, bullets, detail, learnings, post.metadata)
    if page_id:
        notion_request("PATCH", f"/pages/{format_uuid(page_id)}", json={"properties": properties})
        print(f"[notion] 프로젝트 업데이트 — {project_name}")
    else:
        payload = {
            "parent": {"database_id": format_uuid(db_id)},
            "properties": properties,
        }
        created = notion_request("POST", "/pages", json=payload)
        page_id = created["id"]
        print(f"[notion] 프로젝트 생성 — {project_name}")

    replace_child_blocks(page_id, body_blocks)
    state[key] = page_id


def find_resume_contact_column(state: dict) -> str:
    if state.get("contact_column_id"):
        return state["contact_column_id"]
    for block in list_child_blocks(resume_page_id()):
        if block.get("type") != "column_list":
            continue
        columns = list_child_blocks(block["id"])
        if len(columns) < 2:
            continue
        for column in columns[1:]:
            for child in list_child_blocks(column["id"]):
                if block_plain_text(child) == "Contact.":
                    state["contact_column_id"] = column["id"]
                    return column["id"]
    raise RuntimeError("Contact/Channel 컬럼을 찾지 못했습니다.")


def sync_contact_channel(path: Path, state: dict):
    post = frontmatter.load(path)
    section = post.metadata.get("notion_section")
    if section not in ("contact", "channel"):
        return

    column_id = find_resume_contact_column(state)
    blocks = list_child_blocks(column_id)

    contact_lines = []
    channel_lines = []
    if section == "contact":
        contact_lines = [line.strip() for line in post.content.splitlines() if line.strip()]
        for block in blocks:
            text = block_plain_text(block)
            if text == "Channel.":
                break
            if block.get("type") == "paragraph" and text and text != "Contact.":
                pass
        for block in blocks:
            text = block_plain_text(block)
            if text == "Channel.":
                capture = False
                for next_block in blocks[blocks.index(block) + 1:]:
                    if next_block.get("type") == "heading_3":
                        break
                    line = block_plain_text(next_block)
                    if line:
                        channel_lines.append(line)
    else:
        channel_lines = [line.strip() for line in post.content.splitlines() if line.strip()]
        capture_contact = False
        for block in blocks:
            text = block_plain_text(block)
            if text == "Contact.":
                capture_contact = True
                continue
            if text == "Channel.":
                capture_contact = False
                continue
            if capture_contact and block.get("type") == "paragraph" and text:
                contact_lines.append(text)

    contact_path = CONTENT_DIR / "Contact.md"
    channel_path = CONTENT_DIR / "Channel.md"
    if section == "contact" and channel_path.exists() and not channel_lines:
        channel_post = frontmatter.load(channel_path)
        channel_lines = [line.strip() for line in channel_post.content.splitlines() if line.strip()]
    if section == "channel" and contact_path.exists() and not contact_lines:
        contact_post = frontmatter.load(contact_path)
        contact_lines = [line.strip() for line in contact_post.content.splitlines() if line.strip()]

    new_blocks = [heading3_block("Contact.")]
    new_blocks.extend(paragraph_block(line) for line in contact_lines)
    new_blocks.append(heading3_block("Channel."))
    new_blocks.extend(paragraph_block(line) for line in channel_lines)

    replace_child_blocks(column_id, new_blocks)
    print(f"[notion] {section} 반영")


def sync_contact_and_channel(state: dict):
    contact_path = CONTENT_DIR / "Contact.md"
    channel_path = CONTENT_DIR / "Channel.md"
    if not contact_path.exists() and not channel_path.exists():
        return
    column_id = find_resume_contact_column(state)
    contact_lines = []
    channel_lines = []
    if contact_path.exists():
        contact_lines = [line.strip() for line in frontmatter.load(contact_path).content.splitlines() if line.strip()]
    if channel_path.exists():
        channel_lines = [line.strip() for line in frontmatter.load(channel_path).content.splitlines() if line.strip()]

    new_blocks = [heading3_block("Contact.")]
    new_blocks.extend(paragraph_block(line) for line in contact_lines)
    new_blocks.append(heading3_block("Channel."))
    new_blocks.extend(paragraph_block(line) for line in channel_lines)
    replace_child_blocks(column_id, new_blocks)
    print("[notion] Contact / Channel 반영")


def find_section_range(blocks: list, section_title: str) -> tuple[int, int]:
    start = end = -1
    for index, block in enumerate(blocks):
        if block.get("type") == "heading_1" and block_plain_text(block) == section_title:
            start = index
            continue
        if start >= 0 and block.get("type") == "heading_1":
            end = index
            break
    if start < 0:
        raise RuntimeError(f"섹션을 찾지 못했습니다: {section_title}")
    if end < 0:
        end = len(blocks)
    return start, end


def replace_section_content(resume_id: str, section_title: str, new_blocks: list | None = None, column_rows: list | None = None):
    top_blocks = list_child_blocks(resume_id)
    start, end = find_section_range(top_blocks, section_title)
    insert_after = None
    content_ids = []
    passed_heading = False
    for block in top_blocks[start:end]:
        if block.get("type") == "heading_1":
            passed_heading = True
            continue
        if not passed_heading:
            continue
        if block.get("type") == "divider":
            insert_after = block["id"]
            continue
        content_ids.append(block["id"])
    delete_blocks(content_ids)
    if not insert_after:
        insert_after = top_blocks[start]["id"]
    resume_id = format_uuid(resume_id)

    if new_blocks:
        payload = {"children": new_blocks}
        if insert_after:
            payload["after"] = insert_after
        notion_request("PATCH", f"/blocks/{resume_id}/children", json=payload)

    if column_rows:
        anchor = insert_after
        for left_blocks, right_blocks in column_rows:
            payload = {"children": [column_list_block_nested(left_blocks, right_blocks)]}
            if anchor:
                payload["after"] = anchor
            created = notion_request("PATCH", f"/blocks/{resume_id}/children", json=payload)
            anchor = created["results"][0]["id"]


def sync_introduce(path: Path, state: dict):
    post = frontmatter.load(path)
    if post.metadata.get("notion_section") != "introduce":
        return
    blocks = []
    for line in post.content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("<!--"):
            continue
        if stripped.startswith("- "):
            blocks.append(bullet_block(stripped[2:].strip()))
        else:
            blocks.append(paragraph_block(stripped))
    replace_section_content(resume_page_id(), post.metadata.get("title", "Introduce."), blocks)
    print("[notion] Introduce 반영")


def sync_skills(path: Path, state: dict):
    post = frontmatter.load(path)
    if post.metadata.get("notion_section") != "skills":
        return

    column_rows = []
    current_category = None
    current_items = []

    def flush_category():
        nonlocal current_category, current_items
        if not current_category:
            return
        right_blocks = [bullet_block(item) for item in current_items if item]
        column_rows.append(([paragraph_block(current_category)], right_blocks or [paragraph_block("")]))
        current_category = None
        current_items = []

    for line in post.content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("### "):
            flush_category()
            current_category = stripped[4:].strip()
            continue
        if not current_category:
            continue
        if stripped.startswith("- "):
            current_items.append(stripped[2:].strip())
        else:
            current_items.extend(part.strip() for part in stripped.split(",") if part.strip())

    flush_category()
    replace_section_content(resume_page_id(), post.metadata.get("title", "Skills."), column_rows=column_rows)
    print("[notion] Skills 반영")


def sync_education(path: Path, state: dict):
    post = frontmatter.load(path)
    if post.metadata.get("notion_section") != "education":
        return
    items = post.metadata.get("items") or []
    if not items:
        items = [line.strip() for line in post.content.splitlines() if line.strip() and not line.startswith("#")]
    blocks = [callout_block(item) for item in items if item]
    replace_section_content(resume_page_id(), post.metadata.get("title", "Education."), blocks)
    print("[notion] Education 반영")


def sync_certifications(path: Path, state: dict):
    post = frontmatter.load(path)
    if post.metadata.get("notion_section") != "certifications":
        return
    items = post.metadata.get("items") or []
    column_rows = []
    for item in items:
        if isinstance(item, dict):
            column_rows.append((
                [paragraph_block(str(item.get("date", "")).strip())],
                [paragraph_block(str(item.get("name", "")).strip())],
            ))
    if not column_rows:
        return
    replace_section_content(resume_page_id(), post.metadata.get("title", "Certifications."), column_rows=column_rows)
    print("[notion] Certifications 반영")


def sync_etc(path: Path, state: dict):
    post = frontmatter.load(path)
    if post.metadata.get("notion_section") != "etc":
        return
    items = post.metadata.get("items") or []
    column_rows = []
    for item in items:
        if isinstance(item, dict):
            column_rows.append((
                [paragraph_block(str(item.get("date", "")).strip())],
                [paragraph_block(str(item.get("text", "")).strip())],
            ))
    if not column_rows:
        return
    replace_section_content(resume_page_id(), post.metadata.get("title", "Etc."), column_rows=column_rows)
    print("[notion] Etc 반영")


def import_projects_from_notion():
    db_id = projects_db_id()
    if not db_id:
        print("경고: NOTION_PROJECTS_DB_ID 미설정", file=sys.stderr)
        return

    projects_dir = CONTENT_DIR / "Projects"
    projects_dir.mkdir(parents=True, exist_ok=True)
    state = load_state()

    cursor = None
    pages = []
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        data = notion_request("POST", f"/databases/{format_uuid(db_id)}/query", json=body)
        pages.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")

    for page in pages:
        props = page["properties"]
        project_name = "".join(item.get("plain_text", "") for item in props.get("프로젝트 명", {}).get("title", []))
        if not project_name:
            continue

        blocks = list_child_blocks(page["id"])
        layout = "description"
        intro = []
        bullets = []
        detail = []
        learnings = []
        section = "intro"
        duties_label = True

        for index, block in enumerate(blocks):
            block_type = block.get("type")
            if block_type == "divider":
                continue
            text = block_plain_text(block)
            color = paragraph_annotation_color(block) if block_type == "paragraph" else ""

            if block_type == "paragraph" and color == "blue" and "Project Description" in text:
                layout = "description"
                duties_label = True
                if text.strip() == "Project Description":
                    section = "intro"
                    continue
                parts = text.split("\n", 1)
                if len(parts) == 2 and parts[0].strip() == "Project Description":
                    intro.append(parts[1].strip())
                section = "intro"
                continue
            if block_type == "paragraph" and color in ("blue", "gray_background") and text.strip().startswith("담당 업무"):
                section = "bullets"
                duties_label = True
                continue
            if block_type == "heading_3" and text == "프로젝트 상세 내용":
                nested = heading_children_to_md_lines(block)
                if nested:
                    detail = nested
                else:
                    detail, _ = section_siblings_to_md_lines(
                        blocks, index + 1, {"프로젝트를 통해 얻은 것"}, split_callouts=False,
                    )
                section = None
                continue
            if block_type == "heading_3" and text == "프로젝트를 통해 얻은 것":
                nested = heading_children_to_md_lines(block, split_callouts=True)
                if nested:
                    learnings = nested
                else:
                    learnings, _ = section_siblings_to_md_lines(blocks, index + 1, set(), split_callouts=True)
                section = None
                continue
            if block_type == "heading_3":
                section = None
                continue
            if block_type == "bulleted_list_item":
                if section == "detail":
                    detail.append(f"- {text}")
                elif section == "learnings":
                    learnings.append(f"- {text}")
                else:
                    bullets.append(text)
                continue
            if block_type == "paragraph" and text:
                if section == "bullets":
                    bullets.append(text)
                elif section == "detail":
                    detail.append(text)
                elif section == "learnings":
                    learnings.append(text)
                elif section in ("intro", "header"):
                    intro.append(text)
                continue
            if block_type == "callout" and section in ("detail", "learnings"):
                if section == "learnings" and learnings:
                    learnings.append("---")
                chunk = callout_to_md_lines(block)
                if section == "detail":
                    detail.extend(chunk)
                else:
                    learnings.extend(chunk)

        meta_lines = ["---", "notion_section: project", f'project_name: {project_name}']
        meta_lines.append(f'layout: {layout}')
        meta_lines.append(f'duties_label: {"true" if duties_label else "false"}')

        for key, prop_name, parser in [
            ("affiliation", "소속", lambda value: value),
            ("period_start", "진행 기간", None),
            ("team_members", "Team Members", None),
            ("role", "역할", None),
            ("one_liner", "한 줄 소개", None),
            ("skills", "Skills", None),
        ]:
            prop = props.get(prop_name, {})
            prop_type = prop.get("type")
            if prop_type == "multi_select":
                values = [item["name"] for item in prop.get("multi_select", [])]
                if key == "affiliation" and len(values) == 1:
                    meta_lines.append(f"affiliation: {values[0]}")
                elif values:
                    meta_lines.append(f"{key}:")
                    meta_lines.extend(f"  - {value}" for value in values)
            elif prop_type == "rich_text":
                text = "".join(item.get("plain_text", "") for item in prop.get("rich_text", []))
                if text:
                    meta_lines.append(f'{key}: {text}')
            elif prop_type == "date" and key == "period_start":
                date_value = prop.get("date") or {}
                if date_value.get("start"):
                    meta_lines.append(f'period_start: "{date_value["start"]}"')
                    meta_lines.append(f'period_end: {json.dumps(date_value.get("end"))}')

        meta_lines.append('project_learnings: ""')
        meta_lines.append("---")

        body_lines = ["Project Description"]
        if intro:
            body_lines.extend(intro)
        body_lines.append("")
        body_lines.append("담당 업무")
        body_lines.extend(f"- {bullet}" for bullet in bullets)
        body_lines.append("")
        body_lines.append("### 프로젝트 상세 내용")
        body_lines.append("")
        body_lines.extend(section_lines_to_md(detail))
        body_lines.append("")
        body_lines.append("### 프로젝트를 통해 얻은 것")
        body_lines.append("")
        body_lines.extend(section_lines_to_md(learnings))

        filename = project_name.replace("/", "-").replace("\\", "-")[:180] + ".md"
        (projects_dir / filename).write_text("\n".join(meta_lines) + "\n\n" + "\n".join(body_lines).strip() + "\n", encoding="utf-8")
        state[f"project:{project_name}"] = page["id"]
        print(f"[import] {project_name}")

    save_state(state)
    print("[import] Projects MD 가져오기 완료.")


def sync_all():
    state = load_state()
    ensure_project_view_sort()
    sync_contact_and_channel(state)

    handlers = {
        "introduce": sync_introduce,
        "skills": sync_skills,
        "education": sync_education,
        "certifications": sync_certifications,
        "etc": sync_etc,
    }

    for path in sorted(CONTENT_DIR.rglob("*.md")):
        post = frontmatter.load(path)
        section = post.metadata.get("notion_section")
        if section == "project":
            sync_project_file(path, state)
        elif section in handlers:
            handlers[section](path, state)

    save_state(state)
    print("[notion] 동기화 완료.")


def main():
    parser = argparse.ArgumentParser(description="Notion 경력기술서 동기화")
    parser.add_argument("--discover", action="store_true", help="Projects DB ID 찾기")
    parser.add_argument("--import", dest="import_projects", action="store_true", help="Notion Projects → MD 가져오기")
    args = parser.parse_args()
    load_env()
    if args.discover:
        discover_databases()
        return
    if args.import_projects:
        import_projects_from_notion()
        return
    sync_all()


if __name__ == "__main__":
    main()

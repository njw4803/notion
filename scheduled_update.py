#!/usr/bin/env python3
"""launchd 주간 실행 + 로그인 시 놓친 주 보완(catch-up)."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, time, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
STATE_FILE = ROOT / ".launchd_state.json"
LOG_FILE = Path("/tmp/notion-update.log")
SCHEDULE_HOUR = 10
SCHEDULE_MINUTE = 30


def log(message: str) -> None:
    line = f"[launchd] {datetime.now().isoformat(timespec='seconds')} {message}\n"
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(line)
    print(line, end="")


def this_week_slot(now: datetime | None = None) -> datetime:
    now = now or datetime.now()
    monday = now.date() - timedelta(days=now.weekday())
    return datetime.combine(monday, time(SCHEDULE_HOUR, SCHEDULE_MINUTE))


def load_last_success() -> datetime | None:
    if not STATE_FILE.is_file():
        return None
    raw = STATE_FILE.read_text(encoding="utf-8").strip()
    if not raw:
        return None
    value = json.loads(raw).get("last_success_at")
    if not value:
        return None
    return datetime.fromisoformat(value)


def save_last_success() -> None:
    STATE_FILE.write_text(
        json.dumps({"last_success_at": datetime.now().isoformat(timespec="seconds")}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )


def should_catchup(now: datetime | None = None) -> bool:
    now = now or datetime.now()
    slot = this_week_slot(now)
    if now < slot:
        return False
    last = load_last_success()
    if last is None:
        return True
    return last < slot


def run_update() -> int:
    script = ROOT / "update_detail_on_tag.sh"
    if not script.is_file():
        log(f"ERROR: missing {script}")
        return 1
    result = subprocess.run([str(script)], cwd=str(REPO_ROOT), check=False)
    return result.returncode


def main() -> int:
    trigger = sys.argv[1] if len(sys.argv) > 1 else "calendar"
    log(f"trigger={trigger} start")

    if trigger == "load":
        if not should_catchup():
            log("catch-up skip (이번 주 월 10:30 이전이거나 이미 실행됨)")
            return 0
        log("catch-up run (잠자기·종료로 놓친 주간 실행 보완)")

    code = run_update()
    if code == 0:
        save_last_success()
        log(f"done exit={code}")
    else:
        log(f"failed exit={code}")
    return code


if __name__ == "__main__":
    sys.exit(main())

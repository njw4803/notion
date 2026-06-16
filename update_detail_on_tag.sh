#!/bin/sh
# 본인 커밋 → SyncBox 경력 MD 상세·배운 점 자동 갱신 (launchd 주간: 월 10:30)
# 대상 브랜치: 항상 현재 checkout 브랜치
set -eu

DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$DIR/.." && pwd)"
VENV="$DIR/.venv"
ENV_FILE="$DIR/.env"

cd "$REPO_ROOT"

# NOTION_* 등은 update_from_git.py 가 .env 를 직접 읽습니다 (한글 값 shell source 오류 방지)

if [ -d "$VENV" ]; then
  # shellcheck disable=SC1091
  . "$VENV/bin/activate"
fi

if ! python3 -c "import frontmatter" 2>/dev/null; then
  python3 -m venv "$VENV"
  # shellcheck disable=SC1091
  . "$VENV/bin/activate"
  pip install -q -r "$DIR/requirements.txt"
fi

exec python3 "$DIR/update_from_git.py" "$@"

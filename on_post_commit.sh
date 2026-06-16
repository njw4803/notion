#!/bin/sh
# git post-commit: notion/content MD 변경 시 Notion 동기화

REPO_ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null)"
NOTION_DIR="$REPO_ROOT/notion"
ENV_FILE="$NOTION_DIR/.env"
CONTENT_PREFIX="notion/content/"

if [ ! -f "$ENV_FILE" ]; then
  exit 0
fi

# shellcheck disable=SC1090
set -a
. "$ENV_FILE"
set +a

SYNC=0
if [ "${NOTION_SYNC_EVERY_COMMIT:-0}" = "1" ]; then
  SYNC=1
elif git -C "$REPO_ROOT" diff-tree --no-commit-id --name-only -r HEAD | grep -q "^${CONTENT_PREFIX}"; then
  SYNC=1
fi

if [ "$SYNC" -eq 0 ]; then
  exit 0
fi

echo "[notion] 커밋 감지 → Notion 동기화 시작..."
"$NOTION_DIR/run_sync.sh" || echo "[notion] 동기화 실패 (커밋은 정상 완료됨)" >&2

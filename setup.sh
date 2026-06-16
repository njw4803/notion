#!/bin/sh
# 최초 1회: git hook 등록 + 실행 권한 + .env 생성

set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

chmod +x notion/githooks/post-commit
chmod +x notion/on_post_commit.sh
chmod +x notion/run_sync.sh

git config core.hooksPath notion/githooks
echo "[notion] git hooksPath → notion/githooks 설정 완료"

if [ ! -f notion/.env ]; then
  cp notion/config.example.env notion/.env
  echo "[notion] .env 생성됨 — NOTION_TOKEN 과 DB ID 를 입력하세요."
fi

echo ""
echo "다음 단계:"
echo "  1. notion/.env 에 NOTION_TOKEN·DB ID 입력 (python3 sync_to_notion.py --discover)"
echo "  2. cp notion/git_projects.example.yaml notion/git_projects.yaml 후 수정"
echo "  3. cd notion && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt"
echo "  4. content/ 수정 → CAREER_AUTOMATION_GUIDE.md §0 7~9단계 (갱신 + install_launchd + 자동 실행 확인)"

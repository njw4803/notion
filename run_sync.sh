#!/bin/sh
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$DIR/.venv"

if [ -d "$VENV" ]; then
  # shellcheck disable=SC1091
  . "$VENV/bin/activate"
fi

if ! python3 -c "import frontmatter" 2>/dev/null; then
  echo "[notion] 의존성 설치 중..."
  python3 -m venv "$VENV"
  # shellcheck disable=SC1091
  . "$VENV/bin/activate"
  pip install -q -r "$DIR/requirements.txt"
fi

python3 "$DIR/sync_to_notion.py"

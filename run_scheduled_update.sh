#!/bin/sh
# launchd → scheduled_update.py (calendar | load)
set -eu

DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$DIR/.venv"

if [ -d "$VENV" ]; then
  # shellcheck disable=SC1091
  . "$VENV/bin/activate"
fi

exec python3 "$DIR/scheduled_update.py" "${1:-calendar}"

#!/bin/sh
# launchd 주간 스케줄 설치 (cron 제거 포함)
set -eu

DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$DIR/.." && pwd)"
AGENTS_DIR="$HOME/Library/LaunchAgents"
UID_NUM="$(id -u)"
DOMAIN="gui/$UID_NUM"

chmod +x "$DIR/run_scheduled_update.sh" "$DIR/update_detail_on_tag.sh" "$DIR/scheduled_update.py" "$DIR/install_launchd.sh"

PYTHON3="$(/usr/bin/python3 -c 'import sys; print(sys.executable)')"
echo "[launchd] Python: ${PYTHON3}"

if [ "${REMOVE_CRON:-0}" = "1" ]; then
  echo "[launchd] crontab 항목 제거 (REMOVE_CRON=1)"
  if crontab -l 2>/dev/null | grep -q 'update_detail_on_tag.sh'; then
    crontab -l | grep -v 'update_detail_on_tag.sh' | grep -v 'SyncBox Notion 경력 MD' | crontab - || crontab -r 2>/dev/null || true
    echo "[launchd] crontab 에서 notion 항목 삭제됨"
  fi
else
  echo "[launchd] crontab 유지 (제거하려면 REMOVE_CRON=1 ./notion/install_launchd.sh)"
fi

mkdir -p "$AGENTS_DIR"

for name in com.dorosee.syncbox-notion-update com.dorosee.syncbox-notion-update-catchup; do
  src="$DIR/launchd/$name.plist"
  dest="$AGENTS_DIR/$name.plist"
  if [ ! -f "$src" ]; then
    echo "[launchd] ERROR: $src 없음" >&2
    exit 1
  fi
  sed \
    -e "s|__NOTION_DIR__|$DIR|g" \
    -e "s|__REPO_ROOT__|$REPO_ROOT|g" \
    -e "s|__PYTHON3__|$PYTHON3|g" \
    "$src" > "$dest"
  launchctl bootout "$DOMAIN" "$dest" 2>/dev/null || true
  launchctl bootstrap "$DOMAIN" "$dest"
  launchctl enable "$DOMAIN/$name" 2>/dev/null || true
  echo "[launchd] 등록: $dest"
done

echo ""
echo "[launchd] 설치 완료"
echo "  - 매주 월요일 10:30: com.dorosee.syncbox-notion-update"
echo "  - 로그인 시 놓친 주 보완: com.dorosee.syncbox-notion-update-catchup (RunAtLoad)"
echo ""
echo "확인:"
echo "  launchctl print $DOMAIN/com.dorosee.syncbox-notion-update | head -20"
echo "  tail -30 /tmp/notion-update.log"

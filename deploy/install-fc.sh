#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
STAGE="$ROOT/site"
TARGET=/opt/fred-node/runtime/cap/frontend/dist/playable
ROLLBACK_ROOT=/opt/fred-node/rollback
MARKER=.playable-universe-v0
STAMP=$(date -u +%Y%m%dT%H%M%SZ)

test "$(id -u)" -eq 0 || {
  echo "REFUSED: run as root"
  exit 1
}

test -f "$STAGE/$MARKER" || {
  echo "REFUSED: Playable Universe marker missing from $STAGE"
  exit 1
}

test -f "$STAGE/index.html"
test -f "$STAGE/styles.css"
test -f "$STAGE/app.js"
test -f "$STAGE/data/tiles.json"

if [ -e "$TARGET" ]; then
  test -f "$TARGET/$MARKER" || {
    echo "REFUSED: target exists and is not owned by Playable Universe deployment"
    exit 1
  }
  mkdir -p "$ROLLBACK_ROOT"
  BACKUP="$ROLLBACK_ROOT/playable-universe-pre-$STAMP"
  cp -a "$TARGET" "$BACKUP"
  echo "rollback_backup=$BACKUP"
fi

TMP="${TARGET}.new-$STAMP"
rm -rf "$TMP"
mkdir -p "$TMP"
cp -a "$STAGE/." "$TMP/"
chown -R quietwire:quietwire "$TMP"
find "$TMP" -type d -exec chmod 0755 {} +
find "$TMP" -type f -exec chmod 0644 {} +

if [ -e "$TARGET" ]; then
  OLD="${TARGET}.old-$STAMP"
  mv "$TARGET" "$OLD"
  mv "$TMP" "$TARGET"
  rm -rf "$OLD"
else
  mv "$TMP" "$TARGET"
fi

echo "target=$TARGET"
echo "nginx_reload_required=false"

BODY=$(curl -ksS --max-time 10 https://fc.quietwire.ai/playable/)
printf "%s" "$BODY" | grep -q "<title>Playable Universe</title>" || {
  echo "FAILED: public smoke test did not find Playable Universe title"
  exit 1
}

CODE=$(curl -ksS -o /dev/null -w "%{http_code}" https://fc.quietwire.ai/playable/)
test "$CODE" = "200" || {
  echo "FAILED: public HTTP status=$CODE"
  exit 1
}

echo "PLAYABLE_UNIVERSE_FC_DEPLOY_OK=true"
echo "url=https://fc.quietwire.ai/playable/"

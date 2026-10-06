#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
SITE_SRC="$REPO_ROOT/site"
SERVER_SRC="$REPO_ROOT/server/attestation_intake.py"
APPROVE_SRC="$REPO_ROOT/server/review_media.py"
UNIT_SRC="$REPO_ROOT/deploy/playable-universe-intake.service"

SITE_TARGET=/opt/fred-node/runtime/cap/frontend/dist/playable
APP_TARGET=/opt/playable-universe/intake
WORLD_TARGET=/opt/playable-universe/world
DATA_TARGET=/var/lib/playable-universe
UNIT_TARGET=/etc/systemd/system/playable-universe-intake.service
NGINX=/etc/nginx/sites-available/capweb.conf
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP_ROOT=/opt/fred-node/rollback/playable-universe-evidence-world-$STAMP

test "$(id -u)" -eq 0 || { echo "REFUSED: run as root"; exit 1; }
test -f "$SITE_SRC/.playable-universe-v0"
test -f "$SERVER_SRC"
test -f "$APPROVE_SRC"
test -f "$UNIT_SRC"
test -f "$NGINX"
test -d "$REPO_ROOT/data"
test -d "$REPO_ROOT/examples"
command -v ffmpeg >/dev/null

mkdir -p "$BACKUP_ROOT"
cp -a "$SITE_TARGET" "$BACKUP_ROOT/site"
cp -a "$NGINX" "$BACKUP_ROOT/capweb.conf"
if [ -f "$UNIT_TARGET" ]; then cp -a "$UNIT_TARGET" "$BACKUP_ROOT/service.unit"; fi
if [ -d "$APP_TARGET" ]; then cp -a "$APP_TARGET" "$BACKUP_ROOT/intake"; fi
if [ -d "$WORLD_TARGET" ]; then cp -a "$WORLD_TARGET" "$BACKUP_ROOT/world"; fi

echo "backup=$BACKUP_ROOT"

mkdir -p "$APP_TARGET" "$DATA_TARGET"
install -m 0755 "$SERVER_SRC" "$APP_TARGET/attestation_intake.py"
install -m 0755 "$APPROVE_SRC" "$APP_TARGET/review_media.py"

rm -rf "$WORLD_TARGET.new"
mkdir -p "$WORLD_TARGET.new"
cp -a "$REPO_ROOT/data" "$WORLD_TARGET.new/data"
cp -a "$REPO_ROOT/examples" "$WORLD_TARGET.new/examples"
chown -R quietwire:quietwire "$WORLD_TARGET.new"
if [ -d "$WORLD_TARGET" ]; then rm -rf "$WORLD_TARGET.old"; mv "$WORLD_TARGET" "$WORLD_TARGET.old"; fi
mv "$WORLD_TARGET.new" "$WORLD_TARGET"
rm -rf "$WORLD_TARGET.old"

chown -R quietwire:quietwire "$APP_TARGET" "$DATA_TARGET"
install -m 0644 "$UNIT_SRC" "$UNIT_TARGET"

python3 - "$NGINX" <<'PY'
from pathlib import Path
import sys
path=Path(sys.argv[1])
text=path.read_text()
begin="    # PLAYABLE-UNIVERSE-API-BEGIN\n"
end="    # PLAYABLE-UNIVERSE-API-END\n"
block=(
    begin
    + "    location /playable/api/ {\n"
    + "        proxy_pass http://127.0.0.1:18270/;\n"
    + "        proxy_http_version 1.1;\n"
    + "        proxy_set_header Host $host;\n"
    + "        proxy_set_header X-Real-IP $remote_addr;\n"
    + "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n"
    + "        proxy_set_header X-Forwarded-Proto $scheme;\n"
    + "        client_max_body_size 9m;\n"
    + "    }\n"
    + end
)
if begin in text:
    a=text.index(begin)
    b=text.index(end,a)+len(end)
    text=text[:a]+block+text[b:]
else:
    needle="    location / {\n"
    if needle not in text:
        raise SystemExit("REFUSED: expected nginx insertion point missing")
    text=text.replace(needle,block+"\n"+needle,1)
path.write_text(text)
PY

nginx -t || {
  cp -a "$BACKUP_ROOT/capweb.conf" "$NGINX"
  echo "REFUSED: nginx validation failed; configuration restored"
  exit 1
}

systemctl daemon-reload
systemctl enable playable-universe-intake.service >/dev/null
systemctl restart playable-universe-intake.service

for _ in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:18270/healthz >/dev/null; then break; fi
  sleep 0.25
done
curl -fsS http://127.0.0.1:18270/healthz >/dev/null
curl -fsS http://127.0.0.1:18270/v0/scenes >/dev/null
curl -fsS http://127.0.0.1:18270/v0/world/tiles >/dev/null

mkdir -p "$SITE_TARGET"
cp -a "$SITE_SRC/." "$SITE_TARGET/"
chown -R quietwire:quietwire "$SITE_TARGET"
find "$SITE_TARGET" -type d -exec chmod 0755 {} +
find "$SITE_TARGET" -type f -exec chmod 0644 {} +

systemctl reload nginx

curl -fsS https://fc.quietwire.ai/playable/ >/dev/null
curl -fsS https://fc.quietwire.ai/playable/attest/ | grep -q "Make an Attest"
curl -fsS https://fc.quietwire.ai/playable/play/ | grep -q "Walk the Valley"
curl -fsS https://fc.quietwire.ai/playable/api/healthz >/dev/null
curl -fsS https://fc.quietwire.ai/playable/api/v0/scenes >/dev/null
curl -fsS https://fc.quietwire.ai/playable/api/v0/world/tiles >/dev/null

echo "PLAYABLE_EVIDENCE_WORLD_V1_DEPLOY_OK=true"
echo "attest=https://fc.quietwire.ai/playable/attest/"
echo "play=https://fc.quietwire.ai/playable/play/"
echo "scenes=https://fc.quietwire.ai/playable/api/v0/scenes"
echo "tiles=https://fc.quietwire.ai/playable/api/v0/world/tiles"
echo "review=/opt/playable-universe/intake/review_media.py"

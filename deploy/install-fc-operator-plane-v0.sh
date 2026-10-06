#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
OPERATOR_SRC="$REPO_ROOT/server/operator_plane.py"
CLIENT_SRC="$REPO_ROOT/server/playable_ops.py"
UNIT_SRC="$REPO_ROOT/deploy/playable-universe-operator.service"
POLICY_SRC="$REPO_ROOT/deploy/operator-policy.fc.v0.json"
INTERLOCK_SEED="$REPO_ROOT/deploy/operator-interlock.normal.v0.json"

APP_DIR=/opt/playable-universe/operator
CLIENT_DST=/usr/local/bin/playable-ops
UNIT_DST=/etc/systemd/system/playable-universe-operator.service
ETC_DIR=/etc/playable-universe
POLICY_DST="$ETC_DIR/operator-policy.json"
INTERLOCK_DST="$ETC_DIR/operator-interlock.json"
DB=/var/lib/playable-universe/attestation-intake.sqlite3

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP=/opt/fred-node/rollback/playable-universe-operator-plane-$STAMP

test "$(id -u)" -eq 0 || {
  echo "REFUSED: run as root"
  exit 1
}

for f in "$OPERATOR_SRC" "$CLIENT_SRC" "$UNIT_SRC" "$POLICY_SRC" "$INTERLOCK_SEED"; do
  test -f "$f" || {
    echo "REFUSED: missing $f"
    exit 1
  }
done

test -f "$DB" || {
  echo "REFUSED: Playable Universe database missing"
  exit 1
}

getent passwd quietwire >/dev/null
getent passwd rdc-fc >/dev/null

mkdir -p "$BACKUP"

python3 - "$DB" "$BACKUP/attestation-intake.sqlite3" <<'PYDB'
import sqlite3,sys
src=sqlite3.connect(sys.argv[1])
dst=sqlite3.connect(sys.argv[2])
with dst:
    src.backup(dst)
dst.close()
src.close()
PYDB

for f in "$CLIENT_DST" "$UNIT_DST" "$POLICY_DST" "$INTERLOCK_DST"; do
  if [ -e "$f" ]; then
    cp -a "$f" "$BACKUP/$(basename "$f")"
  fi
done

if [ -d "$APP_DIR" ]; then
  cp -a "$APP_DIR" "$BACKUP/operator-app"
fi

for service in   qwos-rdc-fc.service   quiet-hands-agent-fc-common.service   quiet-hands-agent-fc.service   quiet-hands-mcp-fc.service
do
  dropin="/etc/systemd/system/${service}.d/50-playable-ops.conf"
  if [ -f "$dropin" ]; then
    mkdir -p "$BACKUP/dropins"
    cp -a "$dropin" "$BACKUP/dropins/${service}.conf"
  fi
done

echo "backup=$BACKUP"

groupadd -f playable-ops
usermod -a -G playable-ops quietwire
usermod -a -G playable-ops rdc-fc

install -d -o root -g root -m 0755 "$APP_DIR"
install -o root -g root -m 0755 "$OPERATOR_SRC" "$APP_DIR/operator_plane.py"
install -o root -g root -m 0755 "$CLIENT_SRC" "$CLIENT_DST"

install -d -o root -g root -m 0755 "$ETC_DIR"
install -o root -g root -m 0644 "$POLICY_SRC" "$POLICY_DST"

if [ ! -e "$INTERLOCK_DST" ]; then
  install -o root -g root -m 0644 "$INTERLOCK_SEED" "$INTERLOCK_DST"
else
  echo "interlock_preserved=$INTERLOCK_DST"
fi

install -o root -g root -m 0644 "$UNIT_SRC" "$UNIT_DST"

for service in   qwos-rdc-fc.service   quiet-hands-agent-fc-common.service   quiet-hands-agent-fc.service   quiet-hands-mcp-fc.service
do
  mkdir -p "/etc/systemd/system/${service}.d"
  cat >"/etc/systemd/system/${service}.d/50-playable-ops.conf" <<'DROPIN'
[Service]
SupplementaryGroups=playable-ops
DROPIN
done

python3 -m py_compile "$APP_DIR/operator_plane.py" "$CLIENT_DST"
python3 -m json.tool "$POLICY_DST" >/dev/null
python3 -m json.tool "$INTERLOCK_DST" >/dev/null

systemctl daemon-reload
systemctl enable --now playable-universe-operator.service

for _ in $(seq 1 30); do
  if [ -S /run/playable-universe/operator.sock ]; then break; fi
  sleep 0.2
done

test -S /run/playable-universe/operator.sock
test "$(stat -c %a /run/playable-universe/operator.sock)" = "660"
test "$(stat -c %G /run/playable-universe/operator.sock)" = "playable-ops"
test "$(stat -c %G /run/playable-universe)" = "playable-ops"

# Restart only rdc-fc execution/carriage services so the newly admitted
# supplementary group is effective in future agent/RDC child processes.
systemctl restart qwos-rdc-fc.service
systemctl restart quiet-hands-agent-fc-common.service
systemctl restart quiet-hands-agent-fc.service
systemctl restart quiet-hands-mcp-fc.service

for service in   playable-universe-operator.service   qwos-rdc-fc.service   quiet-hands-agent-fc-common.service   quiet-hands-agent-fc.service   quiet-hands-mcp-fc.service
do
  systemctl is-active --quiet "$service" || {
    echo "FAILED: $service is not active"
    exit 1
  }
done

runuser -u rdc-fc -- "$CLIENT_DST" status > /tmp/playable-ops-rdc-status.json
runuser -u quietwire -- "$CLIENT_DST" status > /tmp/playable-ops-quietwire-status.json

python3 - <<'PY'
import json
rdc=json.load(open("/tmp/playable-ops-rdc-status.json"))
operator=json.load(open("/tmp/playable-ops-quietwire-status.json"))
assert rdc["ok"] is True
assert rdc["result"]["actor"]["user"]=="rdc-fc"
assert rdc["result"]["actor"]["role"]=="agent-steward"
assert "candidate.inspect" in rdc["result"]["allowed_operations"]
assert "evidence.report_unavailable" in rdc["result"]["allowed_operations"]
assert "promotion.propose_cap" in rdc["result"]["allowed_operations"]
assert "media.review.approve" not in rdc["result"]["allowed_operations"]
assert operator["ok"] is True
assert operator["result"]["actor"]["user"]=="quietwire"
assert operator["result"]["actor"]["role"]=="operator"
assert "media.review.approve" in operator["result"]["allowed_operations"]
assert rdc["result"]["interlock"]["state"] in {"NORMAL","CONSTRAINED"}
print("OPERATOR_ROLE_SMOKE_OK=true")
PY

rm -f /tmp/playable-ops-rdc-status.json /tmp/playable-ops-quietwire-status.json

echo "PLAYABLE_OPERATOR_PLANE_V0_DEPLOY_OK=true"
echo "socket=/run/playable-universe/operator.sock"
echo "policy=$POLICY_DST"
echo "interlock=$INTERLOCK_DST"
echo "client=$CLIENT_DST"
echo "rdc_role=agent-steward"
echo "quietwire_role=operator"

#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
SITE_SRC="$REPO_ROOT/site"
INTAKE_SRC="$REPO_ROOT/server/attestation_intake.py"
TEST_ROOT="$REPO_ROOT/tests"

SITE_TARGET=/opt/fred-node/runtime/cap/frontend/dist/playable
INTAKE_TARGET=/opt/playable-universe/intake/attestation_intake.py
SERVICE=playable-universe-intake.service

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP=/opt/fred-node/rollback/playable-facebook-field-pilot-$STAMP

test "$(id -u)" -eq 0 || {
  echo "REFUSED: run as root"
  exit 1
}

for f in   "$SITE_SRC/.playable-universe-v0"   "$SITE_SRC/index.html"   "$SITE_SRC/attest/index.html"   "$SITE_SRC/attest/attest.js"   "$SITE_SRC/attest/attest.css"   "$INTAKE_SRC"; do
  test -f "$f" || {
    echo "REFUSED: missing $f"
    exit 1
  }
done

grep -q "OPEN FIELD TEST" "$SITE_SRC/index.html" || {
  echo "REFUSED: public pilot marker missing"
  exit 1
}

grep -q "How do you know this?" "$SITE_SRC/attest/index.html" || {
  echo "REFUSED: provenance UI marker missing"
  exit 1
}

grep -q '"provenance"' "$INTAKE_SRC" || {
  echo "REFUSED: intake provenance support missing"
  exit 1
}

echo "=== PREDEPLOY TESTS ==="

python3 -m py_compile "$INTAKE_SRC"
python3 -m unittest discover -s "$TEST_ROOT" -p 'test_*.py'

python3 - "$INTAKE_SRC" <<'PY'
import importlib.util
import sys

path = sys.argv[1]
spec = importlib.util.spec_from_file_location("playable_intake_predeploy", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

packet = {
    "schema": "playable.mobile-attestation.v0",
    "client_id": "browser:deploy-smoke",
    "created_at": "2026-10-06T23:45:00Z",
    "claim": {
        "text": "Deployment provenance smoke.",
        "kind": "witness_statement",
    },
    "witness": {
        "mode": "anonymous",
        "display_name": None,
        "identity_ref": None,
    },
    "assurance": {
        "class": "browser-self-asserted",
        "signature": None,
    },
    "provenance": {
        "mode": "direct_observation",
        "source_refs": [],
        "note": None,
    },
    "evidence": [],
    "location": {
        "mode": "none",
        "latitude": None,
        "longitude": None,
        "accuracy_m": None,
        "place_label": None,
    },
    "sharing": {
        "candidate_visibility": "receipt-only",
        "media_disposition": "hash-only-v0",
    },
    "refs": [],
    "notes": [],
}

clean = mod.validate_packet(packet)
assert clean["provenance"]["mode"] == "direct_observation"

legacy = dict(packet)
legacy.pop("provenance")
clean_legacy = mod.validate_packet(legacy)
assert clean_legacy["provenance"]["mode"] == "unspecified"

print("provenance_validation_ok=true")
PY

echo "=== BACKUP ==="

mkdir -p "$BACKUP"
cp -a "$SITE_TARGET" "$BACKUP/site"
cp -a "$INTAKE_TARGET" "$BACKUP/attestation_intake.py"
echo "backup=$BACKUP"

restore() {
  set +e
  echo "ROLLBACK_BEGIN=true"

  rm -rf "$SITE_TARGET"
  cp -a "$BACKUP/site" "$SITE_TARGET"

  install -o root -g root -m 0755     "$BACKUP/attestation_intake.py" "$INTAKE_TARGET"

  systemctl restart "$SERVICE" || true

  echo "ROLLBACK_END=true"
}

finish() {
  rc=$?
  trap - EXIT
  if [ "$rc" -ne 0 ]; then
    restore
  fi
  exit "$rc"
}
trap finish EXIT

echo "=== DEPLOY SITE ==="

SITE_NEW="$SITE_TARGET.new-$STAMP"
rm -rf "$SITE_NEW"
mkdir -p "$SITE_NEW"
cp -a "$SITE_SRC/." "$SITE_NEW/"
chown -R quietwire:quietwire "$SITE_NEW"
find "$SITE_NEW" -type d -exec chmod 0755 {} +
find "$SITE_NEW" -type f -exec chmod 0644 {} +

rm -rf "$SITE_TARGET.old-$STAMP"
mv "$SITE_TARGET" "$SITE_TARGET.old-$STAMP"
mv "$SITE_NEW" "$SITE_TARGET"

echo "=== DEPLOY INTAKE ==="

install -o root -g root -m 0755 "$INTAKE_SRC" "$INTAKE_TARGET"
python3 -m py_compile "$INTAKE_TARGET"

systemctl restart "$SERVICE"

for _ in $(seq 1 40); do
  if curl -fsS http://127.0.0.1:18270/healthz >/dev/null 2>&1; then
    break
  fi
  sleep 0.25
done

systemctl is-active --quiet "$SERVICE"
curl -fsS http://127.0.0.1:18270/healthz   | python3 -c 'import json,sys; x=json.load(sys.stdin); assert x.get("status") == "ok"'

echo "=== CANONICAL SMOKE ==="

check_contains() {
  local url=$1
  local marker=$2
  local label=$3

  curl -fsS "$url" \
    | python3 -c 'import sys; marker=sys.argv[1]; body=sys.stdin.read(); assert marker in body' "$marker"

  echo "$label=ok"
}

check_contains \
  https://playable.quietwire.ai/ \
  "OPEN FIELD TEST" \
  canonical_root

check_contains \
  https://playable.quietwire.ai/attest/ \
  "How do you know this?" \
  canonical_attest_provenance

curl -fsS https://playable.quietwire.ai/api/healthz \
  | python3 -c 'import json,sys; x=json.load(sys.stdin); assert x.get("status") == "ok"'

echo "canonical_api=ok"

rm -rf "$SITE_TARGET.old-$STAMP"

trap - EXIT

echo
echo "PLAYABLE_FACEBOOK_FIELD_PILOT_V0_DEPLOY_OK=true"
echo "canonical=https://playable.quietwire.ai/"
echo "attest=https://playable.quietwire.ai/attest/"
echo "provenance_modes=direct_observation,own_capture,relayed_report,source_material,derived_inference,unknown"
echo "public_default=receipt-only"
echo "backup=$BACKUP"

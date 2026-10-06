#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)

HOST=playable.quietwire.ai
PLAY_ROOT=/opt/fred-node/runtime/cap/frontend/dist/playable
NGINX_AVAILABLE=/etc/nginx/sites-available/playable.quietwire.ai.conf
NGINX_ENABLED=/etc/nginx/sites-enabled/playable.quietwire.ai.conf
NGINX_FINAL="$REPO_ROOT/deploy/playable.quietwire.ai.nginx.conf"

INTAKE_SRC="$REPO_ROOT/server/attestation_intake.py"
REVIEW_SRC="$REPO_ROOT/server/review_media.py"
UNIT_SRC="$REPO_ROOT/deploy/playable-universe-intake.service"

INTAKE_DST=/opt/playable-universe/intake/attestation_intake.py
REVIEW_DST=/opt/playable-universe/intake/review_media.py
UNIT_DST=/etc/systemd/system/playable-universe-intake.service

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP=/opt/fred-node/rollback/playable-public-origin-$STAMP

test "$(id -u)" -eq 0 || {
  echo "REFUSED: run as root"
  exit 1
}

for f in "$NGINX_FINAL" "$INTAKE_SRC" "$REVIEW_SRC" "$UNIT_SRC"; do
  test -f "$f" || {
    echo "REFUSED: missing $f"
    exit 1
  }
done

test -d "$PLAY_ROOT" || {
  echo "REFUSED: Playable static root missing"
  exit 1
}

getent ahostsv4 "$HOST" | awk '{print $1}' | grep -qx '178.128.224.207' || {
  echo "REFUSED: $HOST does not resolve to FC"
  exit 1
}

mkdir -p "$BACKUP"

for f in "$NGINX_AVAILABLE" "$UNIT_DST" "$INTAKE_DST" "$REVIEW_DST"; do
  if [ -e "$f" ]; then
    cp -a "$f" "$BACKUP/$(basename "$f")"
  fi
done

if [ -L "$NGINX_ENABLED" ]; then
  readlink "$NGINX_ENABLED" > "$BACKUP/nginx-enabled-target.txt"
elif [ -e "$NGINX_ENABLED" ]; then
  cp -a "$NGINX_ENABLED" "$BACKUP/nginx-enabled-file"
else
  touch "$BACKUP/nginx-enabled-absent"
fi

echo "backup=$BACKUP"

restore() {
  set +e
  echo "ROLLBACK_BEGIN=true"

  if [ -f "$BACKUP/$(basename "$INTAKE_DST")" ]; then
    install -o root -g root -m 0755       "$BACKUP/$(basename "$INTAKE_DST")" "$INTAKE_DST"
  fi

  if [ -f "$BACKUP/$(basename "$REVIEW_DST")" ]; then
    install -o root -g root -m 0755       "$BACKUP/$(basename "$REVIEW_DST")" "$REVIEW_DST"
  fi

  if [ -f "$BACKUP/$(basename "$UNIT_DST")" ]; then
    install -o root -g root -m 0644       "$BACKUP/$(basename "$UNIT_DST")" "$UNIT_DST"
  fi

  if [ -f "$BACKUP/$(basename "$NGINX_AVAILABLE")" ]; then
    install -o root -g root -m 0644       "$BACKUP/$(basename "$NGINX_AVAILABLE")" "$NGINX_AVAILABLE"
  else
    rm -f "$NGINX_AVAILABLE"
  fi

  rm -f "$NGINX_ENABLED"
  if [ -f "$BACKUP/nginx-enabled-target.txt" ]; then
    ln -s "$(cat "$BACKUP/nginx-enabled-target.txt")" "$NGINX_ENABLED"
  elif [ -f "$BACKUP/nginx-enabled-file" ]; then
    cp -a "$BACKUP/nginx-enabled-file" "$NGINX_ENABLED"
  fi

  systemctl daemon-reload
  systemctl restart playable-universe-intake.service || true
  nginx -t && systemctl reload nginx || true

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

# Deploy canonical-origin aware intake code first.
install -d -o root -g root -m 0755 /opt/playable-universe/intake
install -o root -g root -m 0755 "$INTAKE_SRC" "$INTAKE_DST"
install -o root -g root -m 0755 "$REVIEW_SRC" "$REVIEW_DST"
install -o root -g root -m 0644 "$UNIT_SRC" "$UNIT_DST"

python3 -m py_compile "$INTAKE_DST" "$REVIEW_DST"

# Temporary HTTP-only vhost so ACME webroot validation has an exact host.
cat >"$NGINX_AVAILABLE" <<'NGINX_HTTP'
server {
    listen 80;
    listen [::]:80;
    server_name playable.quietwire.ai;

    root /opt/fred-node/runtime/cap/frontend/dist/playable;

    location ^~ /.well-known/acme-challenge/ {
        try_files $uri =404;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
NGINX_HTTP

ln -sfn "$NGINX_AVAILABLE" "$NGINX_ENABLED"

nginx -t
systemctl reload nginx

# Reuse the existing Certbot account; do not create a new account identity.
certbot certonly   --webroot   --webroot-path "$PLAY_ROOT"   --cert-name "$HOST"   -d "$HOST"   --non-interactive   --agree-tos   --keep-until-expiring   --deploy-hook "systemctl reload nginx"

test -f "/etc/letsencrypt/live/$HOST/fullchain.pem"
test -f "/etc/letsencrypt/live/$HOST/privkey.pem"

install -o root -g root -m 0644 "$NGINX_FINAL" "$NGINX_AVAILABLE"

systemctl daemon-reload
systemctl restart playable-universe-intake.service

for _ in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:18270/healthz >/dev/null 2>&1; then
    break
  fi
  sleep 0.25
done

curl -fsS http://127.0.0.1:18270/healthz >/dev/null

nginx -t
systemctl reload nginx

# nginx reload is asynchronous. Do not race the old TLS workers.
# Wait until the local SNI path presents the canonical certificate.
tls_ready=false
for _ in $(seq 1 80); do
  if echo | openssl s_client \
      -connect 127.0.0.1:443 \
      -servername "$HOST" 2>/dev/null \
      | openssl x509 -noout -ext subjectAltName 2>/dev/null \
      | grep -q "DNS:$HOST"; then
    tls_ready=true
    break
  fi
  sleep 0.25
done

test "$tls_ready" = true || {
  echo "REFUSED: nginx did not begin serving the playable.quietwire.ai certificate"
  exit 1
}

# Then wait for the canonical vhost content/API, locally through SNI.
origin_ready=false
for _ in $(seq 1 40); do
  if curl -fsS --resolve "$HOST:443:127.0.0.1" "https://$HOST/" \
       | grep -q "Playable Universe" \
     && curl -fsS --resolve "$HOST:443:127.0.0.1" "https://$HOST/api/healthz" \
       | python3 -c 'import json,sys; x=json.load(sys.stdin); assert x.get("ok") is True' \
       >/dev/null 2>&1; then
    origin_ready=true
    break
  fi
  sleep 0.25
done

test "$origin_ready" = true || {
  echo "REFUSED: canonical local vhost did not become healthy"
  exit 1
}

# Canonical public origin must now be real, not a browser/cache alias.
curl -fsS "https://$HOST/" | grep -q "Playable Universe"
curl -fsS "https://$HOST/attest/" | grep -q "Make an Attest"
curl -fsS "https://$HOST/play/" | grep -q "Walk the Valley"

curl -fsS "https://$HOST/api/healthz"   | python3 -c 'import json,sys; x=json.load(sys.stdin); assert x.get("ok") is True'

curl -fsS "https://$HOST/api/v0/scenes"   | python3 -c 'import json,sys; x=json.load(sys.stdin); assert "items" in x'

# Old FC path remains a compatibility surface.
curl -fsS "https://fc.quietwire.ai/playable/"   | grep -q "Walk the world we can actually get to"

# Verify the certificate actually names the new origin.
echo | openssl s_client   -connect "$HOST:443"   -servername "$HOST" 2>/dev/null   | openssl x509 -noout -ext subjectAltName   | grep -q "DNS:$HOST"

echo "PLAYABLE_PUBLIC_ORIGIN_V1_1_DEPLOY_OK=true"
echo "canonical=https://playable.quietwire.ai/"
echo "attest=https://playable.quietwire.ai/attest/"
echo "play=https://playable.quietwire.ai/play/"
echo "api=https://playable.quietwire.ai/api/healthz"
echo "host_node=qwos:fc"
echo "compatibility=https://fc.quietwire.ai/playable/"

#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
BUILDER="$REPO_ROOT/deploy/build-fc-oauth-playable-policy.py"

SOURCE_POLICY=/home/rdc-fc/.quiet-hands-common/oauth-executor-policy.v0.json
ETC_DIR=/etc/quiet-hands
DEST_POLICY="$ETC_DIR/oauth-executor-policy.fc.v1.json"
SERVICE=quiet-hands-agent-fc-common.service
DROPIN=/etc/systemd/system/quiet-hands-agent-fc-common.service.d/70-oauth-executor-policy-v1.conf

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP=/opt/fred-node/rollback/quiet-hands-oauth-playable-v1-$STAMP

test "$(id -u)" -eq 0 || {
  echo "REFUSED: run as root"
  exit 1
}

test -f "$SOURCE_POLICY" || {
  echo "REFUSED: source OAuth executor policy missing"
  exit 1
}
test -f "$BUILDER" || {
  echo "REFUSED: OAuth policy builder missing"
  exit 1
}

test -S /run/playable-universe/operator.sock || {
  echo "REFUSED: Playable operator socket missing"
  exit 1
}

mkdir -p "$BACKUP"
cp -a "$SOURCE_POLICY" "$BACKUP/source-policy.json"
if [ -f "$DEST_POLICY" ]; then cp -a "$DEST_POLICY" "$BACKUP/dest-policy.json"; fi
if [ -f "$DROPIN" ]; then cp -a "$DROPIN" "$BACKUP/dropin.conf"; fi

echo "backup=$BACKUP"

install -d -o root -g root -m 0755 "$ETC_DIR"

python3 "$BUILDER" "$SOURCE_POLICY" "$DEST_POLICY.new"
install -o root -g rdc-fc -m 0640 "$DEST_POLICY.new" "$DEST_POLICY"
rm -f "$DEST_POLICY.new"

cat >"$DROPIN" <<EOF
[Service]
Environment=QUIET_HANDS_OAUTH_EXECUTOR_POLICY=$DEST_POLICY
ReadOnlyPaths=$ETC_DIR
EOF

python3 -m json.tool "$DEST_POLICY" >/dev/null

NODE=/home/rdc-fc/.local/node-v22.12.0-linux-x64/bin/node
test -x "$NODE"

# Validate policy using the same implementation the public/common agent uses.
"$NODE" --input-type=module <<NODE
import fs from 'node:fs';
import {
  validateOAuthExecutorPolicy,
  evaluateOAuthExecutorCall
} from '/home/rdc-fc/src/quiet-hands-common/src/oauth-executor-policy.js';

const policy=validateOAuthExecutorPolicy(JSON.parse(
  fs.readFileSync('$DEST_POLICY','utf8')
));
const principal=policy.principals.find(p => (p.nodes ?? []).includes('qwos:fc'));
if (!principal) throw new Error('no FC principal');

const auth={
  authenticated:true,
  auth_type:'oauth2',
  issuer:principal.issuer,
  subject:principal.subject,
  audience:principal.audience,
  client_id:principal.client_id_prefix+'policy-smoke/client.json',
  scopes:['hands.read','hands.execute','hands.write']
};

for (const name of [
  'playable_operator_status',
  'playable_operator_receipts',
  'playable_candidate_inspect',
  'playable_evidence_report_unavailable',
  'playable_candidate_corroborate',
  'playable_candidate_dispute',
  'playable_promotion_propose_cap'
]) {
  const d=evaluateOAuthExecutorCall(policy,auth,'qwos:fc',name);
  if (!d.ok) throw new Error(name+' unexpectedly denied: '+JSON.stringify(d));
}

const readOnly={
  ...auth,
  scopes:['hands.read']
};
if (!evaluateOAuthExecutorCall(
  policy,readOnly,'qwos:fc','playable_candidate_inspect'
).ok) throw new Error('read-only candidate inspection should be admitted');

const noExecute={
  ...auth,
  scopes:['hands.read','hands.write']
};
const denied=evaluateOAuthExecutorCall(
  policy,noExecute,'qwos:fc','playable_candidate_corroborate'
);
if (denied.ok || denied.code!=='insufficient_scope') {
  throw new Error('bounded mutation should require hands.execute');
}

const executeNoWrite={
  ...auth,
  scopes:['hands.execute']
};
if (!evaluateOAuthExecutorCall(
  policy,executeNoWrite,'qwos:fc','playable_candidate_corroborate'
).ok) {
  throw new Error('semantic transition should not require generic hands.write');
}

console.log('OAUTH_PLAYABLE_POLICY_SMOKE_OK=true');
NODE

systemctl daemon-reload
systemctl restart "$SERVICE"

for _ in $(seq 1 30); do
  if systemctl is-active --quiet "$SERVICE"; then break; fi
  sleep 0.25
done
systemctl is-active --quiet "$SERVICE"

ACTIVE_POLICY=$(systemctl show "$SERVICE" -p Environment --value | tr ' ' '\n' | sed -n 's/^QUIET_HANDS_OAUTH_EXECUTOR_POLICY=//p' | tail -n1)
test "$ACTIVE_POLICY" = "$DEST_POLICY" || {
  echo "REFUSED: service did not adopt root-owned policy"
  exit 1
}

test "$(stat -c %U "$DEST_POLICY")" = root
test "$(stat -c %G "$DEST_POLICY")" = rdc-fc
test "$(stat -c %a "$DEST_POLICY")" = 640

echo "QUIET_HANDS_OAUTH_PLAYABLE_V1_DEPLOY_OK=true"
echo "policy=$DEST_POLICY"
echo "policy_owner=$(stat -c %U:%G "$DEST_POLICY")"
echo "policy_mode=$(stat -c %a "$DEST_POLICY")"
echo "semantic_read_scope=hands.read"
echo "semantic_transition_scope=hands.execute"
echo "generic_write_scope_required=false"

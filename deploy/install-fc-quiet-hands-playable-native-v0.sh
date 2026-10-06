#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
ADAPTER_SRC="$REPO_ROOT/integrations/quiet-hands/playable-operator-adapter.js"
PATCHER="$REPO_ROOT/deploy/patch-fc-quiet-hands-agent.py"

COMMON=/home/rdc-fc/src/quiet-hands-common/src
RESILIENCE=/home/rdc-fc/src/quiet-hands-resilience/src
SOCKET=/run/playable-universe/operator.sock

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP=/opt/fred-node/rollback/quiet-hands-playable-native-$STAMP

test "$(id -u)" -eq 0 || {
  echo "REFUSED: run as root"
  exit 1
}

test -f "$ADAPTER_SRC" || {
  echo "REFUSED: adapter source missing"
  exit 1
}
test -f "$PATCHER" || {
  echo "REFUSED: agent patch helper missing"
  exit 1
}

test -S "$SOCKET" || {
  echo "REFUSED: Playable operator socket missing"
  exit 1
}

for dir in "$COMMON" "$RESILIENCE"; do
  test -f "$dir/agent.js" || {
    echo "REFUSED: missing $dir/agent.js"
    exit 1
  }
done

mkdir -p "$BACKUP/common" "$BACKUP/resilience"
cp -a "$COMMON/agent.js" "$BACKUP/common/agent.js"
cp -a "$RESILIENCE/agent.js" "$BACKUP/resilience/agent.js"
if [ -f "$COMMON/playable-operator-adapter.js" ]; then
  cp -a "$COMMON/playable-operator-adapter.js" "$BACKUP/common/playable-operator-adapter.js"
fi
if [ -f "$RESILIENCE/playable-operator-adapter.js" ]; then
  cp -a "$RESILIENCE/playable-operator-adapter.js" "$BACKUP/resilience/playable-operator-adapter.js"
fi

echo "backup=$BACKUP"

install -o rdc-fc -g rdc-fc -m 0644 "$ADAPTER_SRC" "$COMMON/playable-operator-adapter.js"
install -o rdc-fc -g rdc-fc -m 0644 "$ADAPTER_SRC" "$RESILIENCE/playable-operator-adapter.js"

python3 "$PATCHER" "$COMMON/agent.js" "$RESILIENCE/agent.js"
chown rdc-fc:rdc-fc "$COMMON/agent.js" "$RESILIENCE/agent.js"
chmod 0644 "$COMMON/agent.js" "$RESILIENCE/agent.js"

for service in quiet-hands-agent-fc-common.service quiet-hands-agent-fc.service; do
  mkdir -p "/etc/systemd/system/${service}.d"
  cat >"/etc/systemd/system/${service}.d/60-playable-semantic-adapter.conf" <<DROPIN
[Service]
Environment=QUIET_HANDS_PLAYABLE_OPERATOR_SOCKET=$SOCKET
DROPIN
done

NODE=/home/rdc-fc/.local/node-v22.12.0-linux-x64/bin/node
test -x "$NODE"

"$NODE" --check "$COMMON/agent.js"
"$NODE" --check "$COMMON/playable-operator-adapter.js"
"$NODE" --check "$RESILIENCE/agent.js"
"$NODE" --check "$RESILIENCE/playable-operator-adapter.js"

systemctl daemon-reload
systemctl restart quiet-hands-agent-fc.service
systemctl restart quiet-hands-agent-fc-common.service

for service in quiet-hands-agent-fc.service quiet-hands-agent-fc-common.service; do
  for _ in $(seq 1 30); do
    if systemctl is-active --quiet "$service"; then break; fi
    sleep 0.25
  done
  systemctl is-active --quiet "$service" || {
    echo "FAILED: $service"
    exit 1
  }
done

# Verify the adapter itself can bind the actual rdc-fc OS identity to the
# Playable agent-steward role. This exercises the Unix socket directly,
# not the CLI wrapper and not database access.
runuser -u rdc-fc -- env   QUIET_HANDS_PLAYABLE_OPERATOR_SOCKET="$SOCKET"   "$NODE" --input-type=module <<'NODE'
import { PlayableOperatorAdapter } from '/home/rdc-fc/src/quiet-hands-common/src/playable-operator-adapter.js';
const adapter = new PlayableOperatorAdapter(process.env.QUIET_HANDS_PLAYABLE_OPERATOR_SOCKET);
await adapter.initialize();
const tools = await adapter.listTools();
const names = tools.map(t => t.name).sort();
for (const required of [
  'playable_candidate_inspect',
  'playable_evidence_report_unavailable',
  'playable_candidate_corroborate',
  'playable_candidate_dispute',
  'playable_promotion_propose_cap'
]) {
  if (!names.includes(required)) throw new Error('missing tool '+required);
}
const result = await adapter.callTool('playable_operator_status', {});
const parsed = JSON.parse(result.content[0].text);
if (!parsed.ok) throw new Error('operator status not ok');
if (parsed.result?.actor?.user !== 'rdc-fc') throw new Error('wrong peer user');
if (parsed.result?.actor?.role !== 'agent-steward') throw new Error('wrong peer role');
console.log('PLAYABLE_SEMANTIC_ADAPTER_SMOKE_OK=true');
console.log('semantic_tool_count='+names.length);
NODE

# Resilience edge is local and can be checked without disclosing its admin
# token. Confirm the current qwos:fc device advertisement contains the tools.
ADMIN=/home/rdc-fc/.quiet-hands/admin.token
if [ -f "$ADMIN" ]; then
  TOKEN=$(cat "$ADMIN")
  for _ in $(seq 1 30); do
    if curl -fsS -H "Authorization: Bearer $TOKEN"       http://127.0.0.1:18220/v0/devices/qwos%3Afc       -o /tmp/qh-fc-device.json; then
      if python3 - <<'PY'
import json
x=json.load(open('/tmp/qh-fc-device.json'))
names={t.get('name') for t in x.get('capabilities',[])}
need={
 'playable_candidate_inspect',
 'playable_evidence_report_unavailable',
 'playable_candidate_corroborate',
 'playable_candidate_dispute',
 'playable_promotion_propose_cap'
}
raise SystemExit(0 if need <= names else 1)
PY
      then
        break
      fi
    fi
    sleep 0.25
  done
  python3 - <<'PY'
import json
x=json.load(open('/tmp/qh-fc-device.json'))
names=sorted(t.get('name') for t in x.get('capabilities',[]) if t.get('name','').startswith('playable_'))
need={
 'playable_candidate_inspect',
 'playable_evidence_report_unavailable',
 'playable_candidate_corroborate',
 'playable_candidate_dispute',
 'playable_promotion_propose_cap'
}
assert need <= set(names)
print('LOCAL_EDGE_PLAYABLE_ADVERTISEMENT_OK=true')
print('advertised_playable_tools='+','.join(names))
PY
  rm -f /tmp/qh-fc-device.json
fi

echo "QUIET_HANDS_PLAYABLE_NATIVE_V0_DEPLOY_OK=true"
echo "common_agent=quiet-hands-agent-fc-common.service"
echo "resilience_agent=quiet-hands-agent-fc.service"
echo "operator_socket=$SOCKET"

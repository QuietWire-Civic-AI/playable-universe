import { PlayableOperatorAdapter } from './playable-operator-adapter.js';

const socket = process.env.QUIET_HANDS_PLAYABLE_OPERATOR_SOCKET
  ?? '/run/playable-universe/operator.sock';
const candidate = process.env.PLAYABLE_SMOKE_CANDIDATE
  ?? 'attest:eb5f3f11-7b29-4717-ad0e-54931dceb161';

const adapter = new PlayableOperatorAdapter(socket);
await adapter.initialize();

const tools = await adapter.listTools();
const names = tools.map(t => t.name).sort();

for (const required of [
  'playable_operator_status',
  'playable_operator_receipts',
  'playable_candidate_inspect',
  'playable_evidence_report_unavailable',
  'playable_candidate_corroborate',
  'playable_candidate_dispute',
  'playable_promotion_propose_cap'
]) {
  if (!names.includes(required)) {
    throw new Error('missing semantic tool: ' + required);
  }
}

const result = await adapter.callTool('playable_candidate_inspect', {
  candidate_id: candidate
});
const response = JSON.parse(result.content[0].text);
if (!response.ok) throw new Error('candidate inspect was not admitted');
if (response.result?.candidate_id !== candidate) {
  throw new Error('candidate identity mismatch');
}

console.log('PLAYABLE_NATIVE_ADAPTER_SMOKE_OK=true');
console.log('semantic_tool_count=' + names.length);
console.log('inspect_receipt=' + response.receipt.receipt_id);

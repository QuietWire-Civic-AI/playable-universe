import fs from 'node:fs';
import {
  validateOAuthExecutorPolicy,
  evaluateOAuthExecutorCall
} from '/home/rdc-fc/src/quiet-hands-common/src/oauth-executor-policy.js';

const policyPath = process.argv[2];
if (!policyPath) throw new Error('policy path required');

const policy = validateOAuthExecutorPolicy(
  JSON.parse(fs.readFileSync(policyPath, 'utf8'))
);

const principal = policy.principals.find(
  p => (p.nodes ?? []).includes('qwos:fc')
);
if (!principal) throw new Error('no FC principal');

const base = {
  authenticated: true,
  auth_type: 'oauth2',
  issuer: principal.issuer,
  subject: principal.subject,
  audience: principal.audience,
  client_id: principal.client_id_prefix + 'policy-smoke/client.json'
};

const full = {
  ...base,
  scopes: ['hands.read', 'hands.execute', 'hands.write']
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
  const decision = evaluateOAuthExecutorCall(
    policy, full, 'qwos:fc', name
  );
  if (!decision.ok) {
    throw new Error(name + ' unexpectedly denied: ' + JSON.stringify(decision));
  }
}

const readInspect = evaluateOAuthExecutorCall(
  policy,
  {...base, scopes:['hands.read']},
  'qwos:fc',
  'playable_candidate_inspect'
);
if (!readInspect.ok) {
  throw new Error('read-only candidate inspection should be admitted');
}

const executeNoWrite = evaluateOAuthExecutorCall(
  policy,
  {...base, scopes:['hands.execute']},
  'qwos:fc',
  'playable_candidate_corroborate'
);
if (!executeNoWrite.ok) {
  throw new Error('semantic transition should not require hands.write');
}

const noExecute = evaluateOAuthExecutorCall(
  policy,
  {...base, scopes:['hands.read','hands.write']},
  'qwos:fc',
  'playable_candidate_corroborate'
);
if (noExecute.ok || noExecute.code !== 'insufficient_scope') {
  throw new Error('bounded transition should require hands.execute');
}

console.log('OAUTH_SEMANTIC_SCOPE_PREFLIGHT_OK=true');
console.log('fc_principal_count=' + policy.principals.filter(
  p => (p.nodes ?? []).includes('qwos:fc')
).length);

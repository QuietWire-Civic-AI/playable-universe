import net from 'node:net';
import crypto from 'node:crypto';

const DEFAULT_SOCKET = '/run/playable-universe/operator.sock';

function textResult(value) {
  return {
    content: [{
      type: 'text',
      text: JSON.stringify(value, null, 2)
    }]
  };
}

function cleanString(value, name) {
  if (typeof value !== 'string' || !value.trim()) {
    throw new Error(`${name} is required`);
  }
  return value.trim();
}

function cleanRefs(value) {
  if (value === undefined) return [];
  if (!Array.isArray(value)) throw new Error('source_refs must be an array');
  return value.map((v) => cleanString(v, 'source_ref'));
}

export class PlayableOperatorAdapter {
  constructor(socketPath = DEFAULT_SOCKET) {
    this.socketPath = socketPath || DEFAULT_SOCKET;
  }

  async initialize() {
    const response = await this.#request('operator.status', null, {});
    if (!response?.ok) {
      throw new Error(`Playable operator status refused: ${response?.error ?? 'unknown error'}`);
    }
  }

  async listTools() {
    return [
      {
        name: 'playable_operator_status',
        title: 'Playable Universe Operator Status',
        description: 'Inspect the local Playable Universe steward role, policy version, interlock state, and admitted semantic operations.',
        inputSchema: { type: 'object', properties: {}, additionalProperties: false },
        annotations: {
          readOnlyHint: true,
          destructiveHint: false,
          idempotentHint: true,
          openWorldHint: false
        }
      },
      {
        name: 'playable_operator_receipts',
        title: 'Playable Universe Operator Receipts',
        description: 'Read recent bounded Playable Universe operator receipts.',
        inputSchema: {
          type: 'object',
          properties: {
            limit: { type: 'integer', minimum: 1, maximum: 100, default: 20 }
          },
          additionalProperties: false
        },
        annotations: {
          readOnlyHint: true,
          destructiveHint: false,
          idempotentHint: true,
          openWorldHint: false
        }
      },
      {
        name: 'playable_candidate_inspect',
        title: 'Inspect Playable Candidate',
        description: 'Inspect one Playable Universe attestation candidate, its immutable packet, evidence state, media, and lifecycle.',
        inputSchema: {
          type: 'object',
          required: ['candidate_id'],
          properties: {
            candidate_id: { type: 'string', pattern: '^attest:' }
          },
          additionalProperties: false
        },
        annotations: {
          readOnlyHint: true,
          destructiveHint: false,
          idempotentHint: true,
          openWorldHint: false
        }
      },
      {
        name: 'playable_evidence_report_unavailable',
        title: 'Report Bound Evidence Unavailable',
        description: 'Append the fact that source bytes for an evidence digest already bound to a candidate are no longer available. The original candidate packet is not rewritten.',
        inputSchema: {
          type: 'object',
          required: ['candidate_id', 'source_sha256', 'note'],
          properties: {
            candidate_id: { type: 'string', pattern: '^attest:' },
            source_sha256: { type: 'string', pattern: '^[0-9a-fA-F]{64}$' },
            note: { type: 'string', minLength: 1, maxLength: 4000 }
          },
          additionalProperties: false
        },
        annotations: {
          readOnlyHint: false,
          destructiveHint: false,
          idempotentHint: true,
          openWorldHint: false
        }
      },
      {
        name: 'playable_candidate_corroborate',
        title: 'Corroborate Playable Candidate',
        description: 'Append a corroboration record with explicit source references to an existing candidate.',
        inputSchema: {
          type: 'object',
          required: ['candidate_id', 'note', 'source_refs'],
          properties: {
            candidate_id: { type: 'string', pattern: '^attest:' },
            note: { type: 'string', minLength: 1, maxLength: 4000 },
            source_refs: {
              type: 'array',
              minItems: 1,
              maxItems: 20,
              items: { type: 'string', minLength: 1, maxLength: 600 }
            }
          },
          additionalProperties: false
        },
        annotations: {
          readOnlyHint: false,
          destructiveHint: false,
          idempotentHint: false,
          openWorldHint: false
        }
      },
      {
        name: 'playable_candidate_dispute',
        title: 'Dispute Playable Candidate',
        description: 'Append a dispute record to an existing candidate without rewriting the original claim.',
        inputSchema: {
          type: 'object',
          required: ['candidate_id', 'note'],
          properties: {
            candidate_id: { type: 'string', pattern: '^attest:' },
            note: { type: 'string', minLength: 1, maxLength: 4000 },
            source_refs: {
              type: 'array',
              maxItems: 20,
              items: { type: 'string', minLength: 1, maxLength: 600 }
            }
          },
          additionalProperties: false
        },
        annotations: {
          readOnlyHint: false,
          destructiveHint: false,
          idempotentHint: false,
          openWorldHint: false
        }
      },
      {
        name: 'playable_promotion_propose_cap',
        title: 'Propose Candidate for CAP Promotion',
        description: 'Append a proposal-only promotion event for an existing candidate. This does not mutate CAP or Canon.',
        inputSchema: {
          type: 'object',
          required: ['candidate_id', 'note'],
          properties: {
            candidate_id: { type: 'string', pattern: '^attest:' },
            note: { type: 'string', minLength: 1, maxLength: 4000 },
            source_refs: {
              type: 'array',
              maxItems: 20,
              items: { type: 'string', minLength: 1, maxLength: 600 }
            }
          },
          additionalProperties: false
        },
        annotations: {
          readOnlyHint: false,
          destructiveHint: false,
          idempotentHint: false,
          openWorldHint: false
        }
      }
    ];
  }

  async callTool(name, args = {}, metadata = {}) {
    let operation;
    let target = null;
    let payload = {};

    switch (name) {
      case 'playable_operator_status':
        operation = 'operator.status';
        break;
      case 'playable_operator_receipts':
        operation = 'operator.receipts';
        payload = { limit: Number(args.limit ?? 20) };
        break;
      case 'playable_candidate_inspect':
        operation = 'candidate.inspect';
        target = cleanString(args.candidate_id, 'candidate_id');
        break;
      case 'playable_evidence_report_unavailable':
        operation = 'evidence.report_unavailable';
        target = cleanString(args.candidate_id, 'candidate_id');
        payload = {
          source_sha256: cleanString(args.source_sha256, 'source_sha256').toLowerCase(),
          note: cleanString(args.note, 'note')
        };
        break;
      case 'playable_candidate_corroborate':
        operation = 'candidate.corroborate';
        target = cleanString(args.candidate_id, 'candidate_id');
        payload = {
          note: cleanString(args.note, 'note'),
          source_refs: cleanRefs(args.source_refs)
        };
        break;
      case 'playable_candidate_dispute':
        operation = 'candidate.dispute';
        target = cleanString(args.candidate_id, 'candidate_id');
        payload = {
          note: cleanString(args.note, 'note'),
          source_refs: cleanRefs(args.source_refs)
        };
        break;
      case 'playable_promotion_propose_cap':
        operation = 'promotion.propose_cap';
        target = cleanString(args.candidate_id, 'candidate_id');
        payload = {
          note: cleanString(args.note, 'note'),
          source_refs: cleanRefs(args.source_refs)
        };
        break;
      default:
        throw new Error(`Playable operator adapter does not own tool ${name}`);
    }

    const response = await this.#request(operation, target, payload, metadata);
    if (!response?.ok) {
      const receipt = response?.receipt?.receipt_id
        ? ` receipt=${response.receipt.receipt_id}`
        : '';
      throw new Error(
        `Playable operator refused ${operation}: ${response?.error ?? 'unknown error'}${receipt}`
      );
    }
    return textResult(response);
  }

  async close() {}

  async #request(operation, target, payload, metadata = {}) {
    const request = {
      schema: 'playable.operator-request.v0',
      request_id: `qh-opreq:${crypto.randomUUID()}`,
      operation,
      target,
      payload
    };

    // Quiet Hands metadata is intentionally not used as the authority identity.
    // The operator plane binds the actual local caller with SO_PEERCRED.
    void metadata;

    return await new Promise((resolve, reject) => {
      const socket = net.createConnection({ path: this.socketPath });
      let buffer = '';
      let settled = false;

      const finish = (fn, value) => {
        if (settled) return;
        settled = true;
        try { socket.destroy(); } catch {}
        fn(value);
      };

      socket.setTimeout(12000);
      socket.setEncoding('utf8');

      socket.on('connect', () => {
        socket.write(JSON.stringify(request) + '\n');
      });
      socket.on('data', (chunk) => {
        buffer += chunk;
        const newline = buffer.indexOf('\n');
        if (newline < 0) return;
        try {
          finish(resolve, JSON.parse(buffer.slice(0, newline)));
        } catch (error) {
          finish(reject, error);
        }
      });
      socket.on('timeout', () => finish(reject, new Error('Playable operator socket timed out')));
      socket.on('error', (error) => finish(reject, error));
      socket.on('end', () => {
        if (!settled) finish(reject, new Error('Playable operator socket closed before response'));
      });
    });
  }
}

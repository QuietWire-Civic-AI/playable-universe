# Playable Attestation Intake v0

## Purpose

Provide the smallest public write boundary for phone-created Playable Universe attestations.

This service receives **candidate attestations**, not Canon writes.

## API

### POST `/v0/attestations`

Accepts `playable.mobile-attestation.v0`.

Returns:

```json
{
  "schema": "playable.attestation-receipt.v0",
  "candidate_id": "attest:...",
  "status": "candidate",
  "received_at": "...",
  "packet_sha256": "...",
  "receipt_sha256": "...",
  "public_candidate": false
}
```

### GET `/v0/attestations/public?limit=50`

Returns public candidates only.

Every item remains explicitly candidate/unverified unless a later promotion state says otherwise.

### GET `/v0/attestations/{candidate_id}`

Returns a public candidate if it was deliberately shared.

Receipt-only candidates are not publicly retrievable.

## v0 limits

- JSON only;
- 32 KiB body;
- 2,000-character claim;
- hashes, not raw media uploads;
- 30 submissions/hour/source address;
- location public path accepts only none/coarse;
- no arbitrary HTML;
- no automatic CAP/Canon promotion.

## Storage

SQLite under FC local custody.

The stored record includes:

- exact canonical packet JSON;
- packet SHA-256;
- server receipt;
- candidate status;
- sharing class.

## Non-goals

v0 is not:

- identity proof;
- moderation infrastructure;
- a social network;
- a public image host;
- a replacement for CAP;
- a claim that submitted content is true.

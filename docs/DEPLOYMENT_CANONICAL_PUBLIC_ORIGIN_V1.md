# Canonical Public Origin v1 — Activation Receipt

Date: 2026-10-06  
Status: **LIVE / VERIFIED**

## Canonical origin

`https://playable.quietwire.ai/`

Current hosting node:

`qwos:fc`

Compatibility surface:

`https://fc.quietwire.ai/playable/`

## Activation

Pinned deployment head:

`e4cc0fae8816206e667baf25fa4e5e250cc4eca8`

Successful activation backup:

`/opt/fred-node/rollback/playable-public-origin-20261006T201551Z`

Deployment marker:

`PLAYABLE_PUBLIC_ORIGIN_V1_3_DEPLOY_OK=true`

## Certificate

The canonical hostname now presents a certificate whose subject and SAN name:

`playable.quietwire.ai`

Observed validity:

- not before: `2026-10-06T19:01:51Z`
- not after: `2027-01-04T19:01:50Z`

## Independent verification

Verified from:

- `qwos:fc`
- `qwos:teddy`
- `qwos:lumina`

All three independently confirmed:

- canonical TLS certificate;
- root Playable page;
- `/attest/`;
- `/play/`;
- `/api/healthz`;
- `/api/v0/scenes`;
- old FC compatibility route.

Health endpoint returned:

```json
{
  "schema": "playable.attestation-intake-health.v1",
  "service": "playable-attestation-intake",
  "status": "ok",
  "media": "pending-review"
}
```

World API returned three scenes at verification time.

## Identity rule

**Playable Universe is `playable.quietwire.ai`. FC is infrastructure.**

Generated scene/media links use:

`PLAYABLE_PUBLIC_ORIGIN=https://playable.quietwire.ai`

Historical receipts that name the old FC path remain historically true and are not rewritten.

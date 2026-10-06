---
title: FC v0 Deployment Receipt
type: deployment-receipt
status: active
date: 2026-10-05
node: qwos:fc
public_url: https://fc.quietwire.ai/playable/
---

# Playable Universe — FC v0 Deployment Receipt

## Outcome

The first public Playable Universe surface is live at:

`https://fc.quietwire.ai/playable/`

Deployment completed successfully on FC / `fred-cohen-node`.

The operator-side installer reported:

```text
target=/opt/fred-node/runtime/cap/frontend/dist/playable
nginx_reload_required=false
PLAYABLE_UNIVERSE_FC_DEPLOY_OK=true
url=https://fc.quietwire.ai/playable/
```

## Independent verification

A separate QuietWire node (`qwos:lumina`) independently fetched:

- `/playable/` -> HTTP 200
- `/playable/styles.css` -> HTTP 200
- `/playable/app.js` -> HTTP 200
- `/playable/data/tiles.json` -> HTTP 200

The public HTML contained the expected Valley phrase:

> A future earns detail by showing its route.

The public tile JSON parsed successfully.

## Deployment integrity

FC compared the staged and deployed copies of:

- `index.html`
- `styles.css`
- `app.js`
- `data/tiles.json`
- `.playable-universe-v0`

All SHA-256 digests matched exactly.

## Governance boundary

The deployment:

- did not modify nginx configuration;
- did not reload nginx;
- did not restart CAP;
- did not alter CAP core/gateway;
- added only the marked static subtree:
  `/opt/fred-node/runtime/cap/frontend/dist/playable/`.

The temporary loopback bridge used to transfer the stage across FC's `PrivateTmp=yes` boundary was terminated after successful deployment and independently verified closed.

## Source lineage

The repository carries the complete 21-file 2025 Playable Universe source corpus from:

`QuietWire-Civic-AI/Quietwire/04_Infrastructure/Playable_Universe/`

source commit:

`a0b31be78d9cd5420276b09c2bff6af3bd2c1d27`

The 2026 Valley / reachability layer is maintained separately rather than rewriting the 2025 source.

## Meaning

This receipt proves the first static public rendering is deployed and independently reachable.

It does **not** imply that:

- a rendered tile is itself an attestation;
- a future projection is a prediction;
- public rendering expands rights to restricted source material;
- the v0 interface is the final Playable Universe architecture.

Rendering != attestation.

Projection != prediction.

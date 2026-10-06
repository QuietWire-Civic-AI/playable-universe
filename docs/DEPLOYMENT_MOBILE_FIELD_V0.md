---
title: Playable Mobile v0 Activation Receipt
type: deployment-receipt
status: verified
date: 2026-10-06
node: qwos:fc
public_surfaces:
  - https://fc.quietwire.ai/playable/attest/
  - https://fc.quietwire.ai/playable/play/
  - https://fc.quietwire.ai/playable/api/healthz
---

# Playable Universe — Mobile / Field v0 Activation Receipt

## Result

**ACTIVE / VERIFIED**

The mobile attestation intake and 2D Walk the Valley client are live on FC.

Pinned deployment source:

`b720c9c17672db6451ac8e3c4c287675cae71f05`

Human-side installer output reported:

```text
backup=/opt/fred-node/rollback/playable-universe-mobile-20261006T023301Z
nginx: configuration file /etc/nginx/nginx.conf test is successful
PLAYABLE_MOBILE_V0_DEPLOY_OK=true
attest=https://fc.quietwire.ai/playable/attest/
play=https://fc.quietwire.ai/playable/play/
api=https://fc.quietwire.ai/playable/api/healthz
```

A transient first health probe returned connection refused while the systemd service was starting. The installer continued its bounded startup wait, the service became healthy, and the final installation health checks passed.

## Independent verification

From FC:

- `playable-universe-intake.service` = active / enabled
- loopback listener = `127.0.0.1:18270`
- public Attest page = HTTP 200
- public Walk page = HTTP 200
- public API health = HTTP 200

From `qwos:lumina`:

- `/playable/attest/` = HTTP 200
- `/playable/play/` = HTTP 200
- `/playable/api/healthz` = HTTP 200
- expected `Make an Attest` page marker found
- expected `Walk the Valley` page marker found
- health JSON parsed successfully

Public candidate feed at closeout contained zero candidates, so no synthetic test object was left in the public field stream.

## Network boundary

The attestation intake binds only to:

`127.0.0.1:18270`

nginx exposes only the bounded:

`/playable/api/`

reverse-proxy path.

## Semantic boundary

A phone-created object begins as a **candidate attestation**.

Receipt != verification.

Candidate != Canon.

Photo hashing in browser v0 binds evidence bytes without uploading the photo itself.

Location is off by default and the public browser path uses only explicitly requested coarse location.

## Rollback

Installer backup:

`/opt/fred-node/rollback/playable-universe-mobile-20261006T023301Z`

## Next field action

Create the first real phone attestation from:

`https://fc.quietwire.ai/playable/attest/`

and, if deliberately public, inspect it as a live marker in:

`https://fc.quietwire.ai/playable/play/`

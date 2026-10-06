---
title: Evidence Custody Lifecycle v2 Activation Receipt
type: deployment-receipt
status: verified
date: 2026-10-06
node: qwos:fc
---

# Playable Universe — Evidence Custody / Lifecycle v2 Receipt

## Result

**ACTIVE / VERIFIED**

Pinned deployment head:

`05f0be5a9bef656107d9b969be2a222ec8f99cfd`

Human activation backup:

`/opt/fred-node/rollback/playable-universe-evidence-custody-20261006T031904Z`

## Live service verification

On FC:

- `playable-universe-intake.service` = active
- service enabled at boot
- private custody directory:
  `/var/lib/playable-universe/private-media`
- private custody directory mode:
  `0700 quietwire:quietwire`
- database tables include:
  - `candidates`
  - `candidate_events`
  - `media`
  - `private_media`

Public surfaces returned HTTP 200:

- `/playable/attest/`
- `/playable/play/`
- `/playable/api/healthz`
- `/playable/api/v0/scenes/present-room/events`

Independent external verification from `qwos:lumina` also returned HTTP 200 and found the new custody UI markers.

## First evidence-lifecycle event

Candidate:

`attest:eb5f3f11-7b29-4717-ad0e-54931dceb161`

Original packet remains unchanged and binds:

- JPEG bytes: `4724109`
- MIME: `image/jpeg`
- source SHA-256:
  `c791da1b2e857cbec06ff93a3ad437b6b8ca28dd713b5e8e70e884ce991feba6`
- original custody at capture:
  `device-local`

Lifecycle now contains:

1. `candidate.received`
   - event:
     `cevent:a6317cda-c529-4301-afdb-aa89080618e7`
   - recorded:
     `2026-10-06T02:53:17.401642Z`

2. `evidence.source_unavailable_reported`
   - event:
     `cevent:ec2d1f9e-e846-4179-92c7-1550e9d794b3`
   - recorded:
     `2026-10-06T03:22:40.574856Z`
   - actor kind:
     `local-operator`

Public evidence summary now reports:

- bound photo count: `1`
- privately retained originals: `0`
- public derivatives: `0`
- source-unavailable reports: `1`

The Playable Present World API exposes two events for this candidate:

- `attestation.candidate_received`
- `evidence.source_unavailable_reported`

## Meaning

The first phone evidence loss is represented as history rather than rewritten state.

**Provenance != custody.**

The system can retain a cryptographically exact reference to evidence whose source bytes are no longer possessed.

Future captures can instead transition through:

`device-local -> private exact custody -> optional reviewed public derivative`

while preserving each state transition as an append-only event.

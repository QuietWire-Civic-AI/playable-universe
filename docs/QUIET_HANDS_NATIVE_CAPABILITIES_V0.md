# Quiet Hands Native Playable Capabilities v0

## Goal

Replace the transitional pattern:

`Quiet Hands start_process -> playable-ops CLI -> operator socket`

with first-class FC agent capabilities:

- `playable_operator_status`
- `playable_operator_receipts`
- `playable_candidate_inspect`
- `playable_evidence_report_unavailable`
- `playable_candidate_corroborate`
- `playable_candidate_dispute`
- `playable_promotion_propose_cap`

## Boundary

Quiet Hands does not decide whether these operations are authorized.

The FC agent adapter converts a named Quiet Hands tool invocation into a Playable operator request over:

`/run/playable-universe/operator.sock`

The operator plane binds the local caller with `SO_PEERCRED`, applies its own root-owned role policy and interlock, validates the domain transition, performs it if admitted, and produces the authoritative domain receipt.

Thus:

```
Quiet Hands
  = discovery + carriage + expiry/replay + transport receipt

Playable operator plane
  = semantic authority decision + domain invariant + domain receipt
```

## Dual FC agents

FC intentionally has two Quiet Hands paths:

- `quiet-hands-agent-fc-common.service` -> public `hands.quietwire.ai`
- `quiet-hands-agent-fc.service` -> local/resilience edge

Both receive the same additive Playable adapter so capability availability does not depend on which carrier is healthy.

## OS authority

Both services continue to execute as:

`rdc-fc`

The adapter receives no database credential, sudo, `quietwire` shell, or direct private-media access.

The only new reach is the already-admitted `playable-ops` Unix socket group membership established by the operator-plane deployment.

## OAuth/public exposure

Advertising a tool from the node does not by itself expose it to every OAuth principal.

The public Quiet Hands MCP executor policy remains an additional carrier-side admission layer.

That policy should be updated explicitly for principals that are intended to see the new `playable_*` tools.

The Playable operator plane remains the final local relying authority even after carrier policy admits a call.

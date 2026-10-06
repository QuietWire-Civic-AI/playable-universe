# FC OAuth Carrier Policy for Native Playable Tools v1

## Decision

Once FC advertises the native `playable_*` capabilities, the public Quiet Hands OAuth executor policy must explicitly admit them for the intended ChatGPT principal.

This is a **carrier-layer** decision.

It does not replace or duplicate Playable Universe domain authority.

## Scope mapping

Read-only semantic tools require:

`hands.read`

- `playable_operator_status`
- `playable_operator_receipts`
- `playable_candidate_inspect`

Bounded semantic state transitions require:

`hands.execute`

- `playable_evidence_report_unavailable`
- `playable_candidate_corroborate`
- `playable_candidate_dispute`
- `playable_promotion_propose_cap`

They deliberately do **not** require `hands.write`.

## Why not hands.write?

`hands.write` describes broad carrier/executor file mutation.

A Playable semantic transition does not grant the caller arbitrary filesystem or database write authority.

The Playable operator plane:

- binds the local caller;
- resolves the standing role;
- evaluates the root-owned domain policy;
- evaluates the domain interlock;
- validates the candidate/media state transition;
- performs the bounded write;
- issues the domain receipt.

Therefore the carrier needs permission to **execute the named semantic operation**, not permission to generically write the node.

This is the practical meaning of:

> Broaden semantic authority before broadening operating-system privilege.

## Root-owned carrier policy

The legacy FC OAuth executor policy lived at:

`/home/rdc-fc/.quiet-hands-common/oauth-executor-policy.v0.json`

The common agent already mounted that path read-only inside its service sandbox, but the durable carrier policy should not be owned by the executor identity.

v1 copies the existing local principal bindings into:

`/etc/quiet-hands/oauth-executor-policy.fc.v1.json`

with:

- owner: `root`
- group: `rdc-fc`
- mode: `0640`

The installer derives the exact issuer/subject/audience/client binding from the existing local policy. Those account identifiers are not embedded in the public repository.

## Two gates, different jobs

```
OAuth carrier policy
  asks:
  may this authenticated remote principal invoke this named tool on FC?
        |
        v
FC Quiet Hands agent
  carries semantic request as actual local rdc-fc process
        |
        v
Playable operator plane
  asks:
  may the locally bound agent-steward role perform this exact domain transition
  under the current local interlock and object state?
```

Both gates matter, but they are not the same authority.

## Long-term direction

The current Chris/ChatGPT principal still has generic engineering tools such as `start_process`, `write_file`, and `edit_block` on FC.

That is useful while the system is being built.

The stronger future proof is a **steward principal/profile** that can execute useful semantic domain actions while generic shell/file mutation is denied.

Native Playable tools make that possible without reducing agent usefulness.

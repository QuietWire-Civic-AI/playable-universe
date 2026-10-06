# Bounded Operator Plane v0

## Decision

Playable Universe owns a node-local semantic operator plane.

Remote Desktop Commander / Quiet Hands may carry requests to it, but the transport identity no longer needs database ownership, `sudo -u quietwire`, or generic filesystem mutation merely to perform ordinary Playable Universe stewardship.

The authority lives **inside the Playable Universe domain**, under a root-owned local policy.

## Why

The first evidence-lifecycle closure exposed the wrong boundary.

A domain action:

> append the already-observed fact that the source photo is unavailable

was semantically safe, append-only, and fully understood by the Playable Universe service.

But because `rdc-fc` lacked write access to the `quietwire` SQLite store, the operation fell back to:

```
agent -> Chris -> sudo -u quietwire -> maintenance script
```

That made Chris a transport adapter rather than a judgment boundary.

The answer is **not** to give RDC generic `quietwire` or root authority.

The answer is to admit the semantic verb where the semantic state lives.

## Shape

```
Companion / Quiet Hands / RDC
          |
          | local carriage as rdc-fc
          v
/run/playable-universe/operator.sock
          |
          | SO_PEERCRED binds actual local caller
          v
Playable Universe operator plane
          |
          +-- root-owned policy
          +-- root-owned interlock state
          +-- exact semantic operation
          +-- domain invariants
          +-- append-only lifecycle effects
          +-- durable operator receipt
          |
          v
Playable Universe state owned by quietwire
```

## What is loosened

`rdc-fc` receives a standing local **agent-steward** role for this domain.

It may perform, without a fresh human copy/paste approval each time:

- `operator.status`
- `operator.receipts`
- `interlock.inspect`
- `candidate.inspect`
- `evidence.report_unavailable`
- `candidate.corroborate`
- `candidate.dispute`
- `promotion.propose_cap`

This is intentionally a real authority grant.

It is not described as mere technical capability.

## What is not loosened

The agent-steward role does **not** receive:

- shell as `quietwire`;
- database credentials or direct SQLite mutation;
- root;
- arbitrary file read/write under private custody;
- nginx/systemd/network/package authority;
- direct CAP/Canon promotion;
- candidate deletion;
- claim rewriting;
- approved-media withdrawal;
- rights/policy editing;
- interlock recovery;
- public-media approval/rejection in v0.

The local `quietwire` operator role additionally receives:

- `media.review.approve`
- `media.review.reject`

The agent-steward can propose CAP promotion; it cannot execute it.

## Why media approval is not yet delegated to rdc-fc

This is not intended as permanent human ceremony.

Current FC agent carriage does not yet provide a reliable, provenance-bound visual review primitive for the pending derivative.

Granting approval before the reviewing agent can actually inspect the exact bytes would be fake autonomy: authority without the perception needed to exercise it responsibly.

Once the agent can inspect the exact derivative digest through a suitable vision/evidence adapter, `media.review.approve` is a candidate for the steward role.

## Caller binding

The operator daemon listens on a Unix-domain socket.

It uses Linux `SO_PEERCRED` to determine:

- caller PID;
- UID;
- GID;
- operating-system username.

Caller identity is **not** accepted from JSON.

The socket is mode `0660`, group `playable-ops`.

The local execution/carriage services receive that group as a systemd supplementary group.

## Policy

Policy is root-owned:

`/etc/playable-universe/operator-policy.json`

The service can read it but cannot rewrite its own authority.

The initial principal bindings are:

```
rdc-fc    -> agent-steward
quietwire -> operator
```

## Interlock

Interlock state is root-owned:

`/etc/playable-universe/operator-interlock.json`

States:

- `NORMAL`
- `CONSTRAINED`

In `CONSTRAINED`, only the policy's explicit evidence/inspection subset remains admitted.

The operator daemon cannot clear or rewrite the interlock.

This is deliberately external to the acting intelligence.

## Receipts

Every valid operator request produces a durable receipt, including refusals.

Receipt fields include:

- request ID;
- actor UID / username;
- actor role;
- policy version;
- interlock state;
- operation;
- target;
- request SHA-256;
- decision;
- bounded result summary;
- time.

The receipt is evidence of the policy decision.

It is not the source of authority.

## State-change model

Candidate mutations remain append-oriented.

Examples:

```
candidate.corroboration_recorded
candidate.dispute_recorded
evidence.source_unavailable_reported
promotion.cap_proposed
```

The original candidate packet is not rewritten.

## A4 / stewardship interpretation

This is the beginning of a concrete Quiet Hands **A4 steward** pattern.

A steward is permitted to make a bounded class of recurring decisions inside a domain without repeatedly asking a human to carry each low-level action.

The role remains bounded by:

- semantic verbs;
- local policy;
- target identity;
- domain validation;
- interlock;
- receipts;
- explicit exclusions.

Higher attention is useful only if standing authority is represented honestly and externally enforced.

## Future conversion to first-class Quiet Hands capabilities

The initial carrier can invoke the local `playable-ops` client through the existing process path.

That is a transitional adapter.

The desired next integration is for Quiet Hands to advertise native semantic capabilities such as:

```
playable.candidate.inspect
playable.evidence.report-unavailable
playable.candidate.corroborate
playable.candidate.dispute
playable.promotion.propose-cap
```

Those capabilities should route to the same operator socket.

Do not create a second authority implementation inside Quiet Hands.

Quiet Hands discovers/carries the capability.

Playable Universe remains the relying execution point that decides whether the operation is admitted.

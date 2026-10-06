# Authority Placement — RDC Is Carriage, Domain Policy Is Authority

## Working decision

The FC Playable Universe field work confirms that the existing RDC-centered operational boundary is too restrictive **when interpreted as the place where ordinary domain authority must live**.

The correction is not:

> give the companion more shell privilege.

The correction is:

> move recurring authority into the smallest service that understands the semantic operation, and let RDC/Quiet Hands carry requests to that service.

## Failure shape

Over-centralized authority:

```
semantic operation
  -> companion
  -> remote transport
  -> generic OS identity
  -> human approval
  -> sudo / shell
  -> domain database
```

This makes transport and human attention unnecessarily central.

Preferred shape:

```
human establishes standing domain charter
          |
          v
root-owned local domain policy
          |
agent request -> transport -> semantic capability
                             |
                             v
                     domain relying point
                     admit / deny / receipt
```

## What "move authority down stack" means

It means a local service is allowed to answer:

> may this exact semantic transition occur?

without escalating merely because the caller does not own the service's database.

The service can make that decision because:

- it understands the object;
- it knows legal state transitions;
- it can enforce invariants;
- it can bind the local caller;
- it can see local revocation/interlock state;
- it can issue a receipt.

## What remains above the domain

Humans and organizational governance still decide:

- which principals receive standing roles;
- what those roles contain;
- where the consequence threshold lies;
- what requires a new grant;
- what requires legal/organizational judgment;
- what clears an interlock;
- what changes the policy itself.

That is meaningful human control.

## Relationship to Quiet Hands doctrine

This implements rather than contradicts:

- transport is not authority;
- privilege is not authority;
- reasoning is not authority;
- human attention is not containment;
- higher attention does not silently grant broader privilege.

A standing semantic grant is explicit authority.

It should be represented as such.

## Reusable fleet pattern

The Playable Universe operator socket should be treated as the first reference instance of a general pattern:

```
domain service
  + semantic operations
  + local principal/role policy
  + external interlock
  + receipts
  + narrow carriage adapter
```

Examples elsewhere might eventually include:

- QuietMemory promotion operations;
- QuietRoom closure operations;
- QuietLibrary custody transitions;
- property-estate workflow actions;
- Audio/DMX scene operations;
- carrier lease operations.

The common mistake to avoid is putting all of those domain authorities into one giant generic RDC/root permission model.

## Rule

**Broaden semantic authority before broadening operating-system privilege.**

If an agent needs to do more useful work, first ask whether the missing permission can be expressed as a domain verb with local validation.

Only widen shell/system privilege when the work is genuinely system administration and cannot be represented safely at a more meaningful layer.

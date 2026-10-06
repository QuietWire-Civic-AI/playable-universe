# Evidence Custody and Lifecycle v1

## Why this exists

The first live public phone attestation exposed an important distinction.

The browser successfully:

- captured a photograph;
- hashed the exact bytes locally;
- bound the SHA-256, MIME type and byte count into the attestation packet;
- submitted the candidate and received a durable receipt.

But the browser camera flow did **not** create a durable gallery copy, and v0 deliberately did not upload the image bytes.

Therefore the attestation retained strong evidence **provenance** while losing evidence **custody**.

That is not the same thing as the evidence never having existed.

## Principle

**Do not rewrite old evidence state to match later custody state.**

Instead append lifecycle events.

Example:

```
T0  photo captured on device
T1  SHA-256 bound into candidate
T2  candidate received
T3  browser/device no longer has source bytes
T4  human reports source unavailable
```

The T1 packet remains immutable.

T4 becomes a new event.

## Lifecycle event types

v1 includes:

- `candidate.received`
- `evidence.private_custody_received`
- `evidence.source_unavailable_reported`
- `evidence.public_derivative_pending`
- `evidence.public_derivative_approved`
- `evidence.public_derivative_rejected`

These events can be surfaced as Playable Present `WorldEvent` objects.

## New phone workflow

After a photograph is captured or selected, the field client now warns that browser camera capture is not guaranteed to create a gallery copy.

The person gets three distinct choices:

### Save a copy on the phone

The browser offers the exact selected bytes as a download.

This normally lands in Downloads/Files rather than necessarily the camera gallery.

### Share / save through the phone

Where the Web Share API supports file sharing, the exact selected file can be handed to the phone share sheet for a user-selected save/share destination.

### Preserve exact original privately on FC

Recommended for field attestations.

After the attestation receipt exists:

1. the browser re-hashes the selected file;
2. the upload carries the already sealed SHA-256;
3. FC confirms:
   - candidate exists;
   - digest is bound in that candidate;
   - byte count matches when sealed;
   - MIME type matches when sealed;
   - actual received bytes hash to the sealed digest;
4. FC stores the exact original outside the public web tree;
5. file permissions are private to the governed service/operator context;
6. an append-only custody event is created.

The original attestation packet still says the photo was `device-local` at packet creation time.

The later custody event says that FC subsequently received the exact same bytes.

## Public publication remains separate

Private retention does not make a photograph public.

For a public candidate, a later explicit publication request can create a metadata-stripped JPEG derivative from the privately retained original.

That derivative enters `pending`.

A local review action must approve it before the public media API will serve it.

## Storage separation

```
/var/lib/playable-universe/private-media/
    exact originals; never exposed by public media route

/var/lib/playable-universe/media/pending/
    generated public-safe derivatives awaiting review

/var/lib/playable-universe/media/approved/
    reviewed derivatives exposed by public media route
```

## Playable Universe implication

Evidence is not a static attachment.

It has a history.

A future Playable Past reconstruction should be able to show not only:

> this claim referenced photograph SHA X

but also:

> at this point in time the photograph was device-local;
> later its source bytes were reported unavailable

or:

> later the exact source bytes entered governed private custody;
> still later a public derivative was approved.

The evidence lifecycle itself is part of the world.

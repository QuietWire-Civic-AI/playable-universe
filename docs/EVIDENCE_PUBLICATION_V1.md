# Evidence Publication v1

## Problem

The phone attestation v0 deliberately bound photographs by SHA-256 without uploading the image bytes.

That was the correct first boundary, but it meant the Playable Universe could prove that a claim referenced a particular photo without being able to render the photograph.

## v1 publication flow

A public candidate containing a `photo_hash` may later publish a photograph only through a digest-verifying continuation:

```
sealed candidate packet
    |
    | contains photo SHA-256 / MIME / byte count
    v
user explicitly chooses matching original photo
    |
    v
browser uploads that file
    |
    v
FC verifies:
  - candidate exists
  - candidate is public
  - photo digest was already sealed into the packet
  - upload byte count matches when sealed
  - upload MIME matches when sealed
  - actual upload SHA-256 exactly matches
    |
    v
temporary original used to create derivative
    |
    +-- original upload deleted by intake service
    |
    v
metadata-stripped bounded JPEG derivative
    |
    v
pending local review
    |
    +-- reject -> delete
    |
    +-- approve -> public media object
                         |
                         +-> field stream
                         +-> WorldEvent payload
                         +-> Valley inspector
```

## What is preserved

The original attestation packet is not rewritten.

The published derivative has its own SHA-256.

The media record retains:

- candidate ID;
- source/original SHA-256;
- public derivative SHA-256;
- creation/review time;
- review state.

## Moderation boundary

**Anyone with a phone may make an attest.**

That does not imply anonymous public image hosting.

Uploaded matching images enter `pending` and are not publicly retrievable until a local operator approves the exact media object.

This can later be replaced or supplemented by stronger identity/reputation/moderation systems without changing the portable attestation format.

## Privacy

Browser v1 does not automatically publish selected media.

The person must:

1. select/bind the photo;
2. make a public candidate;
3. separately choose photo publication.

The server deletes the temporary original after verification/derivative creation.

For higher-assurance QWOS paths such as Android1, the original may already exist in separately governed private custody; that custody is not duplicated merely to support public rendering.

## Truth boundary

A photograph is evidence bound to a claim.

It is not proof of every interpretation of the photograph.

The candidate remains self-attested/unverified unless later review changes that state.

# Android1 → Playable Universe Field Attestation Bridge v0

## Current fact

Android1 is already beyond the generic browser path.

The maintained `qwos-android1` repository records physical proof of:

- A16 — live human push-to-talk field voice + first map observation;
- A17 — deliberate stock-camera still, exact SHA-256 binding, private Foundry media custody and persistent photo observation;
- A18 — exact photo↔voice binding plus pinned local vision, retained as `inferred-model`.

Therefore Playable Universe should **reuse** those artifacts rather than create a second camera or survey subsystem.

## Immediate field path

Until the native promotion control is added, Android1 can use the same public browser page as any other phone:

`https://fc.quietwire.ai/playable/attest/`

That proves the universal participation path.

## Native target

Add an explicit button to the existing Android1 field-survey UI:

**Make Playable Attest**

The action should be available only when the human deliberately invokes it.

### When no existing survey evidence is selected

Create a normal `playable.mobile-attestation.v0` packet from:

- human text/transcript;
- session time;
- QWOS node identity;
- optional coarse/public-safe place information.

### When A17/A18 evidence is selected

Bind:

- existing `survey_session`;
- `observation_id`;
- `media_id = media:sha256:...`;
- retained private media custody ref;
- optional vision interpretation ID;
- human-confirmation state.

Do **not** upload a second copy of the media merely to create the Playable packet.

## Assurance

The intended Android1 packet class is:

`qwos-device-signed`

The signature should cover the exact canonical Playable packet or a stable digest of it, using an admitted QWOS device-signing path.

Existing experimental TEE key possession does not silently become public attestation authority. The signing profile must be explicitly admitted.

Until that admission exists, Android1 may submit at the browser/self-asserted class like any other phone.

## Public projection

Property-map precision remains private by default.

A Playable publication adapter must be able to transform:

```
private exact observation
        ↓ explicit human publication choice
public-safe projection
```

without changing the source evidence.

Examples:

- exact private coordinates -> no location;
- exact private coordinates -> deliberately rounded coarse location;
- private retained photograph -> public hash only;
- private retained photograph -> later deliberate public derivative/thumbnail;
- model interpretation -> visibly inferred;
- human-confirmed statement -> visibly human-confirmed.

## Promotion semantics

```
Android1 survey evidence
      |
      +-- stays private property-map evidence
      |
      +-- explicit Make Playable Attest
               |
               v
       mobile-attestation packet
               |
               v
        intake candidate receipt
               |
       +-------+--------+
       |                |
 public candidate   receipt-only
       |
 later review / corroboration
       |
 CAP / Canon promotion
```

## Tomorrow-success criterion

A field walk succeeds if Chris can:

1. open the phone surface;
2. make several explicit claims;
3. optionally bind deliberate photos;
4. receive candidate receipts;
5. choose public or receipt-only per claim;
6. walk into the 2D Valley and see public candidates appear in the Playable Present;
7. preserve the distinction between the public candidate and Android1's stronger private evidence chain.

That is already enough to make the property walk part of the Playable Universe without waiting for a new native APK.

# Phone Attestation Protocol v0

## Requirement

**Anybody with an ordinary phone should be able to make an attest.**

Android1 is a high-assurance reference implementation, not the participation boundary.

## The basic act

A person deliberately says, types, or otherwise asserts:

> I attest that ...

They may optionally bind evidence that was available to the phone at that moment.

The smallest packet is:

```
human claim
+ client time
+ witness mode
+ assurance class
+ optional evidence hashes
+ optional location
+ sharing choice
```

## Important distinction

`make an attest != prove the claim`

The system records **who/what asserted what, with what evidence and assurance**.

The resulting object can later be:

- corroborated;
- disputed;
- superseded;
- withdrawn;
- verified;
- promoted into CAP/Canon;
- rendered in the Playable Universe.

## Universal browser path

A normal modern phone browser can:

1. accept typed/dictated text;
2. open the phone camera through an explicit human action;
3. hash selected media locally with Web Crypto;
4. request browser geolocation only after a separate explicit button press;
5. build the packet;
6. submit the packet to a Playable Attestation Intake;
7. receive a server-side receipt over the exact packet bytes.

v0 does **not** automatically upload the photograph.

The phone keeps the photo; the attestation carries its SHA-256 and basic metadata.

This is deliberately useful even on a device with no QuietWire software installed.

## Assurance ladder

### Browser self-attested

The service can say:

- this exact packet was received at time T;
- this claim string was supplied;
- this evidence digest was supplied.

It cannot independently establish who held the phone.

### Browser device key

Future WebAuthn/passkey or local device-key binding.

### QWOS device signed

A QWOS node such as Android1 can bind the packet to its established device identity and custody path.

### Institution signed

An organization can submit under its own maintained signing identity.

## Android1 bridge

Android1 has already physically proven:

- explicit push-to-talk;
- deliberate stock-camera capture;
- photo SHA-256;
- private Foundry media custody;
- survey-session binding;
- exact photo ↔ voice binding;
- pinned local vision interpretation;
- claim-state separation.

Therefore Android1 does **not** need a second camera system.

It needs an explicit promotion action:

```
existing survey observation
       ↓
human chooses "Make Playable Attest"
       ↓
build playable.mobile-attestation.v0
       ↓
bind existing media/observation refs
       ↓
sign with QWOS identity where admitted
       ↓
submit to intake
```

## Visibility

v0 supports:

### receipt-only

The service stores the candidate and returns a durable receipt.

It is not shown in the public candidate stream.

### public-candidate

The packet may appear in the public Playable Universe field stream with an unmistakable:

**SELF-ATTESTED / UNVERIFIED**

or stronger assurance label.

Public visibility still does not make it verified.

## Location

Location is off by default.

For the ordinary public browser:

- `none` is default;
- `coarse` may be explicitly requested;
- exact private coordinates are reserved for stronger/private workflows.

The browser demo rounds public coordinates rather than publishing raw precision.

## Evidence custody

Hash presence != server possession.

A browser photo hash means only:

> the attester bound this claim to bytes with this digest.

Android1/private QWOS flows may additionally preserve the actual media under governed custody.

## CAP promotion

The Playable Attestation Intake is not a replacement for CAP.

Intended progression:

```
portable phone packet
    ↓
intake receipt
    ↓
candidate state
    ↓
review / corroboration / identity strengthening
    ↓
CAP subject + evidence
    ↓
CAP draft → submitted → verified → anchored
```

The original packet hash must survive promotion so the later record can point back to exactly what the human submitted.

## First field use

A person walks outside with a phone.

Examples:

> I attest that it is cold outside.

> I attest that I just saw a red-tailed hawk fly east over the barn.

> I attest that this photograph shows the south side of the bird barn.

The resulting candidates become temporal objects in the Playable Present.

If later accepted/verified, the same objects become anchors for Playable Past and future scenario branches.

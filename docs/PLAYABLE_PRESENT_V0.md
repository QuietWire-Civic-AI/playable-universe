# Playable Present v0 — Live Rooms and Real-World Hooks

## Thesis

The Playable Present is a **shared live scene whose state can be affected by observed real-world systems, human participants, companions/agents, and digital objects**.

It is not merely a chat room with avatars.

It is the moving surface where observation can become attested history.

## Room

A Present Room contains:

- scene identity;
- spatial context;
- participant roster;
- personas;
- current world state;
- live source adapters;
- interaction affordances;
- rights/recording policy;
- event stream;
- optional media channels.

## First useful fixture

A live physical installation with a real governed sensor/actuator path is an ideal Present fixture because it exercises both directions:

```
physical world
   |
 observations
   v
Playable Present room
   |
 intents / governed actions
   v
physical world
```

The current Playable Universe repository does not yet contain the Flipper-node technical records, so the adapter should begin as a generic `physical_fixture` profile and be bound to the actual Flipper interfaces once their source record is identified.

## Event classes

Candidate live events:

- `presence.joined`
- `presence.left`
- `presence.moved`
- `participant.spoke`
- `object.observed`
- `object.state_changed`
- `sensor.observation`
- `agent.message`
- `intent.proposed`
- `intent.approved`
- `action.executed`
- `action.refused`
- `attestation.proposed`
- `attestation.accepted`
- `attestation.disputed`
- `room.recording_started`
- `room.recording_stopped`

## Observation != action

A source adapter may publish observations.

That does not grant authority to perform actions.

For a physical actuator:

```
game input / participant intent
        ↓
interaction intent
        ↓
Quiet Hands / governing authority
        ↓
action execution or refusal
        ↓
WorldEvent receipt
        ↓
scene reflects observed result
```

The scene should render the **observed effect**, not merely assume success because an intent was sent.

## Recording

Rooms can have explicit modes:

- ephemeral;
- participant-controlled;
- observed-only;
- attestation-capable;
- fully recorded under agreed policy.

Presence does not silently imply consent to permanent replay.

## Multiplayer

The world-state/event stream and media channels are separate:

### State
WebSocket / event bus:
- movement;
- object state;
- interaction;
- receipts;
- semantic events.

### Media
WebRTC:
- voice;
- video;
- spatial audio where desired.

## Requirement-room use

A Quiet Room / requirements room can be a Playable Present scene.

People can:

- walk around a shared world;
- point at objects;
- pin documents;
- summon past attestations;
- branch proposed future states;
- leave decisions/requirements as structured objects;
- ask a companion to explain or simulate consequences.

The game interface becomes a spatial operational workspace rather than a replacement for the underlying evidence system.

## Present-to-Past transition

When a live event becomes attested:

1. the live event receives/links an attestation;
2. its truth class changes for historical reconstruction;
3. evidence is preserved;
4. future branches may now use it as a source anchor.

The Present literally lays new tiles behind itself.

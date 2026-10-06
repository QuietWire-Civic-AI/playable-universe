# End-State Architecture v1 — One World, Three Temporal Modes

## Purpose

The Playable Universe should become an **engine-neutral temporal world protocol**, not a proprietary game engine.

A browser, game engine, headset, room-scale installation, or future renderer should be able to consume the same world objects and event streams without becoming the source of truth.

## Core proposition

Past, Present, and Future are three operations on the same world model.

```
                         +----------------------+
                         |   Source / Evidence  |
                         |  Canon, AU, Rights   |
                         +----------+-----------+
                                    |
                                    v
+-------------+          +----------+-----------+          +------------------+
| Live Inputs | -------> | Temporal World Graph | <------- | Scenario Branches|
| nodes/rooms |          | entities + scenes   |          | assumptions      |
+-------------+          | relations + events  |          +------------------+
                         +----------+-----------+
                                    |
                   +----------------+----------------+
                   |                |                |
                   v                v                v
             Playable Past    Playable Present  Playable Future
             replay to T      subscribe now     fork from T
                   |                |                |
                   +----------------+----------------+
                                    |
                                    v
                         Engine / Renderer Adapters
                   browser · Godot · Unity · Unreal · XR
```

## The common world objects

### Entity

Anything with persistent identity in the world:

- person;
- companion/agent;
- physical node;
- organization;
- place;
- room;
- object;
- vehicle;
- device;
- asset;
- institution.

### Persona

How an entity appears and acts in a playable context.

A persona is **not** the underlying legal identity.

It can specify:

- display name;
- avatar/skin asset;
- voice profile;
- animation set;
- permissions in the scene;
- whether the entity is human-controlled, agent-controlled, historical simulation, NPC, or mixed;
- participant-controlled disclosure boundaries.

### Scene

A spatial/semantic context that an engine can render.

Examples:

- Binbrook Hearth;
- Melted;
- a Quiet Room;
- a live Flipper installation;
- FC;
- an illustrative Hamilton 2048 branch.

### World Event

A typed change in state.

Examples:

- entity entered scene;
- participant spoke;
- device state changed;
- observation arrived;
- attestation proposed;
- attestation accepted;
- object moved;
- authority changed;
- simulated future decision occurred.

### Attestation

Evidence-bearing statement about an observation/event.

Rendering an event does not itself attest it.

### Projection / Scenario

A future branch rooted in a known state plus explicit assumptions and hypothetical transitions.

### Echo

A new present event referencing a prior event or reconstruction.

### Asset

Renderable media:

- 3D model;
- terrain;
- image;
- audio;
- video;
- animation;
- material;
- spatial map.

### Rights / Authority Reference

Pointer into the governing rights/authority layer controlling:

- who may see;
- who may enter;
- who may speak/act;
- what may be recorded;
- what may be replayed;
- what may be made public.

## The temporal reducer

The core implementation primitive is a deterministic state reducer:

```
WorldState(t0)
  + Event1
  + Event2
  + Event3
  ...
  = WorldState(tN)
```

This permits:

### Past

Reconstruct state at a historical time by replaying source-backed events.

### Present

Apply verified/live events as they arrive.

### Future

Clone a state and apply hypothetical/simulated events on a branch that can never silently merge into attested history.

## Truth classes

Every event/state contribution must expose one of:

- `attested`
- `observed`
- `reported`
- `inferred`
- `reconstructed`
- `simulated`
- `projected`
- `disputed`

A renderer may make all of them immersive.

It may not visually erase the distinction between them.

## Seven planes

### 1. Evidence plane

Attestations, source artifacts, hashes, provenance, evidence envelopes.

### 2. World-state plane

Entities, relationships, places, objects, rooms, current state.

### 3. Temporal event plane

Append-oriented event sequence and state transitions.

### 4. Scenario plane

Future forks, assumptions, branch graphs, transition models.

### 5. Presence / interaction plane

Live people, agents, voice, movement, actions, rooms.

### 6. Rights / authority plane

Visibility, access, recording, action authority, cultural/participant restrictions.

### 7. Rendering plane

Browser, 2D, 3D, game engine, XR, mobile, installations.

Rendering sits at the edge.

It is not the Canon.

## Engine-neutral rule

An engine adapter receives:

1. a `SceneManifest`;
2. a current `WorldState` snapshot;
3. a stream of `WorldEvent` objects;
4. asset references;
5. rights/presence decisions already resolved to the extent appropriate.

The adapter can send back:

- movement/input intent;
- interaction intent;
- voice/presence state;
- proposed simulation events;
- proposed real-world actions.

A renderer must not directly write attested history.

## First reference architecture

```
                    HTTP snapshot API
                           |
                           v
                     World Service
                    /      |       \
             archive    live bus   scenario
                |          |          |
                v          v          v
               state reducer / branch manager
                           |
                   WebSocket / SSE
                           |
              +------------+------------+
              |            |            |
           Browser        Godot       Unreal/Unity
```

Voice/video/spatial media can use WebRTC separately from the durable event stream.

## End-state success test

A developer unfamiliar with QuietWire should be able to:

1. obtain a scene manifest;
2. load its glTF/USD/terrain assets;
3. subscribe to world events;
4. render entities/personas;
5. send interaction intents;
6. display provenance/truth state;
7. switch the same scene among Past, Present, and Future;
8. do all of this without knowing how QuietWire stores Canon or Rights OS internally.

That is the point at which Playable Universe has become a platform rather than a site.

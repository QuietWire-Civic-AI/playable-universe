# Game / XR Interoperability Profile v0

## Goal

Make Playable Universe attractive to ordinary game and XR developers without making any one engine authoritative.

The core protocol should remain small, web-native, and engine-neutral.

## Recommended industry hooks

### Runtime 3D assets — glTF / GLB

Use glTF 2.0 as the default runtime-delivery format for individual models, avatars, props, animations, and compact scenes.

Why:

- open Khronos standard;
- designed for runtime 3D delivery;
- broad engine/tool support;
- compact GLB packaging;
- PBR material model;
- extension mechanism.

Official source:
- https://registry.khronos.org/glTF/

### Rich scene interchange / authoring — OpenUSD

Use OpenUSD for complex authored scenes when hierarchy, composition, variants, layers, or film/game production workflows need more than glTF.

Do not require USD for simple Playable Universe tiles.

Official source:
- https://openusd.org/

### Large geospatial worlds — OGC 3D Tiles

Use 3D Tiles for large spatial environments such as:

- campuses;
- cities;
- terrain/photogrammetry;
- point clouds;
- large instanced geospatial content.

Official source:
- https://www.ogc.org/standards/3DTiles/

### Native XR — OpenXR

Use OpenXR as the native XR target for headset/controller/platform portability.

Official source:
- https://registry.khronos.org/OpenXR/

### Browser XR — WebXR

Use WebXR for browser-based VR/AR access where supported.

Official source:
- https://www.w3.org/TR/webxr/

## Network hooks

### Snapshot/query

HTTP/JSON:
- scene manifest;
- world snapshot;
- entity lookup;
- historical query;
- scenario metadata.

### Durable live state

WebSocket initially.

Server-Sent Events may be sufficient for read-only spectators.

The event format should be transport-neutral so deployments can later use NATS, MQTT, Kafka, Redis streams, or another bus internally.

### Spatial voice / video / low-latency media

WebRTC.

Do not place durable world-state truth in the media transport.

## Engine adapter targets

### Browser adapter

First reference renderer.

Candidate implementation families:
- Three.js;
- Babylon.js;
- WebGPU/WebGL rendering.

The protocol should not depend on a particular library.

### Godot adapter

Strong candidate for the first open game-engine reference adapter.

Responsibilities:
- fetch scene manifest;
- import glTF/GLB;
- create entities/personas;
- consume WorldEvents;
- publish interaction intents;
- expose truth/provenance state in UI.

### Unity adapter

C# package with the same adapter contract.

### Unreal adapter

C++/Blueprint plugin with the same adapter contract.

## Adapter contract

An adapter implements five boundaries:

```
loadScene(sceneManifest)
applySnapshot(worldState)
applyEvent(worldEvent)
publishIntent(interactionIntent)
setTemporalView(past | present | future)
```

Everything else is engine-specific.

## Scene assets versus semantic state

Do not hide semantic truth in engine scene files.

Bad:

`The Unreal map is the only record that an object existed.`

Good:

```
SceneManifest
  -> references asset/model/terrain
  -> declares semantic entity ID
  -> declares spatial transform
  -> declares interaction hooks
  -> declares provenance/rights references
```

The game engine may cache or decorate this information.

The portable manifest remains authoritative for the playable representation.

## Coordinate systems

A scene can use:

- local Cartesian coordinates for rooms/small sites;
- a geospatial anchor for real-world places;
- engine-specific transformed coordinates internally.

The manifest should retain the stable geospatial/local reference so engines can translate without changing identity.

## Avatar / persona rule

Playable Universe should define **persona semantics**, not a single avatar format.

A persona can reference:

- GLB avatar;
- USD character;
- sprite;
- audio-only presence;
- abstract glyph;
- custom engine prefab.

This permits Bone/Fern-like stylization without coupling identity to one copyrighted visual vocabulary or one engine.

## What we deliberately do not standardize yet

- physics engine;
- animation graph;
- shader system;
- navmesh format;
- multiplayer prediction algorithm;
- ECS implementation;
- scripting language;
- renderer;
- AI model/provider.

Those belong to engines/adapters until real interoperability pressure demonstrates a need.

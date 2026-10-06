# Playable Universe

**Status:** v0 field build  
**Origin:** QuietWire Playable Universe work, 2025; Valley / reachability expansion, 2026  
**Working stewards:** Chris Blask + Lumina

The Playable Universe is a navigable semantic world built from attested experience, the live present, and explicitly projected futures.

It has three temporal layers:

- **Playable Past** — original events are fixed; interpretations and echoes may grow.
- **Playable Present** — the live state-transition surface where observation can become attestation.
- **Playable Future** — projected, conditional states that must remain tethered to a traceable path from the present.

The 2026 Valley model adds a stricter question to future play:

> Can we show a coherent route from what is attested now to the projected state?

A future can be causally reachable without being desirable. QuietWire may intentionally deepen some parts of the reachable valley while still rendering dystopian, failed, or adversarial branches for study.

## Repository layout

- `docs/` — model, architecture, tile protocol, roadmap
- `schemas/` — machine-readable tile and future-projection shapes
- `data/` — small v0 example world/tile set
- `site/` — static first web surface
- `legacy/2025/` — preserved source snapshots from the original Playable Universe corpus
- `deploy/` — bounded FC promotion script


## Build toward 11

The current architecture treats the Playable Universe as **one engine-neutral temporal world protocol**:

- **Past** — replay source-backed events to a historical state;
- **Present** — subscribe to live world/presence events;
- **Future** — fork a state into explicit scenario branches.

Key working documents:

- [End-State Architecture v1](docs/END_STATE_ARCHITECTURE_V1.md)
- [Tile Ladder to 11](docs/TILE_LADDER_TO_11.md)
- [Game / XR Interoperability Profile](docs/GAME_ENGINE_INTEROP_V0.md)
- [Playable Past](docs/PLAYABLE_PAST_V0.md)
- [Playable Present](docs/PLAYABLE_PRESENT_V0.md)
- [Playable Future](docs/PLAYABLE_FUTURE_V0.md)
- [World API v0](docs/WORLD_API_V0.md)
- [Bounded Operator Plane v0](docs/OPERATOR_PLANE_V0.md)
- [Authority Placement — RDC to Domain](docs/AUTHORITY_PLACEMENT_RDC_TO_DOMAIN_V0.md)
- [Engine Adapter SDK contract](sdk/README.md)

Portable v0 protocol objects:

- `SceneManifest`
- `WorldState`
- `WorldEvent`
- `Persona`
- `InteractionIntent`

See [examples/](examples/) for small Past, Present, and Future fixtures.

## v0 rule

No projection is allowed to masquerade as an attested event.

Every rendered object must expose its temporal/status class and provenance.

## Licensing

This public repository is intentionally visible while licensing for the new 2026 code/content remains **not yet selected**. The prior source corpus carries its own repository licence/provenance. New Rights OS work is reviewing the appropriate public software/content licensing split.

No additional rights are implied by this README.

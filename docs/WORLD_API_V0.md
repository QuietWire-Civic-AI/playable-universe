# World API v0 — Draft Contract

## Purpose

Give browsers and game engines a stable boundary to the Playable Universe.

The API returns portable protocol objects. Internal Canon, Rights OS, databases, and event buses may change without forcing engine rewrites.

## HTTP

### List scenes

`GET /api/v0/scenes`

Returns scene descriptors.

### Scene manifest

`GET /api/v0/scenes/{scene_id}`

Returns a `playable.scene-manifest.v0`.

### World state

`GET /api/v0/scenes/{scene_id}/state`

Optional query:

- `at=` ISO timestamp;
- `branch=` future/counterfactual branch ID.

Returns `playable.world-state.v0`.

Examples:

- Present: no `at`, live branch;
- Past: `?at=2025-07-08T20:00:00Z`;
- Future: `?branch=scenario:transparent-authority-2041`.

### Events

`GET /api/v0/scenes/{scene_id}/events?since={sequence-or-time}`

Returns ordered `WorldEvent` objects.

### Submit intent

`POST /api/v0/intents`

Body: `playable.interaction-intent.v0`.

Response should identify:

- accepted for evaluation;
- refused;
- transformed/forwarded;
- resulting event/receipt references where available.

Acceptance is **not** proof of external execution.

## WebSocket

Candidate endpoint:

`wss://host/api/v0/ws?scene={scene_id}&branch={branch_id}`

Messages from server:

- `snapshot`
- `world_event`
- `presence`
- `receipt`
- `error`

Messages from client:

- `subscribe`
- `interaction_intent`
- `presence_update`
- `ack`

## Media

Voice/video/spatial audio should use a separate media-room mechanism, normally WebRTC.

The media channel may emit metadata events but is not the durable world-event ledger.

## Authentication / authorization

Authentication proves/links an actor identity.

Authorization determines what that actor may:

- see;
- enter;
- replay;
- record;
- simulate;
- interact with;
- propose as an attestation;
- request as a real-world action.

The engine receives only the permissions needed for its session.

## Versioning

Protocol objects include schema identifiers.

Breaking changes create `v1`, not silent reinterpretation of `v0`.

## Error philosophy

Errors should preserve semantic distinctions.

Examples:

- `not_found`
- `not_visible`
- `not_authorized`
- `historical_source_missing`
- `branch_retired`
- `intent_refused`
- `attestation_required`
- `rights_review_required`

Do not collapse all refusal into HTTP 500.


## Live implementation status

The FC reference service now implements the first read-side subset:

- `GET /v0/world/tiles`
- `GET /v0/scenes`
- `GET /v0/scenes/{slug}`
- `GET /v0/scenes/{slug}/state`
- `GET /v0/scenes/{slug}/events`

The 2D `Walk the Valley` client consumes:

- `/v0/world/tiles` for Past/Present/Future semantic tiles;
- `/v0/scenes/present-room/events` for public field-attestation events.

This is the first proof that the web game is becoming an adapter over the portable world protocol rather than the source of its own world state.

The full interaction-intent and WebSocket portions remain future Tile 2 work.

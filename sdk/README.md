# Engine Adapter SDK Contract v0

## Minimal adapter

An engine integration should be able to implement:

```ts
interface PlayableAdapter {
  loadScene(scene: SceneManifest): Promise<void>;
  applySnapshot(state: WorldState): Promise<void>;
  applyEvent(event: WorldEvent): Promise<void>;
  publishIntent(intent: InteractionIntent): Promise<IntentReceipt>;
  setTemporalView(view: TemporalView): Promise<void>;
}
```

## Temporal view

```ts
type TemporalView =
  | { mode: "present" }
  | { mode: "past"; at: string }
  | { mode: "future"; branchId: string };
```

## Engine responsibilities

The adapter owns:

- rendering;
- camera;
- local physics;
- controller input;
- animation;
- effects;
- asset caching;
- engine-native UI.

## Protocol responsibilities

Playable Universe owns:

- stable semantic identity;
- temporal truth class;
- branch identity;
- event ordering;
- provenance references;
- rights/authority references;
- attestation boundaries.

## Rendering suggestions

Engines should expose truth class in ways appropriate to the experience.

Examples:

- subtle outline/material treatment;
- provenance HUD;
- temporal status icon;
- source panel;
- branch-colored environment;
- explicit transition animation when moving from attested Past into counterfactual branch.

The protocol does not prescribe a single visual style.

## Recommended first adapters

### Browser

Reference implementation for fast protocol testing.

### Godot

Recommended first open-engine adapter unless the first recruited game developer has a stronger engine preference.

### Unity

C# package.

### Unreal

C++/Blueprint plugin.

## Test vector

Every adapter should be able to render the three fixtures under `examples/`:

1. Past reconstruction;
2. live Present room;
3. Future scenario branch.

An adapter passes v0 when semantic state and truth/branch distinction survive engine translation.

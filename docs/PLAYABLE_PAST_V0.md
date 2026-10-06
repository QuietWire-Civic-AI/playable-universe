# Playable Past v0 — Reconstruction Without Counterfeit History

## Thesis

Playable Past renders historical state from source-backed events and artifacts.

It should maximize immersion while minimizing ambiguity about what was actually observed.

## Reconstruction pipeline

```
source artifacts
 + attestations
 + world events
 + place/asset records
        ↓
historical state reducer
        ↓
SceneManifest at time T
        ↓
renderer
```

## Layers in a historical scene

A Past scene can contain:

### Attested objects

Directly supported by source evidence.

### Reconstructed objects

Reasonable spatial/visual reconstruction supported by evidence but not themselves directly captured.

### Inferred objects

System/human inference, visibly marked.

### Interpretive objects

Later commentary, annotation, disagreement, meaning.

### Simulated actors

Source-bounded agents that can answer questions about the historical corpus but are not the historical person.

## Historical actor rule

A visitor may stop a simulated Chris, Ian, Lumina, or another historical persona and ask a question.

The answer must expose:

- source envelope;
- temporal cutoff;
- whether the answer is quotation, paraphrase, inference, or simulation;
- uncertainty.

The actor may say:

> I do not have evidence that Chris knew that at this point in time.

That refusal is a feature.

## Counterfactual mode

Past scenes can allow counterfactual play, but the user must explicitly cross a branch boundary.

Example:

```
Attested reconstruction: Melted, June 2025
          |
          +-- visitor selects "fork counterfactual"
                      |
                      v
             Future-from-Past branch
```

Once forked, no simulated event is allowed to write back into historical truth.

## Cultural / participant boundaries

Some historical worlds may expose:

- exact location;
- approximate location;
- redacted location;
- no spatial rendering;
- participant-only artifacts;
- culturally restricted artifacts.

Immersion does not override source access constraints.

# Attestation Concordance v0 — Source Lineage Before Truth Scoring

## Purpose

Playable Universe should be able to distinguish:

- several genuinely separate observations that happen to agree;
- several attestations derived from one common source;
- relayed reports;
- source-backed claims;
- explicit inference;
- disagreement.

It must do this without silently turning agreement into truth.

## Governing rules

> Agreement is evidence. Independence is additional evidence. Neither is truth by itself.

> Absence of a known dependency is not proof of independence.

> Preserve topology before inventing a score.

The first implementation should therefore expose inspectable evidence relationships rather than a single confidence or truth percentage.

## Public pilot first

The first public slice is intentionally small enough for ordinary phone/browser use.

The attestation form asks:

**How do you know this?**

Supported v0 modes:

- `direct_observation` — the witness says they directly observed or experienced it;
- `own_capture` — the witness says they captured the source evidence themselves;
- `relayed_report` — another person or source reported it to the witness;
- `source_material` — the claim is based on a document, post, recording, link or other source;
- `derived_inference` — the witness says the claim is a conclusion derived from other information;
- `unknown` — other / uncertain;
- `unspecified` — compatibility state for older clients that did not carry provenance.

A candidate may also carry bounded `source_refs`.

These fields are **stated provenance**, not verified provenance.

## Compatibility rule

The existing `playable.mobile-attestation.v0` packet remains accepted.

Older clients without a `provenance` field are normalized at intake to:

```json
{
  "mode": "unspecified",
  "source_refs": [],
  "note": null
}
```

The new public browser client always supplies explicit provenance.

## Concordance ladder

### A. Explicit provenance — current build

Capture how the witness says they know the claim.

Success:

- public browser form records provenance;
- intake validates and preserves it;
- public field stream exposes the stated basis;
- old clients remain accepted.

### B. Typed candidate relations

Append relations without rewriting candidate packets:

- `supports`
- `contradicts`
- `same_event`
- `derived_from`
- `shares_source`
- `quotes`
- `duplicates_artifact`

Avoid asserting `independent_of` merely because no dependency is known.

### C. Deterministic source lineage

Compute known dependency roots where the evidence is mechanical:

- identical artifact SHA-256;
- explicit `derived_from`;
- same cited document/source;
- derivative media linked to one sealed source digest;
- quoted candidate or report.

### D. Concordance report

Expose structure, not a magic truth score.

Candidate fields include:

- attestation count;
- supporting/disputing counts;
- known source roots;
- known shared-source groups;
- declared direct observations;
- evidence-root classes;
- assurance-class distribution;
- unknown-dependency count.

### E. Event clustering

Semantic/time/place similarity may **propose** that candidates refer to the same event.

Proposal is not silent fusion.

### F. Native semantic surface

Read-side candidates:

- `playable_concordance_inspect`
- `playable_candidate_relations`

Append/proposal-side candidates:

- `playable_candidate_relation_record`
- `playable_provenance_record`
- `playable_cluster_relation_propose`

Read operations should remain `hands.read`.
Semantic transitions should use `hands.execute`, not generic `hands.write`.

## Six-attestation fixture

Build a small deterministic fixture:

- A — direct witness, photo 1;
- B — direct witness, photo 2;
- C — reposts A's photo;
- D — repeats C's report;
- E — direct witness, no media;
- F — disputes one detail.

Expected topology:

- six attestations;
- A/C/D share a lineage;
- two distinct photo roots;
- E is a declared direct observation with no media;
- F is an explicit dispute;
- unknown dependency is preserved where not established.

## What v0 will not do

- declare a claim true because many people repeat it;
- treat accounts or devices as equivalent to independent humans;
- infer independence from missing metadata;
- emit a universal truth percentage;
- expose private device/location/source identifiers merely to improve scoring;
- rewrite original attestation packets when relationships are learned later.

## Public field-test question

The first Facebook-scale experiment is deliberately empirical:

> Will ordinary people understand and use explicit provenance when the question is phrased simply as “How do you know this?”

The resulting packets will tell us what provenance vocabulary is intuitive before we harden the next relation and lineage schemas.

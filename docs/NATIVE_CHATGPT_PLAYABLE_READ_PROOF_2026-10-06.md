# Native ChatGPT -> Playable read proof — 2026-10-06

## Result

The first native read-only Playable Universe candidate inspection from ChatGPT succeeded end-to-end.

Proven path:

```text
ChatGPT conversation
-> Quiet Hands public MCP / OAuth carrier
-> Teddy edge + durable device catalog
-> qwos:fc public Quiet Hands agent
-> FC Playable semantic adapter
-> Playable operator plane
```

No shell, curl, CLI, `start_process`, or semantic substitute was used for the proof call.

## Calls

### Operator status

Native `playable_operator_status(qwos:fc)` returned:

- status: `ok`
- interlock: `NORMAL`
- policy: `fc-playable-operator-2026-10-06-v0`
- actor role: `agent-steward`
- admitted semantic operations: 8
- receipt: `opreceipt:3a4540ce-f55b-46cb-a97f-4506f76b685a`

### Right-foot candidate inspection

Native call:

`playable_candidate_inspect(qwos:fc, attest:eb5f3f11-7b29-4717-ad0e-54931dceb161)`

returned `ok: true`.

Operator receipt:

`opreceipt:256e0fcf-7234-4b57-a499-f1876ef152f3`

Request:

`qh-opreq:9093837c-d64d-4547-81aa-d8d4736c5473`

Observed candidate summary:

- candidate id: `attest:eb5f3f11-7b29-4717-ad0e-54931dceb161`
- status: `candidate`
- visibility: `public-candidate`
- lifecycle events: 2
- public media count: 0
- private media count: 0
- packet sha256: `27615a3e01412a9948134ae92eee91086c4099abfb8ce57084e0ac3e8801105d`
- receipt sha256: `9aa58345c2a841e896bbffc91656b8ae6d5dda3cafedd622d961ce1628dd11c2`

The inspect operation was read-only. No candidate mutation was performed.

## Schema boundary resolved

The initial proof was blocked by an interoperability mismatch around the candidate-id JSON Schema pattern.

The portable candidate pattern is now:

`^attest:.*$`

The correction was propagated through both FC Quiet Hands agent trees, including the public common agent that feeds Teddy's durable device catalog. Teddy's current `qwos:fc` record was verified to advertise only the portable pattern for all five candidate-bearing Playable tools before the successful native inspect.

## Doctrine preserved

This proof exercises domain-native semantic authority without broadening generic operating-system privilege.

- Quiet Hands remains carriage.
- Playable Universe remains the semantic relying authority.
- Read-only status and candidate inspection remain `hands.read` operations.
- No generic `hands.write` authority was required.
- No candidate state was rewritten.

This is the first completed native conversation -> carrier -> semantic adapter -> Playable operator read proof.

# Review handoff and feedback loop

Use this reference for every `standard` or `hero` review and whenever the
companion review Skill improves this production workflow.

## Responsibility split

- This Skill owns production intent, media generation, repair, generation
  evidence, and production-side regression.
- `video-review-evolution` owns independent findings, review evidence, change
  requests, review memory, and verification of changed media.
- The user or accountable owner decides business intent, taste acceptance,
  budget, rights, and final release authority.

## Contract sequence

```text
final candidate
  -> qa/review-handoff.json
  -> qa/review-result.json
  -> qa/change-response.json
  -> qa/review-verification.json
  -> final release gate
```

The response is provisional. A change is not validated until an independent
review examines the new file bytes and records the result.

## Required handoff

Create `qa/review-handoff.json` after selecting the final candidate.
`schema_version` is `2`.

Required content:

- exact project ID and creation time;
- generation Skill name/version and optional bundle hash;
- minimum review Skill version;
- actual review scope;
- final media path, SHA-256, duration, raster, fps, and audio state;
- delivery platform, intended size, and quality mode;
- paths and hashes for brief, project contract, shots, timeline, and QA report;
- required observations and acceptance IDs;
- stable shot, graphic, and event anchors;
- intentional choices, allowed effects, and must-preserve items;
- route, model, prompt/source, and references;
- known-clean and known-failure controls;
- explicit unavailable or excluded checks.

### Project contract hash

`project.json` changes whenever a gate is approved. Bind its reviewable content
with:

```json
{
  "path": "project.json",
  "sha256": "64-hex",
  "hash_mode": "json-without-gates"
}
```

This hash removes the mutable top-level `gates` object, serializes the remaining
JSON with stable sorting and separators, then hashes the UTF-8 bytes.

## Stable anchors

Use IDs that survive re-rendering and timeline changes:

- `SHOT-S01`
- `TXT-TITLE`
- `FX-SEAM-03`
- `AUDIO-CUE-02`

Keep their current time windows in the handoff. Comparing the same anchor before
and after a fix is more reliable than comparing an old fixed timecode.

## Intentional choices

Declare the relationship, allowed effect, preserved properties, and source:

```json
{
  "id": "INT-01",
  "relationship": "text-graphic-overlap",
  "declared": "The accent line intentionally crosses the title.",
  "allowed_effects": ["partial glyph occlusion"],
  "must_preserve": ["exact text", "recognizable title"],
  "evidence": "creative-bible.md#title-treatment"
}
```

An intentional choice cannot excuse wrong facts, misleading claims, missing
rights, safety failures, or platform violations.

## Review result

Read `qa/review-result.json` only after confirming:

- its `project_id` matches the handoff;
- its review Skill version meets the minimum;
- its generation Skill version matches the handoff;
- the reviewer is identified and independent when required;
- the reviewed media hash matches the handoff;
- every declared coverage category has a status and reason;
- confirmed issues have hashed evidence;
- change requests link confirmed issues and structured regression roles.

## Production response

For every change request, decide `accepted`, `rejected`, or `deferred`.

For accepted changes:

1. change the cheapest responsible layer;
2. change one causal variable at a time;
3. preserve approved identity, product state, composition, audio, and rights;
4. produce a new file without overwriting the reviewed bytes;
5. run every required regression case;
6. record the new media hash and project revision;
7. keep the generation Skill version unchanged unless the Skill itself changed;
8. write `qa/change-response.json`.

## Independent verification

The generation response cannot validate itself. A new independent review round
writes `qa/review-verification.json`, which binds:

- prior review and change request IDs;
- original and changed media hashes;
- the changed media file and hash;
- the independent reviewer;
- original failure, same-mechanism positives, known-clean controls, negative
  examples, cross-route cases, and holdout when required;
- final verification status.

## Project policy

New `standard` and `hero` projects default to:

```json
{
  "require_companion_review": true
}
```

When true, the review gate requires all four review artifacts. When false, the
handoff remains required, but an external review path can be documented in the
project QA report. Final release still requires accountable independent review
according to project policy.

## Validation

The canonical validator belongs to `video-review-evolution`:

```bash
python <video-review-evolution>/scripts/validate_contracts.py \
  --handoff <project>/qa/review-handoff.json \
  --result <project>/qa/review-result.json \
  --response <project>/qa/change-response.json \
  --verification <project>/qa/review-verification.json \
  --require-complete
```

`video-production-director` runs the sibling validator during final
`validate_project.py` validation when companion review is required. Override
discovery with `VIDEO_REVIEW_VALIDATOR` only when the companion Skill is
installed elsewhere.

## Evolution rules

- A finding is not automatically a generation rule.
- One case or one preference stays project-specific.
- A repeated route mechanism may become route-specific.
- A model limitation belongs in model configuration.
- A process invariant can be enforced directly.
- A visual/physical heuristic needs positive, negative, clean-control, and
  scoped regression evidence.
- Stop after three failed repairs of the same cause and escalate.
- Never claim a fix from the existence of a response file alone.

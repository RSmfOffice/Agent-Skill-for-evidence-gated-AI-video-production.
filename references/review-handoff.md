# Review handoff and feedback loop

Use this reference for every `standard` or `hero` review, and whenever the user
asks the review Skill to improve this production Skill.

## Why

A bare MP4 forces the reviewer to guess intent, anchors, model limits, and which
effects are deliberate. A review handoff makes the review reproducible without
letting generation claims replace actual output evidence.

The contract is:

```text
production intent and exact bytes
  -> independent review evidence
  -> scoped generation change request
  -> minimum responsible fix
  -> old failure + clean control + negative-example regression
  -> validated rule or rejected proposal
```

The companion review Skill, when installed, is
`video-review-evolution`. It owns issue memory and review rules. This Skill
owns production, repair, and production evidence.

## Required artifact

Create `qa/review-handoff.json` after the final candidate is selected. The full
schema and examples are in the review Skill's
`references/coevolution-contract.md`.

Required content:

- `schema_version`;
- generation Skill name, version, path, and optional bundle hash;
- minimum review Skill version;
- review scope;
- final media path, SHA-256, duration, raster, fps, and audio presence;
- intended platform, viewing size, and quality mode;
- source files for brief, project, shots, timeline, and QA;
- required observations and acceptance IDs;
- stable anchors for shots, graphics, events, and deliberate effects;
- route/model/prompt/reference context;
- intentional choices with allowed effects and must-preserve items;
- known-clean and known-failure controls when available;
- excluded or unavailable checks.

Never put a low-resolution proxy or animatic hash in `media`.

## Stable anchors

Use IDs that survive a re-render or timeline adjustment:

- `SHOT-S01`
- `TXT-TITLE`
- `FX-SEAM-03`
- `AUDIO-CUE-02`

Keep the corresponding time windows in the handoff. A rule failure may move in
time while retaining the same anchor, which makes before/after comparison
possible.

## Intentional choices

Declare the exact relationship and its acceptance boundary, for example:

```json
{
  "id": "INT-01",
  "relationship": "text-graphic-overlap",
  "declared": "The accent line intentionally crosses the title as a strike-through.",
  "allowed_effects": ["partial glyph occlusion"],
  "must_preserve": ["exact text", "recognizable title"],
  "evidence": "creative-bible.md#title-treatment"
}
```

An intentional choice explains the design; it does not exempt wrong text,
misleading facts, rights, safety, or platform requirements.

## Consume review results

When `qa/review-result.json` is available:

1. Re-open the exact reviewed file and confirm its hash.
2. For each `generation_change_request`, decide `accepted`, `rejected`, or
   `deferred`.
3. Apply the cheapest responsible fix.
4. Change one causal variable at a time.
5. Preserve the approved subject, action, composition, audio, and rights state.
6. Re-render a new file; never overwrite the reviewed bytes.
7. Run the original failure, known-clean control, negative examples, and normal
   acceptance.
8. Write `qa/change-response.json`.
9. Ask the review Skill to verify the new bytes before calling the fix validated.

The response includes:

- review and change-request IDs;
- decision and reason;
- responsible layer;
- changed files/rules;
- preserved properties;
- new media hash;
- original-case and canary regression;
- negative-example results;
- unresolved risks and new Skill version.

## Production-side repair ladder

Choose the cheapest layer that explains the observed failure:

1. quality contract or acceptance;
2. direction/reference;
3. script or master clock;
4. shot/action/camera design;
5. asset, keyframe, depth, or mask;
6. route/model/parameters;
7. prompt;
8. compositing or timeline;
9. QA and evidence;
10. internal Skill rule.

Do not add a prompt instruction when the failure is deterministic layout or
geometry that can be solved in the responsible controllable layer.

## Evolution rules

- A review finding is not automatically a generation rule.
- One project or user preference becomes project-specific.
- A repeatable mechanism may become route-specific.
- A model limitation belongs in model configuration.
- Cross-route promotion requires positive, negative, and regression evidence.
- Never optimize for a single reviewer phrase if it damages other valid work.
- Keep a known-clean output as a false-positive canary.
- Stop after three failed repairs of the same cause and escalate.

## Validation

When the review Skill is available:

```bash
python <video-review-evolution>/scripts/validate_contracts.py \
  --handoff <project>/qa/review-handoff.json \
  --result <project>/qa/review-result.json \
  --response <project>/qa/change-response.json
```

`review-result.json` and `change-response.json` may be omitted for the first
handoff, but the final co-evolution receipt requires all three.

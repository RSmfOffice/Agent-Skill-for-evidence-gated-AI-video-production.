# Generation routing, prompting, and repair

Use this reference for external video models, image-to-video workflows,
ComfyUI-class pipelines, keyframe chains, and motion repair.

## Select control before model

Choose the least stochastic route that satisfies the shot:

1. deterministic code, vector, 3D, real footage, or approved asset compositing;
2. existing footage with a controlled edit;
3. image-to-video from an approved keyframe;
4. first-frame and last-frame control;
5. multi-reference or identity-conditioned video;
6. video-to-video surface repair;
7. text-to-video for exploration.

Route per shot and per layer. A project may combine footage, code graphics,
generated inserts, and post-produced text.

Route-specific implementation guides:

- [programmatic](routes/programmatic.md)
- [external-video](routes/external-video.md)
- [timeline-edit](routes/timeline-edit.md)
- [hybrid](routes/hybrid.md)

Exact logos, prices, legal copy, CRUD UI, data, and subtitles normally belong
outside the generative layer. If a model cannot hold a critical object, use a
deterministic asset, 3D, compositing, or a different shot design.

## Record model capability

Do not assume vendor features from older documentation. Verify and record:

- provider and model ID;
- model or endpoint version;
- verification date;
- accepted modes: text/image/reference/video-to-video;
- maximum and minimum duration;
- aspect ratios and resolutions;
- image, video, audio, and first/last-frame slots;
- camera, motion, keyframe, seed, and negative-prompt controls;
- native audio and language behavior;
- prompt length and schema validation;
- queue, polling, webhook, cancellation, and retention behavior;
- pricing basis and failure billing;
- output rights, commercial restrictions, and moderation behavior.

Treat the catalog as volatile metadata. Keep it in project or adapter
configuration, never in the core craft rules.

## Prompt shapes

Choose a shape from the actual capability surface.

### S1: Motion-only image-to-video

The image supplies identity, composition, environment, and style. The prompt
supplies only what must change:

```text
[Camera behavior]. [Subject's visible start state], then [one primary action
with direction and pace]. [One environmental reaction]. End with [visible end
state]. Maintain [identity, wardrobe, light direction, spatial anchors].
```

### S2: Full text-to-video

Use when the model has full control over the image:

```text
[Medium and style]. [Concrete subject identity]. [Location, weather, time, and
atmosphere]. [One primary action]. [Shot size, camera position, field of view,
and camera behavior]. [Light source and direction]. [Visible start and end
states]. [Continuity anchors].
```

### S3: First/last-frame bridge

Describe only the transition between approved frames:

```text
Start from the first image and end at the second. Between them, [one continuous
transformation or action]. The camera [path or locked behavior]. Keep
[identity, product state, wardrobe, set, and light direction] identical.
```

Build shot B's first frame from shot A's approved end frame when exact
continuity matters.

### S4: Timestamped multi-shot

Use only when the model genuinely supports a controlled multi-shot sequence.
Keep global identity and style once in the header, then describe each time range
with one action, camera behavior, and cue. Do not repeat and reinterpret the
subject in every segment.

Prompt shape varies by model. These are structures, not required syntax.

## Prompt construction

Keep story explanation outside the prompt unless it changes pixels. Use concrete
visible language:

- subject and setting;
- start composition;
- action chronology with visible contacts and direction;
- camera geometry, path, and endpoint;
- light and environment reaction;
- exact end state;
- continuity invariants;
- only the negative constraints relevant to this shot;
- review target.

Prefer "waist-high camera at the left end of the counter, locked, subject enters
from frame right and stops at the marked cup" over "dynamic cinematic angle."

One primary action and one dominant camera idea are default risk controls. If a
shot needs more, split it or explicitly justify the added complexity.

## Keyframe-first workflow

1. Establish identity and look with cheap stills.
2. Approve the hero composition and actual scene lighting.
3. Reject keyframes with wrong silhouette, product geometry, text, hands,
   contact, or occlusion.
4. Use the keyframe as an input rather than restating all visual identity in a
   long video prompt.
5. Create end frames only when they clarify the action or transition.
6. Test the hardest motion on a short, cheap clip before a batch.

Patch a bad keyframe or asset before rerolling many videos. Regeneration does not
repair a weak input.

## Candidate policy

Pre-register criteria before seeing outputs:

- identity and product fidelity;
- instruction following;
- action completion and timing;
- camera path;
- continuity and screen direction;
- anatomy and physical contact;
- text, UI, and logo defects;
- temporal stability;
- editability;
- intended-size readability.

When the shot contains an important temporal or physical relationship, judge it
against the project's [motion contract](motion-contracts.md), not only a visual
impression.

For Hero shots, generate multiple candidates where budget permits. Use full-size
evidence and a motion sweep, not one favorite frame. For supporting shots, use
the minimum candidates needed to satisfy risk.

When comparing models, hold the brief, references, output count, and requested
size as stable as their schemas allow. Disable prompt rewriting or expansion
where possible. Record forced differences. Compare cost, latency, and criteria
passes together. Do not compare different models by raw seed values.

## Generation log

Record one append-only row per candidate:

- candidate and shot IDs;
- model/version and control mode;
- prompt file and hash;
- reference assets;
- parameters and seed;
- cost and latency;
- output path and hash when available;
- failure codes;
- verdict and notes.

Change one causal variable between attempts. Preserve the prompt and input set
that produced an accepted take.

## Failure taxonomy

Use stable categories:

- `identity-drift`;
- `product-morph`;
- `action-weak`;
- `action-overload`;
- `camera-path`;
- `anatomy`;
- `contact-physics`;
- `prop-state`;
- `text-ui`;
- `screen-direction`;
- `light-continuity`;
- `flicker`;
- `flicker-texture`;
- `fusion-penetration`;
- `temporal-jump`;
- `audio-sync`;
- `uncuttable`;
- `model-limitation`.

An issue may receive more than one code, but state the shared root cause before
repairing.

## Repair ladder

Try the cheapest responsible intervention first:

1. edit the prompt to remove contradiction or overload;
2. change one parameter;
3. regenerate the same controlled setup;
4. repair or replace the keyframe;
5. change the reference set;
6. use a stronger control mode;
7. use video-to-video for surface-only repair;
8. split or simplify the shot;
9. solve with an insert, reaction, trim, or other edit;
10. cut the shot.

After two failures from the same cause, stop the same prompt family. After the
project iteration cap, re-plan the shot. Do not spend an unlimited budget
polishing instructions that ask the model for a capability it does not have.

## Generation acceptance

A candidate is usable only when:

- the intended action starts and completes;
- the camera has one readable path and a stable endpoint;
- identity, product, and required states remain within tolerance;
- no critical object is fused, duplicated, hidden, or transformed;
- the clip has clean usable handles and cuts to its neighbors;
- critical text and graphics can be composited;
- motion has been watched, not inferred from a still;
- the selected take is logged with all relevant inputs.

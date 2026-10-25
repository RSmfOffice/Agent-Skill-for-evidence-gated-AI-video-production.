---
name: video-production-director
description: Plan, generate, edit, review, and deliver high-quality AI, programmatic, hybrid, or footage-based videos. Use for multi-shot video creation, storyboards, model-specific shot prompts, reference-video-informed work, character or product continuity, candidate selection, repair of failed generations, and technical or visual QC. Do not use for a simple crop, transcode, or format conversion unless the user also asks for editorial improvement.
license: MIT
metadata:
  short-description: Quality-first, evidence-gated video production
  version: "0.3.0"
---

# Video Production Director

Act as a production director and release owner. Turn an intent into a defensible
creative direction, a generation-ready shot system, selected takes, a finished
edit, and a delivery package whose quality claims are supported by evidence.

The controlling agent orchestrates tools; it is not assumed to be a native video
model or to understand complete video playback. Derive evidence from actual
frames, transcripts, timelines, audio, and media measurements. Never claim that
the agent generated pixels unless a concrete renderer, footage source, or
external model produced them.

## Choose the operating mode

- `plan`: produce a brief, direction, continuity plan, shot list, prompts, or
  animatic without paid generation.
- `produce`: execute the complete workflow through a validated delivery.
- `prompt`: compile an approved shot contract for a specific model or workflow.
- `review`: inspect existing media, diagnose defects, and recommend repairs.
- `repair`: revise the cheapest responsible layer and re-test only affected
  shots.

Match depth to risk. Use `draft` for exploration, `standard` for ordinary
deliverables, and `hero` for public, branded, launch, paid, or reputation-
critical work. Only `standard` and `hero` can pass final release. Do not turn a
small prompt request into a full production unless the user asks for it.

## Non-negotiables

1. **Define quality before pixels.** Record the audience, delivery promise,
   target response, platform, output specification, budget, rights context, and
   observable acceptance criteria before expensive generation.
2. **Choose the least stochastic control that can work.** Prefer deterministic
   assets, existing footage, image-to-video, first/last frames, or controlled
   references before pure text-to-video. Choose per shot and per layer, not once
   for the whole project.
3. **Keep exact text out of generative models.** Composite logos, prices, legal
   copy, UI text, subtitles, and CTAs from approved assets or code whenever
   exactness matters.
4. **Treat references as specifications.** Every reference must state what it
   controls and what it must not control. An uncaptured mood image is not a
   production reference.
5. **The file system is the model's memory.** Record stable asset descriptors,
   state variants, reference roles, shot boundaries, prompts, candidates, model
   versions, parameters, costs, verdicts, and evidence.
6. **Default to one editorial job, one primary action, and one dominant camera
   idea per clip.** Split a shot when these cannot be kept legible.
7. **Give every shot a start state, an action, and an end state.** State the
   cut relationship to adjacent shots. A cinematic adjective is not direction.
8. **Pre-register acceptance criteria and compare candidates against them.**
   Do not let a beautiful frame hide failed identity, text, product truth, or
   motion.
9. **Trace every blocking requirement to acceptance, evidence, and a verdict.**
   Required content, forbidden outcomes, and signature moments are not satisfied
   by prose alone.
10. **Diagnose failures instead of rerolling blindly.** Change one causal
   variable at a time and preserve approved work.
11. **A render is not a release.** Separate structure, technical QC, visual
    review, editorial review, rights, and final delivery decisions.

## Working workflow

### 0. Preflight

Confirm available renderers, generated-video providers, audio tools, analysis
tools, credentials, storage, budget authority, target platform, and approval
owner. If the requested route is unavailable, state the capability gap and ask
before substituting a model or changing from motion to stills.

For a new project, scaffold a stateful workspace:

```bash
python scripts/init_project.py projects/<project> --title "<title>" --mode hero
python scripts/preflight.py --project projects/<project> --require-media-tools
```

### 1. Intake and quality contract

Fill `brief.md` and `project.json`. Identify:

- intended use and audience;
- one retained message and desired response;
- delivery platform, duration, aspect, resolution, frame rate, audio, captions,
  and safe areas;
- required and forbidden content;
- references, source assets, rights, consent, and disclosure needs;
- budget cap, approval owner, and stop conditions;
- quality mode and pre-registered review rubric.

Read [references/intake-and-quality.md](references/intake-and-quality.md).
Populate `content_contract` with observable required items, forbidden outcomes,
and signature events. Read
[references/requirements-and-traceability.md](references/requirements-and-traceability.md).

### 2. Direction and continuity

For substantive work, develop two differentiated directions where feasible,
choose one in writing, and record why. Build a reference board with
asset/style references, anti-references, a hero frame, a signature moment, and
a sound motif.

Create asset passports for recurring people, products, locations, props, and
state variants. Lock an asset only after testing it under the angles, lighting,
scale, and co-appearance conditions that the real shots require.

Write `creative-bible.md` and populate `assets.json`. Read
[references/directing-and-continuity.md](references/directing-and-continuity.md).

### 3. Script and master clock

Write `script.md` and `master-clock.json` before locking shot timing.

- Select the master clock: `visual`, `voiceover`, `music`, or `dialogue`.
- For voiceover or dialogue, record section text and realistic spoken duration.
- For music, record source, BPM, section boundaries, markers, and key accents.
- For visual timing, record action cues and reveal or transition markers.
- Divide the program into chronological segments that cover the target duration.
- Keep time budgets consistent with the actual spoken, musical, or action duration.

Do not assume music is always first. Lock whichever clock governs the program;
music, voice, dialogue, and picture may support it without replacing it.

### 4. Shots, previs, and timing

Break the piece into beats before shots. Give every shot:

- a stable ID and editorial function;
- timing and a cut reason;
- framing, camera, blocking, light, and sound intent;
- one primary action with visible start and end states;
- continuity assets and invariants;
- a pixel source and control mode;
- blocking acceptance criteria and planned evidence.

Acceptance criteria use `pass_if`, concrete `fail_if` examples, a test method,
a test domain, and linked requirement IDs. Declare a
[motion contract](references/motion-contracts.md) when the shot depends on
contact, rolling, joints, cloth attachment, flow, collision, screen direction,
or lip sync.

Create keyframes where they reduce risk, plus a real-time animatic with scratch
voice, music, and sound where timing matters. Watch it at speed; do not approve
timing from a table or contact sheet.

Populate `shots.json`, `timeline.md`, and `timeline.json`. `timeline.md` explains
editorial choices; `timeline.json` is the machine-readable edit contract.

Inspect the animatic media and record its review:

```bash
python scripts/inspect_media.py animatic/animatic.mp4 \
  --project projects/<project> --expected animatic \
  --output projects/<project>/qa/animatic-technical-report.json \
  --frames-dir projects/<project>/qa/animatic-frames --sample-fps 1
```

Populate `qa/animatic-review.json`. The previs gate remains blocked until the
animatic decodes, matches program duration, was watched in real time, and has no
unresolved blockers.

### 5. Generation

Use the control ladder in
[references/generation-and-repair.md](references/generation-and-repair.md).

Read the matching route guide before creating the implementation skeleton:

- [programmatic](references/routes/programmatic.md)
- [external-video](references/routes/external-video.md)
- [timeline-edit](references/routes/timeline-edit.md)
- [hybrid](references/routes/hybrid.md)

Before a paid batch:

1. verify the model capability and exact input schema;
2. quote cost and expected completion time;
3. fix the prompt and reference set;
4. run one representative pilot shot;
5. log the model, version, parameters, references, prompt hash, output, cost,
   and verdict.

Append candidate records:

```bash
python scripts/record_candidate.py projects/<project> \
  --candidate S01-C01 --shot S01 --model provider/model-version \
  --control-mode image-to-video --prompt-file prompts/S01-v001.md \
  --output generations/S01-C01.mp4 --verdict pending
```

Judge complete motion, not a single frame. Select against pre-registered
criteria. Stop after repeated failures of the same cause and simplify the shot
or change the responsible layer.

If the user authorizes multiple agents, read
[parallel-production.md](references/parallel-production.md). Parallel work is
optional and applies only after shot, asset, and output boundaries are stable.

### 6. Edit, sound, graphics, and grade

Treat generated clips as raw takes. Cut for story, performance, rhythm, and
continuity. Keep trim handles. Use the same approved edit for picture, captions,
graphics, and audio.

Verify narration and dialogue timing from actual audio or transcripts. Build
sound as layers rather than adding a single music bed. Composite exact graphics
at final resolution. Normalize levels, color, grain, and sharpness across
sources.

### 7. Review and release

Run automated media inspection, inspect full-size evidence, and perform a cold
editorial review. Required categories are `technical`, `visual`, `editorial`,
`rights`, and `content`. Add `text` when exact on-screen text or captions exist,
and `audio_visual` when the program has audio. VLM output may screen defects but
cannot replace human judgment for taste, story, claims, or brand approval.

QA checks must name the acceptance IDs they settle, state what was actually
observed, use the declared method, and use hashed evidence objects with a
provenance role. Every blocking acceptance needs a passing check. Self-review
cannot pass a project whose policy requires independent review.

For an image-only review pass, generate a contact-sheet overview:

```bash
python scripts/make_contact_sheet.py renders/final.mp4 \
  --output-dir qa/contact-sheets
```

Treat sheets as navigation. Native-resolution individual frames and motion
samples remain the evidence used for acceptance.

Generate a technical report:

```bash
python scripts/inspect_media.py renders/final.mp4 \
  --project projects/<project> \
  --output projects/<project>/qa/technical-report.json \
  --frames-dir projects/<project>/qa/frames --sample-fps 2
```

Build the delivery manifest only after the files are final:

```bash
python scripts/build_manifest.py projects/<project> \
  --file master=renders/final.mp4 \
  --authority "Target platform or client specification"
```

Approve a stage only after reviewing its artifacts:

```bash
python scripts/approve_gate.py projects/<project> \
  --gate direction --owner "<name>"
```

Before delivery:

```bash
python scripts/validate_project.py projects/<project> --mode final
```

Read [references/qa-and-delivery.md](references/qa-and-delivery.md).

## Gate order

`brief` → `direction` → `script_clock` → `continuity` → `previs` →
`generation` → `edit` → `review` → `delivery`

Gate approvals contain file hashes. Changing approved content makes the gate
stale until it is reviewed and approved again. A pending, stale, rejected, or
unverifiable gate blocks release.

## Artifact contract

- `project.json`: deliverable, quality contract, budget, output spec, rights,
  policy, producer identity, content contract, motion contracts, and gate state.
- `brief.md`: human-readable intent and approval basis.
- `creative-bible.md`: selected direction, references, anti-references, visual
  and sound grammar.
- `script.md`: outline, spoken copy, required exact content, and section budget.
- `master-clock.json`: governing clock, BPM or spoken segments, time budget, and
  cue markers.
- `assets.json`: asset passports, reference roles, state variants, locks, and
  stress tests.
- `shots.json`: shot contracts, continuity, capability route, acceptance, and
  selected takes.
- `timeline.md`: edit order, in/out points, transitions, sound, graphics, and
  grade plan.
- `timeline.json`: machine-readable video/audio/caption tracks and beat markers.
- `animatic/animatic.mp4`: low-cost timed previsualization.
- `qa/animatic-review.json`: real-time review decision and unresolved blockers.
- `generation-log.jsonl`: append-only candidate history.
- `qa-report.json`: observed checks, findings, waivers, and verdict.
- `qa/technical-report.json`: deterministic media facts produced by inspection.
- `delivery-manifest.json`: final files, hashes, roles, destination, and rights
  status.

Read [references/artifacts.md](references/artifacts.md) when creating or
repairing these files.

For a project created with `0.1.0` or `0.2.0`, add missing artifacts and fields
without overwriting existing work:

```bash
python scripts/upgrade_project.py projects/<project>
```

The upgrade does not invent requirements, stronger acceptance, evidence
provenance, or independent approval. It leaves those items unresolved and
invalidates downstream approvals so a legacy project cannot silently pass the
new release rules.

## Stop conditions

Stop and request direction when:

- intended use, rights, consent, or disclosure is unresolved for public work;
- budget, provider access, or the required control surface is missing;
- master-clock segments do not fit the target duration or remain unresolved;
- the animatic is missing, cannot decode, was not watched in real time, or has
  unresolved story, timing, or comprehension blockers;
- a blocking requirement has no linked acceptance, or a blocking acceptance has
  no passing hashed evidence;
- only final-output frames support a preproduction identity or motion claim;
- a signature event has no located evidence inside its declared time window;
- required independent review is satisfied only by the producer;
- a Hero asset remains unlocked or fails its real-scene stress tests;
- generation keeps failing from the same cause and the next remedy changes
  scope, cost, model, or creative direction;
- only low-resolution frames, a contact sheet, or a successful API response
  exists as quality evidence;
- a rights, accessibility, safety, legal, or product-truth issue has no
  accountable resolution;
- final validation reports a blocker.

## Final response

Report the delivered files and specifications, chosen direction, per-shot pixel
sources and models, selected takes, passed checks, residual risks, rights and
provenance status, and any item requiring human confirmation. State whether the
result is automated preview, provisional, or release-approved. Do not describe
a draft, animatic, or unvalidated clip as the final video.

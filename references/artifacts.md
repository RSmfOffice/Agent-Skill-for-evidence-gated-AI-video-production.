# Project artifacts

Use the scaffold produced by `scripts/init_project.py`. Paths are relative to the
project directory.

## Directory layout

```text
<project>/
├── project.json
├── brief.md
├── creative-bible.md
├── script.md
├── master-clock.json
├── assets.json
├── shots.json
├── timeline.md
├── timeline.json
├── generation-log.jsonl
├── qa-report.json
├── delivery-manifest.json
├── inputs/
├── assets/
├── prompts/
├── generations/
├── selects/
├── animatic/
├── qa/
│   ├── review-handoff.json
│   ├── review-result.json
│   ├── review-state.json
│   ├── change-response.json
│   └── review-verification.json
├── rights/
├── renders/
└── delivery/
```

Do not store provider credentials in the project.

## project.json

Important fields:

- `project_id`, `title`, `goal`, `audience`, `platform`;
- `producer_id`: accountable production identity;
- `quality_mode`: `draft`, `standard`, or `hero`;
- `delivery_promise` and `target_response`;
- `clock`: summary `type` and source for `visual`, `voiceover`, `music`, or
  `dialogue`; detailed timing lives in `master-clock.json`;
- `output`: final path, duration, raster, frame rate, audio specification, and
  whether exact on-screen text or captions are required;
- `budget`: cap, spend, and currency;
- `quality`: thesis, hero frame, signature moment, sound motif, references, and
  rubric;
- `content_contract`: required, forbidden, and signature requirements;
- `motion_contracts`: opt-in spatial, temporal, and physical tests;
- `rights`: intended use, disclosure, and ledger;
- `policy`: candidate, retry, and fallback rules;
- `gates`: approval state and artifact hashes.

Keep gate state in `project.json`. Keep the content that was approved in the
stage files so hashes remain meaningful.

## brief.md

Human-readable source of truth for purpose, audience, delivery, constraints,
approval basis, and rights context. A `brief` gate approval hashes this file.

## creative-bible.md

Contains:

- two directions when required;
- selected direction and reason;
- reference and anti-reference table with concrete captions;
- visual thesis;
- hero frame, signature moment, and sound motif;
- palette, light, optics, texture, camera, performance, and edit rules;
- forbidden drift.

## content_contract and motion_contracts

`project.json` keeps project-specific requirements and optional motion tests.
The exact schemas and bidirectional requirement/acceptance rules are documented
in [requirements-and-traceability.md](requirements-and-traceability.md) and
[motion-contracts.md](motion-contracts.md).

## script.md

Human-readable script and time budget:

- one-line premise;
- outline or beat order;
- voiceover or dialogue copy;
- section time budget;
- required exact facts and copy;
- visual and audio cues.

Spoken copy should be checked against actual voice duration before shot timing
is locked.

## master-clock.json

The governing timing document:

```json
{
  "schema_version": 1,
  "type": "music",
  "source": "approved music asset or script",
  "duration_sec": 15,
  "bpm": 120,
  "segments": [
    {
      "id": "B01",
      "start_sec": 0,
      "end_sec": 5,
      "intent": "Hook and establish the product."
    }
  ],
  "markers": [
    {
      "time_sec": 4.8,
      "kind": "music-accent",
      "label": "first product reveal"
    }
  ]
}
```

`type` must match `project.clock.type`. Segments should cover the full program
without accidental gaps. Voiceover and dialogue segments need visible script
text or `spoken_text`. Music-driven work needs BPM and markers; visual-driven
work needs action or reveal markers.

## assets.json

Contains an `assets` array and optional sequence continuity defaults. Required
asset fields:

```json
{
  "id": "hero-product",
  "name": "Product",
  "type": "product",
  "role": "hero",
  "status": "draft",
  "descriptor": "Concrete permanent visual description",
  "invariants": ["product-geometry", "brand-color"],
  "allowed_variation": ["lighting", "camera-angle"],
  "references": [
    {
      "path": "assets/product-front.png",
      "provenance": "preproduction-reference",
      "use": "identity",
      "controls": "silhouette, controls, material",
      "must_not_control": "scene lighting or camera angle"
    }
  ],
  "stress_tests": [
    {
      "case": "front at delivery size",
      "result": "pass",
      "evidence": "qa/assets/product-front.jpg",
      "provenance": "render-test"
    }
  ],
  "rights": "approved-for-this-project"
}
```

Use `locked` only after required stress tests pass.

For Hero and Critical assets, at least one reference and one passing stress test
must come from a source other than `observed-final-frame`. See
[requirements-and-traceability.md](requirements-and-traceability.md).

## shots.json

Every shot includes:

- timing;
- editorial function, intent, information delta, and cut reason;
- frame and camera direction;
- action start, primary action, and end state;
- continuity fields;
- source and control mode;
- model/prompt/candidate records;
- acceptance criteria with `pass_if`, concrete `fail_if` examples, method, test
  domain, requirement links, and optional motion-contract links;
- review status, reviewer, evidence frames, and notes.

Use `approved` only after reviewing motion and cut relationships.

## generation-log.jsonl

One JSON object per candidate. The file is append-only. `record_candidate.py`
adds records and hashes prompt and output files when available.

Do not record a successful API response as a selected take. The candidate needs
an explicit visual verdict.

## qa-report.json

Contains:

- reviewer ID, reviewer kind, name, date, target, reviewed package, and human
  approval;
- verdict: `pending`, `pass`, `revise`, `reject`, or `waived`;
- checks with category, acceptance IDs, method, observed result, status,
  reviewer, hashed evidence objects, and timecode/region;
- findings with severity, evidence, impact, fix, owner, and status;
- residual risks.

Required categories for final release are `technical`, `visual`, `editorial`,
`rights`, and `content`. Add `text` when captions or exact on-screen text are
required, and `audio_visual` when the program has audio. Add `accessibility`
when captions are required.

## qa/technical-report.json

Generated by `inspect_media.py`. It records measured file facts, expected-spec
comparisons, full-decode status, sampled frames, observations, and file hash.

Regenerate it after any final-file change.

## qa/review-handoff.json

Required for `standard` and `hero` review under Skill `0.5.1+`. It binds the
exact reviewed media and gives an independent reviewer:

- generation and review Skill versions;
- final media path and SHA-256;
- delivery size, platform, and quality mode;
- stable shot, graphic, event, and deliberate-effect anchors;
- required observations and linked acceptance;
- intentional choices with allowed effects and must-preserve items;
- route, model, prompt/source, and reference context;
- known-clean and known-failure controls;
- exclusions and unavailable checks.

The full contract is in [review-handoff.md](review-handoff.md).
`schema_version` is `2`. Source paths are project-relative and carry shared
SHA-256 hashes; `project.json` uses `json-without-gates` so gate approvals do not
invalidate the intent hash.

## qa/review-result.json

Produced by the review side. It contains coverage statuses, evidence-bound
issues, intentional-overlap judgments, generation change requests, limitations,
and residual risks. It must bind the same media hash as the handoff.

Initial review uses `phase: "initial"` with no change requests. After explicit
user issue calibration it becomes `phase: "calibrated"` and may contain change
requests.

## qa/review-state.json

Records the mandatory issue-list stop and user calibration receipt:

- `status`: `awaiting_user_issue_calibration`, `calibrated`,
  `repair_in_progress`, `verification_pending`, or `complete`;
- initial review result SHA-256 and issue-list presentation time;
- human calibration status, user, time, actions, and notes.

Final release requires `status: "complete"` and
`human_calibration.status: "confirmed"`.

## qa/change-response.json

Produced by the generation side after a review. It maps every change request to
`accepted`, `rejected`, or `deferred`, records the responsible layer and changed
files/rules, preserves approved work, supplies the new media hash, and reports
original-case, known-clean, negative-example, and residual-risk regression.

## qa/review-verification.json

Produced by a new independent review round after accepted changes. It binds the
prior review, accepted request IDs, original and changed media hashes, reviewer
independence, and all required regression results. A generation response alone
is provisional; only a matching `review-verification.json` with
`result: "validated"` closes the loop.

## timeline.md

The edit contract:

- shot order;
- in/out points;
- transitions and cut motivation;
- handles;
- text and graphics;
- dialogue, voice, music, and sound effects;
- color and finishing;
- variants.

## timeline.json

Machine-readable edit contract:

```json
{
  "schema_version": 1,
  "duration_sec": 15,
  "tracks": [
    {
      "id": "V1",
      "type": "video",
      "role": "primary",
      "items": [
        {
          "id": "V1-01",
          "shot_id": "S01",
          "source": "selects/S01.mp4",
          "source_in": 0.4,
          "source_out": 4.1,
          "timeline_start": 0,
          "duration": 3.7,
          "transition": "hard-cut"
        }
      ]
    }
  ],
  "beat_markers": []
}
```

There must be exactly one primary video track. Its items cover the program with
no accidental gaps or overlap. If the output has audio, the timeline needs an
audio, voice, or music track. Captions or graphics are required when declared by
the output contract.

## animatic

- `animatic/animatic.mp4`: timed low-fidelity preview with temporary audio.
- `qa/animatic-technical-report.json`: measured file facts from
  `inspect_media.py --expected animatic`.
- `qa/animatic-review.json`: reviewer, real-time viewing status, decision,
  issues, and unresolved blockers.

The animatic technical report must match the animatic file's SHA-256 and target
program duration. A still contact sheet does not replace it.

## delivery-manifest.json

Generated by `build_manifest.py` after files are final. It stores each
deliverable's role, relative path, size, and SHA-256, plus spec authority and
rights status. Update it whenever a delivered byte changes.

## Gate approval

Canonical artifacts:

```text
brief       -> brief.md
direction   -> creative-bible.md
script_clock -> script.md, master-clock.json
continuity  -> assets.json
previs      -> animatic/animatic.mp4, qa/animatic-technical-report.json,
               qa/animatic-review.json, qa/previs-review.md, shots.json,
               timeline.md, timeline.json
generation  -> generation-log.jsonl, shots.json
edit        -> timeline.md, timeline.json
review      -> qa-report.json, qa/technical-report.json,
               qa/review-handoff.json, qa/review-result.json,
               qa/review-state.json,
               qa/change-response.json, qa/review-verification.json
delivery    -> delivery-manifest.json
```

Use:

```bash
python scripts/approve_gate.py <project> --gate <gate> --owner "<name>"
```

The script hashes the artifacts. If a hashed artifact changes, the approval is
stale and final validation fails until the artifact is reviewed again.

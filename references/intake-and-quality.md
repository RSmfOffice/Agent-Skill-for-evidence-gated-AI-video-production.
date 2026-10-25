# Intake and quality contract

Use this reference before direction, shot planning, or paid generation.

## Establish the production contract

Capture the following in `brief.md` and `project.json`:

- **Purpose:** intended use, audience, publication context, and success signal.
- **Promise:** one sentence describing what the viewer should understand, feel,
  remember, or do.
- **Delivery:** platform, placement, master specifications, variants, captions,
  safe areas, and required metadata.
- **Master clock:** whether picture, voiceover, music, or dialogue governs time.
- **Must include:** exact product, people, claims, actions, copy, logos, data, or
  legal text.
- **Must avoid:** forbidden imagery, claims, styles, likenesses, competitors,
  artifacts, or editing conventions.
- **Approval:** who can approve story, visual direction, claims, rights, and
  final release.
- **Limits:** deadline, compute, paid budget, retry cap, available footage, and
  required model access.
- **Rights:** ownership or license for supplied media, music, fonts, likeness,
  voice, locations, and generated outputs; consent and AI-disclosure needs.

If a field is unknown, mark it unresolved. Do not silently invent a public-use
right, a factual claim, or a platform requirement.

Translate must-include and must-avoid language into `content_contract` entries
with stable IDs and observable meanings. Link those IDs to shot acceptance
criteria before approving direction. See
[requirements-and-traceability.md](requirements-and-traceability.md).

## Classify quality mode

- `draft`: exploration or internal preview. A draft may be useful but cannot
  pass final release.
- `standard`: ordinary public or internal deliverable. Requires locked Hero and
  Critical assets, approved shots, technical QC, visual QC, editorial review,
  and rights review.
- `hero`: launch, brand, paid, or reputation-critical work. Requires
  differentiated direction options, continuity stress tests, candidate
  selection, three evidence points per shot, and a cold review.

Use the smallest mode that respects the consequence of failure. Do not upgrade
the implementation burden merely to look thorough.

## Reference-video intake

When the user supplies a video as inspiration, analyze:

- transcript and information order;
- hook, beats, turn, and payoff;
- scene boundaries and average shot length;
- shot sizes, lens behavior, blocking, and camera movement;
- lighting, palette, texture, typography, and sound;
- what makes the reference effective and what should not be copied.

Return two or three differentiated concepts for the new purpose. Extract
observable principles; do not reuse unlicensed footage, distinctive frames, or
protected characters as generation references.

## Reference board

Every reference entry has:

- source and rights status;
- type: story, composition, motion, design, continuity, sound, or
  anti-reference;
- a concrete caption: what exact property the production should take from it;
- a scope: what this reference may control;
- a limit: what it must not control.

An image that the user merely likes is not yet a reference. Ask what visible or
audible property it specifies.

Maintain anti-references with observable failures, such as "plastic skin,"
"floating feet," "centered stock-footage iconography," or "unmotivated orbiting
camera." Do not use a generic ban such as "bad quality."

## Quality rubric

Use the weighted defaults in `project.json` unless the project needs different
priorities:

- story or message clarity: 25;
- visual direction and composition: 20;
- motion, performance, and continuity: 20;
- edit, sound, and information pacing: 20;
- technical, accessibility, and delivery quality: 15.

Weights are for comparison, not for averaging away blockers. A critical failure
in product truth, identity, safety, rights, accessibility, or required copy
fails regardless of total score.

Before generating, write observable acceptance statements. Prefer:

- "the same left-hemisphere logo remains legible from 0.0 to 4.9 s";
- "the rider's right foot remains on the pedal through the downstroke";
- "the offscreen destination stays screen-right across S02-S04";
- "the CTA appears after the claim and remains readable for at least 2.5 s."

Avoid untestable criteria such as "premium," "cinematic," or "high quality" with
no observable consequence.

## Budget and approval

For every paid batch, record:

- models and candidates;
- expected unit price and total quote;
- expected queue time;
- planned retries and maximum candidates;
- stop threshold.

Before the first paid call, verify that current spend plus quoted spend plus
reserved spend for required remaining work is within the cap. A failure or
timeout is not permission to submit a duplicate job. Poll or await the existing
job first.

No silent model substitution, quality downgrade, loss of audio, or switch from
motion to stills after approval. State the change and obtain approval when it
materially changes the deliverable or cost.

## Preflight outcome

Report one of:

- `ready`: required tool, model, rights, and budget conditions are present;
- `degraded`: a non-critical capability is missing and a safe fallback is
  approved;
- `blocked`: a required capability, right, claim, or approval is missing.

Do not begin an expensive batch while the outcome is blocked.

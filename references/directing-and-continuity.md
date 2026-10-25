# Directing and continuity

Use this reference when shaping story, beats, shots, blocking, keyframes,
performance, sound, or edit decisions.

## Start with an editorial job

For each beat, write one sentence:

> The audience should notice **[subject or change]**, understand
> **[relationship or information]**, and feel **[quality]**, while
> **[secondary information] remains secondary or concealed**.

A shot is not defined by a style adjective. It is a controlled change in
attention, knowledge, space, or feeling.

Common editorial functions:

- orient the viewer to geography or scale;
- reveal new information;
- witness a performance or consequence;
- identify a point of view;
- compare subjects or states;
- isolate a detail, face, gesture, or object;
- provide a reaction;
- transition by direction, action, shape, light, or sound;
- land the payoff.

If a shot does not serve one of these jobs, cut it or merge it.

## Build beats before shots

For narrative work, identify:

- literal event;
- dramatic question;
- pressure or conflict;
- what the scene is actually about;
- emotional movement from opening state to closing state;
- a visual thesis that can be photographed.

For non-narrative work, use the delivery promise and proof structure: hook,
claim, demonstration or evidence, consequence, action. Do not invent dramatic
subtext for a product demo, but do require a visible reason for each beat.

Watch for template output. If the same generic imagery could sell any product,
replace it with a surface, action, or evidence unique to this subject.

## Write a usable shot contract

Each shot should include:

- stable shot ID and version;
- editorial function, intent, information delta, and cut reason;
- start and end time, usable duration, and trim handles;
- framing and frame landmarks;
- camera distance, height, angle, field of view, focus, and stabilization;
- start state, one primary action, and end state;
- blocking, eyeline, entry/exit, and prop contacts;
- camera movement geometry, motivation, path, speed, and end point;
- light direction, quality, contrast, practicals, and changes;
- screen direction, axis side, and cut relationship to adjacent shots;
- asset tags and state variants;
- exact text treatment kept outside generated pixels;
- audio cue, ambience, dialogue, or silence;
- acceptance criteria;
- risk level and plausible fallback.

Do not use shot-size abbreviations alone. State what is visible, such as "full
figure with feet and doorway" or "shoulders and head with CTA-safe space."

## Camera and blocking heuristics

- Let the audience's required information choose shot size.
- Treat camera position as the source of perspective. Focal length and distance
  work together.
- Give camera movement a job: reveal, follow, connect, isolate, destabilize, or
  change relationship.
- Specify start frame, path, cue, speed profile, and end frame.
- Prefer a locked camera until movement earns its place.
- State what moves: subject, camera, both, or neither.
- Preserve the line of action when orientation matters. Cross it only for a
  motivated rupture and re-establish space.
- Give adjacent shots enough difference in size, angle, or subject emphasis to
  cut cleanly.
- Reserve complex simultaneous action and camera movement for cases where the
  model or renderer has demonstrated control.

These are production heuristics, not universal laws. A deliberate jump cut,
surreal floating, or montage discontinuity can be correct when declared.

## Asset passports

Create one passport per reusable asset:

- `id` and human-readable name;
- type: character, product, location, prop, UI, typography, or programmatic;
- role: hero, critical, supporting, or decorative;
- canonical descriptor in concrete language;
- state variants such as wet, open, damaged, or selected;
- stable reference files;
- each reference's use, control scope, and forbidden scope;
- locked invariants;
- allowed variation;
- stress-test cases and results;
- rights and consent status.

Keep model-specific styling out of the permanent identity descriptor. Put scene
lighting, wardrobe state, pose, lens, and action in the shot.

Use separate descriptors for meaningful state changes. Do not let one reference
silently imply a new costume, product geometry, age, logo, or prop state.

## Asset lock tests

Test against the conditions that can break the real production:

- front, 3/4, profile, or relevant product angles;
- every shot size that must carry identity;
- the actual scene lighting and palette;
- the co-stars, hands, or props that share frame;
- the extreme expression, action, or articulation;
- small delivery size and full-resolution crop;
- every required state variant.

For Hero characters or products, prefer at least eight diverse stress cases and
require all critical invariants to pass. If budget forces fewer tests, record
the residual risk. Static tests do not prove video motion; use representative
motion samples for the most failure-prone action.

## Sequence continuity

Maintain a sequence-level record of:

- geography and fixed anchors;
- screen-left/right placement;
- travel direction and axis side;
- eyeline targets;
- key and fill direction, time of day, practicals;
- palette and grade logic;
- costume, product, prop, and UI states;
- which shot introduces and resolves each state.

The end state of shot A should be a credible start for shot B, or the cut should
be an intentional discontinuity.

## Sound and editing

Plan sound in layers:

1. room tone;
2. ambience;
3. foley;
4. spot effects;
5. dialogue or voice;
6. music.

Derive timing from actual audio or transcripts. For music-driven work, define
beats, sections, accents, and a small number of sync events; do not force every
cut onto a beat.

Editing decisions should state in/out points, transition type, and motivation.
Keep enough handles to move a cut. Prefer a cutaway, trim, or montage solution
before regenerating an otherwise usable shot.

## Direction selection

For Hero work, compare at least two directions using the same brief:

- visual thesis;
- reference board;
- lens and camera grammar;
- palette and light;
- performance register;
- edit tempo;
- sound motif;
- one representative hero frame.

Select in writing. Do not combine several directions by default. A coherent
single direction is stronger than an average of incompatible references.

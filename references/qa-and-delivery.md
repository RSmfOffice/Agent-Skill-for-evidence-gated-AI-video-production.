# QA and delivery

Use this reference for shot review, final review, export, and release.

## Keep evidence lanes separate

- **Documented fact:** approved brief, client spec, platform requirement, legal
  requirement, or measured file fact.
- **Empirical observation:** what was seen, heard, measured, or extracted from
  the actual asset.
- **Production heuristic:** professional judgment used where no hard requirement
  exists.

Do not present a heuristic as a platform rule or a measured fact as a creative
opinion.

## Pre-register acceptance

Before generation, define pass/fail criteria per shot and for the full program.
Critically, define "blocker" for this project. Common blockers:

- wrong product, identity, price, claim, or required text;
- missing rights or consent;
- unreadable CTA or legal copy;
- impossible-to-cut motion, missing action, or broken continuity;
- corrupt file, missing audio, or platform rejection;
- unsafe or inaccessible content where compliance is required.

A minor visual artifact may be accepted if it is invisible at intended size and
does not undermine the subject. A face, product, logo, price, claim, or safety
instruction receives stricter treatment.

## Review passes

Run these as separate passes:

1. **Plan conformance:** required beats, claims, assets, and CTA exist.
2. **Technical:** file integrity, streams, timing, audio, captions, color, and
   platform constraints.
3. **Shot visual:** identity, product truth, anatomy, motion, contact, light,
   geometry, screen direction, and compositing.
4. **Sequence editorial:** story, attention, pacing, cuts, continuity, sound,
   and comprehension.
5. **Rights and provenance:** sources, licenses, likeness, voice, synthetic
   disclosure, and output-use terms.
6. **Cold review:** a reviewer or review pass that has not been looking at the
   work throughout.

Do not combine these into a single "does it look good?" question.

Conditional review categories:

- `text` when captions, exact labels, prices, legal copy, or logos appear;
- `audio_visual` when the program has speech, music cues, lip sync, or timed SFX;
- `content` for product truth, factual claims, identity, and story meaning;
- `accessibility` when captions or accessible media deliverables are required.

The base final categories are `technical`, `visual`, `editorial`, `rights`, and
`content`.

Every check that settles a project requirement names its `acceptance_ids`, test
method, observed result, and hashed evidence. Read
[requirements-and-traceability.md](requirements-and-traceability.md).

## Evidence requirements

Every significant quality claim needs evidence:

- source file and SHA-256;
- acceptance and requirement IDs;
- test method and test domain;
- shot or program ID;
- timecode or frame;
- artifact path;
- region or full frame;
- reviewer and date;
- criterion and verdict;
- observed result, not only a status word;
- severity and repair status.

Evidence entries use a provenance role:

- `preproduction-reference`;
- `canonical-source`;
- `render-test`;
- `observed-final-frame`;
- `independent-review`.

Final-output frames can prove what the output looks like; they cannot by
themselves prove that an identity or motion system was controlled before
production.

For Hero video, inspect:

- start, action middle, and end of each shot;
- every internal cut;
- every transition;
- full-resolution crops of faces, hands, products, logos, UI, and legal copy;
- a sampled motion sweep at approximately two frames per second or better;
- the final file at intended size and on target-class playback.

A contact sheet is an overview. It cannot pass identity, text, motion, or seam
quality.

Use `scripts/make_contact_sheet.py` only to navigate a long program or to give an
image-only reviewer an overview. Full-size individual frames and motion samples
remain the acceptance evidence.

## Technical inspection

Use `scripts/inspect_media.py` to record measured facts. Verify against the
approved deliverable:

- file opens and decodes end-to-end;
- container, codecs, resolution, pixel aspect, frame rate, duration, and bit
  depth;
- color primaries, transfer, matrix, and range;
- audio sample rate, channels, codec, loudness, and true peak;
- caption/subtitle streams or sidecars;
- black, freeze, flash, silence, clipping, and sync anomalies;
- final-file hash.

Automated checks do not decide whether a black frame is an intentional fade or
whether a synthetic product is misleading. Record observations and review them
in context.

## Visual and motion inspection

Watch the whole file without pausing, then scrub it slowly, then inspect native-
resolution evidence. Look for:

- identity, age, face, hair, wardrobe, and product drift;
- finger, hand, tooth, limb, eye, and mouth artifacts;
- foot sliding, floating, impossible contacts, rubber motion, and broken
  causality;
- object popping, duplication, melting, fusion, penetration, or occlusion;
- camera acceleration, accidental reverses, axis jumps, or impossible paths;
- text, labels, logos, prices, dates, UI, QR codes, and graphs;
- light direction, shadow, reflection, weather, time, and palette continuity;
- matte edges, grain mismatch, resolution changes, and composite seams;
- captions and lower thirds covering critical action;
- performance, intention, gaze, breath, and emotional readability.

Judge at both intended size and detailed crop. Some generative artifacts vanish
on mobile; a pause-frame artifact may not be a blocker. Conversely, a small logo
error may be critical at platform size.

## Video-specific quality dimensions

For edit or VFX comparisons, adapt the VEFX-inspired dimensions:

- `instruction-following`: did the requested edit occur without unrelated
  semantic changes?
- `render-quality`: clarity, temporal stability, and physical plausibility;
- `edit-exclusivity`: were only intended regions and properties changed?

For generative shots, add identity fidelity, action completion, camera control,
cutability, and product truth. These metrics support review; they do not replace
editorial judgment.

## Findings and waivers

Use:

- `blocker`: cannot release;
- `major`: must fix or receive accountable waiver before normal release;
- `minor`: fix if efficient; document acceptance;
- `note`: observation or optional improvement.

Each finding records category, issue, evidence, impact, fix, owner, retest
requirement, and status. Rights, consent, accessibility, safety, and legal
compliance cannot be waived by the agent.

A waiver is valid only for a non-prohibited issue and includes owner, reference,
reason, accepted impact, and date. A waiver does not erase the finding.

## Release rule

Final validation passes only when:

- all required gates are approved and their hashes are current;
- every blocking content requirement has linked acceptance and passing QA;
- every blocking acceptance has located, hashed evidence using its declared
  method;
- every signature event has passing evidence inside its declared time window;
- motion contracts, when declared, have linked acceptance and evidence;
- the master clock covers the target duration with coherent segments and markers;
- the animatic decodes, matches the program duration, was watched in real time,
  and has no unresolved blockers;
- `timeline.json` has a complete primary video track and required audio,
  caption, or graphic tracks;
- all used assets are locked;
- every shot is approved and has the required native-resolution evidence;
- technical inspection passed on the actual final file;
- required visual, editorial, rights, and accessibility checks passed;
- no open blocker or major issue remains;
- every waiver is valid and in a waivable category;
- the reviewer satisfies the project's independence policy; and
- the delivery manifest matches the final files byte-for-byte;
- the final quality mode is `standard` or `hero`.

## Delivery package

Record:

- package and campaign IDs;
- destination and deliverable role;
- version and creation date;
- locale and market;
- duration, aspect, raster, frame rate, color, audio, and caption specs;
- spec authority and verification date when external;
- master and platform derivatives;
- audio stems, captions, thumbnails, and metadata when required;
- SHA-256 for every delivered file;
- sources, licenses, consent, provenance, model usage, and AI disclosure;
- QC result, known waivers, residual risks, and approver.

Export derivatives from the approved master, not from an already compressed
social file. Re-check the delivered files after any platform transcode or copy
when possible.

## Final report

Use:

```text
STRUCTURE: PASS / FAIL
TECHNICAL: PASS / FAIL
VISUAL: PASS / FAIL
EDITORIAL: PASS / FAIL
RIGHTS: PASS / FAIL
CONTENT: PASS / FAIL
TEXT: PASS / FAIL / NOT APPLICABLE
AUDIO_VISUAL: PASS / FAIL / NOT APPLICABLE
RELEASE LEVEL: RELEASE / PROVISIONAL / AUTOMATED PREVIEW

Delivered files:
Specifications:
Shot sources and models:
Evidence:
Residual risks:
Waivers:
Human confirmation required:
```

Do not collapse these into one unconditional "PASS."

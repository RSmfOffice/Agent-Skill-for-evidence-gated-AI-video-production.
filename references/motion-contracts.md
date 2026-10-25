# Motion contracts

Motion contracts make temporal claims testable without turning the core Skill
into a library of one-off object rules.

Declare a motion contract only when a shot depends on a physical, temporal,
spatial, or audiovisual relationship that must remain coherent.

## Contract shape

```json
{
  "id": "M1",
  "type": "fixed-contact",
  "subjects": ["tool-a", "surface-b"],
  "applies_to_shots": ["S02"],
  "constraints": {
    "contact_visible": true,
    "separation_tolerance_px": 1
  },
  "blocking": true,
  "acceptance_ids": ["A4"],
  "evidence": [
    {
      "path": "qa/motion/contact-test.json",
      "role": "render-test",
      "sha256": "64 hexadecimal characters"
    }
  ]
}
```

The constraint fields are project-specific. Validators should check that the
contract exists, is linked bidirectionally to acceptance, and has evidence.
They should not guess that every moving object obeys the same physics.

## Supported contract types

### `rolling-contact`

Validate that circular travel and surface travel are coherent. Applicable to
wheels, rollers, gears presented as rolling, or tracked objects.

Useful constraints:

- radius or diameter;
- angular speed;
- linear surface speed;
- direction;
- tolerance.

### `fixed-contact`

Validate intentional contact between hands, feet, tools, surfaces, props, or
characters.

Useful constraints:

- contact point or region;
- permitted gap;
- contact duration;
- which frames or beats must maintain contact.

### `speed-coherence`

Validate relative speeds between a tracked subject, foreground, and background
parallax layers.

Useful constraints:

- reference travel speed;
- layer speed ratios;
- direction;
- allowed acceleration or drift.

### `rigid-joint`

Validate preserved segment lengths, hinge attachment, or rigid-body relations.

Useful constraints:

- pivot;
- segment lengths;
- allowed rotation;
- minimum and maximum opening.

### `cloth-root-attachment`

Validate that a cloth, hair, cable, or ribbon remains attached to its root while
the free portion moves.

Useful constraints:

- root object or point;
- minimum visible movement;
- attachment tolerance;
- layering.

### `fluid-flow`

Validate direction, continuity, and plausible motion for water, smoke, or other
flowing media.

Useful constraints:

- direction;
- speed relation to another layer;
- continuity;
- turbulence allowed.

### `collision`

Validate contact, blocking, deflection, or intended pass-through.

Useful constraints:

- interacting objects;
- expected contact time;
- post-contact state;
- whether penetration is forbidden.

### `screen-direction`

Validate travel, eyeline, or reveal direction across shots.

Useful constraints:

- expected direction;
- axis side;
- allowed reversals and the motivating event.

### `lip-sync`

Validate speech and mouth timing.

Useful constraints:

- approved audio or transcript;
- start and end tolerance;
- languages and visemes;
- expected silence.

## Programmatic route

Prefer executable assertions or structured tests:

- geometry constraints;
- segment length preservation;
- wheel-to-surface travel equations;
- frame-distance checks;
- audio marker alignment;
- component snapshots.

Store the output as a JSON, CSV, or image evidence record and hash it.

## External-video route

Prefer:

- a short motion sample;
- consecutive-frame strips;
- contact-point crops;
- a tracked observation of direction or cyclic motion;
- lip-sync or audio-sync measurement when available.

Do not require exact pixel coordinates from a generative model. Use semantic
constraints and project-appropriate tolerances.

## Anti-overfitting rule

The generic contract types are allowed to cover a wide range of scenes. A
bicycle, character, robot, cloth, or liquid should only instantiate a contract
in its project.

Do not:

- require wheel checks for videos without rolling objects;
- assume stylized physics must match live action;
- create one global tolerance for every scene;
- treat a decorative object as a mechanical system without a declared risk;
- rewrite the core after one failed shot.

If a new failure does not fit an existing type, add a reusable motion class only
after it appears across multiple unrelated projects. Otherwise keep it in the
project contract.

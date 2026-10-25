# Hybrid route

Use when generated, programmatic, and existing assets occupy different layers or
shots.

## Declare boundaries

For every shot and layer, state:

- source type;
- control mode;
- owner of exact text, UI, logos, and data;
- resolution, frame rate, color space, alpha, and audio expectations;
- handoff file and accepted version.

A common split is:

```text
generated/keyframed background or performance
+ deterministic product UI, text, charts, and logo
+ approved audio and captions
+ shared edit and grade
```

## Integration contract

- Composite on the same timeline and timebase.
- Use approved clean plates where overlays must remain exact.
- Match perspective, grain, blur, light direction, color, and black levels.
- Keep transparent assets free of matte halos and accidental background.
- Normalize audio at the mix stage, not by regenerating accepted picture.
- Check source boundaries and every transition between media types.

## Checks

- Each source is evaluated by the rules appropriate to that source.
- A generated shot passing does not imply programmatic or footage layers pass.
- Joints and state changes that cross source boundaries have dedicated evidence.
- The final composited program passes the same edit and delivery gates as a
  single-source project.

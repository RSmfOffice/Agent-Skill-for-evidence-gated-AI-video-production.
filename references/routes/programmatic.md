# Programmatic video route

Use for product demos, UI, data graphics, kinetic type, 2D/3D scenes, and any
deliverable where exact geometry, text, timing, or repeatability matters.

## Renderer fit

- **Remotion:** React/TypeScript timelines, exact typography, UI mockups,
  captions, reusable scenes, and deterministic frame rendering.
- **HyperFrames/HTML:** HTML/CSS/GSAP-native compositions and browser previews.
- **Manim:** mathematical, scientific, and diagram-led explanation.
- **Canvas/WebGL/Three.js:** interactive-looking graphics, particles, and 3D.
- **Pillow/SVG:** controlled 2D assets, simple motion, and deterministic stills.
- **FFmpeg:** assembly, trimming, compositing, timing, audio, and final encoding.

Choose one primary renderer and keep the final timeline in `timeline.json`.
Do not use a renderer only because it is available.

## Project skeleton

```text
project/
├── src/                  # scenes, components, or generators
├── public/               # approved fonts, logos, images, footage, audio
├── prompts/              # keyframe or external-asset prompts, if any
├── animatic/             # low-fidelity preview output
├── selects/              # accepted rendered clips
├── renders/              # final master and derivatives
└── qa/                   # evidence, technical report, and review
```

Keep timing in frames derived from `fps`, not unexplained magic numbers. Keep
colors, typography, safe areas, and asset paths in project configuration.

## Implementation checks

- Layout at final aspect and intended viewing size.
- Text overflow, line breaks, font fallback, and safe areas.
- Composition at first, middle, and last frame of each scene.
- Asset resolution and correct image/video loading.
- Layer order, mattes, transparency, and blend behavior.
- Deterministic frame numbers and no unexplained dead air.
- Audio sample alignment and loudness on the rendered file.
- Final encode through the same approved timeline.

## Output contract

Produce a low-resolution animatic before the high-resolution master when timing
or composition is uncertain. Keep source components and a command that
reproduces every accepted render.

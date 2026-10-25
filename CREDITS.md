# Design credits and source boundaries

This repository is an original implementation. No source code was copied from
the projects below. Their public workflows were reviewed on 2026-10-25 for
architecture and craft patterns, then independently restated and implemented.

## Projects that informed the design

- [calesthio/OpenMontage](https://github.com/calesthio/OpenMontage) — pipeline
  manifests, capability preflight, stage checkpoints, decision logging, and
  production-state thinking. The repository is AGPLv3; no code is copied.
- [calesthio/generative-media-skills](https://github.com/calesthio/generative-media-skills)
  — provider-independent directing, previsualization, continuity, generated
  media QA, and delivery craft. Licensed MIT.
- [machina-exm/film-studio-skills](https://github.com/machina-exm/film-studio-skills)
  — asset passports, locked references, stress testing, and generation logs. No
  root license file was visible in the reviewed snapshot; only general methods
  informed this work and no code or substantial wording is reused.
- [wuwangzhang1216/DirectorSKILL](https://github.com/wuwangzhang1216/DirectorSKILL)
  — editorial shot functions, capability-first prompt shapes, continuity
  geometry, failure diagnosis, and cost-ordered repair. Licensed MIT.
- [scenario-labs/skills](https://github.com/scenario-labs/skills) — fixed-input
  model comparison, spend gates, schema discovery, and keyframe chaining.
  Reviewed video skills are MIT-licensed; provider-specific APIs are isolated
  from this implementation.
- [cablate/ai-video-generation-skills](https://github.com/cablate/ai-video-generation-skills)
  — evidence levels, control-mode priority, experiment logging, and deliverable
  verification. Licensed MIT.
- [zenstory-ai/drama-skills](https://github.com/zenstory-ai/drama-skills) —
  file-based creative decisions, reference roles, continuity locks, production
  previews, and independent review. Licensed MIT.
- [Bomx/super-video-maker-skill](https://github.com/Bomx/super-video-maker-skill)
  — recipe routing, job state, machine-readable stage results, copy gates, and
  audio-derived timing. No root license file was visible in the reviewed
  snapshot; no code is copied.
- [haidrrrry/claude-remotion-skill](https://github.com/haidrrrry/claude-remotion-skill)
  — motion-design craft and the mandatory render-inspect-fix loop. Licensed MIT.
- [Visko-Platform/VEFX-Bench](https://github.com/Visko-Platform/VEFX-Bench) —
  instruction-following, render-quality, and edit-exclusivity dimensions for
  video-edit evaluation. Licensed Apache-2.0.

Project names, licenses, and repository contents can change. Re-verify the
license and the exact revision before copying any third-party implementation or
substantial text.

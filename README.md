# Agent-Skill-for-evidence-gated-AI-video-production.

**English** | [简体中文](README.zh-CN.md)

用于增强 DeepSeek 在接入 Codex 环境下的视频生成能力。

Used to enhance DeepSeek's video generation capability when connecting to the
Codex environment.

## Video Production Director

A quality-first Agent Skill for planning, generating, editing, reviewing, and
delivering AI, programmatic, hybrid, or footage-based videos.

Most prompt collections optimize one call. This skill maintains production
memory across calls: creative direction, asset continuity, shot contracts,
model capability, candidate evidence, edit decisions, technical QC, rights, and
final delivery.

## What it changes

- Chooses control before model: deterministic assets and footage first,
  image-to-video and keyframe control next, text-to-video for exploration.
- Treats references as specifications with control scope and exclusions.
- Locks recurring people, products, locations, props, and state variants before
  expensive generation.
- Gives every shot an editorial job, one primary action, a camera motivation,
  visible start and end states, and pre-registered acceptance criteria.
- Records every candidate's prompt, model, version, references, parameters,
  cost, output hash, and verdict.
- Separates technical, visual, editorial, and rights review.
- Uses hashed stage approvals. Changing approved content invalidates the gate.
- Requires native-resolution shot evidence and an actual full-file technical
  inspection before release.

## Workflow

```text
intake
  -> creative direction
  -> continuity and asset locks
  -> shots and animatic
  -> capability-based generation
  -> candidate selection
  -> edit, sound, graphics, grade
  -> technical + visual + editorial + rights review
  -> delivery manifest
```

The entry skill routes to four focused references:

- `intake-and-quality.md`
- `directing-and-continuity.md`
- `generation-and-repair.md`
- `qa-and-delivery.md`

`artifacts.md` explains the project state consumed by the scripts.

## Install

Copy this repository into your Codex skills directory:

```bash
git clone <repository-url> \
  "${CODEX_HOME:-$HOME/.codex}/skills/video-production-director"
```

Or use a compatible skills installer:

```bash
npx skills add <owner>/<repository>
```

Start a new Codex conversation after installation so the skill is rediscovered.

## Quick start

Create a project:

```bash
python scripts/init_project.py projects/my-video \
  --title "My Video" --mode hero
```

Fill the brief and creative direction, then validate the planning state:

```bash
python scripts/preflight.py --project projects/my-video
python scripts/validate_project.py projects/my-video --mode plan
```

Hash and approve a completed stage:

```bash
python scripts/approve_gate.py projects/my-video \
  --gate direction --owner "director"
```

After rendering, inspect the actual file:

```bash
python scripts/inspect_media.py projects/my-video/renders/final.mp4 \
  --project projects/my-video \
  --output projects/my-video/qa/technical-report.json \
  --frames-dir projects/my-video/qa/frames \
  --sample-fps 2
```

Create the delivery manifest:

```bash
python scripts/build_manifest.py projects/my-video \
  --file master=renders/final.mp4 \
  --authority "Client or platform specification" \
  --rights-verified
```

Enforce release:

```bash
python scripts/validate_project.py projects/my-video --mode final
```

## Requirements

- Python 3.10 or newer.
- `ffmpeg` and `ffprobe` for automatic media inspection.
- Provider-specific API tools, renderers, or MCP servers only when the selected
  production route requires them.
- Image/video understanding tools are optional. They screen defects; they do
  not replace an accountable final visual review.

The validation and project-state scripts use only the Python standard library.
If FFmpeg is not on `PATH`, set `FFMPEG_BIN` and `FFPROBE_BIN` to the two
executables. `preflight.py` reports whether the inspection route is ready.

## Project state

```text
project/
├── project.json
├── brief.md
├── creative-bible.md
├── assets.json
├── shots.json
├── timeline.md
├── generation-log.jsonl
├── qa-report.json
├── delivery-manifest.json
├── inputs/
├── assets/
├── prompts/
├── generations/
├── selects/
├── qa/
├── rights/
├── renders/
└── delivery/
```

## Scripts

| Script | Purpose |
| --- | --- |
| `init_project.py` | Create the stateful project scaffold |
| `preflight.py` | Check Python, media tools, project state, and model profiles |
| `validate_project.py` | Validate planning structure or enforce final release |
| `approve_gate.py` | Hash stage artifacts and record explicit approval |
| `record_candidate.py` | Append a generated candidate with model, prompt, cost, and hashes |
| `inspect_media.py` | Probe, decode, sample frames, measure loudness, and record observations |
| `build_manifest.py` | Hash final delivery files and create the release manifest |

## Quality model

The default rubric covers story or message, visual direction, motion and
continuity, edit and sound, and delivery quality. Scores support comparison;
they do not average away blockers.

Rights, consent, accessibility, safety, and legal issues cannot be waived by the
agent. A successful API request or decodable file is not a release.

## Model profiles

Copy `assets/model-profile.example.json` into the adapter layer and populate it
from current provider documentation. Record a verification date. Model catalogs,
prices, limits, modalities, moderation, retention, and commercial terms change;
they do not belong in the stable craft rules.

## Design provenance

This is an original implementation. Its architecture was informed by public
agent-video workflows including OpenMontage, Generative Media Skills, Film Studio
Skills, DirectorSKILL, Scenario Skills, AI Video Generation Skills, Drama Skills,
Super Video Maker, Claude Remotion Skill, and VEFX-Bench. See
[CREDITS.md](CREDITS.md) for the reviewed sources and license boundaries.

## License

MIT. See [LICENSE](LICENSE).

# External video API route

Use for generated live-action, human performance, environments, organic motion,
and shots that cannot be authored deterministically.

## Inputs

- approved shot contract and master-clock markers;
- model profile with verified capabilities;
- approved keyframe, first/last frames, or reference pack;
- prompt file with a stable version;
- budget, retry, and candidate limit.

Use the least stochastic surface the model supports. Prefer image-to-video,
first/last-frame bridging, or identity-conditioned references over pure
text-to-video.

## Orchestration skeleton

```text
project/
├── prompts/              # one versioned prompt per shot/candidate
├── assets/               # references and model profile inputs
├── generations/          # raw provider outputs
├── selects/              # only approved candidates
├── generation-log.jsonl  # append-only candidate history
└── qa/                   # full-resolution evidence and failures
```

Normalize every adapter to the same submission, polling/webhook, download,
error, cost, cancellation, and result contract. Persist outputs before provider
retention expires.

## Before a paid batch

1. Discover the current model schema and version.
2. Verify duration, resolution, aspect, reference slots, audio, and seed.
3. Quote the exact batch cost.
4. Run one representative pilot shot.
5. Review motion and continuity, not only the first frame.
6. Record the configuration before submitting the rest.

Do not silently change model, duration, audio, or reference inputs after budget
approval. Preserve rejected candidates until the selected take is safely logged.

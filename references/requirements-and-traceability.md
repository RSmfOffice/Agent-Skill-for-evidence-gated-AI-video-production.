# Requirements and traceability

Use this reference when converting a brief into acceptance criteria and QA
evidence.

## The traceability chain

```text
required / forbidden / signature requirement
→ shot acceptance criterion
→ QA check
→ hashed evidence
→ release decision
```

Every blocking requirement needs a path through this chain. A file existing, a
category being marked PASS, or a generic reviewer note is not a substitute.

## Content contract

`project.json` contains:

```json
{
  "content_contract": {
    "required": [
      {
        "id": "REQ-MAIN-SUBJECT",
        "observable": "The required subject is visible.",
        "blocking": true,
        "acceptance_ids": ["A1"]
      }
    ],
    "forbidden": [
      {
        "id": "FORBID-TEXT-ERROR",
        "observable": "No incorrect or unreadable required text appears.",
        "blocking": true,
        "acceptance_ids": ["A2"]
      }
    ],
    "signature_events": [
      {
        "id": "SIG-REVEAL",
        "observable": "The reveal is perceptible at delivery size.",
        "time_window_sec": [4.0, 5.0],
        "blocking": true,
        "acceptance_ids": ["A3"]
      }
    ]
  }
}
```

`observable` describes what a reviewer can see or measure. Keep project-specific
content here, not in validator code.

## Acceptance criterion

Use `pass_if` and at least one concrete `fail_if`:

```json
{
  "id": "A1",
  "pass_if": "The subject is visible with the required silhouette.",
  "fail_if": [
    "The subject is absent.",
    "The subject is present only as an unrecognizable fragment."
  ],
  "method": "native-crop-sequence",
  "test_domain": "visual",
  "requirement_ids": ["REQ-MAIN-SUBJECT"],
  "motion_contract_ids": [],
  "blocking": true
}
```

Supported methods:

- `native-crop`
- `native-crop-sequence`
- `image-sequence`
- `motion-audit`
- `numeric-test`
- `ocr`
- `transcript`
- `waveform`
- `human-review`

Supported test domains:

- `visual`
- `motion`
- `audio`
- `text`
- `technical`
- `content`
- `rights`

Do not use only a broad positive statement such as "looks correct" when a
specific visible failure can be named.

## QA check

Every pass or fail record references the acceptance IDs it settles:

```json
{
  "category": "visual",
  "acceptance_ids": ["A1"],
  "method": "native-crop-sequence",
  "status": "pass",
  "criterion": "The subject remains recognizable.",
  "observed": "The subject silhouette remains unchanged from 0.2 to 4.8 seconds.",
  "time_sec": 2.5,
  "region": [700, 180, 800, 720],
  "reviewer": "cold review",
  "evidence": [
    {
      "path": "qa/evidence/subject-mid.jpg",
      "role": "observed-final-frame",
      "sha256": "64 hexadecimal characters"
    }
  ]
}
```

For text and temporal claims, include a locator such as `time_sec`, `timecode`,
or frame range. Native crop methods require a positive `[x, y, width, height]`
region.

## Evidence provenance

- `preproduction-reference`: reference assembled before scene production;
- `canonical-source`: approved source asset, source definition, or source
  footage;
- `render-test`: deterministic test render, numeric test, benchmark, or report;
- `observed-final-frame`: frame or clip taken from the completed output;
- `independent-review`: note or report from a reviewer independent of the
  producer.

A finished frame may describe the final result, but it cannot be the only
reference used to prove that an identity, design, or motion system was
controlled before production.

## Review independence

`project.producer_id` and `qa-report.review.reviewer_id` identify the two roles.

Reviewer kinds:

- `self`
- `cold-agent`
- `human`
- `external`

When `policy.require_independent_review` is true, self-review blocks final
release. When `policy.require_human_final_approval` is true, a human or external
reviewer and `human_approved: true` are required.

An internal preview may intentionally disable these policies, but it must not
be described as an independently approved final.

## Traceability failures

Block release when:

- a blocking content requirement has no acceptance ID;
- an acceptance references an unknown requirement;
- a requirement and acceptance do not point to each other;
- a blocking acceptance has no passing QA check;
- a QA check references unknown acceptance;
- evidence lacks a role or hash, or the hash is stale;
- a signature event has no located passing evidence inside its time window;
- a visual/content/audio/text check has no acceptance ID.

## Anti-overfitting rule

Do not encode project language such as "bird", "wheel", "logo", or "close-up"
into the core validator. Put those words in the project's content contract.
The core only understands:

- requirement IDs and observability;
- acceptance methods and domains;
- evidence provenance;
- temporal and regional traceability;
- review independence.

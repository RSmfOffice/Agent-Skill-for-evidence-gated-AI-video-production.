# Timeline-edit route

Use for existing footage, recordings, stock, podcasts, interviews,
localization, and repurposed long-form material.

## Source intake

Inventory each source's:

- technical format and integrity;
- ownership, license, consent, and usage restrictions;
- transcript, spoken language, and timecode;
- visual content, framing, and quality;
- audio channels, noise floor, and sync offset.

Do not infer a license from where a file was downloaded.

## Edit contract

Create:

- a human-readable paper edit or rationale in `timeline.md`;
- machine-readable clip/track data in `timeline.json`;
- selected source ranges and handles;
- captions/subtitles and their maximum read rate;
- audio stems, music cues, and sound effects;
- aspect-ratio variants composed deliberately.

Conform sources before final assembly. Preserve original frame rate where
possible; document any retiming, interpolation, stabilization, or upscale.

## Checks

- No missing or offline source.
- In/out points remain inside source duration.
- Program and audio duration match.
- Cut continuity is intentional.
- Captions match the approved edit and do not cover critical content.
- Color, grain, noise floor, and loudness are coherent across sources.
- The final export comes from the approved master edit.

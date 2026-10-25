#!/usr/bin/env python3
"""Validate a video-production-director project or enforce final release."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from _common import (
    DEFAULT_GATE_ARTIFACTS,
    GATE_ORDER,
    REQUIRED_PROJECT_FILES,
    ProjectError,
    as_number,
    is_within,
    load_json,
    nonempty_string,
    project_path,
    sha256_file,
)


QUALITY_MODES = {"draft", "standard", "hero"}
ASSET_ROLES = {"hero", "critical", "supporting", "decorative"}
ASSET_TYPES = {
    "character",
    "product",
    "location",
    "prop",
    "ui",
    "typography",
    "programmatic",
}
ASSET_STATUSES = {"draft", "locked", "discontinued"}
SHOT_SOURCES = {
    "programmatic",
    "external-video",
    "existing-footage",
    "hybrid",
}
CONTROL_MODES = {
    "deterministic",
    "image-to-video",
    "first-last-frame",
    "reference-conditioned",
    "text-to-video",
    "video-to-video",
    "edit-only",
    "not-applicable",
}
REQUIRED_QA_CATEGORIES = {"technical", "visual", "editorial", "rights", "content"}
NON_WAIVABLE_CATEGORIES = {"rights", "accessibility", "safety", "legal", "policy"}
ACCEPTANCE_METHODS = {
    "native-crop",
    "native-crop-sequence",
    "image-sequence",
    "motion-audit",
    "numeric-test",
    "ocr",
    "transcript",
    "waveform",
    "human-review",
}
TEST_DOMAINS = {
    "visual",
    "motion",
    "audio",
    "text",
    "technical",
    "content",
    "rights",
}
EVIDENCE_ROLES = {
    "preproduction-reference",
    "canonical-source",
    "render-test",
    "observed-final-frame",
    "independent-review",
}
MOTION_TYPES = {
    "rolling-contact",
    "fixed-contact",
    "speed-coherence",
    "rigid-joint",
    "cloth-root-attachment",
    "fluid-flow",
    "collision",
    "screen-direction",
    "lip-sync",
}
REVIEWER_KINDS = {"self", "cold-agent", "human", "external"}


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def text(self, condition: bool, message: str, final: bool) -> None:
        if not condition:
            (self.error if final else self.warn)(message)


def _required_dict(
    value: Any,
    path: str,
    report: Report,
    final: bool,
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        report.error(f"{path} must be an object")
        return None
    if not value and final:
        report.error(f"{path} must not be empty")
    return value


def _required_text(
    value: Any,
    path: str,
    report: Report,
    final: bool,
) -> None:
    report.text(nonempty_string(value), f"{path} must be a non-empty string", final)


def _path_status(
    project_root: Path,
    value: Any,
    path: str,
    report: Report,
    final: bool,
    must_be_file: bool = True,
) -> Path | None:
    if not nonempty_string(value):
        report.text(
            False,
            f"{path} must be a project-relative path",
            final,
        )
        return None
    try:
        resolved = project_path(project_root, str(value))
    except ProjectError as exc:
        report.error(f"{path}: {exc}")
        return None
    exists = resolved.is_file() if must_be_file else resolved.exists()
    if not exists:
        report.text(
            False,
            f"{path} does not exist: {value}",
            final,
        )
        return None
    return resolved


def _validate_base_files(project_root: Path, report: Report) -> None:
    if not project_root.is_dir():
        report.error(f"project directory does not exist: {project_root}")
        return
    for value in REQUIRED_PROJECT_FILES:
        if not (project_root / value).is_file():
            report.error(f"missing required project file: {value}")


def _validate_project_contract(
    project: dict[str, Any],
    report: Report,
    final: bool,
) -> None:
    if project.get("schema_version") != 1:
        report.error("project.json schema_version must be 1")

    for key, path in (
        ("project_id", "project.project_id"),
        ("title", "project.title"),
        ("producer_id", "project.producer_id"),
        ("goal", "project.goal"),
        ("audience", "project.audience"),
        ("platform", "project.platform"),
        ("delivery_promise", "project.delivery_promise"),
        ("target_response", "project.target_response"),
    ):
        _required_text(project.get(key), path, report, final)

    if project.get("quality_mode") not in QUALITY_MODES:
        report.error("project.quality_mode must be draft, standard, or hero")
    elif final and project.get("quality_mode") == "draft":
        report.error("draft quality mode cannot pass final release")

    output = _required_dict(project.get("output"), "project.output", report, final)
    if output:
        _required_text(output.get("path"), "project.output.path", report, final)
        for key in ("duration_sec", "width", "height", "fps"):
            number = as_number(output.get(key))
            if number is None or number <= 0:
                report.error(f"project.output.{key} must be a positive number")
        for key in ("has_audio", "captions_required", "text_required"):
            if not isinstance(output.get(key), bool):
                report.error(f"project.output.{key} must be a boolean")
        if output.get("has_audio") is True:
            for key in ("sample_rate", "channels"):
                number = as_number(output.get(key))
                if number is None or number <= 0:
                    report.error(
                        f"project.output.{key} must be positive when has_audio is true"
                    )
            _required_text(
                output.get("audio_codec"),
                "project.output.audio_codec",
                report,
                final,
            )
        for key in ("loudness_target_lufs", "true_peak_max_db"):
            if output.get(key) is not None and as_number(output.get(key)) is None:
                report.error(f"project.output.{key} must be null or numeric")

    clock = _required_dict(project.get("clock"), "project.clock", report, final)
    if clock:
        if clock.get("type") not in {"visual", "voiceover", "music", "dialogue"}:
            report.error(
                "project.clock.type must be visual, voiceover, music, or dialogue"
            )
        _required_text(clock.get("source"), "project.clock.source", report, final)
        if not isinstance(clock.get("markers", []), list):
            report.error("project.clock.markers must be an array")

    budget = _required_dict(project.get("budget"), "project.budget", report, final)
    if budget:
        spent = as_number(budget.get("spent", 0))
        cap = budget.get("cap")
        if spent is None or spent < 0:
            report.error("project.budget.spent must be a non-negative number")
        if cap is not None:
            cap_number = as_number(cap)
            if cap_number is None or cap_number < 0:
                report.error("project.budget.cap must be null or non-negative")
            elif spent is not None and spent > cap_number:
                report.error("project.budget.spent exceeds budget.cap")

    quality = _required_dict(project.get("quality"), "project.quality", report, final)
    if quality:
        for key in ("thesis", "hero_frame", "signature_moment", "sound_motif"):
            _required_text(quality.get(key), f"project.quality.{key}", report, final)
        if not isinstance(quality.get("references", []), list):
            report.error("project.quality.references must be an array")
        if not isinstance(quality.get("anti_references", []), list):
            report.error("project.quality.anti_references must be an array")
        rubric = quality.get("rubric")
        if not isinstance(rubric, dict) or not rubric:
            report.text(False, "project.quality.rubric should be an object", final)
        elif any(as_number(value) is None or float(value) < 0 for value in rubric.values()):
            report.error("project.quality.rubric values must be non-negative numbers")

    rights = _required_dict(project.get("rights"), "project.rights", report, final)
    if rights:
        _required_text(
            rights.get("intended_use"),
            "project.rights.intended_use",
            report,
            final,
        )
        _required_text(
            rights.get("ledger"),
            "project.rights.ledger",
            report,
            final,
        )
        if not isinstance(rights.get("commercial_use_allowed"), bool):
            report.error("project.rights.commercial_use_allowed must be a boolean")
        if not isinstance(rights.get("ai_disclosure_required"), bool):
            report.error("project.rights.ai_disclosure_required must be a boolean")

    policy = project.get("policy")
    if not isinstance(policy, dict):
        report.error("project.policy must be an object")
    else:
        for key in (
            "least_stochastic_control",
            "allow_silent_model_fallback",
            "require_independent_review",
            "require_human_final_approval",
        ):
            if not isinstance(policy.get(key), bool):
                report.error(f"project.policy.{key} must be a boolean")
        for key in (
            "hero_candidate_target",
            "max_failures_same_cause",
            "max_candidates_per_shot",
        ):
            number = as_number(policy.get(key))
            if number is None or number <= 0:
                report.error(f"project.policy.{key} must be a positive number")

    gates = project.get("gates")
    if not isinstance(gates, dict):
        report.error("project.gates must be an object")
    else:
        missing = [gate for gate in GATE_ORDER if gate not in gates]
        if missing:
            report.error(f"project.gates is missing: {', '.join(missing)}")
        for gate, state in gates.items():
            if gate not in GATE_ORDER:
                report.warn(f"unknown gate will not affect release: {gate}")
                continue
            if not isinstance(state, dict):
                report.error(f"project.gates.{gate} must be an object")
                continue
            if state.get("status") not in {"pending", "approved", "rejected"}:
                report.error(
                    f"project.gates.{gate}.status must be pending, approved, or rejected"
                )


def _validate_master_clock(
    project: dict[str, Any],
    master_clock: dict[str, Any],
    report: Report,
    final: bool,
) -> None:
    if master_clock.get("schema_version") != 1:
        report.error("master-clock.json schema_version must be 1")

    clock_type = master_clock.get("type")
    allowed_types = {"visual", "voiceover", "music", "dialogue"}
    if clock_type not in allowed_types:
        report.error(
            "master-clock.type must be visual, voiceover, music, or dialogue"
        )
    project_clock = project.get("clock")
    if (
        isinstance(project_clock, dict)
        and clock_type
        and project_clock.get("type") != clock_type
    ):
        report.error("master-clock.type must match project.clock.type")

    _required_text(
        master_clock.get("source"),
        "master-clock.source",
        report,
        final,
    )
    duration = as_number(master_clock.get("duration_sec"))
    if duration is None or duration <= 0:
        report.error("master-clock.duration_sec must be positive")
        duration = None

    output = project.get("output")
    output_duration = (
        as_number(output.get("duration_sec")) if isinstance(output, dict) else None
    )
    if (
        final
        and duration is not None
        and output_duration is not None
        and abs(duration - output_duration) > 0.1
    ):
        report.error("master-clock.duration_sec must match project.output.duration_sec")

    if clock_type == "music":
        bpm = as_number(master_clock.get("bpm"))
        if bpm is None or bpm <= 0:
            report.text(False, "music master clock needs a positive bpm", final)

    segments = master_clock.get("segments")
    if not isinstance(segments, list):
        report.error("master-clock.segments must be an array")
        segments = []
    if final and not segments:
        report.error("master-clock.segments must not be empty")

    ranges: list[tuple[float, float, str]] = []
    for index, segment in enumerate(segments):
        prefix = f"master-clock.segments[{index}]"
        if not isinstance(segment, dict):
            report.error(f"{prefix} must be an object")
            continue
        segment_id = segment.get("id")
        _required_text(segment_id, f"{prefix}.id", report, final)
        _required_text(segment.get("intent"), f"{prefix}.intent", report, final)
        start = as_number(segment.get("start_sec"))
        end = as_number(segment.get("end_sec"))
        if start is None or end is None or start < 0 or end <= start:
            report.error(f"{prefix} needs numeric 0 <= start_sec < end_sec")
            continue
        if duration is not None and end > duration + 0.001:
            report.error(f"{prefix} ends after the master-clock duration")
        ranges.append((start, end, str(segment_id)))
        if clock_type in {"voiceover", "dialogue"} and final:
            if not nonempty_string(segment.get("text")) and not nonempty_string(
                segment.get("spoken_text")
            ):
                report.error(f"{prefix} needs text or spoken_text")

    ranges.sort(key=lambda item: (item[0], item[1]))
    previous_end = 0.0
    previous_name = "clock start"
    for start, end, name in ranges:
        if start + 0.001 < previous_end:
            report.error(f"{name} overlaps {previous_name} in master-clock segments")
        elif start - previous_end > 0.05:
            report.text(
                False,
                f"master-clock segment gap of {start - previous_end:.3f}s before {name}",
                final,
            )
        previous_end = max(previous_end, end)
        previous_name = name
    if final and duration is not None and ranges and abs(previous_end - duration) > 0.1:
        report.error(
            f"master-clock segments cover {previous_end:.3f}s, expected {duration:.3f}s"
        )

    markers = master_clock.get("markers")
    if not isinstance(markers, list):
        report.error("master-clock.markers must be an array")
        markers = []
    if final and clock_type in {"music", "visual"} and not markers:
        report.error(f"{clock_type} master clock needs at least one marker")
    previous_marker = -1.0
    for index, marker in enumerate(markers):
        prefix = f"master-clock.markers[{index}]"
        if not isinstance(marker, dict):
            report.error(f"{prefix} must be an object")
            continue
        marker_time = as_number(marker.get("time_sec"))
        if marker_time is None or marker_time < 0:
            report.error(f"{prefix}.time_sec must be non-negative")
            continue
        if duration is not None and marker_time > duration + 0.001:
            report.error(f"{prefix}.time_sec is after the clock duration")
        if marker_time < previous_marker:
            report.warn(f"{prefix} is out of chronological order")
        previous_marker = marker_time
        for key in ("kind", "label"):
            _required_text(marker.get(key), f"{prefix}.{key}", report, final)


def _validate_timeline(
    project: dict[str, Any],
    timeline: dict[str, Any],
    shots: list[dict[str, Any]],
    report: Report,
    final: bool,
) -> None:
    if timeline.get("schema_version") != 1:
        report.error("timeline.json schema_version must be 1")

    output = project.get("output")
    output_duration = (
        as_number(output.get("duration_sec")) if isinstance(output, dict) else None
    )
    timeline_duration = as_number(timeline.get("duration_sec"))
    if timeline_duration is None or timeline_duration <= 0:
        report.error("timeline.duration_sec must be positive")
        timeline_duration = None
    if (
        final
        and timeline_duration is not None
        and output_duration is not None
        and abs(timeline_duration - output_duration) > 0.1
    ):
        report.error("timeline.duration_sec must match project output duration")

    known_shots = {
        str(shot.get("id")) for shot in shots if isinstance(shot, dict) and shot.get("id")
    }
    tracks = timeline.get("tracks")
    if not isinstance(tracks, list):
        report.error("timeline.tracks must be an array")
        tracks = []
    if final and not tracks:
        report.error("timeline.tracks must not be empty")

    primary_tracks: list[dict[str, Any]] = []
    has_audio_track = False
    has_caption_track = False
    has_graphic_track = False
    for index, track in enumerate(tracks):
        prefix = f"timeline.tracks[{index}]"
        if not isinstance(track, dict):
            report.error(f"{prefix} must be an object")
            continue
        _required_text(track.get("id"), f"{prefix}.id", report, final)
        track_type = track.get("type")
        if track_type not in {"video", "audio", "voice", "music", "caption", "graphic"}:
            report.error(f"{prefix}.type is invalid")
        role = track.get("role")
        if role not in {"primary", "overlay", "mix", "reference"}:
            report.error(f"{prefix}.role is invalid")
        if track_type == "video" and role == "primary":
            primary_tracks.append(track)
        if track_type in {"audio", "voice", "music"}:
            has_audio_track = True
        if track_type == "caption":
            has_caption_track = True
        if track_type == "graphic":
            has_graphic_track = True

        items = track.get("items")
        if not isinstance(items, list):
            report.error(f"{prefix}.items must be an array")
            continue
        for item_index, item in enumerate(items):
            item_prefix = f"{prefix}.items[{item_index}]"
            if not isinstance(item, dict):
                report.error(f"{item_prefix} must be an object")
                continue
            _required_text(item.get("id"), f"{item_prefix}.id", report, final)
            _required_text(item.get("source"), f"{item_prefix}.source", report, final)
            start = as_number(item.get("timeline_start"))
            item_duration = as_number(item.get("duration"))
            if start is None or start < 0:
                report.error(f"{item_prefix}.timeline_start must be non-negative")
            if item_duration is None or item_duration <= 0:
                report.error(f"{item_prefix}.duration must be positive")
            if (
                timeline_duration is not None
                and start is not None
                and item_duration is not None
                and start + item_duration > timeline_duration + 0.001
            ):
                report.error(f"{item_prefix} ends after the timeline duration")
            if track_type == "video":
                shot_id = item.get("shot_id")
                if not nonempty_string(shot_id):
                    report.error(f"{item_prefix}.shot_id is required")
                elif shot_id not in known_shots:
                    report.error(f"{item_prefix} references unknown shot {shot_id}")
                source_in = as_number(item.get("source_in"))
                source_out = as_number(item.get("source_out"))
                if source_in is None or source_in < 0:
                    report.error(f"{item_prefix}.source_in must be non-negative")
                if source_out is None or (
                    source_in is not None and source_out <= source_in
                ):
                    report.error(
                        f"{item_prefix}.source_out must be greater than source_in"
                    )
                _required_text(
                    item.get("transition"),
                    f"{item_prefix}.transition",
                    report,
                    final,
                )

    if final and len(primary_tracks) != 1:
        report.error("timeline needs exactly one primary video track")
    if final and isinstance(output, dict):
        if output.get("has_audio") and not has_audio_track:
            report.error("timeline needs an audio, voice, or music track")
        if output.get("captions_required") and not has_caption_track:
            report.error("timeline needs a caption track")
        if output.get("text_required") and not (has_caption_track or has_graphic_track):
            report.error("timeline needs a caption or graphic track for required text")

    if primary_tracks and timeline_duration is not None:
        primary = primary_tracks[0]
        items = primary.get("items", [])
        ranges: list[tuple[float, float, str]] = []
        for index, item in enumerate(items if isinstance(items, list) else []):
            if not isinstance(item, dict):
                continue
            start = as_number(item.get("timeline_start"))
            item_duration = as_number(item.get("duration"))
            if start is None or item_duration is None or item_duration <= 0:
                continue
            ranges.append(
                (
                    start,
                    start + item_duration,
                    str(item.get("id", f"item[{index}]")),
                )
            )
        ranges.sort(key=lambda item: (item[0], item[1]))
        previous_end = 0.0
        previous_name = "timeline start"
        for start, end, name in ranges:
            if start + 0.001 < previous_end:
                report.error(f"{name} overlaps {previous_name} on the primary track")
            elif start - previous_end > 0.05:
                report.text(
                    False,
                    f"primary timeline gap of {start - previous_end:.3f}s before {name}",
                    final,
                )
            previous_end = max(previous_end, end)
            previous_name = name
        if final and abs(previous_end - timeline_duration) > 0.1:
            report.error(
                f"primary timeline covers {previous_end:.3f}s, "
                f"expected {timeline_duration:.3f}s"
            )

    beat_markers = timeline.get("beat_markers")
    if not isinstance(beat_markers, list):
        report.error("timeline.beat_markers must be an array")
        beat_markers = []
    clock = project.get("clock")
    if (
        final
        and isinstance(clock, dict)
        and clock.get("type") == "music"
        and not beat_markers
    ):
        report.error("music-driven timeline needs beat_markers")
    for index, marker in enumerate(beat_markers):
        prefix = f"timeline.beat_markers[{index}]"
        if not isinstance(marker, dict):
            report.error(f"{prefix} must be an object")
            continue
        marker_time = as_number(marker.get("time_sec"))
        if marker_time is None or marker_time < 0:
            report.error(f"{prefix}.time_sec must be non-negative")
        elif timeline_duration is not None and marker_time > timeline_duration + 0.001:
            report.error(f"{prefix}.time_sec is after the timeline duration")
        _required_text(marker.get("label"), f"{prefix}.label", report, final)


def _validate_animatic(
    project_root: Path,
    project: dict[str, Any],
    animatic_review: dict[str, Any],
    report: Report,
    final: bool,
) -> None:
    if animatic_review.get("schema_version") != 1:
        report.error("qa/animatic-review.json schema_version must be 1")
    for key in ("reviewer", "reviewed_at"):
        _required_text(
            animatic_review.get(key),
            f"animatic-review.{key}",
            report,
            final,
        )
    if not isinstance(animatic_review.get("watched_in_real_time"), bool):
        report.error("animatic-review.watched_in_real_time must be a boolean")
    elif final and not animatic_review.get("watched_in_real_time"):
        report.error("animatic must be watched in real time")
    if animatic_review.get("decision") not in {
        "pending",
        "approved",
        "revise",
        "rejected",
    }:
        report.error("animatic-review.decision is invalid")
    elif final and animatic_review.get("decision") != "approved":
        report.error("animatic-review.decision must be approved")
    for key in ("issues", "unresolved_blockers"):
        if not isinstance(animatic_review.get(key), list):
            report.error(f"animatic-review.{key} must be an array")
    if final and animatic_review.get("unresolved_blockers"):
        report.error("animatic has unresolved blockers")

    animatic_path = project_root / "animatic" / "animatic.mp4"
    if not animatic_path.is_file() or animatic_path.stat().st_size == 0:
        report.text(False, "animatic/animatic.mp4 is missing or empty", final)
        return
    if not final:
        return

    technical_path = project_root / "qa" / "animatic-technical-report.json"
    if not technical_path.is_file():
        report.error("qa/animatic-technical-report.json is missing")
        return
    try:
        technical = load_json(technical_path)
    except ProjectError as exc:
        report.error(str(exc))
        return
    if not isinstance(technical, dict):
        report.error("qa/animatic-technical-report.json must be an object")
        return
    if technical.get("decode_ok") is not True:
        report.error("animatic technical report indicates a failed decode")
    if technical.get("inspection_complete") is not True:
        report.error("animatic technical inspection was not completed")
    if technical.get("matched_expected") is not True:
        report.error("animatic technical report does not match the expected duration")
    if technical.get("source") != "animatic/animatic.mp4":
        report.error("animatic technical report source must be animatic/animatic.mp4")
    if technical.get("source_sha256") != sha256_file(animatic_path):
        report.error("animatic technical report hash is stale")
    if not technical.get("sample_frames"):
        report.error("animatic technical report contains no sampled frames")
    format_info = technical.get("format")
    report_duration = (
        as_number(format_info.get("duration_sec"))
        if isinstance(format_info, dict)
        else None
    )
    output = project.get("output")
    output_duration = (
        as_number(output.get("duration_sec")) if isinstance(output, dict) else None
    )
    if (
        report_duration is not None
        and output_duration is not None
        and abs(report_duration - output_duration) > 0.1
    ):
        report.error("animatic duration does not match the target program duration")


def _validate_assets(
    project_root: Path,
    assets_document: dict[str, Any],
    report: Report,
    final: bool,
    quality_mode: str,
    used_asset_ids: set[str],
) -> dict[str, dict[str, Any]]:
    assets_by_id: dict[str, dict[str, Any]] = {}
    if assets_document.get("schema_version") != 1:
        report.error("assets.json schema_version must be 1")
    assets = assets_document.get("assets")
    if not isinstance(assets, list):
        report.error("assets.json assets must be an array")
        return assets_by_id
    if final and not assets:
        report.error("assets.json must contain at least one asset")

    for index, asset in enumerate(assets):
        prefix = f"assets[{index}]"
        if not isinstance(asset, dict):
            report.error(f"{prefix} must be an object")
            continue
        asset_id = asset.get("id")
        if not nonempty_string(asset_id):
            report.error(f"{prefix}.id must be a non-empty string")
            continue
        if asset_id in assets_by_id:
            report.error(f"duplicate asset id: {asset_id}")
        assets_by_id[asset_id] = asset
        prefix = f"asset {asset_id}"

        if asset.get("type") not in ASSET_TYPES:
            report.error(f"{prefix}.type is invalid")
        role = asset.get("role")
        if role not in ASSET_ROLES:
            report.error(f"{prefix}.role is invalid")
        status = asset.get("status")
        if status not in ASSET_STATUSES:
            report.error(f"{prefix}.status is invalid")
        elif final and asset_id in used_asset_ids and status != "locked":
            report.error(f"{prefix} is used by a shot but is not locked")

        _required_text(asset.get("descriptor"), f"{prefix}.descriptor", report, final)
        for key in ("invariants", "allowed_variation", "references", "stress_tests"):
            if not isinstance(asset.get(key, []), list):
                report.error(f"{prefix}.{key} must be an array")

        references = asset.get("references", [])
        approved_references = 0
        if isinstance(references, list):
            if final and role in {"hero", "critical"} and not references:
                report.error(f"{prefix} needs at least one approved reference")
            for ref_index, reference in enumerate(references):
                ref_prefix = f"{prefix}.references[{ref_index}]"
                if not isinstance(reference, dict):
                    report.error(f"{ref_prefix} must be an object")
                    continue
                _path_status(
                    project_root,
                    reference.get("path"),
                    f"{ref_prefix}.path",
                    report,
                    final,
                )
                provenance = reference.get("provenance")
                if provenance not in EVIDENCE_ROLES:
                    report.text(
                        False,
                        f"{ref_prefix}.provenance is required and must be valid",
                        final,
                    )
                elif provenance != "observed-final-frame":
                    approved_references += 1
                for key in ("use", "controls", "must_not_control"):
                    _required_text(
                        reference.get(key),
                        f"{ref_prefix}.{key}",
                        report,
                        final,
                    )

        stress_tests = asset.get("stress_tests", [])
        passes = 0
        qualifying_passes = 0
        stress_evidence_paths: set[str] = set()
        if isinstance(stress_tests, list):
            for test_index, stress in enumerate(stress_tests):
                test_prefix = f"{prefix}.stress_tests[{test_index}]"
                if not isinstance(stress, dict):
                    report.error(f"{test_prefix} must be an object")
                    continue
                _required_text(
                    stress.get("case"),
                    f"{test_prefix}.case",
                    report,
                    final,
                )
                result = stress.get("result")
                if result not in {"pass", "fail", "not-applicable"}:
                    report.error(
                        f"{test_prefix}.result must be pass, fail, or not-applicable"
                    )
                elif result == "pass":
                    passes += 1
                    evidence_path = _path_status(
                        project_root,
                        stress.get("evidence"),
                        f"{test_prefix}.evidence",
                        report,
                        final,
                    )
                    if evidence_path:
                        stress_evidence_paths.add(str(evidence_path.resolve()))
                    provenance = stress.get("provenance")
                    if provenance not in EVIDENCE_ROLES:
                        report.text(
                            False,
                            f"{test_prefix}.provenance is required and must be valid",
                            final,
                        )
                    elif provenance != "observed-final-frame":
                        qualifying_passes += 1
                elif result == "not-applicable":
                    _required_text(
                        stress.get("reason"),
                        f"{test_prefix}.reason",
                        report,
                        final,
                    )

        if final:
            required_passes = 0
            if role == "hero":
                required_passes = 3 if quality_mode == "hero" else 1
            elif role == "critical":
                required_passes = 1
            if min(required_passes, 1) and passes < required_passes:
                report.error(
                    f"{prefix} needs {required_passes} passing stress test(s), "
                    f"found {passes}"
                )
            if role in {"hero", "critical"} and required_passes:
                if approved_references == 0:
                    report.error(
                        f"{prefix} needs a reference whose provenance is not "
                        "observed-final-frame"
                    )
                if qualifying_passes < required_passes:
                    report.error(
                        f"{prefix} needs {required_passes} non-final stress test(s), "
                        f"found {qualifying_passes}"
                    )
            if role == "hero" and quality_mode == "hero" and len(
                stress_evidence_paths
            ) < 3:
                report.error(
                    f"{prefix} Hero stress tests need at least three distinct evidence files"
                )
            _required_text(asset.get("rights"), f"{prefix}.rights", report, final)

    continuity = assets_document.get("continuity")
    if not isinstance(continuity, dict):
        report.text(False, "assets.json continuity must be an object", final)
    return assets_by_id


def _validate_stress_structure(
    shots_document: dict[str, Any],
    report: Report,
    final: bool,
    output_duration: float | None,
    assets_by_id: dict[str, dict[str, Any]],
    project_root: Path,
    quality_mode: str,
) -> tuple[set[str], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    if shots_document.get("schema_version") != 1:
        report.error("shots.json schema_version must be 1")
    shots = shots_document.get("shots")
    if not isinstance(shots, list):
        report.error("shots.json shots must be an array")
        return set(), [], {}
    if final and not shots:
        report.error("shots.json must contain at least one shot")

    used_assets: set[str] = set()
    valid_shots: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    acceptance_by_id: dict[str, dict[str, Any]] = {}

    for index, shot in enumerate(shots):
        prefix = f"shots[{index}]"
        if not isinstance(shot, dict):
            report.error(f"{prefix} must be an object")
            continue
        shot_id = shot.get("id")
        if not nonempty_string(shot_id):
            report.error(f"{prefix}.id must be a non-empty string")
            continue
        if shot_id in seen_ids:
            report.error(f"duplicate shot id: {shot_id}")
        seen_ids.add(shot_id)
        prefix = f"shot {shot_id}"
        valid_shots.append(shot)

        start = as_number(shot.get("start_sec"))
        end = as_number(shot.get("end_sec"))
        if start is None or end is None or start < 0 or end <= start:
            report.error(f"{prefix} needs numeric 0 <= start_sec < end_sec")
            start = end = None
        elif output_duration is not None and end > output_duration + 0.001:
            report.error(f"{prefix} ends after the project duration")

        editorial = _required_dict(
            shot.get("editorial"), f"{prefix}.editorial", report, final
        )
        if editorial:
            for key in ("function", "intent", "information_delta", "cut_reason"):
                _required_text(
                    editorial.get(key),
                    f"{prefix}.editorial.{key}",
                    report,
                    final,
                )

        frame = _required_dict(shot.get("frame"), f"{prefix}.frame", report, final)
        if frame:
            for key in ("shot_size", "camera_height", "angle", "field_of_view"):
                _required_text(
                    frame.get(key),
                    f"{prefix}.frame.{key}",
                    report,
                    final,
                )

        action = _required_dict(shot.get("action"), f"{prefix}.action", report, final)
        if action:
            for key in ("start", "primary", "end"):
                _required_text(
                    action.get(key),
                    f"{prefix}.action.{key}",
                    report,
                    final,
                )

        camera = _required_dict(shot.get("camera"), f"{prefix}.camera", report, final)
        if camera:
            for key in ("move", "motivation", "path", "end_frame"):
                _required_text(
                    camera.get(key),
                    f"{prefix}.camera.{key}",
                    report,
                    final,
                )

        continuity = _required_dict(
            shot.get("continuity"),
            f"{prefix}.continuity",
            report,
            final,
        )
        if continuity:
            for key in ("screen_direction", "eyeline", "lighting"):
                _required_text(
                    continuity.get(key),
                    f"{prefix}.continuity.{key}",
                    report,
                    final,
                )
            for key in ("assets", "props"):
                if not isinstance(continuity.get(key, []), list):
                    report.error(f"{prefix}.continuity.{key} must be an array")
            for asset_id in continuity.get("assets", []):
                if not isinstance(asset_id, str):
                    report.error(f"{prefix}.continuity.assets entries must be strings")
                    continue
                used_assets.add(asset_id)
                if asset_id not in assets_by_id:
                    report.error(f"{prefix} references unknown asset: {asset_id}")

        generation = _required_dict(
            shot.get("generation"),
            f"{prefix}.generation",
            report,
            final,
        )
        if generation:
            source = generation.get("source")
            if source not in SHOT_SOURCES:
                report.error(f"{prefix}.generation.source is invalid")
            control_mode = generation.get("control_mode")
            if control_mode not in CONTROL_MODES:
                report.error(f"{prefix}.generation.control_mode is invalid")
            if generation.get("status") not in {
                "planned",
                "generating",
                "approved",
                "failed",
            }:
                report.error(f"{prefix}.generation.status is invalid")
            if final and generation.get("status") != "approved":
                report.error(f"{prefix}.generation.status must be approved")
            if final and source in {"external-video", "hybrid"} and control_mode != "deterministic":
                _required_text(
                    generation.get("model"),
                    f"{prefix}.generation.model",
                    report,
                    final,
                )
                _required_text(
                    generation.get("selected_candidate_id"),
                    f"{prefix}.generation.selected_candidate_id",
                    report,
                    final,
                )

        acceptance = shot.get("acceptance")
        if not isinstance(acceptance, list) or not acceptance:
            report.text(
                False,
                f"{prefix}.acceptance should contain observable criteria",
                final,
            )
        else:
            blocking_count = 0
            for acceptance_index, criterion in enumerate(acceptance):
                criterion_prefix = f"{prefix}.acceptance[{acceptance_index}]"
                if not isinstance(criterion, dict):
                    report.error(f"{criterion_prefix} must be an object")
                    continue
                acceptance_id = criterion.get("id")
                if not nonempty_string(acceptance_id):
                    report.error(f"{criterion_prefix}.id must be a non-empty string")
                    acceptance_id = None
                elif acceptance_id in acceptance_by_id:
                    report.error(f"duplicate acceptance id: {acceptance_id}")
                _required_text(
                    criterion.get("pass_if"),
                    f"{criterion_prefix}.pass_if",
                    report,
                    final,
                )
                fail_if = criterion.get("fail_if")
                if not isinstance(fail_if, list) or not fail_if:
                    report.text(
                        False,
                        f"{criterion_prefix}.fail_if should list concrete failures",
                        final,
                    )
                elif any(not nonempty_string(item) for item in fail_if):
                    report.error(
                        f"{criterion_prefix}.fail_if entries must be non-empty strings"
                    )
                method = criterion.get("method")
                if method not in ACCEPTANCE_METHODS:
                    report.text(
                        False,
                        f"{criterion_prefix}.method must be a supported test method",
                        final,
                    )
                test_domain = criterion.get("test_domain")
                if test_domain not in TEST_DOMAINS:
                    report.text(
                        False,
                        f"{criterion_prefix}.test_domain must be a supported domain",
                        final,
                    )
                requirement_ids = criterion.get("requirement_ids", [])
                if not isinstance(requirement_ids, list) or any(
                    not nonempty_string(item) for item in requirement_ids
                ):
                    report.error(
                        f"{criterion_prefix}.requirement_ids must be an array of strings"
                    )
                    requirement_ids = []
                motion_contract_ids = criterion.get("motion_contract_ids", [])
                if not isinstance(motion_contract_ids, list) or any(
                    not nonempty_string(item) for item in motion_contract_ids
                ):
                    report.error(
                        f"{criterion_prefix}.motion_contract_ids must be an array of strings"
                    )
                    motion_contract_ids = []
                if (
                    final
                    and test_domain == "motion"
                    and not motion_contract_ids
                ):
                    report.error(
                        f"{criterion_prefix} motion tests need motion_contract_ids"
                    )
                if not isinstance(criterion.get("blocking"), bool):
                    report.error(f"{criterion_prefix}.blocking must be a boolean")
                elif criterion["blocking"]:
                    blocking_count += 1
                if acceptance_id is not None and acceptance_id not in acceptance_by_id:
                    acceptance_by_id[acceptance_id] = {
                        "shot_id": shot_id,
                        "blocking": criterion.get("blocking") is True,
                        "method": method,
                        "test_domain": test_domain,
                        "requirement_ids": requirement_ids,
                        "motion_contract_ids": motion_contract_ids,
                    }
            if final and blocking_count == 0:
                report.error(f"{prefix} needs at least one blocking acceptance criterion")

        review = shot.get("review")
        if not isinstance(review, dict):
            report.text(False, f"{prefix}.review should be an object", final)
            review = {}
        if final:
            if review.get("status") != "approved":
                report.error(f"{prefix}.review.status must be approved")
            _required_text(
                review.get("reviewer"),
                f"{prefix}.review.reviewer",
                report,
                final,
            )
            evidence = review.get("evidence_frames")
            minimum = 3 if quality_mode == "hero" else 1
            if not isinstance(evidence, list) or len(evidence) < minimum:
                report.error(
                    f"{prefix}.review.evidence_frames needs at least {minimum} entry(s)"
                )
            elif start is not None and end is not None:
                times: list[float] = []
                for evidence_index, item in enumerate(evidence):
                    item_prefix = f"{prefix}.review.evidence_frames[{evidence_index}]"
                    if not isinstance(item, dict):
                        report.error(f"{item_prefix} must be an object")
                        continue
                    _path_status(
                        project_root,
                        item.get("path"),
                        f"{item_prefix}.path",
                        report,
                        final,
                    )
                    time_value = as_number(item.get("time_sec"))
                    if time_value is None or time_value < start - 0.001 or time_value > end + 0.001:
                        report.error(
                            f"{item_prefix}.time_sec must fall inside shot {shot_id}"
                        )
                    else:
                        times.append(time_value)
                    if item.get("native_source") is not True:
                        report.error(
                            f"{item_prefix}.native_source must be true for release evidence"
                        )
                if quality_mode == "hero" and start is not None and end is not None:
                    span = end - start
                    buckets = (0, 0, 0)
                    for time_value in times:
                        position = (time_value - start) / span if span else 0
                        if position < 1 / 3:
                            buckets = (1, buckets[1], buckets[2])
                        elif position <= 2 / 3:
                            buckets = (buckets[0], 1, buckets[2])
                        else:
                            buckets = (buckets[0], buckets[1], 1)
                    if 0 in buckets:
                        report.error(
                            f"{prefix} Hero evidence must cover start, middle, and end thirds"
                        )

    valid_shots.sort(
        key=lambda shot: (
            as_number(shot.get("start_sec")) or 0,
            as_number(shot.get("end_sec")) or 0,
        )
    )
    previous_end = 0.0
    previous_id = "timeline start"
    for shot in valid_shots:
        start = as_number(shot.get("start_sec"))
        end = as_number(shot.get("end_sec"))
        if start is None or end is None:
            continue
        if start < -0.001:
            report.error(f"shot {shot.get('id')} starts before zero")
        if start + 0.001 < previous_end:
            report.error(
                f"shot {shot.get('id')} overlaps {previous_id}; "
                "represent transitions with an edit track instead"
            )
        elif start - previous_end > 0.05:
            report.text(
                False,
                f"timeline gap of {start - previous_end:.3f}s before {shot.get('id')}",
                final,
            )
        previous_end = max(previous_end, end)
        previous_id = str(shot.get("id"))

    if valid_shots and final:
        first_start = as_number(valid_shots[0].get("start_sec"))
        if first_start is not None and first_start > 0.05:
            report.error("timeline does not start at or near zero")
        if output_duration is not None and abs(previous_end - output_duration) > 0.05:
            report.error(
                f"shots cover {previous_end:.3f}s, expected {output_duration:.3f}s"
            )
    return used_assets, valid_shots, acceptance_by_id


def _read_generation_log(project_root: Path, report: Report) -> list[dict[str, Any]]:
    path = project_root / "generation-log.jsonl"
    records: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        report.error(f"cannot read generation-log.jsonl: {exc}")
        return records
    for index, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            report.error(f"generation-log.jsonl line {index}: {exc}")
            continue
        if not isinstance(value, dict):
            report.error(f"generation-log.jsonl line {index} must be an object")
            continue
        records.append(value)
    return records


def _validate_generation_selection(
    project_root: Path,
    project: dict[str, Any],
    shots: list[dict[str, Any]],
    records: list[dict[str, Any]],
    report: Report,
) -> None:
    selected = {
        (record.get("shot_id"), record.get("candidate_id")): record
        for record in records
        if record.get("verdict") == "selected"
    }
    selected_counts: dict[str, int] = {}
    for record in records:
        if record.get("verdict") == "selected":
            shot_key = str(record.get("shot_id"))
            selected_counts[shot_key] = selected_counts.get(shot_key, 0) + 1
    for shot_key, count in selected_counts.items():
        if count > 1:
            report.error(f"shot {shot_key} has multiple selected candidates")

    for shot in shots:
        generation = shot.get("generation")
        if not isinstance(generation, dict):
            continue
        if generation.get("source") not in {"external-video", "hybrid"}:
            continue
        if generation.get("control_mode") == "deterministic":
            continue
        shot_id = shot.get("id")
        candidate_id = generation.get("selected_candidate_id")
        key = (shot_id, candidate_id)
        if key not in selected:
            report.error(
                f"shot {shot_id} has no selected generation-log record for {candidate_id}"
            )
            continue
        record = selected[key]
        output = record.get("output")
        output_path = _path_status(
            project_root,
            output,
            f"generation-log {shot_id}/{candidate_id}.output",
            report,
            True,
        )
        if output_path and record.get("output_sha256") != sha256_file(output_path):
            report.error(
                f"generation-log {shot_id}/{candidate_id}.output_sha256 is stale"
            )
        prompt_path = _path_status(
            project_root,
            record.get("prompt_file"),
            f"generation-log {shot_id}/{candidate_id}.prompt_file",
            report,
            True,
        )
        if prompt_path and record.get("prompt_sha256") != sha256_file(prompt_path):
            report.error(
                f"generation-log {shot_id}/{candidate_id}.prompt_sha256 is stale"
            )
        if record.get("model") != generation.get("model"):
            report.error(
                f"generation-log {shot_id}/{candidate_id}.model does not match shot"
            )
        if record.get("control_mode") != generation.get("control_mode"):
            report.error(
                f"generation-log {shot_id}/{candidate_id}.control_mode "
                "does not match shot"
            )
        if project.get("quality_mode") == "hero":
            policy = project.get("policy", {})
            candidate_count = sum(
                1 for item in records if item.get("shot_id") == shot_id
            )
            minimum = int(policy.get("hero_candidate_target", 1))
            maximum = int(policy.get("max_candidates_per_shot", candidate_count))
            if candidate_count < minimum:
                report.error(
                    f"shot {shot_id} has {candidate_count} logged candidate(s); "
                    f"Hero policy requires at least {minimum}"
                )
            if candidate_count > maximum:
                report.error(
                    f"shot {shot_id} has {candidate_count} logged candidate(s); "
                    f"policy maximum is {maximum}"
                )


def _validate_evidence_list(
    project_root: Path,
    value: Any,
    prefix: str,
    report: Report,
    final: bool,
) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        report.error(f"{prefix} must be an array")
        return []
    records: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        item_prefix = f"{prefix}[{index}]"
        if isinstance(item, str):
            report.text(
                False,
                f"{item_prefix} must be an evidence object for release",
                final,
            )
            path = _path_status(
                project_root,
                item,
                f"{item_prefix}.path",
                report,
                final,
            )
            records.append(
                {
                    "path": path,
                    "relative_path": item,
                    "role": None,
                    "sha256": None,
                }
            )
            continue
        if not isinstance(item, dict):
            report.error(f"{item_prefix} must be a string or evidence object")
            continue
        path_value = item.get("path")
        path = _path_status(
            project_root,
            path_value,
            f"{item_prefix}.path",
            report,
            final,
        )
        role = item.get("role")
        if role not in EVIDENCE_ROLES:
            report.text(
                False,
                f"{item_prefix}.role must be a supported evidence role",
                final,
            )
            role = None
        expected_hash = item.get("sha256")
        if not isinstance(expected_hash, str) or not re.fullmatch(
            r"[0-9a-fA-F]{64}", expected_hash
        ):
            report.text(
                False,
                f"{item_prefix}.sha256 must be a 64-character SHA-256",
                final,
            )
            expected_hash = None
        if path and expected_hash and sha256_file(path).lower() != expected_hash.lower():
            report.error(f"{item_prefix}.sha256 is stale")
        records.append(
            {
                "path": path,
                "relative_path": str(path_value),
                "role": role,
                "sha256": expected_hash,
            }
        )
    return records


def _validate_content_contract(
    project: dict[str, Any],
    acceptance_by_id: dict[str, dict[str, Any]],
    report: Report,
    final: bool,
) -> None:
    contract = project.get("content_contract")
    if not isinstance(contract, dict):
        report.error("project.content_contract must be an object")
        return

    output = project.get("output")
    output_duration = (
        as_number(output.get("duration_sec")) if isinstance(output, dict) else None
    )
    requirement_ids: set[str] = set()
    requirements_by_id: dict[str, dict[str, Any]] = {}
    core_requirements = 0

    for section in ("required", "forbidden", "signature_events"):
        items = contract.get(section)
        if not isinstance(items, list):
            report.error(f"content_contract.{section} must be an array")
            continue
        if section in {"required", "forbidden"}:
            core_requirements += len(items)
        for index, item in enumerate(items):
            prefix = f"content_contract.{section}[{index}]"
            if not isinstance(item, dict):
                report.error(f"{prefix} must be an object")
                continue
            requirement_id = item.get("id")
            if not nonempty_string(requirement_id):
                report.error(f"{prefix}.id must be a non-empty string")
                requirement_id = None
            elif requirement_id in requirement_ids:
                report.error(f"duplicate content requirement id: {requirement_id}")
            else:
                requirement_ids.add(requirement_id)
            _required_text(
                item.get("observable"),
                f"{prefix}.observable",
                report,
                final,
            )
            if not isinstance(item.get("blocking"), bool):
                report.error(f"{prefix}.blocking must be a boolean")
            acceptance_ids = item.get("acceptance_ids")
            if not isinstance(acceptance_ids, list) or any(
                not nonempty_string(value) for value in acceptance_ids
            ):
                report.error(f"{prefix}.acceptance_ids must be an array of strings")
                acceptance_ids = []
            if final and item.get("blocking") is True and not acceptance_ids:
                report.error(
                    f"{prefix} is blocking but has no linked acceptance criterion"
                )
            linked_blocking_acceptance = False
            for acceptance_id in acceptance_ids:
                acceptance = acceptance_by_id.get(acceptance_id)
                if not acceptance:
                    report.error(
                        f"{prefix} references unknown acceptance id {acceptance_id}"
                    )
                elif requirement_id and requirement_id not in acceptance["requirement_ids"]:
                    report.error(
                        f"acceptance {acceptance_id} does not reference "
                        f"requirement {requirement_id}"
                    )
                elif acceptance.get("blocking"):
                    linked_blocking_acceptance = True
            if (
                final
                and item.get("blocking") is True
                and acceptance_ids
                and not linked_blocking_acceptance
            ):
                report.error(
                    f"{prefix} is blocking but links only non-blocking acceptance"
                )
            if section == "signature_events":
                window = item.get("time_window_sec")
                if (
                    not isinstance(window, list)
                    or len(window) != 2
                    or any(as_number(value) is None for value in window)
                    or float(window[0]) < 0
                    or float(window[1]) <= float(window[0])
                ):
                    report.error(
                        f"{prefix}.time_window_sec must be an increasing [start,end] range"
                    )
                elif (
                    output_duration is not None
                    and float(window[1]) > output_duration + 0.1
                ):
                    report.error(
                        f"{prefix}.time_window_sec ends after the program duration"
                    )
            if requirement_id:
                requirements_by_id[requirement_id] = item

    if final and core_requirements == 0:
        report.error(
            "content_contract needs at least one required or forbidden requirement"
        )

    for acceptance_id, acceptance in acceptance_by_id.items():
        for requirement_id in acceptance.get("requirement_ids", []):
            requirement = requirements_by_id.get(requirement_id)
            if not requirement:
                report.error(
                    f"acceptance {acceptance_id} references unknown requirement "
                    f"{requirement_id}"
                )
            elif acceptance_id not in requirement.get("acceptance_ids", []):
                report.error(
                    f"requirement {requirement_id} does not list acceptance "
                    f"{acceptance_id}"
                )


def _validate_motion_contracts(
    project: dict[str, Any],
    project_root: Path,
    acceptance_by_id: dict[str, dict[str, Any]],
    report: Report,
    final: bool,
) -> None:
    contracts = project.get("motion_contracts", [])
    if not isinstance(contracts, list):
        report.error("project.motion_contracts must be an array")
        return
    contracts_by_id: dict[str, dict[str, Any]] = {}
    known_shots = {
        acceptance["shot_id"] for acceptance in acceptance_by_id.values()
    }

    for index, contract in enumerate(contracts):
        prefix = f"motion_contracts[{index}]"
        if not isinstance(contract, dict):
            report.error(f"{prefix} must be an object")
            continue
        contract_id = contract.get("id")
        if not nonempty_string(contract_id):
            report.error(f"{prefix}.id must be a non-empty string")
            contract_id = None
        elif contract_id in contracts_by_id:
            report.error(f"duplicate motion contract id: {contract_id}")
        else:
            contracts_by_id[contract_id] = contract
        if contract.get("type") not in MOTION_TYPES:
            report.error(f"{prefix}.type is invalid")
        subjects = contract.get("subjects")
        if not isinstance(subjects, list) or not subjects or any(
            not nonempty_string(value) for value in subjects
        ):
            report.error(f"{prefix}.subjects must contain at least one string")
        applies_to = contract.get("applies_to_shots")
        if not isinstance(applies_to, list) or not applies_to:
            report.error(f"{prefix}.applies_to_shots must be a non-empty array")
        else:
            for shot_id in applies_to:
                if shot_id not in known_shots:
                    report.error(f"{prefix} references unknown shot {shot_id}")
        if not isinstance(contract.get("constraints"), dict) or not contract.get(
            "constraints"
        ):
            report.error(f"{prefix}.constraints must be a non-empty object")
        if not isinstance(contract.get("blocking"), bool):
            report.error(f"{prefix}.blocking must be a boolean")
        acceptance_ids = contract.get("acceptance_ids")
        if not isinstance(acceptance_ids, list):
            report.error(f"{prefix}.acceptance_ids must be an array")
            acceptance_ids = []
        if final and contract.get("blocking") is True and not acceptance_ids:
            report.error(f"{prefix} is blocking but has no linked acceptance")
        for acceptance_id in acceptance_ids:
            acceptance = acceptance_by_id.get(acceptance_id)
            if not acceptance:
                report.error(
                    f"{prefix} references unknown acceptance id {acceptance_id}"
                )
            elif contract_id not in acceptance.get("motion_contract_ids", []):
                report.error(
                    f"acceptance {acceptance_id} does not reference motion contract "
                    f"{contract_id}"
                )
        evidence = _validate_evidence_list(
            project_root,
            contract.get("evidence", []),
            f"{prefix}.evidence",
            report,
            final,
        )
        if final and not evidence:
            report.error(f"{prefix} needs evidence")

    for acceptance_id, acceptance in acceptance_by_id.items():
        for contract_id in acceptance.get("motion_contract_ids", []):
            contract = contracts_by_id.get(contract_id)
            if not contract:
                report.error(
                    f"acceptance {acceptance_id} references unknown motion contract "
                    f"{contract_id}"
                )
            elif acceptance_id not in contract.get("acceptance_ids", []):
                report.error(
                    f"motion contract {contract_id} does not list acceptance "
                    f"{acceptance_id}"
                )


def _validate_qa(
    project_root: Path,
    project: dict[str, Any],
    qa: dict[str, Any],
    acceptance_by_id: dict[str, dict[str, Any]],
    report: Report,
    final: bool,
) -> None:
    if qa.get("schema_version") != 1:
        report.error("qa-report.json schema_version must be 1")
    review = qa.get("review")
    if not isinstance(review, dict):
        report.text(False, "qa-report.json review should be an object", final)
        review = {}
    for key in ("reviewer_id", "reviewer", "date", "target"):
        _required_text(review.get(key), f"qa-report.review.{key}", report, final)
    reviewer_kind = review.get("reviewer_kind")
    if reviewer_kind not in REVIEWER_KINDS:
        report.text(
            False,
            "qa-report.review.reviewer_kind must be self, cold-agent, human, or external",
            final,
        )
    if qa.get("verdict") not in {"pending", "pass", "revise", "reject", "waived"}:
        report.error("qa-report.verdict is invalid")
    elif final and qa.get("verdict") != "pass":
        report.error("qa-report.verdict must be pass for release")

    checks = qa.get("checks")
    if not isinstance(checks, list):
        report.error("qa-report.checks must be an array")
        checks = []
    passed_categories: set[str] = set()
    evidenced_categories: set[str] = set()
    located_categories: set[str] = set()
    technical_evidence_found = False
    passed_acceptance: set[str] = set()
    failed_acceptance: set[str] = set()
    checks_by_acceptance: dict[str, list[dict[str, Any]]] = {}
    for index, check in enumerate(checks):
        prefix = f"qa-report.checks[{index}]"
        if not isinstance(check, dict):
            report.error(f"{prefix} must be an object")
            continue
        category = check.get("category")
        if not nonempty_string(category):
            report.error(f"{prefix}.category must be a non-empty string")
            continue
        status = check.get("status")
        if status not in {"pass", "fail", "not_applicable", "not_checked"}:
            report.error(f"{prefix}.status is invalid")
        _required_text(check.get("criterion"), f"{prefix}.criterion", report, final)
        _required_text(check.get("reviewer"), f"{prefix}.reviewer", report, final)
        _required_text(check.get("observed"), f"{prefix}.observed", report, final)
        method = check.get("method")
        if method is not None and method not in ACCEPTANCE_METHODS:
            report.error(f"{prefix}.method is invalid")
        acceptance_ids = check.get("acceptance_ids", [])
        if not isinstance(acceptance_ids, list) or any(
            not nonempty_string(value) for value in acceptance_ids
        ):
            report.error(f"{prefix}.acceptance_ids must be an array of strings")
            acceptance_ids = []
        if final and category in {"visual", "content", "text", "audio_visual"}:
            if not acceptance_ids:
                report.error(f"{prefix} needs at least one acceptance_id")
        for acceptance_id in acceptance_ids:
            acceptance = acceptance_by_id.get(acceptance_id)
            if not acceptance:
                report.error(
                    f"{prefix} references unknown acceptance id {acceptance_id}"
                )
                continue
            checks_by_acceptance.setdefault(acceptance_id, []).append(check)
            if method is not None and acceptance.get("method") != method:
                report.error(
                    f"{prefix}.method does not match acceptance {acceptance_id}"
                )
            if status == "pass":
                passed_acceptance.add(acceptance_id)
            elif status in {"fail", "not_checked"}:
                failed_acceptance.add(acceptance_id)
        if (
            final
            and isinstance(method, str)
            and method.startswith("native-crop")
        ):
            region = check.get("region")
            if (
                not isinstance(region, list)
                or len(region) != 4
                or any(as_number(value) is None for value in region)
                or float(region[2]) <= 0
                or float(region[3]) <= 0
            ):
                report.error(
                    f"{prefix}.region must be [x,y,positive width,positive height]"
                )
        evidence_records = _validate_evidence_list(
            project_root,
            check.get("evidence", []),
            f"{prefix}.evidence",
            report,
            final,
        )
        if status == "pass":
            passed_categories.add(category)
            evidence_values = [
                record["relative_path"]
                for record in evidence_records
                if record.get("relative_path")
            ]
            if evidence_records:
                evidenced_categories.add(category)
            if category == "technical" and "qa/technical-report.json" in evidence_values:
                technical_evidence_found = True
            if evidence_records and (
                as_number(check.get("time_sec")) is not None
                or nonempty_string(check.get("timecode"))
            ):
                located_categories.add(category)

    required_categories = set(REQUIRED_QA_CATEGORIES)
    output = project.get("output")
    if isinstance(output, dict):
        if output.get("captions_required"):
            required_categories.add("accessibility")
        if output.get("captions_required") or output.get("text_required"):
            required_categories.add("text")
        if output.get("has_audio"):
            required_categories.add("audio_visual")
    if final:
        missing = sorted(required_categories - passed_categories)
        if missing:
            report.error(
                "qa-report has no pass check for required categories: "
                + ", ".join(missing)
            )
        unevidenced = sorted(required_categories - evidenced_categories)
        if unevidenced:
            report.error(
                "qa-report has no evidence-backed pass check for: "
                + ", ".join(unevidenced)
            )
        if not technical_evidence_found:
            report.error(
                "qa-report needs a passing technical check citing "
                "qa/technical-report.json"
            )
        locator_categories = {"visual", "audio_visual"}
        if output.get("captions_required") or output.get("text_required"):
            locator_categories.add("text")
        unlocated = sorted(
            category
            for category in locator_categories & required_categories
            if category not in located_categories
        )
        if unlocated:
            report.error(
                "qa-report needs located evidence with time_sec or timecode for: "
                + ", ".join(unlocated)
            )
        for acceptance_id, acceptance in acceptance_by_id.items():
            if not acceptance.get("blocking"):
                continue
            if acceptance_id not in passed_acceptance:
                report.error(
                    f"blocking acceptance {acceptance_id} has no passing QA check"
                )
            if acceptance_id in failed_acceptance:
                report.error(
                    f"blocking acceptance {acceptance_id} has a failed QA check"
                )
        content_contract = project.get("content_contract")
        signature_events = (
            content_contract.get("signature_events", [])
            if isinstance(content_contract, dict)
            else []
        )
        for event in signature_events if isinstance(signature_events, list) else []:
            if not isinstance(event, dict):
                continue
            event_id = str(event.get("id", "signature-event"))
            window = event.get("time_window_sec")
            if (
                not isinstance(window, list)
                or len(window) != 2
                or any(as_number(value) is None for value in window)
            ):
                continue
            start, end = float(window[0]), float(window[1])
            evidence_found = False
            for acceptance_id in event.get("acceptance_ids", []):
                for check in checks_by_acceptance.get(acceptance_id, []):
                    time_value = as_number(check.get("time_sec"))
                    if (
                        check.get("status") == "pass"
                        and check.get("evidence")
                        and time_value is not None
                        and start - 0.001 <= time_value <= end + 0.001
                    ):
                        evidence_found = True
                        break
                if evidence_found:
                    break
            if not evidence_found:
                report.error(
                    f"signature event {event_id} has no located passing evidence "
                    "inside its time window"
                )
        policy = project.get("policy")
        if isinstance(policy, dict) and policy.get("require_independent_review"):
            producer_id = project.get("producer_id")
            if reviewer_kind == "self" or review.get("reviewer_id") == producer_id:
                report.error(
                    "final release requires a reviewer independent from the producer"
                )
        if isinstance(policy, dict) and policy.get("require_human_final_approval"):
            if reviewer_kind not in {"human", "external"}:
                report.error("final release requires a human or external reviewer")
            if review.get("human_approved") is not True:
                report.error("qa-report.review.human_approved must be true")

    findings = qa.get("findings")
    if not isinstance(findings, list):
        report.error("qa-report.findings must be an array")
        findings = []
    for index, finding in enumerate(findings):
        prefix = f"qa-report.findings[{index}]"
        if not isinstance(finding, dict):
            report.error(f"{prefix} must be an object")
            continue
        severity = finding.get("severity")
        if severity not in {"blocker", "major", "minor", "note"}:
            report.error(f"{prefix}.severity is invalid")
        category = finding.get("category", "unspecified")
        status = finding.get("status", "open")
        if final and status == "open" and severity in {"blocker", "major"}:
            report.error(f"{prefix} remains open as {severity}")
        if status == "waived":
            if category in NON_WAIVABLE_CATEGORIES:
                report.error(f"{prefix} cannot waive category {category}")
            waiver = finding.get("waiver")
            if not isinstance(waiver, dict):
                report.error(f"{prefix}.waiver must be an object")
            else:
                for key in ("owner", "reference"):
                    _required_text(
                        waiver.get(key),
                        f"{prefix}.waiver.{key}",
                        report,
                        final,
                    )

    risks = qa.get("residual_risks")
    if not isinstance(risks, list):
        report.error("qa-report.residual_risks must be an array")


def _validate_technical_report(
    project_root: Path,
    project: dict[str, Any],
    report: Report,
    final: bool,
) -> None:
    path = project_root / "qa" / "technical-report.json"
    if not path.is_file():
        report.text(False, "qa/technical-report.json is missing", final)
        return
    technical = load_json(path)
    if not isinstance(technical, dict):
        report.error("qa/technical-report.json must be an object")
        return
    if final and technical.get("decode_ok") is not True:
        report.error("technical report indicates a failed full decode")
    if final and technical.get("matched_expected") is not True:
        report.error("technical report does not match the expected output spec")
    if final and technical.get("inspection_complete") is not True:
        report.error("technical inspection was not completed")
    comparisons = technical.get("comparisons")
    if final:
        if not isinstance(comparisons, list) or not comparisons:
            report.error("technical report contains no expected-spec comparisons")
        elif any(
            not isinstance(item, dict) or item.get("ok") is not True
            for item in comparisons
        ):
            report.error("technical report contains failed comparisons")
    source = technical.get("source")
    source_hash = technical.get("source_sha256")
    output = project.get("output")
    if isinstance(output, dict):
        output_path = _path_status(
            project_root,
            output.get("path"),
            "project.output.path",
            report,
            final,
        )
        if output_path and final:
            if source != output_path.relative_to(project_root.resolve()).as_posix():
                report.error("technical report source does not match project output")
            if source_hash != sha256_file(output_path):
                report.error("technical report hash is stale for project output")
    if final and not technical.get("sample_frames"):
        report.error("technical report contains no sampled review frames")


def _validate_manifest(
    project_root: Path,
    project: dict[str, Any],
    manifest: dict[str, Any],
    report: Report,
    final: bool,
) -> None:
    if manifest.get("schema_version") != 1:
        report.error("delivery-manifest.json schema_version must be 1")
    for key in ("package_id", "created_at", "spec_authority"):
        _required_text(manifest.get(key), f"delivery-manifest.{key}", report, final)
    if not isinstance(manifest.get("rights_verified"), bool):
        report.error("delivery-manifest.rights_verified must be a boolean")
    elif final and not manifest.get("rights_verified"):
        report.error("delivery-manifest rights are not verified")

    files = manifest.get("files")
    if not isinstance(files, list):
        report.error("delivery-manifest.files must be an array")
        return
    if final and not files:
        report.error("delivery-manifest.files must not be empty")
    master_paths: list[str] = []
    has_captions = False
    for index, item in enumerate(files):
        prefix = f"delivery-manifest.files[{index}]"
        if not isinstance(item, dict):
            report.error(f"{prefix} must be an object")
            continue
        role = item.get("role")
        if role not in {
            "master",
            "platform",
            "captions",
            "audio",
            "thumbnail",
            "metadata",
            "other",
        }:
            report.error(f"{prefix}.role is invalid")
        if role == "captions":
            has_captions = True
        file_path = _path_status(
            project_root,
            item.get("path"),
            f"{prefix}.path",
            report,
            final,
        )
        if role == "master" and nonempty_string(item.get("path")):
            master_paths.append(item["path"])
        if file_path and final:
            if item.get("sha256") != sha256_file(file_path):
                report.error(f"{prefix}.sha256 is stale")
            if as_number(item.get("size_bytes")) != file_path.stat().st_size:
                report.error(f"{prefix}.size_bytes is stale")

    output = project.get("output")
    if final and isinstance(output, dict):
        output_path = output.get("path")
        if output_path not in master_paths:
            report.error("project output must appear once as a master delivery file")
        if len(master_paths) != 1:
            report.error("delivery manifest must contain exactly one master")
        if output.get("captions_required") and not has_captions:
            report.error("captions are required but no captions file is delivered")


def _validate_gates(
    project_root: Path,
    project: dict[str, Any],
    report: Report,
    final: bool,
) -> None:
    gates = project.get("gates")
    if not isinstance(gates, dict):
        return
    for gate in GATE_ORDER:
        state = gates.get(gate)
        if not isinstance(state, dict):
            report.error(f"gate {gate} is missing")
            continue
        if state.get("status") != "approved":
            report.text(False, f"gate {gate} is not approved", final)
            continue
        if final:
            _required_text(
                state.get("approved_by"),
                f"gate {gate}.approved_by",
                report,
                final,
            )
            _required_text(
                state.get("approved_at"),
                f"gate {gate}.approved_at",
                report,
                final,
            )
        artifacts = state.get("artifacts")
        if not isinstance(artifacts, dict) or not artifacts:
            report.error(f"gate {gate} has no approved artifact hashes")
            continue
        for required in DEFAULT_GATE_ARTIFACTS[gate]:
            if required not in artifacts:
                report.error(f"gate {gate} does not approve required artifact {required}")
        for value, expected_hash in artifacts.items():
            if not isinstance(value, str) or not isinstance(expected_hash, str):
                report.error(f"gate {gate} has an invalid artifact entry")
                continue
            path = _path_status(
                project_root,
                value,
                f"gate {gate} artifact {value}",
                report,
                final,
            )
            if path and sha256_file(path) != expected_hash:
                report.error(
                    f"gate {gate} is stale because {value} changed after approval"
                )


def _validate_markdown_basis(project_root: Path, report: Report, final: bool) -> None:
    minimums = {
        "brief.md": 180,
        "creative-bible.md": 350,
        "script.md": 180,
        "timeline.md": 120,
        "qa/previs-review.md": 80,
        "rights/asset-ledger.md": 40,
    }
    for value, minimum in minimums.items():
        path = project_root / value
        if not path.is_file():
            report.text(False, f"missing review artifact: {value}", final)
            continue
        text = path.read_text(encoding="utf-8").strip()
        if final and len(text) < minimum:
            report.error(f"{value} is too thin to support a final release")


def validate(project_root: Path, mode: str) -> Report:
    report = Report()
    final = mode == "final"
    _validate_base_files(project_root, report)
    if report.errors:
        return report

    try:
        project = load_json(project_root / "project.json")
        master_clock = load_json(project_root / "master-clock.json")
        assets_document = load_json(project_root / "assets.json")
        shots_document = load_json(project_root / "shots.json")
        timeline_document = load_json(project_root / "timeline.json")
        animatic_review = load_json(project_root / "qa" / "animatic-review.json")
        qa_report = load_json(project_root / "qa-report.json")
        delivery_manifest = load_json(project_root / "delivery-manifest.json")
    except ProjectError as exc:
        report.error(str(exc))
        return report

    if not all(
        isinstance(value, dict)
        for value in (
            project,
            master_clock,
            assets_document,
            shots_document,
            timeline_document,
            animatic_review,
            qa_report,
            delivery_manifest,
        )
    ):
        report.error("all root JSON artifacts must be objects")
        return report

    _validate_project_contract(project, report, final)
    _validate_master_clock(project, master_clock, report, final)
    output = project.get("output")
    output_duration = (
        as_number(output.get("duration_sec")) if isinstance(output, dict) else None
    )
    quality_mode = str(project.get("quality_mode", "standard"))

    assets_by_id = _validate_assets(
        project_root,
        assets_document,
        report,
        final,
        quality_mode,
        set(),
    )
    used_assets, shots, acceptance_by_id = _validate_stress_structure(
        shots_document,
        report,
        final,
        output_duration,
        assets_by_id,
        project_root,
        quality_mode,
    )
    _validate_content_contract(project, acceptance_by_id, report, final)
    _validate_motion_contracts(project, project_root, acceptance_by_id, report, final)
    _validate_timeline(project, timeline_document, shots, report, final)
    _validate_animatic(project_root, project, animatic_review, report, final)

    if used_assets:
        for asset_id in sorted(used_assets):
            asset = assets_by_id.get(asset_id)
            if asset and final and asset.get("status") != "locked":
                report.error(f"asset {asset_id} is used but not locked")
            if (
                asset
                and final
                and asset.get("role") in {"hero", "critical"}
                and not asset.get("references")
            ):
                report.error(f"asset {asset_id} has no approved reference")

    records = _read_generation_log(project_root, report)
    if final:
        _validate_generation_selection(project_root, project, shots, records, report)
        _validate_qa(
            project_root,
            project,
            qa_report,
            acceptance_by_id,
            report,
            final,
        )
        _validate_technical_report(project_root, project, report, final)
        _validate_manifest(project_root, project, delivery_manifest, report, final)
        _validate_gates(project_root, project, report, final)
        _validate_markdown_basis(project_root, report, final)
    else:
        _validate_qa(
            project_root,
            project,
            qa_report,
            acceptance_by_id,
            report,
            final,
        )

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--mode", choices=("plan", "final"), default="plan")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    report = validate(args.project.resolve(), args.mode)
    if args.json_output:
        print(
            json.dumps(
                {
                    "mode": args.mode,
                    "ok": not report.errors,
                    "errors": report.errors,
                    "warnings": report.warnings,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        for message in report.errors:
            print(f"ERROR: {message}")
        for message in report.warnings:
            print(f"WARNING: {message}")
        status = "PASS" if not report.errors else "FAIL"
        print(
            f"{status}: {len(report.errors)} error(s), "
            f"{len(report.warnings)} warning(s)"
        )
    return 0 if not report.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

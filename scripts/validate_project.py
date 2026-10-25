#!/usr/bin/env python3
"""Validate a video-production-director project or enforce final release."""

from __future__ import annotations

import argparse
import json
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
REQUIRED_QA_CATEGORIES = {"technical", "visual", "editorial", "rights"}
NON_WAIVABLE_CATEGORIES = {"rights", "accessibility", "safety", "legal", "policy"}


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
        for key in ("has_audio", "captions_required"):
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
                for key in ("use", "controls", "must_not_control"):
                    _required_text(
                        reference.get(key),
                        f"{ref_prefix}.{key}",
                        report,
                        final,
                    )

        stress_tests = asset.get("stress_tests", [])
        passes = 0
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
                    _path_status(
                        project_root,
                        stress.get("evidence"),
                        f"{test_prefix}.evidence",
                        report,
                        final,
                    )
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
) -> tuple[set[str], list[dict[str, Any]]]:
    if shots_document.get("schema_version") != 1:
        report.error("shots.json schema_version must be 1")
    shots = shots_document.get("shots")
    if not isinstance(shots, list):
        report.error("shots.json shots must be an array")
        return set(), []
    if final and not shots:
        report.error("shots.json must contain at least one shot")

    used_assets: set[str] = set()
    valid_shots: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

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
                _required_text(
                    criterion.get("criterion"),
                    f"{criterion_prefix}.criterion",
                    report,
                    final,
                )
                if not isinstance(criterion.get("blocking"), bool):
                    report.error(f"{criterion_prefix}.blocking must be a boolean")
                elif criterion["blocking"]:
                    blocking_count += 1
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
    return used_assets, valid_shots


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


def _artifact_paths(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _validate_qa(
    project_root: Path,
    project: dict[str, Any],
    qa: dict[str, Any],
    report: Report,
    final: bool,
) -> None:
    if qa.get("schema_version") != 1:
        report.error("qa-report.json schema_version must be 1")
    review = qa.get("review")
    if not isinstance(review, dict):
        report.text(False, "qa-report.json review should be an object", final)
        review = {}
    for key in ("reviewer", "date", "target"):
        _required_text(review.get(key), f"qa-report.review.{key}", report, final)
    if qa.get("verdict") not in {"pending", "pass", "revise", "reject", "waived"}:
        report.error("qa-report.verdict is invalid")
    elif final and qa.get("verdict") != "pass":
        report.error("qa-report.verdict must be pass for release")

    checks = qa.get("checks")
    if not isinstance(checks, list):
        report.error("qa-report.checks must be an array")
        checks = []
    passed_categories: set[str] = set()
    technical_evidence_found = False
    located_visual_evidence = False
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
        if status == "pass":
            passed_categories.add(category)
            evidence_values = _artifact_paths(check.get("evidence"))
            for evidence_index, value in enumerate(evidence_values):
                _path_status(
                    project_root,
                    value,
                    f"{prefix}.evidence[{evidence_index}]",
                    report,
                    final,
                )
            if category == "technical" and "qa/technical-report.json" in evidence_values:
                technical_evidence_found = True
            if (
                category == "visual"
                and evidence_values
                and (
                    as_number(check.get("time_sec")) is not None
                    or nonempty_string(check.get("timecode"))
                )
            ):
                located_visual_evidence = True

    required_categories = set(REQUIRED_QA_CATEGORIES)
    output = project.get("output")
    if isinstance(output, dict) and output.get("captions_required"):
        required_categories.add("accessibility")
    if final:
        missing = sorted(required_categories - passed_categories)
        if missing:
            report.error(
                "qa-report has no pass check for required categories: "
                + ", ".join(missing)
            )
        if not technical_evidence_found:
            report.error(
                "qa-report needs a passing technical check citing "
                "qa/technical-report.json"
            )
        if not located_visual_evidence:
            report.error(
                "qa-report needs located visual evidence with time_sec or timecode"
            )
        policy = project.get("policy")
        if isinstance(policy, dict) and policy.get("require_human_final_approval"):
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
        assets_document = load_json(project_root / "assets.json")
        shots_document = load_json(project_root / "shots.json")
        qa_report = load_json(project_root / "qa-report.json")
        delivery_manifest = load_json(project_root / "delivery-manifest.json")
    except ProjectError as exc:
        report.error(str(exc))
        return report

    if not all(
        isinstance(value, dict)
        for value in (
            project,
            assets_document,
            shots_document,
            qa_report,
            delivery_manifest,
        )
    ):
        report.error("all root JSON artifacts must be objects")
        return report

    _validate_project_contract(project, report, final)
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
    used_assets, shots = _validate_stress_structure(
        shots_document,
        report,
        final,
        output_duration,
        assets_by_id,
        project_root,
        quality_mode,
    )

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
        _validate_qa(project_root, project, qa_report, report, final)
        _validate_technical_report(project_root, project, report, final)
        _validate_manifest(project_root, project, delivery_manifest, report, final)
        _validate_gates(project_root, project, report, final)
        _validate_markdown_basis(project_root, report, final)
    else:
        _validate_qa(project_root, project, qa_report, report, final)

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

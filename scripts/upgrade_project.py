#!/usr/bin/env python3
"""Add schema-v2 review artifacts without overwriting existing work."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from _common import (
    GATE_ORDER,
    REVIEW_CONTRACT_SCHEMA_VERSION,
    SKILL_ROOT,
    SKILL_VERSION,
    ProjectError,
    load_json,
    sha256_bytes,
    sha256_file,
    utc_now,
    write_json_atomic,
)


SKILL_ROOT = Path(__file__).resolve().parent.parent
SCAFFOLD = SKILL_ROOT / "assets" / "scaffold"


def copy_missing(project_root: Path, value: str) -> bool:
    source = SCAFFOLD / value
    target = project_root / value
    if target.exists():
        return False
    if not source.is_file():
        raise ProjectError(f"scaffold file is missing: {value}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return True


def project_contract_hash(project_root: Path) -> str | None:
    path = project_root / "project.json"
    if not path.is_file():
        return None
    project = load_json(path)
    if not isinstance(project, dict):
        return None
    project.pop("gates", None)
    canonical = json.dumps(
        project,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(canonical)


def upgrade_handoff(project_root: Path) -> bool:
    path = project_root / "qa" / "review-handoff.json"
    if not path.is_file():
        return False
    handoff = load_json(path)
    if not isinstance(handoff, dict):
        raise ProjectError("qa/review-handoff.json must contain an object")
    original = json.dumps(handoff, ensure_ascii=False, sort_keys=True)
    handoff["schema_version"] = REVIEW_CONTRACT_SCHEMA_VERSION
    if not isinstance(handoff.get("created_at"), str) or not handoff.get("created_at"):
        handoff["created_at"] = utc_now()
    handoff.setdefault("generation_skill", {})
    generation = handoff["generation_skill"]
    if not isinstance(generation, dict):
        generation = {}
        handoff["generation_skill"] = generation
    generation["name"] = "video-production-director"
    generation["version"] = SKILL_VERSION
    if not isinstance(generation.get("path"), str) or not generation.get("path"):
        generation["path"] = str(SKILL_ROOT)
    generation.setdefault("sha256", None)
    handoff["review_skill_min_version"] = "0.3.0"
    handoff.setdefault("review_scope", [])
    handoff.setdefault("required_observations", [])
    handoff.setdefault("intentional_choices", [])
    handoff.setdefault("anchors", [])
    handoff.setdefault("known_clean_controls", [])
    handoff.setdefault("known_failure_controls", [])
    handoff.setdefault("excluded_checks", [])

    sources = handoff.get("sources")
    if isinstance(sources, dict):
        for role, value in list(sources.items()):
            if isinstance(value, str):
                value = {"path": value, "sha256": None}
                sources[role] = value
            if not isinstance(value, dict) or not isinstance(value.get("path"), str):
                continue
            source_path = project_root / value["path"]
            if not source_path.is_file():
                continue
            if role == "project":
                value["sha256"] = project_contract_hash(project_root)
                value["hash_mode"] = "json-without-gates"
            else:
                value["sha256"] = sha256_file(source_path)
                value.pop("hash_mode", None)
    updated = json.dumps(handoff, ensure_ascii=False, sort_keys=True)
    if updated != original:
        write_json_atomic(path, handoff)
        return True
    return False


def upgrade(project_root: Path) -> dict[str, Any]:
    project_file = project_root / "project.json"
    if not project_file.is_file():
        raise ProjectError(f"project.json is missing: {project_root}")
    project = load_json(project_file)
    if not isinstance(project, dict):
        raise ProjectError("project.json must contain an object")

    created: list[str] = []
    for value in (
        "script.md",
        "master-clock.json",
        "timeline.json",
        "qa/animatic-review.json",
        "qa/review-handoff.json",
        "qa/review-result.json",
        "qa/change-response.json",
        "qa/review-verification.json",
    ):
        if copy_missing(project_root, value):
            created.append(value)
    handoff_upgraded = upgrade_handoff(project_root)
    (project_root / "animatic").mkdir(parents=True, exist_ok=True)

    output = project.get("output")
    if not isinstance(output, dict):
        raise ProjectError("project.json has no valid output object")
    output.setdefault("text_required", False)
    project.setdefault("producer_id", "legacy-project")
    project.setdefault(
        "content_contract",
        {
            "required": [],
            "forbidden": [],
            "signature_events": [],
        },
    )
    project.setdefault("motion_contracts", [])
    policy = project.get("policy")
    if not isinstance(policy, dict):
        policy = {}
    policy.setdefault("require_independent_review", True)
    policy.setdefault("require_companion_review", True)
    project["policy"] = policy
    duration = output.get("duration_sec")
    clock = project.get("clock")
    clock_type = clock.get("type") if isinstance(clock, dict) else "visual"
    clock_source = clock.get("source") if isinstance(clock, dict) else ""

    if "master-clock.json" in created:
        master_clock = load_json(project_root / "master-clock.json")
        master_clock["type"] = clock_type or "visual"
        master_clock["source"] = clock_source or master_clock.get("source", "")
        if isinstance(duration, (int, float)) and not isinstance(duration, bool):
            master_clock["duration_sec"] = duration
        write_json_atomic(project_root / "master-clock.json", master_clock)

    if "timeline.json" in created:
        timeline = load_json(project_root / "timeline.json")
        if isinstance(duration, (int, float)) and not isinstance(duration, bool):
            timeline["duration_sec"] = duration
        write_json_atomic(project_root / "timeline.json", timeline)

    gates = project.get("gates")
    if not isinstance(gates, dict):
        gates = {}
    ordered_gates: dict[str, Any] = {}
    for gate in GATE_ORDER:
        state = gates.get(
            gate,
            {
                "status": "pending",
                "approved_by": None,
                "approved_at": None,
                "artifacts": {},
            },
        )
        if (
            gate != "brief"
            and isinstance(state, dict)
            and state.get("status") == "approved"
        ):
            history = state.get("history")
            if not isinstance(history, list):
                history = []
            history.append(
                {
                    "status": state.get("status"),
                    "approved_by": state.get("approved_by"),
                    "approved_at": state.get("approved_at"),
                    "artifacts": state.get("artifacts", {}),
                }
            )
            state = {
                "status": "pending",
                "approved_by": None,
                "approved_at": None,
                "artifacts": {},
                "history": history,
            }
        ordered_gates[gate] = state
    project["gates"] = ordered_gates
    project["upgraded_to"] = SKILL_VERSION
    project["upgraded_at"] = utc_now()
    write_json_atomic(project_file, project)

    qa_file = project_root / "qa-report.json"
    if qa_file.is_file():
        qa = load_json(qa_file)
        if isinstance(qa, dict):
            review = qa.get("review")
            if not isinstance(review, dict):
                review = {}
            review.setdefault("reviewer_id", review.get("reviewer") or "legacy-reviewer")
            review.setdefault("reviewer_kind", "self")
            review.setdefault("human_approved", False)
            qa["review"] = review
            checks = qa.get("checks")
            if isinstance(checks, list):
                for check in checks:
                    if isinstance(check, dict):
                        check.setdefault("acceptance_ids", [])
            write_json_atomic(qa_file, qa)
    return {
        "status": "upgraded",
        "project": str(project_root),
        "created": created,
        "review_handoff_upgraded": handoff_upgraded,
        "text_required": output["text_required"],
        "gate_count": len(ordered_gates),
        "requires_manual_review": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    try:
        result = upgrade(args.project.resolve())
    except ProjectError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print("RESULT: " + json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Add v0.2.0 project artifacts without overwriting existing work."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from _common import (
    GATE_ORDER,
    ProjectError,
    load_json,
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
    ):
        if copy_missing(project_root, value):
            created.append(value)
    (project_root / "animatic").mkdir(parents=True, exist_ok=True)

    output = project.get("output")
    if not isinstance(output, dict):
        raise ProjectError("project.json has no valid output object")
    output.setdefault("text_required", False)
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
        ordered_gates[gate] = gates.get(
            gate,
            {
                "status": "pending",
                "approved_by": None,
                "approved_at": None,
                "artifacts": {},
            },
        )
    project["gates"] = ordered_gates
    project["upgraded_to"] = "0.2.0"
    project["upgraded_at"] = utc_now()
    write_json_atomic(project_file, project)
    return {
        "status": "upgraded",
        "project": str(project_root),
        "created": created,
        "text_required": output["text_required"],
        "gate_count": len(ordered_gates),
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

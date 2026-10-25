#!/usr/bin/env python3
"""Hash gate artifacts and record an explicit stage approval."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _common import (
    DEFAULT_GATE_ARTIFACTS,
    GATE_ORDER,
    ProjectError,
    load_json,
    project_path,
    sha256_file,
    utc_now,
    write_json_atomic,
)


def approve(
    project_root: Path,
    gate: str,
    owner: str,
    custom_artifacts: list[str] | None,
) -> dict[str, object]:
    project_file = project_root / "project.json"
    project = load_json(project_file)
    gates = project.get("gates")
    if not isinstance(gates, dict):
        raise ProjectError("project.json has no valid gates object")

    index = GATE_ORDER.index(gate)
    for previous in GATE_ORDER[:index]:
        previous_gate = gates.get(previous)
        if not isinstance(previous_gate, dict) or previous_gate.get("status") != "approved":
            raise ProjectError(f"previous gate is not approved: {previous}")

    artifact_values = custom_artifacts or list(DEFAULT_GATE_ARTIFACTS[gate])
    if not artifact_values:
        raise ProjectError(f"no artifacts configured for gate: {gate}")

    artifacts: dict[str, str] = {}
    for value in artifact_values:
        path = project_path(project_root, value)
        if not path.is_file():
            raise ProjectError(f"missing gate artifact: {value}")
        artifacts[path.relative_to(project_root.resolve()).as_posix()] = sha256_file(
            path
        )

    current = gates.get(gate)
    if not isinstance(current, dict):
        current = {}
    history = current.get("history")
    if not isinstance(history, list):
        history = []
    if current.get("status") == "approved" and current.get("approved_at"):
        history.append(
            {
                "status": current.get("status"),
                "approved_by": current.get("approved_by"),
                "approved_at": current.get("approved_at"),
                "artifacts": current.get("artifacts", {}),
            }
        )

    approval = {
        "status": "approved",
        "approved_by": owner,
        "approved_at": utc_now(),
        "artifacts": artifacts,
        "history": history,
    }
    gates[gate] = approval
    project["gates"] = gates
    write_json_atomic(project_file, project)
    return {
        "status": "approved",
        "gate": gate,
        "owner": owner,
        "artifacts": artifacts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--gate", required=True, choices=GATE_ORDER)
    parser.add_argument("--owner", required=True)
    parser.add_argument(
        "--artifact",
        action="append",
        help="Override the default project-relative artifact list; repeatable",
    )
    args = parser.parse_args()

    try:
        result = approve(
            args.project.resolve(),
            args.gate,
            args.owner,
            args.artifact,
        )
    except ProjectError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(
        "RESULT: "
        + __import__("json").dumps(result, ensure_ascii=False)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

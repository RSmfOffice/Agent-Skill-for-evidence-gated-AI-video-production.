#!/usr/bin/env python3
"""Append one generated-video candidate to the project generation log."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from _common import (
    ProjectError,
    as_number,
    load_json,
    project_path,
    sha256_file,
    utc_now,
)


CONTROL_MODES = {
    "image-to-video",
    "first-last-frame",
    "reference-conditioned",
    "text-to-video",
    "video-to-video",
}
VERDICTS = {"pending", "selected", "rejected", "repair"}


def command_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return as_number(value)
    try:
        return as_number(float(str(value)))
    except ValueError:
        return None


def read_log(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ProjectError(f"{path.name} line {index}: {exc}") from exc
        if not isinstance(value, dict):
            raise ProjectError(f"{path.name} line {index} must be an object")
        records.append(value)
    return records


def record(project_root: Path, args: argparse.Namespace) -> dict[str, Any]:
    shots_document = load_json(project_root / "shots.json")
    shots = shots_document.get("shots")
    if not isinstance(shots, list):
        raise ProjectError("shots.json has no valid shots array")
    if not any(isinstance(shot, dict) and shot.get("id") == args.shot for shot in shots):
        raise ProjectError(f"unknown shot: {args.shot}")

    log_path = project_root / "generation-log.jsonl"
    records = read_log(log_path)
    if any(item.get("candidate_id") == args.candidate for item in records):
        raise ProjectError(f"candidate already appears in the log: {args.candidate}")

    output_path = project_path(project_root, args.output)
    if not output_path.is_file():
        raise ProjectError(f"candidate output does not exist: {args.output}")
    prompt_path = project_path(project_root, args.prompt_file)
    if not prompt_path.is_file():
        raise ProjectError(f"prompt file does not exist: {args.prompt_file}")

    parameters: dict[str, Any] = {}
    if args.parameters:
        try:
            parameters = json.loads(args.parameters)
        except json.JSONDecodeError as exc:
            raise ProjectError(f"--parameters is not valid JSON: {exc}") from exc
        if not isinstance(parameters, dict):
            raise ProjectError("--parameters must decode to a JSON object")

    references: list[dict[str, str]] = []
    for value in args.reference or []:
        path = project_path(project_root, value)
        if not path.is_file():
            raise ProjectError(f"reference does not exist: {value}")
        references.append(
            {
                "path": path.relative_to(project_root.resolve()).as_posix(),
                "sha256": sha256_file(path),
            }
        )

    if args.verdict == "selected":
        for item in records:
            if item.get("shot_id") == args.shot and item.get("verdict") == "selected":
                raise ProjectError(
                    f"shot {args.shot} already has selected candidate "
                    f"{item.get('candidate_id')}"
                )

    cost = command_number(args.cost)
    latency = command_number(args.latency_seconds)
    if cost is None or cost < 0:
        raise ProjectError("--cost must be a non-negative number")
    if latency is not None and latency < 0:
        raise ProjectError("--latency-seconds must be non-negative")

    record_value: dict[str, Any] = {
        "schema_version": 1,
        "candidate_id": args.candidate,
        "shot_id": args.shot,
        "model": args.model,
        "model_version": args.model_version,
        "control_mode": args.control_mode,
        "prompt_file": prompt_path.relative_to(project_root.resolve()).as_posix(),
        "prompt_sha256": sha256_file(prompt_path),
        "reference_assets": references,
        "parameters": parameters,
        "seed": args.seed,
        "cost": cost,
        "latency_seconds": latency,
        "output": output_path.relative_to(project_root.resolve()).as_posix(),
        "output_sha256": sha256_file(output_path),
        "verdict": args.verdict,
        "failure_codes": args.failure_code or [],
        "notes": args.note or "",
        "created_at": utc_now(),
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record_value, ensure_ascii=False) + "\n")
    return record_value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--shot", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--model-version", default="")
    parser.add_argument("--control-mode", required=True, choices=sorted(CONTROL_MODES))
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--reference", action="append")
    parser.add_argument("--parameters", default="")
    parser.add_argument("--seed", default="")
    parser.add_argument("--cost", default="0")
    parser.add_argument("--latency-seconds", default=None)
    parser.add_argument("--verdict", choices=sorted(VERDICTS), default="pending")
    parser.add_argument("--failure-code", action="append")
    parser.add_argument("--note")
    args = parser.parse_args()

    try:
        value = record(args.project.resolve(), args)
    except ProjectError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print("RESULT: " + json.dumps(value, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

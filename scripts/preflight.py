#!/usr/bin/env python3
"""Report local capabilities relevant to a video production run."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from _common import ProjectError, load_json, nonempty_string
from validate_project import validate


def tool_status(
    command: str,
    environment_name: str,
) -> dict[str, Any]:
    explicit = os.environ.get(environment_name)
    if explicit:
        path = Path(explicit).expanduser()
        return {
            "available": path.is_file(),
            "path": str(path),
            "source": f"env:{environment_name}",
        }
    found = shutil.which(command)
    return {
        "available": bool(found),
        "path": found,
        "source": "PATH" if found else "missing",
    }


def validate_model_profile(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        value = load_json(path)
    except ProjectError as exc:
        return [str(exc)]
    if not isinstance(value, dict):
        return [f"{path} must contain an object"]
    if value.get("schema_version") != 1:
        errors.append(f"{path}: schema_version must be 1")
    for key in ("provider", "model", "endpoint_version", "verified_at"):
        if not nonempty_string(value.get(key)) or str(value.get(key)).strip() in {
            "replace-me",
            "YYYY-MM-DD",
        }:
            errors.append(f"{path}: {key} must be non-empty")
    if not isinstance(value.get("modes"), list) or not value.get("modes"):
        errors.append(f"{path}: modes must be a non-empty array")
    if not isinstance(value.get("controls"), dict):
        errors.append(f"{path}: controls must be an object")
    if not isinstance(value.get("commercial"), dict):
        errors.append(f"{path}: commercial must be an object")
    return errors


def preflight(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    tools = {
        "ffmpeg": tool_status("ffmpeg", "FFMPEG_BIN"),
        "ffprobe": tool_status("ffprobe", "FFPROBE_BIN"),
        "node": tool_status("node", "NODE_BIN"),
        "npx": tool_status("npx", "NPX_BIN"),
        "git": tool_status("git", "GIT_BIN"),
    }
    errors: list[str] = []
    warnings: list[str] = []

    if sys.version_info < (3, 10):
        errors.append("Python 3.10 or newer is required")
    for required in ("ffmpeg", "ffprobe"):
        if not tools[required]["available"]:
            message = f"{required} is not available"
            if args.require_media_tools:
                errors.append(message)
            else:
                warnings.append(message)
    for optional in ("node", "npx", "git"):
        if not tools[optional]["available"]:
            warnings.append(f"{optional} is not available")

    project_report: dict[str, Any] | None = None
    if args.project:
        report = validate(args.project.resolve(), "plan")
        project_report = {
            "project": str(args.project.resolve()),
            "errors": report.errors,
            "warnings": report.warnings,
        }
        errors.extend(f"project: {message}" for message in report.errors)
        warnings.extend(f"project: {message}" for message in report.warnings)

    profiles: list[dict[str, Any]] = []
    for value in args.model_profile or []:
        path = Path(value).resolve()
        profile_errors = validate_model_profile(path)
        profiles.append(
            {
                "path": str(path),
                "ok": not profile_errors,
                "errors": profile_errors,
            }
        )
        errors.extend(profile_errors)

    status = "blocked" if errors else ("degraded" if warnings else "ready")
    return (
        {
            "status": status,
            "python": {
                "available": True,
                "version": sys.version.split()[0],
                "supported": sys.version_info >= (3, 10),
            },
            "tools": tools,
            "project": project_report,
            "model_profiles": profiles,
            "errors": errors,
            "warnings": warnings,
        },
        2 if status == "blocked" else 0,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path)
    parser.add_argument("--model-profile", action="append")
    parser.add_argument("--require-media-tools", action="store_true")
    args = parser.parse_args()

    result, code = preflight(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

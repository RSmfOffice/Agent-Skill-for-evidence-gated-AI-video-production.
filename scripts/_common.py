#!/usr/bin/env python3
"""Shared helpers for video-production-director scripts."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


GATE_ORDER = (
    "brief",
    "direction",
    "continuity",
    "previs",
    "generation",
    "edit",
    "review",
    "delivery",
)

DEFAULT_GATE_ARTIFACTS = {
    "brief": ("brief.md",),
    "direction": ("creative-bible.md",),
    "continuity": ("assets.json",),
    "previs": ("shots.json", "timeline.md", "qa/previs-review.md"),
    "generation": ("generation-log.jsonl", "shots.json"),
    "edit": ("timeline.md",),
    "review": ("qa-report.json", "qa/technical-report.json"),
    "delivery": ("delivery-manifest.json",),
}

REQUIRED_PROJECT_FILES = (
    "project.json",
    "brief.md",
    "creative-bible.md",
    "assets.json",
    "shots.json",
    "timeline.md",
    "generation-log.jsonl",
    "qa-report.json",
    "delivery-manifest.json",
)


class ProjectError(Exception):
    """A predictable project or command error."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ProjectError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ProjectError(f"invalid JSON in {path}: {exc}") from exc


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def project_path(project_root: Path, value: str) -> Path:
    path = (project_root / value).resolve()
    if not is_within(path, project_root):
        raise ProjectError(f"path escapes the project: {value}")
    return path


def relative_project_path(project_root: Path, path: Path) -> str:
    resolved = path.resolve()
    if not is_within(resolved, project_root):
        raise ProjectError(f"path escapes the project: {path}")
    return resolved.relative_to(project_root.resolve()).as_posix()


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def as_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number

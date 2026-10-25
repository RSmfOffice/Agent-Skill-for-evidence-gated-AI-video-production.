#!/usr/bin/env python3
"""Create a stateful video-production project from the bundled scaffold."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

from _common import ProjectError, load_json, utc_now, write_json_atomic


SKILL_ROOT = Path(__file__).resolve().parent.parent
SCAFFOLD = SKILL_ROOT / "assets" / "scaffold"
EXTRA_DIRECTORIES = (
    "inputs",
    "assets",
    "prompts",
    "generations",
    "selects",
    "qa",
    "rights",
    "renders",
    "delivery",
)


def project_slug(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:48] or "video-project"


def initialize(destination: Path, title: str, quality_mode: str) -> dict[str, str]:
    if not SCAFFOLD.is_dir():
        raise ProjectError(f"scaffold is missing: {SCAFFOLD}")
    if destination.exists() and any(destination.iterdir()):
        raise ProjectError(
            f"destination already exists and is not empty: {destination}"
        )

    destination.mkdir(parents=True, exist_ok=True)
    for source in SCAFFOLD.rglob("*"):
        relative = source.relative_to(SCAFFOLD)
        target = destination / relative
        if source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    for directory in EXTRA_DIRECTORIES:
        (destination / directory).mkdir(parents=True, exist_ok=True)

    project_file = destination / "project.json"
    project = load_json(project_file)
    project["title"] = title
    project["project_id"] = project_slug(title)
    project["quality_mode"] = quality_mode
    project["created_at"] = utc_now()
    write_json_atomic(project_file, project)

    brief_file = destination / "brief.md"
    brief = brief_file.read_text(encoding="utf-8")
    brief = brief.replace("# Brief\n", f"# Brief: {title}\n", 1)
    brief_file.write_text(brief, encoding="utf-8")

    (destination / "generation-log.jsonl").write_text("", encoding="utf-8")
    return {
        "status": "created",
        "project": str(destination.resolve()),
        "quality_mode": quality_mode,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path, help="New project directory")
    parser.add_argument("--title", required=True)
    parser.add_argument(
        "--mode",
        choices=("draft", "standard", "hero"),
        default="hero",
    )
    args = parser.parse_args()

    try:
        result = initialize(args.destination.resolve(), args.title, args.mode)
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

#!/usr/bin/env python3
"""Build a hash-verified delivery manifest from final project files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _common import (
    ProjectError,
    load_json,
    project_path,
    sha256_file,
    utc_now,
    write_json_atomic,
)


ROLES = {
    "master",
    "platform",
    "captions",
    "audio",
    "thumbnail",
    "metadata",
    "other",
}


def parse_file(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise ProjectError(f"--file must be ROLE=PATH: {value}")
    role, path = value.split("=", 1)
    if role not in ROLES:
        raise ProjectError(f"invalid delivery role: {role}")
    if not path.strip():
        raise ProjectError("delivery file path must not be empty")
    return role, path


def build_manifest(project_root: Path, args: argparse.Namespace) -> dict[str, object]:
    project = load_json(project_root / "project.json")
    output = project.get("output")
    if not isinstance(output, dict):
        raise ProjectError("project.json has no valid output object")
    output_path = output.get("path")
    if not isinstance(output_path, str) or not output_path:
        raise ProjectError("project.output.path is missing")

    seen_paths: set[str] = set()
    files: list[dict[str, object]] = []
    for value in args.file:
        role, raw_path = parse_file(value)
        path = project_path(project_root, raw_path)
        if not path.is_file():
            raise ProjectError(f"delivery file does not exist: {raw_path}")
        relative = path.relative_to(project_root.resolve()).as_posix()
        if relative in seen_paths:
            raise ProjectError(f"delivery path appears more than once: {relative}")
        seen_paths.add(relative)
        files.append(
            {
                "role": role,
                "path": relative,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )

    masters = [item for item in files if item["role"] == "master"]
    if len(masters) != 1:
        raise ProjectError("exactly one --file master=PATH entry is required")
    if masters[0]["path"] != output_path:
        raise ProjectError("the master path must equal project.output.path")

    manifest = {
        "schema_version": 1,
        "package_id": f"{project.get('project_id', 'video-project')}-{args.version}",
        "created_at": utc_now(),
        "spec_authority": args.authority,
        "rights_verified": bool(args.rights_verified),
        "files": files,
    }
    write_json_atomic(project_root / "delivery-manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument(
        "--file",
        action="append",
        required=True,
        metavar="ROLE=PATH",
    )
    parser.add_argument("--authority", required=True)
    parser.add_argument("--version", default="v001")
    parser.add_argument("--rights-verified", action="store_true")
    args = parser.parse_args()

    try:
        manifest = build_manifest(args.project.resolve(), args)
    except ProjectError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(
        "RESULT: "
        + json.dumps(
            {
                "status": "written",
                "package_id": manifest["package_id"],
                "files": len(manifest["files"]),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

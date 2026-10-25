#!/usr/bin/env python3
"""Create uniformly sampled contact-sheet pages with FFmpeg."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def resolve_tool(
    explicit: str | None,
    environment_name: str,
    command: str,
) -> Path | None:
    candidate = explicit or os.environ.get(environment_name)
    if candidate:
        path = Path(candidate).expanduser()
        return path if path.is_file() else None
    found = shutil.which(command)
    return Path(found) if found else None


def run_capture(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def media_duration(ffprobe: Path, media: Path) -> float:
    result = run_capture(
        [
            str(ffprobe),
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(media),
        ]
    )
    if result.returncode != 0:
        raise ValueError(
            "ffprobe failed: " + "\n".join(result.stderr.splitlines()[-8:])
        )
    try:
        value = json.loads(result.stdout)
        duration = float(value["format"]["duration"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read media duration: {exc}") from exc
    if duration <= 0:
        raise ValueError("media duration must be positive")
    return duration


def choose_output_dir(requested: Path) -> Path:
    if requested.exists() and list(requested.glob("sheet_*.jpg")):
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        requested = requested / f"run-{stamp}"
    requested.mkdir(parents=True, exist_ok=True)
    return requested


def create_sheets(args: argparse.Namespace) -> dict[str, object]:
    media = args.media.resolve()
    if not media.is_file():
        raise ValueError(f"media file does not exist: {media}")
    ffmpeg = resolve_tool(args.ffmpeg, "FFMPEG_BIN", "ffmpeg")
    ffprobe = resolve_tool(args.ffprobe, "FFPROBE_BIN", "ffprobe")
    if ffmpeg is None:
        raise ValueError("ffmpeg not found; pass --ffmpeg or set FFMPEG_BIN")
    if ffprobe is None:
        raise ValueError("ffprobe not found; pass --ffprobe or set FFPROBE_BIN")

    duration = media_duration(ffprobe, media)
    frames_per_page = args.columns * args.rows
    interval = args.interval or duration / frames_per_page
    if interval <= 0:
        raise ValueError("sampling interval must be positive")

    output_dir = choose_output_dir(args.output_dir.resolve())
    filter_graph = (
        f"fps=1/{interval:.8f},"
        f"scale={args.cell_width}:-2,"
        f"tile={args.columns}x{args.rows}:padding=4:margin=4"
    )
    result = run_capture(
        [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(media),
            "-vf",
            filter_graph,
            "-q:v",
            "2",
            str(output_dir / "sheet_%03d.jpg"),
        ]
    )
    if result.returncode != 0:
        raise ValueError(
            "ffmpeg contact-sheet render failed: "
            + "\n".join(result.stderr.splitlines()[-12:])
        )
    sheets = sorted(output_dir.glob("sheet_*.jpg"))
    if not sheets:
        raise ValueError("ffmpeg produced no contact-sheet pages")
    return {
        "status": "created",
        "media": str(media),
        "duration_sec": duration,
        "interval_sec": interval,
        "columns": args.columns,
        "rows": args.rows,
        "cell_width": args.cell_width,
        "output_dir": str(output_dir),
        "sheets": [str(path) for path in sheets],
        "note": "Use sheets as overview only; inspect individual native-resolution frames.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("media", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--columns", type=int, default=5)
    parser.add_argument("--rows", type=int, default=4)
    parser.add_argument("--cell-width", type=int, default=320)
    parser.add_argument("--interval", type=float)
    parser.add_argument("--ffmpeg")
    parser.add_argument("--ffprobe")
    args = parser.parse_args()

    if args.columns <= 0 or args.rows <= 0 or args.cell_width <= 0:
        print("ERROR: columns, rows, and cell width must be positive", file=sys.stderr)
        return 2
    try:
        result = create_sheets(args)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print("RESULT: " + json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

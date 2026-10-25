#!/usr/bin/env python3
"""Inspect a rendered video and record deterministic technical evidence."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _common import (
    ProjectError,
    as_number,
    is_within,
    load_json,
    project_path,
    relative_project_path,
    sha256_file,
    utc_now,
    write_json_atomic,
)


def resolve_tool(
    explicit: str | None,
    environment_name: str,
    command: str,
) -> Path | None:
    candidate: str | None = explicit or os.environ.get(environment_name)
    if candidate:
        path = Path(candidate).expanduser()
        return path if path.is_file() else None
    found = shutil.which(command)
    return Path(found) if found else None


def sibling_ffprobe(ffmpeg: Path) -> Path | None:
    filename = "ffprobe.exe" if ffmpeg.suffix.lower() == ".exe" else "ffprobe"
    candidate = ffmpeg.with_name(filename)
    return candidate if candidate.is_file() else None


def run_capture(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def probe_number(value: Any) -> float | None:
    number = as_number(value)
    if number is not None:
        return number
    if isinstance(value, str) and value.strip():
        try:
            parsed = float(value)
        except ValueError:
            return None
        if parsed == parsed and parsed not in (float("inf"), float("-inf")):
            return parsed
    return None


def parse_rate(value: Any) -> float | None:
    if not isinstance(value, str) or not value or value == "0/0":
        return probe_number(value)
    if "/" not in value:
        return probe_number(value)
    left, right = value.split("/", 1)
    numerator = probe_number(left)
    denominator = probe_number(right)
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def summarize_streams(probe: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None, int]:
    streams = probe.get("streams")
    if not isinstance(streams, list):
        return {}, None, 0
    video = next(
        (stream for stream in streams if stream.get("codec_type") == "video"),
        None,
    )
    audio = next(
        (stream for stream in streams if stream.get("codec_type") == "audio"),
        None,
    )
    subtitles = [
        stream for stream in streams if stream.get("codec_type") == "subtitle"
    ]
    if not isinstance(video, dict):
        return {}, audio if isinstance(audio, dict) else None, len(subtitles)
    summary = {
        "codec_name": video.get("codec_name"),
        "profile": video.get("profile"),
        "pix_fmt": video.get("pix_fmt"),
        "width": video.get("width"),
        "height": video.get("height"),
        "sample_aspect_ratio": video.get("sample_aspect_ratio"),
        "display_aspect_ratio": video.get("display_aspect_ratio"),
        "avg_frame_rate": video.get("avg_frame_rate"),
        "fps": parse_rate(video.get("avg_frame_rate")),
        "color_range": video.get("color_range"),
        "color_space": video.get("color_space"),
        "color_transfer": video.get("color_transfer"),
        "color_primaries": video.get("color_primaries"),
        "duration_sec": probe_number(video.get("duration")),
        "nb_frames": probe_number(video.get("nb_frames")),
    }
    return summary, audio if isinstance(audio, dict) else None, len(subtitles)


def expected_comparisons(
    project_root: Path,
    media_path: Path,
    project: dict[str, Any],
    video: dict[str, Any],
    audio: dict[str, Any] | None,
    subtitle_count: int,
    format_info: dict[str, Any],
) -> list[dict[str, Any]]:
    output = project.get("output")
    if not isinstance(output, dict):
        raise ProjectError("project.output must be an object")

    comparisons: list[dict[str, Any]] = []

    def compare(field: str, expected: Any, actual: Any, ok: bool) -> None:
        comparisons.append(
            {
                "field": field,
                "expected": expected,
                "actual": actual,
                "ok": bool(ok),
            }
        )

    expected_source = output.get("path")
    actual_source = relative_project_path(project_root, media_path)
    compare("source", expected_source, actual_source, actual_source == expected_source)

    expected_width = as_number(output.get("width"))
    compare("width", expected_width, video.get("width"), expected_width == video.get("width"))
    expected_height = as_number(output.get("height"))
    compare(
        "height",
        expected_height,
        video.get("height"),
        expected_height == video.get("height"),
    )

    expected_fps = as_number(output.get("fps"))
    actual_fps = as_number(video.get("fps"))
    compare(
        "fps",
        expected_fps,
        actual_fps,
        expected_fps is not None
        and actual_fps is not None
        and abs(expected_fps - actual_fps) <= 0.05,
    )

    expected_duration = as_number(output.get("duration_sec"))
    actual_duration = probe_number(format_info.get("duration"))
    if actual_duration is None:
        actual_duration = probe_number(video.get("duration_sec"))
    compare(
        "duration_sec",
        expected_duration,
        actual_duration,
        expected_duration is not None
        and actual_duration is not None
        and abs(expected_duration - actual_duration) <= 0.1,
    )

    expected_container = output.get("container")
    actual_container = format_info.get("format_name")
    compare(
        "container",
        expected_container,
        actual_container,
        isinstance(expected_container, str)
        and isinstance(actual_container, str)
        and expected_container.lower() in actual_container.lower(),
    )

    expected_video_codec = output.get("video_codec")
    actual_video_codec = video.get("codec_name")
    compare(
        "video_codec",
        expected_video_codec,
        actual_video_codec,
        isinstance(expected_video_codec, str)
        and isinstance(actual_video_codec, str)
        and expected_video_codec.lower() in actual_video_codec.lower(),
    )

    expected_has_audio = output.get("has_audio", True)
    compare("has_audio", expected_has_audio, audio is not None, expected_has_audio == (audio is not None))
    if expected_has_audio:
        expected_audio_codec = output.get("audio_codec")
        actual_audio_codec = audio.get("codec_name") if audio else None
        compare(
            "audio_codec",
            expected_audio_codec,
            actual_audio_codec,
            isinstance(expected_audio_codec, str)
            and isinstance(actual_audio_codec, str)
            and expected_audio_codec.lower() in actual_audio_codec.lower(),
        )

        expected_sample_rate = as_number(output.get("sample_rate"))
        actual_sample_rate = probe_number(audio.get("sample_rate")) if audio else None
        compare(
            "sample_rate",
            expected_sample_rate,
            actual_sample_rate,
            expected_sample_rate == actual_sample_rate,
        )

        expected_channels = as_number(output.get("channels"))
        actual_channels = probe_number(audio.get("channels")) if audio else None
        compare(
            "channels",
            expected_channels,
            actual_channels,
            expected_channels == actual_channels,
        )

    if output.get("captions_required"):
        compare("captions", "at least one subtitle stream", subtitle_count, subtitle_count > 0)
    return comparisons


def motion_observations(ffmpeg: Path, media_path: Path) -> dict[str, Any]:
    command = [
        str(ffmpeg),
        "-hide_banner",
        "-nostats",
        "-i",
        str(media_path),
        "-vf",
        "blackdetect=d=0.2:pic_th=0.98,freezedetect=n=0.003:d=0.5",
        "-an",
        "-f",
        "null",
        "-",
    ]
    result = run_capture(command)
    output = result.stderr
    black_intervals = [
        {
            "start_sec": float(start),
            "end_sec": float(end),
            "duration_sec": float(duration),
        }
        for start, end, duration in re.findall(
            r"black_start:([0-9.]+) black_end:([0-9.]+) black_duration:([0-9.]+)",
            output,
        )
    ]
    freeze_starts = re.findall(r"freeze_start:\s*([0-9.]+)", output)
    freeze_ends = re.findall(r"freeze_end:\s*([0-9.]+)", output)
    freeze_intervals = [
        {"start_sec": float(start), "end_sec": float(end)}
        for start, end in zip(freeze_starts, freeze_ends)
    ]
    return {
        "ok": result.returncode == 0 and not (black_intervals and not output),
        "black_intervals": black_intervals,
        "freeze_intervals": freeze_intervals,
        "return_code": result.returncode,
        "error_tail": "\n".join(output.splitlines()[-8:]),
    }


def loudness_observations(ffmpeg: Path, media_path: Path) -> dict[str, Any]:
    command = [
        str(ffmpeg),
        "-hide_banner",
        "-nostats",
        "-i",
        str(media_path),
        "-filter_complex",
        "ebur128=peak=true",
        "-f",
        "null",
        "-",
    ]
    result = run_capture(command)
    output = result.stderr
    integrated_matches = re.findall(r"\bI:\s*(-?[0-9.]+)\s*LUFS", output)
    peak_matches = re.findall(r"\bPeak:\s*(-?[0-9.]+)\s*dBFS", output)
    lra_matches = re.findall(r"\bLRA:\s*(-?[0-9.]+)\s*LU", output)
    return {
        "ok": result.returncode == 0 and bool(integrated_matches),
        "integrated_lufs": float(integrated_matches[-1])
        if integrated_matches
        else None,
        "true_peak_db": float(peak_matches[-1]) if peak_matches else None,
        "loudness_range_lu": float(lra_matches[-1]) if lra_matches else None,
        "return_code": result.returncode,
        "error_tail": "\n".join(output.splitlines()[-8:]),
    }


def extract_frames(
    ffmpeg: Path,
    media_path: Path,
    requested_dir: Path,
    sample_fps: float,
) -> tuple[Path, list[dict[str, Any]], dict[str, Any]]:
    target = requested_dir
    if target.exists() and list(target.glob("frame_*.jpg")):
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        target = requested_dir / f"run-{stamp}"
    target.mkdir(parents=True, exist_ok=True)

    command = [
        str(ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(media_path),
        "-vf",
        f"fps={sample_fps}",
        "-q:v",
        "2",
        "-start_number",
        "0",
        str(target / "frame_%05d.jpg"),
    ]
    result = run_capture(command)
    frames: list[dict[str, Any]] = []
    for index, path in enumerate(sorted(target.glob("frame_*.jpg"))):
        frames.append(
            {
                "path": path,
                "time_sec": index / sample_fps,
            }
        )
    return (
        target,
        frames,
        {
            "ok": result.returncode == 0 and bool(frames),
            "return_code": result.returncode,
            "error_tail": "\n".join(result.stderr.splitlines()[-8:]),
        },
    )


def inspect(media_path: Path, project_root: Path | None, args: argparse.Namespace) -> dict[str, Any]:
    if not media_path.is_file():
        raise ProjectError(f"media file does not exist: {media_path}")

    ffmpeg = resolve_tool(args.ffmpeg, "FFMPEG_BIN", "ffmpeg")
    if ffmpeg is None:
        raise ProjectError("ffmpeg not found; pass --ffmpeg or set FFMPEG_BIN")
    ffprobe = resolve_tool(args.ffprobe, "FFPROBE_BIN", "ffprobe")
    if ffprobe is None:
        ffprobe = sibling_ffprobe(ffmpeg)
    if ffprobe is None:
        raise ProjectError("ffprobe not found; pass --ffprobe or set FFPROBE_BIN")

    probe_result = run_capture(
        [
            str(ffprobe),
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-of",
            "json",
            str(media_path),
        ]
    )
    if probe_result.returncode != 0:
        raise ProjectError(
            "ffprobe failed: " + "\n".join(probe_result.stderr.splitlines()[-10:])
        )
    try:
        probe = json.loads(probe_result.stdout)
    except json.JSONDecodeError as exc:
        raise ProjectError(f"ffprobe returned invalid JSON: {exc}") from exc

    format_info = probe.get("format") if isinstance(probe, dict) else None
    if not isinstance(format_info, dict):
        raise ProjectError("ffprobe output contains no format object")
    video, audio, subtitle_count = summarize_streams(probe)
    if not video:
        raise ProjectError("media contains no video stream")

    decode_result = run_capture(
        [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(media_path),
            "-f",
            "null",
            "-",
        ]
    )

    motion = motion_observations(ffmpeg, media_path)
    loudness = (
        loudness_observations(ffmpeg, media_path)
        if audio
        else {
            "ok": True,
            "integrated_lufs": None,
            "true_peak_db": None,
            "loudness_range_lu": None,
            "return_code": 0,
            "error_tail": "",
        }
    )

    source = str(media_path.resolve())
    if project_root is not None:
        source = relative_project_path(project_root, media_path)
        frames_dir = (
            Path(args.frames_dir).resolve()
            if args.frames_dir
            else project_root / "qa" / "frames"
        )
        if not is_within(frames_dir, project_root):
            raise ProjectError("--frames-dir must stay inside the project")
    else:
        frames_dir = (
            Path(args.frames_dir).resolve()
            if args.frames_dir
            else media_path.parent / "frames"
        )

    actual_frames_dir, frames, extraction = extract_frames(
        ffmpeg,
        media_path,
        frames_dir,
        args.sample_fps,
    )
    for frame in frames:
        frame["path"] = (
            relative_project_path(project_root, frame["path"])
            if project_root is not None
            else str(frame["path"])
        )

    comparisons: list[dict[str, Any]] = []
    if project_root is not None:
        project = load_json(project_root / "project.json")
        comparisons = expected_comparisons(
            project_root,
            media_path,
            project,
            video,
            audio,
            subtitle_count,
            format_info,
        )

    decode_ok = decode_result.returncode == 0
    matched_expected = all(item["ok"] for item in comparisons) if comparisons else True
    inspection_complete = (
        decode_ok
        and extraction["ok"]
        and motion["ok"]
        and loudness["ok"]
    )
    report = {
        "schema_version": 1,
        "tool": "inspect_media.py",
        "inspected_at": utc_now(),
        "source": source,
        "source_size_bytes": media_path.stat().st_size,
        "source_sha256": sha256_file(media_path),
        "ffmpeg": str(ffmpeg),
        "ffprobe": str(ffprobe),
        "format": {
            "name": format_info.get("format_name"),
            "long_name": format_info.get("long_name"),
            "duration_sec": probe_number(format_info.get("duration")),
            "size_bytes": probe_number(format_info.get("size")),
            "bit_rate": probe_number(format_info.get("bit_rate")),
        },
        "video_stream": video,
        "audio_stream": {
            "codec_name": audio.get("codec_name"),
            "sample_rate": probe_number(audio.get("sample_rate")),
            "channels": probe_number(audio.get("channels")),
            "channel_layout": audio.get("channel_layout"),
            "duration_sec": probe_number(audio.get("duration")),
        }
        if audio
        else None,
        "subtitle_stream_count": subtitle_count,
        "decode_ok": decode_ok,
        "decode_errors": "\n".join(decode_result.stderr.splitlines()[-12:]),
        "matched_expected": matched_expected,
        "comparisons": comparisons,
        "observations": {
            "black_and_freeze": motion,
            "loudness": loudness,
        },
        "sample_fps": args.sample_fps,
        "frames_dir": (
            relative_project_path(project_root, actual_frames_dir)
            if project_root is not None
            else str(actual_frames_dir)
        ),
        "sample_frames": frames,
        "frame_extraction": extraction,
        "inspection_complete": inspection_complete,
        "review_required": [
            "Watch complete playback for story, motion, performance, and edit rhythm.",
            "Inspect native-resolution crops for identity, product, text, hands, and seams.",
            "Interpret black and freeze observations against intentional creative choices.",
        ],
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("media", type=Path)
    parser.add_argument("--project", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--frames-dir", type=Path)
    parser.add_argument("--sample-fps", type=float, default=2.0)
    parser.add_argument("--ffmpeg")
    parser.add_argument("--ffprobe")
    args = parser.parse_args()

    if args.sample_fps <= 0:
        print("ERROR: --sample-fps must be positive", file=sys.stderr)
        return 2

    project_root = args.project.resolve() if args.project else None
    media_path = args.media.resolve()
    try:
        report_value = inspect(media_path, project_root, args)
    except ProjectError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.output:
        output_path = args.output.resolve()
        if project_root is not None and not is_within(output_path, project_root):
            print("ERROR: --output must stay inside the project", file=sys.stderr)
            return 2
    elif project_root is not None:
        output_path = project_root / "qa" / "technical-report.json"
    else:
        output_path = media_path.with_name("technical-report.json")
    write_json_atomic(output_path, report_value)

    ok = (
        report_value["inspection_complete"]
        and report_value["matched_expected"]
        and report_value["decode_ok"]
    )
    print(
        "RESULT: "
        + json.dumps(
            {
                "status": "pass" if ok else "review",
                "report": str(output_path),
                "decode_ok": report_value["decode_ok"],
                "matched_expected": report_value["matched_expected"],
                "sample_frames": len(report_value["sample_frames"]),
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from _common import ProjectError, load_json, sha256_file, write_json_atomic
from approve_gate import approve
from build_manifest import build_manifest
from init_project import initialize
from inspect_media import expected_comparisons, parse_rate
from preflight import validate_model_profile
from record_candidate import record
from upgrade_project import upgrade
from validate_project import Report, _validate_generation_selection, validate


class ProjectStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "project"
        initialize(self.root, "State Test", "hero")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_text(self, relative: str, value: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")

    def write_json(self, relative: str, value: object) -> None:
        write_json_atomic(self.root / relative, value)

    def make_file(self, relative: str, payload: bytes) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return path

    def build_releasable_fixture(self) -> None:
        project = load_json(self.root / "project.json")
        project.update(
            {
                "goal": "Deliver a controlled two-second product proof.",
                "audience": "Prospective customers.",
                "platform": "Local review first, public web second.",
                "delivery_promise": "The viewer sees the product remain intact.",
                "target_response": "Understand the mechanism and trust the product.",
                "quality_mode": "hero",
            }
        )
        project["clock"]["source"] = "Visual action timing"
        project["clock"]["markers"] = [{"time_sec": 1.0, "event": "action peak"}]
        project["output"].update(
            {
                "path": "renders/final.mp4",
                "duration_sec": 2.0,
                "width": 1920,
                "height": 1080,
                "fps": 30,
                "captions_required": False,
            }
        )
        project["quality"].update(
            {
                "thesis": "One stable object changes state without losing identity.",
                "hero_frame": "Product centered at the action peak.",
                "signature_moment": "The controlled state change.",
                "sound_motif": "One clean mechanical click.",
            }
        )
        self.write_json("project.json", project)

        self.write_text(
            "brief.md",
            "# Brief\n\n"
            "The video is a two-second public product proof for prospective "
            "customers. It must show a controlled state change, preserve the "
            "product exactly, avoid invented claims, include one clean click, "
            "and remain readable at delivery size. The approval owner is the "
            "project director, and the intended use is noncommercial public "
            "release. Source assets are approved for this test and no real "
            "person appears. The release must stop if product geometry changes.\n",
        )
        self.write_text(
            "creative-bible.md",
            "# Creative Bible\n\n"
            "## Direction\n"
            "A restrained macro product study with one controlled mechanism "
            "action. The camera remains locked; attention comes from contact, "
            "timing, and a single highlight moving over the product surface.\n\n"
            "## Reference\n"
            "The product passport controls silhouette, material, and geometry. "
            "It must not control scene lighting or camera framing.\n\n"
            "## Anti-reference\n"
            "No generic floating product, no unmotivated orbit, no invented "
            "logos, and no plastic material. The hero frame must read at one "
            "second and the sound motif is one clean click. Light is soft from "
            "camera-left and the background remains quieter than the product.\n",
        )
        self.write_text(
            "script.md",
            "# Script\n\n"
            "The product is closed at the start. It remains completely still "
            "while the camera holds. At the action peak, the latch moves through "
            "one controlled arc. The mechanism settles in the open state, the "
            "highlight comes to rest on the latch, and the video ends without "
            "additional text or claims. The visual action is the master clock.\n",
        )
        self.write_json(
            "master-clock.json",
            {
                "schema_version": 1,
                "type": "visual",
                "source": "programmatic product action",
                "duration_sec": 2.0,
                "bpm": None,
                "segments": [
                    {
                        "id": "B01",
                        "start_sec": 0.0,
                        "end_sec": 1.0,
                        "intent": "Hold the closed state and establish the object.",
                    },
                    {
                        "id": "B02",
                        "start_sec": 1.0,
                        "end_sec": 2.0,
                        "intent": "Complete the latch action and land the end state.",
                    },
                ],
                "markers": [
                    {
                        "time_sec": 1.0,
                        "kind": "action",
                        "label": "latch action peak",
                    }
                ],
            },
        )
        self.write_text(
            "timeline.md",
            "# Timeline\n\n"
            "Shot S01 runs from 0.0 to 2.0 seconds with no transition at the "
            "head and a clean cut at the tail. The only sound is room tone plus "
            "one mechanical click at the action peak. No text is required. "
            "The final render is output from the approved timeline.\n",
        )
        self.write_json(
            "timeline.json",
            {
                "schema_version": 1,
                "duration_sec": 2.0,
                "tracks": [
                    {
                        "id": "V1",
                        "type": "video",
                        "role": "primary",
                        "items": [
                            {
                                "id": "V1-01",
                                "shot_id": "S01",
                                "source": "renders/final.mp4",
                                "source_in": 0.0,
                                "source_out": 2.0,
                                "timeline_start": 0.0,
                                "duration": 2.0,
                                "transition": "hard-cut",
                            }
                        ],
                    },
                    {
                        "id": "A1",
                        "type": "audio",
                        "role": "mix",
                        "items": [
                            {
                                "id": "A1-01",
                                "source": "audio/sound.wav",
                                "timeline_start": 0.0,
                                "duration": 2.0,
                                "transition": "continuous",
                            }
                        ],
                    },
                ],
                "beat_markers": [],
            },
        )
        self.write_text(
            "qa/previs-review.md",
            "# Previs Review\n\n"
            "The two-second animatic was watched at speed. The product stays "
            "visible, the state change reads, and no timing gap remains. The "
            "decision is approved for shot production.\n",
        )
        self.write_text(
            "rights/asset-ledger.md",
            "# Asset Ledger\n\n"
            "The synthetic product and programmatic soundtrack are original "
            "project assets approved for noncommercial public release. No "
            "third-party likeness, music, font, or footage is used.\n",
        )

        for name in ("front", "three-quarter", "detail"):
            self.make_file(f"qa/assets/product-{name}.jpg", b"evidence-" + name.encode())
        for index, time_value in enumerate((0.1, 1.0, 1.9)):
            self.make_file(
                f"qa/frames/frame_{index:05d}.jpg",
                b"frame-" + str(time_value).encode(),
            )
        self.make_file("qa/qa-summary.txt", b"reviewed")
        animatic = self.make_file("animatic/animatic.mp4", b"animatic-fixture")
        animatic_sample_frames = [
            {
                "path": f"qa/frames/frame_{index:05d}.jpg",
                "time_sec": time_value,
                "native_source": True,
            }
            for index, time_value in enumerate((0.1, 1.0, 1.9))
        ]
        self.write_json(
            "qa/animatic-review.json",
            {
                "schema_version": 1,
                "reviewer": "independent-previs-review",
                "reviewed_at": "2026-10-25",
                "watched_in_real_time": True,
                "decision": "approved",
                "issues": [],
                "unresolved_blockers": [],
                "notes": "Watched at real speed.",
            },
        )
        self.write_json(
            "qa/animatic-technical-report.json",
            {
                "schema_version": 1,
                "source": "animatic/animatic.mp4",
                "source_sha256": sha256_file(animatic),
                "decode_ok": True,
                "matched_expected": True,
                "inspection_complete": True,
                "format": {"duration_sec": 2.0},
                "sample_frames": animatic_sample_frames,
            },
        )

        assets = load_json(self.root / "assets.json")
        assets["assets"] = [
            {
                "id": "hero-product",
                "name": "Product",
                "type": "product",
                "role": "hero",
                "status": "locked",
                "descriptor": "Matte graphite cylinder with a single silver latch.",
                "invariants": ["silhouette", "material", "latch-position"],
                "allowed_variation": ["lighting"],
                "references": [
                    {
                        "path": "qa/assets/product-front.jpg",
                        "use": "identity",
                        "controls": "geometry, material, latch",
                        "must_not_control": "scene lighting or camera angle",
                    }
                ],
                "stress_tests": [
                    {
                        "case": case,
                        "result": "pass",
                        "evidence": f"qa/assets/product-{case}.jpg",
                    }
                    for case in ("front", "three-quarter", "detail")
                ],
                "rights": "original test asset",
            }
        ]
        assets["continuity"].update(
            {
                "geography": "single studio table",
                "screen_direction": "not applicable",
                "axis": "not applicable",
                "lighting": "soft key camera-left",
                "palette": ["graphite", "silver"],
                "persistent_props": ["hero-product"],
            }
        )
        self.write_json("assets.json", assets)

        evidence_frames = [
            {
                "path": f"qa/frames/frame_{index:05d}.jpg",
                "time_sec": time_value,
                "native_source": True,
            }
            for index, time_value in enumerate((0.1, 1.0, 1.9))
        ]
        shots = load_json(self.root / "shots.json")
        shots["shots"] = [
            {
                "id": "S01",
                "start_sec": 0.0,
                "end_sec": 2.0,
                "editorial": {
                    "function": "proof",
                    "intent": "Show the mechanism with unchanged product identity.",
                    "information_delta": "The latch completes one clean action.",
                    "cut_reason": "The shot ends after the visible end state.",
                },
                "frame": {
                    "shot_size": "medium close-up with full product",
                    "camera_height": "table height",
                    "angle": "three-quarter frontal",
                    "field_of_view": "normal field of view",
                    "composition": "product centered",
                },
                "action": {
                    "start": "Product closed and stationary.",
                    "primary": "Latch moves through one controlled arc.",
                    "end": "Latch settles in the open state.",
                },
                "camera": {
                    "move": "locked",
                    "motivation": "Keep the mechanical contact readable.",
                    "path": "none",
                    "end_frame": "same framing",
                },
                "continuity": {
                    "assets": ["hero-product"],
                    "screen_direction": "not applicable",
                    "eyeline": "not applicable",
                    "lighting": "soft key camera-left",
                    "props": [],
                },
                "generation": {
                    "source": "programmatic",
                    "control_mode": "deterministic",
                    "model": "",
                    "status": "approved",
                    "selected_candidate_id": "",
                },
                "acceptance": [
                    {
                        "id": "A1",
                        "criterion": "Product geometry remains unchanged.",
                        "blocking": True,
                    }
                ],
                "review": {
                    "status": "approved",
                    "reviewer": "independent-review",
                    "evidence_frames": evidence_frames,
                    "notes": "Reviewed at full size and in motion.",
                },
            }
        ]
        self.write_json("shots.json", shots)

        master = self.make_file("renders/final.mp4", b"not-a-real-mp4-for-state-tests")
        technical = {
            "schema_version": 1,
            "source": "renders/final.mp4",
            "source_sha256": sha256_file(master),
            "decode_ok": True,
            "matched_expected": True,
            "inspection_complete": True,
            "comparisons": [
                {
                    "field": "fixture",
                    "expected": True,
                    "actual": True,
                    "ok": True,
                }
            ],
            "sample_frames": evidence_frames,
        }
        self.write_json("qa/technical-report.json", technical)

        qa = load_json(self.root / "qa-report.json")
        qa["review"] = {
            "reviewer": "independent-review",
            "date": "2026-10-25",
            "target": "2s 1920x1080 public proof",
            "package": "state-test-v001",
            "human_approved": True,
        }
        qa["verdict"] = "pass"
        qa["checks"] = [
            {
                "category": "technical",
                "status": "pass",
                "criterion": "The actual file decodes and matches specifications.",
                "reviewer": "inspect_media.py + human",
                "evidence": ["qa/technical-report.json"],
            },
            {
                "category": "visual",
                "status": "pass",
                "criterion": "Product identity and mechanism are correct.",
                "reviewer": "independent-review",
                "evidence": ["qa/frames/frame_00001.jpg"],
                "time_sec": 1.0,
            },
            {
                "category": "editorial",
                "status": "pass",
                "criterion": "The action and sound land cleanly.",
                "reviewer": "independent-review",
                "evidence": ["timeline.md"],
            },
            {
                "category": "rights",
                "status": "pass",
                "criterion": "All assets are cleared for intended use.",
                "reviewer": "rights-review",
                "evidence": ["rights/asset-ledger.md"],
            },
            {
                "category": "audio_visual",
                "status": "pass",
                "criterion": "The click lands on the visible mechanism peak.",
                "reviewer": "independent-review",
                "evidence": ["qa/qa-summary.txt"],
                "time_sec": 1.0,
            },
            {
                "category": "content",
                "status": "pass",
                "criterion": "The mechanism and product behavior are accurate.",
                "reviewer": "product-review",
                "evidence": ["qa/qa-summary.txt"],
            },
        ]
        self.write_json("qa-report.json", qa)

        build_manifest(
            self.root,
            argparse.Namespace(
                file=["master=renders/final.mp4"],
                authority="Test release specification",
                version="v001",
                rights_verified=True,
            ),
        )

    def approve_all(self) -> None:
        for gate in (
            "brief",
            "direction",
            "script_clock",
            "continuity",
            "previs",
            "generation",
            "edit",
            "review",
            "delivery",
        ):
            approve(self.root, gate, "test-owner", None)

    def test_scaffold_plan_passes_with_warnings(self) -> None:
        report = validate(self.root, "plan")
        self.assertEqual([], report.errors)
        self.assertTrue(report.warnings)

    def test_pending_project_cannot_release(self) -> None:
        report = validate(self.root, "final")
        self.assertTrue(any("gate brief is not approved" in item for item in report.errors))
        self.assertTrue(any("shots.json must contain" in item for item in report.errors))

    def test_complete_fixture_can_release(self) -> None:
        self.build_releasable_fixture()
        self.approve_all()
        report = validate(self.root, "final")
        self.assertEqual([], report.errors, "\n".join(report.errors))

    def test_changed_creative_bible_makes_gate_stale(self) -> None:
        self.build_releasable_fixture()
        self.approve_all()
        self.write_text(
            "creative-bible.md",
            (self.root / "creative-bible.md").read_text(encoding="utf-8")
            + "\nA late unapproved direction change.\n",
        )
        report = validate(self.root, "final")
        self.assertTrue(any("gate direction is stale" in item for item in report.errors))

    def test_changed_master_invalidates_manifest(self) -> None:
        self.build_releasable_fixture()
        with (self.root / "renders/final.mp4").open("ab") as handle:
            handle.write(b"changed")
        report = validate(self.root, "final")
        self.assertTrue(any("sha256 is stale" in item for item in report.errors))

    def test_open_blocker_blocks_release(self) -> None:
        self.build_releasable_fixture()
        qa = load_json(self.root / "qa-report.json")
        qa["findings"] = [
            {
                "severity": "blocker",
                "category": "visual",
                "status": "open",
                "issue": "The product changes geometry at the action peak.",
            }
        ]
        self.write_json("qa-report.json", qa)
        report = validate(self.root, "final")
        self.assertTrue(any("remains open as blocker" in item for item in report.errors))

    def test_missing_human_approval_blocks_release(self) -> None:
        self.build_releasable_fixture()
        qa = load_json(self.root / "qa-report.json")
        qa["review"]["human_approved"] = False
        self.write_json("qa-report.json", qa)
        report = validate(self.root, "final")
        self.assertTrue(
            any("human_approved must be true" in item for item in report.errors)
        )

    def test_init_refuses_nonempty_destination(self) -> None:
        with self.assertRaises(ProjectError):
            initialize(self.root, "Second Project", "hero")

    def test_v01_project_can_be_upgraded_without_overwriting(self) -> None:
        for relative in (
            "script.md",
            "master-clock.json",
            "timeline.json",
            "qa/animatic-review.json",
        ):
            (self.root / relative).unlink()
        project = load_json(self.root / "project.json")
        project["output"].pop("text_required", None)
        project["gates"].pop("script_clock", None)
        self.write_json("project.json", project)

        result = upgrade(self.root)
        self.assertIn("script.md", result["created"])
        self.assertIn("script_clock", load_json(self.root / "project.json")["gates"])
        self.assertFalse(
            load_json(self.root / "project.json")["output"]["text_required"]
        )

    def test_rate_parser(self) -> None:
        self.assertAlmostEqual(parse_rate("30000/1001"), 29.97002997, places=5)
        self.assertIsNone(parse_rate("0/0"))

    def test_expected_comparisons_all_pass(self) -> None:
        self.build_releasable_fixture()
        project = load_json(self.root / "project.json")
        comparisons = expected_comparisons(
            self.root,
            self.root / "renders/final.mp4",
            project,
            {
                "width": 1920,
                "height": 1080,
                "fps": 30.0,
                "duration_sec": 2.0,
                "codec_name": "h264",
            },
            {
                "codec_name": "aac",
                "sample_rate": "48000",
                "channels": 2,
            },
            0,
            {"format_name": "mov,mp4,m4a,3gp,3g2,mj2", "duration": "2.0"},
        )
        self.assertTrue(all(item["ok"] for item in comparisons), comparisons)

    def test_animatic_expected_profile_checks_source_and_duration(self) -> None:
        self.build_releasable_fixture()
        project = load_json(self.root / "project.json")
        comparisons = expected_comparisons(
            self.root,
            self.root / "animatic/animatic.mp4",
            project,
            {
                "width": 960,
                "height": 540,
                "fps": 15.0,
                "duration_sec": 2.0,
                "codec_name": "h264",
            },
            {
                "codec_name": "aac",
                "sample_rate": "48000",
                "channels": 2,
            },
            0,
            {"format_name": "mov,mp4,m4a,3gp,3g2,mj2", "duration": "2.0"},
            profile="animatic",
        )
        self.assertTrue(all(item["ok"] for item in comparisons), comparisons)

    def test_candidate_log_records_hashes_and_blocks_duplicate_selection(self) -> None:
        self.build_releasable_fixture()
        prompt = self.make_file("prompts/S01-v001.md", b"Prompt version one")
        output_one = self.make_file("generations/S01-C01.mp4", b"candidate one")
        output_two = self.make_file("generations/S01-C02.mp4", b"candidate two")
        args = argparse.Namespace(
            shot="S01",
            candidate="S01-C01",
            model="fixture/model",
            model_version="v1",
            control_mode="image-to-video",
            prompt_file="prompts/S01-v001.md",
            output="generations/S01-C01.mp4",
            reference=[],
            parameters='{"duration": 2}',
            seed="42",
            cost="0.10",
            latency_seconds="12",
            verdict="selected",
            failure_code=[],
            note="Selected in fixture.",
        )
        value = record(self.root, args)
        self.assertEqual(value["prompt_sha256"], sha256_file(prompt))
        self.assertEqual(value["output_sha256"], sha256_file(output_one))

        args.candidate = "S01-C02"
        args.output = "generations/S01-C02.mp4"
        with self.assertRaises(ProjectError):
            record(self.root, args)

    def test_model_profile_rejects_unfilled_template(self) -> None:
        errors = validate_model_profile(
            SKILL_ROOT / "assets" / "model-profile.example.json"
        )
        self.assertTrue(any("provider" in item for item in errors), errors)

    def test_selected_candidate_hashes_are_revalidated(self) -> None:
        self.build_releasable_fixture()
        project = load_json(self.root / "project.json")
        project["quality_mode"] = "standard"
        shots = load_json(self.root / "shots.json")
        shot = shots["shots"][0]
        shot["generation"].update(
            {
                "source": "external-video",
                "control_mode": "image-to-video",
                "model": "fixture/model",
                "selected_candidate_id": "S01-C01",
            }
        )
        self.make_file("prompts/S01-v001.md", b"prompt")
        output = self.make_file("generations/S01-C01.mp4", b"selected")
        args = argparse.Namespace(
            shot="S01",
            candidate="S01-C01",
            model="fixture/model",
            model_version="v1",
            control_mode="image-to-video",
            prompt_file="prompts/S01-v001.md",
            output="generations/S01-C01.mp4",
            reference=[],
            parameters="{}",
            seed="",
            cost="0",
            latency_seconds=None,
            verdict="selected",
            failure_code=[],
            note="selected",
        )
        record(self.root, args)
        records = [
            json.loads(line)
            for line in (self.root / "generation-log.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        report = Report()
        _validate_generation_selection(
            self.root,
            project,
            shots["shots"],
            records,
            report,
        )
        self.assertEqual([], report.errors)

        with output.open("ab") as handle:
            handle.write(b"changed")
        report = Report()
        _validate_generation_selection(
            self.root,
            project,
            shots["shots"],
            records,
            report,
        )
        self.assertTrue(any("output_sha256 is stale" in item for item in report.errors))

    def test_master_clock_gap_blocks_release(self) -> None:
        self.build_releasable_fixture()
        clock = load_json(self.root / "master-clock.json")
        clock["segments"][1]["start_sec"] = 1.2
        self.write_json("master-clock.json", clock)
        report = validate(self.root, "final")
        self.assertTrue(any("master-clock segment gap" in item for item in report.errors))

    def test_timeline_gap_blocks_release(self) -> None:
        self.build_releasable_fixture()
        timeline = load_json(self.root / "timeline.json")
        timeline["tracks"][0]["items"][0]["duration"] = 1.8
        self.write_json("timeline.json", timeline)
        report = validate(self.root, "final")
        self.assertTrue(any("primary timeline covers" in item for item in report.errors))

    def test_animatic_requires_real_time_review(self) -> None:
        self.build_releasable_fixture()
        review = load_json(self.root / "qa/animatic-review.json")
        review["watched_in_real_time"] = False
        self.write_json("qa/animatic-review.json", review)
        report = validate(self.root, "final")
        self.assertTrue(any("watched in real time" in item for item in report.errors))

    def test_text_requirement_adds_text_qa_category(self) -> None:
        self.build_releasable_fixture()
        project = load_json(self.root / "project.json")
        project["output"]["text_required"] = True
        self.write_json("project.json", project)
        report = validate(self.root, "final")
        self.assertTrue(any("required categories: text" in item for item in report.errors))

    def test_music_clock_requires_markers(self) -> None:
        self.build_releasable_fixture()
        project = load_json(self.root / "project.json")
        project["clock"]["type"] = "music"
        self.write_json("project.json", project)
        clock = load_json(self.root / "master-clock.json")
        clock["type"] = "music"
        clock["bpm"] = 120
        clock["markers"] = []
        self.write_json("master-clock.json", clock)
        report = validate(self.root, "final")
        self.assertTrue(any("music master clock needs" in item for item in report.errors))


if __name__ == "__main__":
    unittest.main()

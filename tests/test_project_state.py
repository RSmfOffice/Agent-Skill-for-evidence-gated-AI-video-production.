from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from _common import (
    SKILL_ROOT as PRODUCTION_SKILL_ROOT,
    ProjectError,
    load_json,
    sha256_file,
    sha256_bytes,
    utc_now,
    write_json_atomic,
)
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

    def evidence(self, relative: str, role: str) -> dict[str, str]:
        return {
            "path": relative,
            "role": role,
            "sha256": sha256_file(self.root / relative),
        }

    def build_releasable_fixture(self) -> None:
        project = load_json(self.root / "project.json")
        project.update(
            {
                "producer_id": "production-agent",
                "goal": "Deliver a controlled two-second product proof.",
                "audience": "Prospective customers.",
                "platform": "Local review first, public web second.",
                "delivery_promise": "The viewer sees the product remain intact.",
                "target_response": "Understand the mechanism and trust the product.",
                "quality_mode": "hero",
            }
        )
        project["content_contract"] = {
            "required": [
                {
                    "id": "R1",
                    "observable": "The latch completes one readable state change.",
                    "blocking": True,
                    "acceptance_ids": ["A1", "A2", "A3"],
                }
            ],
            "forbidden": [
                {
                    "id": "F1",
                    "observable": "The product geometry must not deform.",
                    "blocking": True,
                    "acceptance_ids": ["A1"],
                }
            ],
            "signature_events": [
                {
                    "id": "SIG1",
                    "observable": "The latch action and click are perceptible together.",
                    "time_window_sec": [0.8, 1.2],
                    "blocking": True,
                    "acceptance_ids": ["A2"],
                }
            ],
        }
        project["motion_contracts"] = [
            {
                "id": "M1",
                "type": "rigid-joint",
                "subjects": ["latch"],
                "applies_to_shots": ["S01"],
                "constraints": {
                    "length_preserved": True,
                    "attachment": "latch remains attached to hinge",
                },
                "blocking": True,
                "acceptance_ids": ["A2", "A3"],
                "evidence": [],
            }
        ]
        project["policy"]["require_independent_review"] = True
        project["policy"]["require_human_final_approval"] = False
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
        self.write_json(
            "qa/motion-report.json",
            {
                "schema_version": 1,
                "contract_id": "M1",
                "accepted": True,
                "observations": [
                    {
                        "time_sec": 1.0,
                        "measurement": "hinge relationship preserved",
                    }
                ],
            },
        )
        project = load_json(self.root / "project.json")
        project["motion_contracts"][0]["evidence"] = [
            self.evidence("qa/motion-report.json", "render-test")
        ]
        self.write_json("project.json", project)
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
                        "provenance": "render-test",
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
                        "provenance": "render-test",
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
                        "pass_if": "Product geometry, material, and latch remain unchanged.",
                        "fail_if": [
                            "The product deforms or changes material.",
                            "The latch detaches from the product.",
                        ],
                        "method": "native-crop-sequence",
                        "test_domain": "visual",
                        "requirement_ids": ["R1", "F1"],
                        "motion_contract_ids": [],
                        "blocking": True,
                    },
                    {
                        "id": "A2",
                        "pass_if": "The latch action and click are perceptible at the action peak.",
                        "fail_if": [
                            "The action occurs without a perceptible change.",
                            "The click does not align with the action.",
                        ],
                        "method": "motion-audit",
                        "test_domain": "motion",
                        "requirement_ids": ["R1", "SIG1"],
                        "motion_contract_ids": ["M1"],
                        "blocking": True,
                    },
                    {
                        "id": "A3",
                        "pass_if": "The latch preserves its rigid relationship with the hinge.",
                        "fail_if": [
                            "The latch stretches.",
                            "The latch separates from the hinge.",
                        ],
                        "method": "numeric-test",
                        "test_domain": "motion",
                        "requirement_ids": ["R1"],
                        "motion_contract_ids": ["M1"],
                        "blocking": True,
                    },
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
            "reviewer_id": "independent-reviewer",
            "reviewer_kind": "cold-agent",
            "reviewer": "independent-review",
            "date": "2026-10-25",
            "target": "2s 1920x1080 public proof",
            "package": "state-test-v001",
            "human_approved": False,
        }
        qa["verdict"] = "pass"
        qa["checks"] = [
            {
                "category": "technical",
                "status": "pass",
                "criterion": "The actual file decodes and matches specifications.",
                "observed": "The measured streams match the output contract.",
                "reviewer": "inspect_media.py + human",
                "method": "numeric-test",
                "acceptance_ids": [],
                "evidence": [
                    self.evidence("qa/technical-report.json", "render-test")
                ],
            },
            {
                "category": "visual",
                "status": "pass",
                "criterion": "Product identity and mechanism are correct.",
                "observed": "The product silhouette and latch position remain unchanged.",
                "reviewer": "independent-review",
                "acceptance_ids": ["A1"],
                "method": "native-crop-sequence",
                "region": [700, 250, 700, 700],
                "evidence": [
                    self.evidence(
                        "qa/frames/frame_00001.jpg",
                        "observed-final-frame",
                    )
                ],
                "time_sec": 1.0,
            },
            {
                "category": "visual",
                "status": "pass",
                "criterion": "The latch retains rigid length and attachment.",
                "observed": "The motion report preserves hinge length through the action.",
                "reviewer": "motion-test",
                "acceptance_ids": ["A3"],
                "method": "numeric-test",
                "evidence": [
                    self.evidence("qa/motion-report.json", "render-test")
                ],
                "time_sec": 1.0,
            },
            {
                "category": "editorial",
                "status": "pass",
                "criterion": "The action and sound land cleanly.",
                "observed": "The action completes before the final hold.",
                "reviewer": "independent-review",
                "method": "human-review",
                "acceptance_ids": [],
                "evidence": [
                    self.evidence("timeline.md", "canonical-source")
                ],
            },
            {
                "category": "rights",
                "status": "pass",
                "criterion": "All assets are cleared for intended use.",
                "observed": "The ledger covers all visible and audible assets.",
                "reviewer": "rights-review",
                "method": "human-review",
                "acceptance_ids": [],
                "evidence": [
                    self.evidence("rights/asset-ledger.md", "canonical-source")
                ],
            },
            {
                "category": "audio_visual",
                "status": "pass",
                "criterion": "The click lands on the visible mechanism peak.",
                "observed": "The click occurs at 1.0 seconds with the latch action.",
                "reviewer": "independent-review",
                "acceptance_ids": ["A2"],
                "method": "motion-audit",
                "evidence": [
                    self.evidence(
                        "animatic/animatic.mp4",
                        "observed-final-frame",
                    )
                ],
                "time_sec": 1.0,
            },
            {
                "category": "content",
                "status": "pass",
                "criterion": "The mechanism and product behavior are accurate.",
                "observed": "The latch changes state without changing the product.",
                "reviewer": "product-review",
                "acceptance_ids": ["A1"],
                "method": "native-crop-sequence",
                "region": [700, 250, 700, 700],
                "evidence": [
                    self.evidence(
                        "qa/frames/frame_00001.jpg",
                        "observed-final-frame",
                    )
                ],
                "time_sec": 1.0,
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
        self.build_review_chain()

    def build_review_chain(self) -> None:
        project = load_json(self.root / "project.json")
        shots = load_json(self.root / "shots.json")
        shot = shots["shots"][0]
        output = project["output"]
        media_hash = sha256_file(self.root / output["path"])
        review_scope = [
            "technical",
            "content",
            "text",
            "visual",
            "motion",
            "editorial",
            "audio_visual",
            "rights",
        ]
        source_paths = {
            "brief": "brief.md",
            "project": "project.json",
            "shots": "shots.json",
            "timeline": "timeline.json",
            "qa_report": "qa-report.json",
        }
        handoff = {
            "schema_version": 2,
            "project_id": project["project_id"],
            "created_at": utc_now(),
            "generation_skill": {
                "name": "video-production-director",
                "version": "0.5.0",
                "path": str(PRODUCTION_SKILL_ROOT),
                "sha256": None,
            },
            "review_skill_min_version": "0.3.0",
            "review_scope": review_scope,
            "media": {
                "path": output["path"],
                "sha256": media_hash,
                "duration_sec": output["duration_sec"],
                "width": output["width"],
                "height": output["height"],
                "fps": output["fps"],
                "has_audio": output["has_audio"],
            },
            "delivery": {
                "platform": project["platform"],
                "intended_size": [output["width"], output["height"]],
                "quality_mode": project["quality_mode"],
            },
            "sources": self.review_sources(source_paths),
            "required_observations": [
                {
                    "id": item["id"],
                    "observable": item["observable"],
                    "acceptance_ids": item["acceptance_ids"],
                }
                for item in project["content_contract"]["required"]
            ],
            "intentional_choices": [],
            "anchors": [
                {
                    "id": f"SHOT-{shot['id']}",
                    "kind": "shot",
                    "start_sec": shot["start_sec"],
                    "end_sec": shot["end_sec"],
                }
            ],
            "control_context": {
                "route": shot["generation"]["source"],
                "model": shot["generation"]["model"] or "programmatic-renderer",
                "prompt_or_source": "timeline.json",
                "references": [],
            },
            "known_clean_controls": [],
            "known_failure_controls": [],
            "excluded_checks": [],
            "notes": "State-test review handoff.",
        }
        self.write_json("qa/review-handoff.json", handoff)
        review_id = "REV-STATE-TEST-001"
        self.write_json(
            "qa/review-result.json",
            {
                "schema_version": 2,
                "review_id": review_id,
                "project_id": project["project_id"],
                "review_skill": {
                    "name": "video-review-evolution",
                    "version": "0.3.0",
                    "sha256": None,
                },
                "generation_skill": {
                    "name": "video-production-director",
                    "version": "0.5.0",
                },
                "reviewer": {
                    "id": "independent-reviewer",
                    "kind": "cold-agent",
                    "reviewed_at": utc_now(),
                    "independent_from_producer": True,
                },
                "media_sha256": media_hash,
                "coverage": {category: "pass" for category in review_scope},
                "coverage_reasons": {},
                "verdict": "pass",
                "issues": [],
                "generation_change_requests": [],
                "residual_risks": [],
                "limitations": [],
            },
        )

        self.write_json(
            "qa/change-response.json",
            {
                "schema_version": 2,
                "review_id": review_id,
                "media_sha256": media_hash,
                "responses": [],
                "new_project_revision": "state-test-v001",
                "new_media_sha256": media_hash,
                "generation_skill_change": {
                    "changed": False,
                    "from_version": "0.5.0",
                    "to_version": "0.5.0",
                },
                "rule_changes": [],
            },
        )
        self.write_json(
            "qa/review-verification.json",
            {
                "schema_version": 2,
                "verification_review_id": "REV-STATE-TEST-VERIFY-001",
                "prior_review_id": review_id,
                "project_id": project["project_id"],
                "review_skill": {
                    "name": "video-review-evolution",
                    "version": "0.3.0",
                    "sha256": None,
                },
                "reviewer": {
                    "id": "independent-reviewer",
                    "kind": "cold-agent",
                    "reviewed_at": utc_now(),
                    "independent_from_producer": True,
                },
                "change_request_ids": [],
                "original_media_sha256": media_hash,
                "reviewed_media_sha256": media_hash,
                "media": {
                    "path": output["path"],
                    "sha256": media_hash,
                },
                "regression_results": [],
                "result": "not_applicable",
                "limitations": [],
            },
        )

    def review_sources(
        self,
        source_paths: dict[str, str],
    ) -> dict[str, dict[str, object]]:
        sources: dict[str, dict[str, object]] = {}
        for role, relative in source_paths.items():
            path = self.root / relative
            if role == "project":
                project = load_json(path)
                project.pop("gates", None)
                canonical = json.dumps(
                    project,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
                sources[role] = {
                    "path": relative,
                    "sha256": sha256_bytes(canonical),
                    "hash_mode": "json-without-gates",
                }
            else:
                sources[role] = {
                    "path": relative,
                    "sha256": sha256_file(path),
                }
        return sources

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

    def test_blank_review_handoff_blocks_release(self) -> None:
        self.build_releasable_fixture()
        self.approve_all()
        shutil.copy2(
            PRODUCTION_SKILL_ROOT
            / "assets"
            / "scaffold"
            / "qa"
            / "review-handoff.json",
            self.root / "qa" / "review-handoff.json",
        )
        report = validate(self.root, "final")
        self.assertTrue(
            any(
                "review handoff project_id must match" in item
                for item in report.errors
            ),
            "\n".join(report.errors),
        )

    def test_missing_companion_review_result_blocks_release(self) -> None:
        self.build_releasable_fixture()
        self.approve_all()
        (self.root / "qa" / "review-result.json").unlink()
        report = validate(self.root, "final")
        self.assertTrue(
            any(
                "companion review is required" in item
                for item in report.errors
            ),
            "\n".join(report.errors),
        )

    def test_review_result_project_mismatch_blocks_release(self) -> None:
        self.build_releasable_fixture()
        result = load_json(self.root / "qa" / "review-result.json")
        result["project_id"] = "different-project"
        self.write_json("qa/review-result.json", result)
        report = validate(self.root, "final")
        self.assertTrue(
            any("project_id differs from handoff" in item for item in report.errors),
            "\n".join(report.errors),
        )

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
        project = load_json(self.root / "project.json")
        project["policy"]["require_human_final_approval"] = True
        self.write_json("project.json", project)
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

    def test_legacy_project_can_be_upgraded_without_overwriting(self) -> None:
        self.build_releasable_fixture()
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
        project.pop("producer_id", None)
        project.pop("content_contract", None)
        project.pop("motion_contracts", None)
        project["policy"].pop("require_independent_review", None)
        self.write_json("project.json", project)
        shots = load_json(self.root / "shots.json")
        for criterion in shots["shots"][0]["acceptance"]:
            criterion["criterion"] = criterion["pass_if"]
            for key in (
                "pass_if",
                "fail_if",
                "method",
                "test_domain",
                "requirement_ids",
                "motion_contract_ids",
            ):
                criterion.pop(key, None)
        self.write_json("shots.json", shots)
        qa = load_json(self.root / "qa-report.json")
        qa["review"].pop("reviewer_id", None)
        qa["review"].pop("reviewer_kind", None)
        self.write_json("qa-report.json", qa)

        result = upgrade(self.root)
        upgraded = load_json(self.root / "project.json")
        self.assertIn("script.md", result["created"])
        self.assertIn("script_clock", upgraded["gates"])
        self.assertFalse(upgraded["output"]["text_required"])
        self.assertEqual("0.5.0", upgraded["upgraded_to"])
        self.assertIn("content_contract", upgraded)
        self.assertIn("motion_contracts", upgraded)
        self.assertTrue((self.root / "qa" / "review-handoff.json").is_file())
        self.assertTrue(result["requires_manual_review"])
        report = validate(self.root, "final")
        self.assertTrue(
            any("content_contract needs at least one" in item for item in report.errors)
        )

    def test_legacy_handoff_upgrade_changes_metadata_not_evidence(self) -> None:
        self.build_releasable_fixture()
        handoff = load_json(self.root / "qa" / "review-handoff.json")
        handoff["schema_version"] = 1
        handoff["generation_skill"]["version"] = "0.4.0"
        handoff["sources"] = {
            role: value["path"]
            for role, value in handoff["sources"].items()
        }
        self.write_json("qa/review-handoff.json", handoff)

        result = upgrade(self.root)
        upgraded = load_json(self.root / "qa" / "review-handoff.json")

        self.assertTrue(result["review_handoff_upgraded"])
        self.assertEqual(2, upgraded["schema_version"])
        self.assertEqual("0.5.0", upgraded["generation_skill"]["version"])
        self.assertEqual(
            "json-without-gates",
            upgraded["sources"]["project"]["hash_mode"],
        )
        self.assertTrue(upgraded["required_observations"])

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

    def test_blocking_content_requirement_needs_acceptance(self) -> None:
        self.build_releasable_fixture()
        project = load_json(self.root / "project.json")
        project["content_contract"]["required"].append(
            {
                "id": "R_UNLINKED",
                "observable": "An unmapped requirement.",
                "blocking": True,
                "acceptance_ids": [],
            }
        )
        self.write_json("project.json", project)
        report = validate(self.root, "final")
        self.assertTrue(
            any("blocking but has no linked acceptance" in item for item in report.errors)
        )

    def test_self_review_blocks_standard_release(self) -> None:
        self.build_releasable_fixture()
        project = load_json(self.root / "project.json")
        project["policy"]["require_independent_review"] = True
        self.write_json("project.json", project)
        qa = load_json(self.root / "qa-report.json")
        qa["review"]["reviewer_kind"] = "self"
        qa["review"]["reviewer_id"] = project["producer_id"]
        self.write_json("qa-report.json", qa)
        report = validate(self.root, "final")
        self.assertTrue(
            any("reviewer independent from the producer" in item for item in report.errors)
        )

    def test_observed_final_frames_cannot_be_only_asset_evidence(self) -> None:
        self.build_releasable_fixture()
        assets = load_json(self.root / "assets.json")
        for reference in assets["assets"][0]["references"]:
            reference["provenance"] = "observed-final-frame"
        for stress in assets["assets"][0]["stress_tests"]:
            stress["provenance"] = "observed-final-frame"
        self.write_json("assets.json", assets)
        report = validate(self.root, "final")
        self.assertTrue(
            any("provenance is not observed-final-frame" in item for item in report.errors)
        )
        self.assertTrue(
            any("non-final stress test" in item for item in report.errors)
        )

    def test_motion_contract_requires_evidence(self) -> None:
        self.build_releasable_fixture()
        project = load_json(self.root / "project.json")
        project["motion_contracts"][0]["evidence"] = []
        self.write_json("project.json", project)
        report = validate(self.root, "final")
        self.assertTrue(any("motion_contracts[0] needs evidence" in item for item in report.errors))

    def test_signature_event_needs_located_evidence(self) -> None:
        self.build_releasable_fixture()
        project = load_json(self.root / "project.json")
        project["content_contract"]["signature_events"][0]["time_window_sec"] = [
            1.5,
            1.8,
        ]
        self.write_json("project.json", project)
        report = validate(self.root, "final")
        self.assertTrue(any("signature event SIG1" in item for item in report.errors))

    def test_qa_evidence_hash_mismatch_blocks_release(self) -> None:
        self.build_releasable_fixture()
        qa = load_json(self.root / "qa-report.json")
        qa["checks"][0]["evidence"][0]["sha256"] = "0" * 64
        self.write_json("qa-report.json", qa)
        report = validate(self.root, "final")
        self.assertTrue(any("sha256 is stale" in item for item in report.errors))


if __name__ == "__main__":
    unittest.main()

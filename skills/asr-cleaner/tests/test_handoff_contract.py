from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "handoff_contract.py"


class HandoffContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_cli(self, *args: str, expected: int = 0) -> dict:
        result = subprocess.run(
            ["python3", str(SCRIPT), *args],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def create_raw_pipeline(self) -> tuple[Path, Path, Path]:
        source = self.root / "raw.txt"
        cleaned = self.root / "cleaned.md"
        report = self.root / "report.md"
        manifest = self.root / "handoff.json"
        source.write_text("上午讨论招聘流程。", encoding="utf-8")
        cleaned.write_text("上午讨论招聘流程。", encoding="utf-8")
        report.write_text("无待确认项。", encoding="utf-8")
        self.run_cli(
            "create",
            "--input-type",
            "raw_transcript",
            "--source-path",
            str(source),
            "--record-date",
            "2026-08-25",
            "--output",
            str(manifest),
        )
        return manifest, cleaned, report

    def mark_raw_cleaned(
        self,
        manifest: Path,
        cleaned: Path,
        report: Path,
        *extra: str,
    ) -> None:
        self.run_cli(
            "mark-cleaned",
            "--manifest",
            str(manifest),
            "--cleaned-text-path",
            str(cleaned),
            "--report-path",
            str(report),
            "--sensitive-data",
            "none",
            *extra,
        )

    def test_full_lifecycle_validates_marker_and_daily_link(self) -> None:
        manifest, cleaned, report = self.create_raw_pipeline()
        self.mark_raw_cleaned(manifest, cleaned, report, "--category-hint", "动作层")
        self.run_cli(
            "validate",
            "--manifest",
            str(manifest),
            "--stage",
            "before-life-log",
        )

        payload = json.loads(manifest.read_text(encoding="utf-8"))
        target = self.root / "2026-08-25 生活记录.md"
        daily = self.root / "2026-08-25.md"
        target.write_text(
            f"%% asr-pipeline:{payload['pipeline_id']} %%\n",
            encoding="utf-8",
        )
        daily.write_text("- [[2026-08-25 生活记录]]\n", encoding="utf-8")
        self.run_cli(
            "complete",
            "--manifest",
            str(manifest),
            "--status",
            "completed",
            "--target-path",
            str(target),
            "--daily-log-path",
            str(daily),
        )
        result = self.run_cli(
            "validate",
            "--manifest",
            str(manifest),
            "--stage",
            "after-life-log",
        )
        self.assertTrue(result["valid"])

    def test_create_reuses_pipeline_id_for_same_source_and_date(self) -> None:
        source = self.root / "same-source.txt"
        manifest = self.root / "same-handoff.json"
        source.write_text("同一录音内容。", encoding="utf-8")
        first = self.run_cli(
            "create",
            "--input-type",
            "raw_transcript",
            "--source-path",
            str(source),
            "--record-date",
            "2026-08-25",
            "--output",
            str(manifest),
        )
        second = self.run_cli(
            "create",
            "--input-type",
            "raw_transcript",
            "--source-path",
            str(source),
            "--record-date",
            "2026-08-25",
            "--output",
            str(manifest),
        )
        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        self.assertEqual(first["pipeline_id"], second["pipeline_id"])

    def test_create_rejects_audio_input(self) -> None:
        source = self.root / "audio.m4a"
        source.write_text("fake audio", encoding="utf-8")
        result = subprocess.run(
            [
                "python3",
                str(SCRIPT),
                "create",
                "--input-type",
                "audio",
                "--source-path",
                str(source),
                "--record-date",
                "2026-08-25",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid choice: 'audio'", result.stderr)

    def test_sensitive_data_blocks_before_life_log_without_confirmation(self) -> None:
        manifest, cleaned, report = self.create_raw_pipeline()
        self.run_cli(
            "mark-cleaned",
            "--manifest",
            str(manifest),
            "--cleaned-text-path",
            str(cleaned),
            "--report-path",
            str(report),
            "--sensitive-data",
            "candidate",
        )
        result = self.run_cli(
            "validate",
            "--manifest",
            str(manifest),
            "--stage",
            "before-life-log",
            expected=1,
        )
        self.assertIn(
            "sensitive personal data requires explicit archival confirmation",
            result["errors"],
        )

    def test_after_life_log_rejects_missing_pipeline_marker(self) -> None:
        manifest, cleaned, report = self.create_raw_pipeline()
        self.mark_raw_cleaned(manifest, cleaned, report)
        target = self.root / "2026-08-25 生活记录.md"
        daily = self.root / "2026-08-25.md"
        target.write_text("# no marker\n", encoding="utf-8")
        daily.write_text("- [[2026-08-25 生活记录]]\n", encoding="utf-8")
        self.run_cli(
            "complete",
            "--manifest",
            str(manifest),
            "--status",
            "completed",
            "--target-path",
            str(target),
            "--daily-log-path",
            str(daily),
        )
        result = self.run_cli(
            "validate",
            "--manifest",
            str(manifest),
            "--stage",
            "after-life-log",
            expected=1,
        )
        self.assertIn(
            "archive target does not contain the pipeline marker", result["errors"]
        )


if __name__ == "__main__":
    unittest.main()

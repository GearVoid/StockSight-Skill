# -*- coding: utf-8 -*-
import tempfile
import unittest
from pathlib import Path

from scripts import report
from tests.fixtures import sample_report


class ReportSnapshotTests(unittest.TestCase):
    def test_snapshot_roundtrip_preserves_report_payload(self):
        data = sample_report()

        with tempfile.TemporaryDirectory() as tmp:
            snapshot = Path(tmp) / "sample.json"
            report._save_snapshot(
                snapshot,
                data,
                mode="detailed",
                provider="unit",
                failed=["bad-code"],
                quality_notes=["turnover_rate skipped"],
            )

            restored, meta = report._load_snapshot(snapshot)

        self.assertEqual(restored.title, data.title)
        self.assertEqual(restored.stocks[0].code, data.stocks[0].code)
        self.assertEqual(restored.signals[0].risk_type, data.signals[0].risk_type)
        self.assertEqual(restored.news[0].title, data.news[0].title)
        self.assertEqual(meta["mode"], "detailed")
        self.assertEqual(meta["provider"], "unit")
        self.assertEqual(meta["failed_codes"], ["bad-code"])
        self.assertEqual(meta["quality_notes"], ["turnover_rate skipped"])

    def test_cli_renders_from_snapshot_without_codes(self):
        data = sample_report()

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            snapshot = base / "sample.json"
            markdown = base / "sample.md"
            html = base / "sample.html"
            report._save_snapshot(snapshot, data, mode="detailed", provider="unit", failed=[], quality_notes=[])

            exit_code = report.main(
                [
                    "--from-snapshot",
                    str(snapshot),
                    "--markdown-out",
                    str(markdown),
                    "--html",
                    "--out",
                    str(html),
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("Sample (600001)", markdown.read_text(encoding="utf-8"))
            self.assertIn("<!doctype html>", html.read_text(encoding="utf-8").lower())


if __name__ == "__main__":
    unittest.main()

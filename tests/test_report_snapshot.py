# -*- coding: utf-8 -*-
import tempfile
import unittest
import json
from pathlib import Path

from core import RSIResult, TechnicalAnalysis, TechnicalSignal
from scripts import report
from tests.fixtures import sample_report


def sample_technical():
    return TechnicalAnalysis(
        rsi=RSIResult(values=[0.0, 72.5], dates=["2026-01-02", "2026-01-03"], period=14),
        signals=[
            TechnicalSignal(
                indicator="RSI",
                signal_type="overbought",
                level=2,
                direction="bearish",
                date="2026-01-03",
                value=72.5,
                description="超买：RSI 高于 70，需警惕追高风险。",
            )
        ],
    )


class ReportSnapshotTests(unittest.TestCase):
    def test_snapshot_roundtrip_preserves_report_payload(self):
        data = sample_report(technical=sample_technical())

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
        self.assertIsNotNone(restored.technical)
        self.assertEqual(restored.technical.rsi.latest, 72.5)
        self.assertEqual(restored.technical.signals[0].indicator, "RSI")
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

    def test_old_snapshot_without_technical_still_loads(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = Path(tmp) / "old.json"
            report._save_snapshot(snapshot, sample_report(), mode="detailed", provider="unit", failed=[], quality_notes=[])
            payload = json.loads(snapshot.read_text(encoding="utf-8"))
            payload["report"].pop("technical", None)
            snapshot.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            restored, _ = report._load_snapshot(snapshot)

        self.assertIsNone(restored.technical)


if __name__ == "__main__":
    unittest.main()

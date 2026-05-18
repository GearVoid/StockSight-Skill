# -*- coding: utf-8 -*-
import unittest

from formatter import (
    render_detailed_report,
    render_html_report,
    render_standard_report,
    validate_report,
)

from tests.fixtures import sample_report


class FormatterTests(unittest.TestCase):
    def test_standard_report_validates(self):
        data = sample_report()
        report = render_standard_report(data)
        result = validate_report(report, data)

        self.assertTrue(result.passed, result.errors)
        self.assertIn("<kbd>", report)
        self.assertIn("▰", report)

    def test_detailed_report_validates(self):
        data = sample_report()
        report = render_detailed_report(data)
        result = validate_report(report, data)

        self.assertTrue(result.passed, result.errors)
        self.assertIn("<details>", report)

    def test_html_report_contains_split_sections(self):
        html = render_html_report(sample_report())

        self.assertIn("<!doctype html>", html)
        self.assertIn("<style>", html)
        self.assertIn("risk-dashboard-shell", html)
        self.assertIn("new-radar-svg", html)
        self.assertIn("StockSight v2.0", html)

    def test_html_report_without_signals_does_not_create_fake_pie(self):
        html = render_html_report(sample_report(signal=None, news=[]))

        self.assertIn("<!doctype html>", html)
        self.assertIn("empty-state", html)
        self.assertNotIn("Sample news", html)


if __name__ == "__main__":
    unittest.main()


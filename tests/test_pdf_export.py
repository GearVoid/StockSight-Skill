import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.pdf_export import (
    PdfExportError,
    export_pdf_from_html,
    export_text_pdf,
    find_browser_executable,
)


class PdfExportTests(unittest.TestCase):
    def test_find_browser_executable_accepts_explicit_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            browser = Path(tmpdir) / "chrome.exe"
            browser.write_text("", encoding="utf-8")

            self.assertEqual(find_browser_executable(browser), browser.resolve())

    def test_find_browser_executable_rejects_missing_explicit_path(self):
        with self.assertRaises(PdfExportError):
            find_browser_executable(Path("missing-browser.exe"))

    def test_export_pdf_from_html_builds_headless_print_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            html = root / "report.html"
            pdf = root / "report.pdf"
            browser = root / "chrome.exe"
            html.write_text("<html><body>ok</body></html>", encoding="utf-8")
            browser.write_text("", encoding="utf-8")

            def fake_run(command, **kwargs):
                pdf.write_bytes(b"%PDF-1.4\n")
                completed = Mock()
                completed.returncode = 0
                completed.stdout = ""
                completed.stderr = ""
                return completed

            with patch("scripts.pdf_export.subprocess.run", side_effect=fake_run) as run:
                result = export_pdf_from_html(html, pdf, browser)

            self.assertEqual(result, pdf.resolve())
            command = run.call_args.args[0]
            self.assertIn("--headless=new", command)
            self.assertIn("--no-pdf-header-footer", command)
            self.assertIn(f"--print-to-pdf={pdf.resolve()}", command)
            self.assertTrue(command[-1].startswith("file:///"))

    def test_export_pdf_from_html_reports_browser_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            html = root / "report.html"
            pdf = root / "report.pdf"
            browser = root / "chrome.exe"
            html.write_text("<html><body>ok</body></html>", encoding="utf-8")
            browser.write_text("", encoding="utf-8")
            completed = Mock(returncode=1, stdout="", stderr="boom")

            with patch("scripts.pdf_export.subprocess.run", return_value=completed):
                with self.assertRaises(PdfExportError):
                    export_pdf_from_html(html, pdf, browser)

    def test_export_text_pdf_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf = Path(tmpdir) / "text.pdf"

            result = export_text_pdf("# Title\n\n| A | B |\n|---|---|\n| 中文 | 123 |", pdf, "Title")

            self.assertEqual(result, pdf.resolve())
            self.assertGreater(pdf.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()

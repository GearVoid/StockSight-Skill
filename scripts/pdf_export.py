"""Stable PDF export for StockSight HTML reports.

The exporter uses a locally installed Chromium-compatible browser in headless
print mode. This avoids the inconsistent scaling and pagination users often see
when manually printing from a visible browser window.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import quote


class PdfExportError(RuntimeError):
    """Raised when a PDF cannot be exported."""


def _candidate_browser_paths() -> Iterable[Path]:
    names = [
        "msedge",
        "msedge.exe",
        "chrome",
        "chrome.exe",
        "chromium",
        "chromium.exe",
    ]
    for name in names:
        resolved = shutil.which(name)
        if resolved:
            yield Path(resolved)

    program_files = [
        os.environ.get("PROGRAMFILES"),
        os.environ.get("PROGRAMFILES(X86)"),
        os.environ.get("LOCALAPPDATA"),
    ]
    relative_paths = [
        Path("Microsoft/Edge/Application/msedge.exe"),
        Path("Google/Chrome/Application/chrome.exe"),
        Path("Chromium/Application/chrome.exe"),
    ]
    for root in program_files:
        if not root:
            continue
        for relative in relative_paths:
            yield Path(root) / relative


def find_browser_executable(browser_path: Optional[Path] = None) -> Path:
    """Return a Chromium-compatible browser executable."""
    if browser_path:
        candidate = browser_path.expanduser().resolve()
        if candidate.exists():
            return candidate
        raise PdfExportError(f"Browser executable not found: {candidate}")

    for candidate in _candidate_browser_paths():
        try:
            resolved = candidate.expanduser().resolve()
        except OSError:
            continue
        if resolved.exists():
            return resolved

    raise PdfExportError(
        "No Chromium-compatible browser found. Install Microsoft Edge/Chrome "
        "or pass --browser-path."
    )


def _file_url(path: Path) -> str:
    resolved = path.resolve()
    return "file:///" + quote(str(resolved).replace("\\", "/"))


def export_pdf_from_html(
    html_path: Path,
    pdf_path: Path,
    browser_path: Optional[Path] = None,
    timeout: int = 60,
) -> Path:
    """Export a local HTML file to a stable A4 PDF."""
    html_path = html_path.resolve()
    pdf_path = pdf_path.resolve()
    if not html_path.exists():
        raise PdfExportError(f"HTML input does not exist: {html_path}")

    browser = find_browser_executable(browser_path)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="stocksight-browser-") as user_data_dir:
        command = [
            str(browser),
            "--headless=new",
            "--disable-gpu",
            "--disable-software-rasterizer",
            "--disable-dev-shm-usage",
            "--disable-extensions",
            "--disable-background-networking",
            "--disable-component-update",
            "--disable-sync",
            "--disable-crash-reporter",
            "--disable-breakpad",
            "--no-first-run",
            "--no-default-browser-check",
            "--hide-scrollbars",
            "--run-all-compositor-stages-before-draw",
            "--virtual-time-budget=1000",
            "--no-pdf-header-footer",
            f"--user-data-dir={user_data_dir}",
            f"--print-to-pdf={pdf_path}",
            _file_url(html_path),
        ]
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.SubprocessError as exc:
            raise PdfExportError(f"PDF export failed: {exc}") from exc

    if completed.returncode != 0:
        details = (completed.stderr or completed.stdout or "").strip()
        raise PdfExportError(f"PDF export failed with code {completed.returncode}: {details}")
    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
        raise PdfExportError(f"PDF export did not create a usable file: {pdf_path}")

    return pdf_path


def _wrap_text(line: str, max_chars: int = 82) -> list[str]:
    if len(line) <= max_chars:
        return [line]
    chunks = []
    current = line
    while len(current) > max_chars:
        split_at = current.rfind(" ", 0, max_chars)
        if split_at < max_chars // 3:
            split_at = max_chars
        chunks.append(current[:split_at].rstrip())
        current = current[split_at:].lstrip()
    if current:
        chunks.append(current)
    return chunks


def export_text_pdf(markdown: str, pdf_path: Path, title: str = "StockSight Report") -> Path:
    """Export a robust text-first PDF from Markdown when browser printing is unavailable."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        from reportlab.pdfgen import canvas
    except ImportError as exc:
        raise PdfExportError(
            "Text PDF fallback requires reportlab. Install it with `pip install reportlab`."
        ) from exc

    font_name = "STSong-Light"
    pdfmetrics.registerFont(UnicodeCIDFont(font_name))

    pdf_path = pdf_path.resolve()
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    page_width, page_height = A4
    margin = 42
    line_height = 15
    normal_size = 9.5
    title_size = 16
    footer_size = 8

    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    c.setTitle(title)

    def new_page(page_no: int) -> float:
        c.setFont(font_name, footer_size)
        c.setFillColorRGB(0.45, 0.48, 0.55)
        c.drawRightString(page_width - margin, 24, f"StockSight · Page {page_no}")
        c.showPage()
        c.setFillColorRGB(0.09, 0.13, 0.2)
        return page_height - margin

    y = page_height - margin
    page_no = 1
    c.setFont(font_name, title_size)
    c.drawString(margin, y, title)
    y -= 28
    c.setFont(font_name, normal_size)

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip() or " "
        is_heading = line.startswith("#")
        wrapped = _wrap_text(line.replace("<kbd>", "`").replace("</kbd>", "`"))
        for chunk in wrapped:
            if y < margin + line_height:
                y = new_page(page_no)
                page_no += 1
                c.setFont(font_name, normal_size)
            if is_heading:
                c.setFont(font_name, 12)
                c.setFillColorRGB(0.09, 0.13, 0.2)
            else:
                c.setFont(font_name, normal_size)
                c.setFillColorRGB(0.15, 0.18, 0.24)
            c.drawString(margin, y, chunk)
            y -= line_height + (3 if is_heading else 0)

    c.setFont(font_name, footer_size)
    c.setFillColorRGB(0.45, 0.48, 0.55)
    c.drawRightString(page_width - margin, 24, f"StockSight · Page {page_no}")
    c.save()

    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
        raise PdfExportError(f"Text PDF export did not create a usable file: {pdf_path}")
    return pdf_path

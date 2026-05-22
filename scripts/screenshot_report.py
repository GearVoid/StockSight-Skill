#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Capture a StockSight HTML report as a long PNG screenshot.

This helper is intentionally dependency-free. It shells out to a local
Chromium-family browser in headless mode, so agents can turn generated HTML
reports into shareable long screenshots without installing Playwright/Pillow.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Sequence


DEFAULT_WIDTH = 1440
DEFAULT_HEIGHT = 5200


WINDOWS_BROWSER_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]

BROWSER_COMMANDS = [
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "msedge",
    "microsoft-edge",
]


class ScreenshotError(RuntimeError):
    """Raised when a screenshot cannot be produced."""


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Capture a StockSight HTML report as a long PNG screenshot.",
    )
    parser.add_argument("html", type=Path, help="Input HTML report path.")
    parser.add_argument(
        "--out",
        type=Path,
        help="Output PNG path. Defaults to input path with .png suffix.",
    )
    parser.add_argument("--browser", type=Path, help="Explicit Chrome/Edge executable path.")
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH, help="Viewport width.")
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT, help="Viewport height.")
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Browser process timeout in seconds.",
    )
    return parser


def resolve_browser(explicit: Optional[Path] = None) -> Optional[Path]:
    """Find a Chrome/Edge executable suitable for headless screenshots."""
    if explicit:
        return explicit if explicit.exists() else None

    for env_name in ("STOCKSIGHT_BROWSER", "CHROME_BIN", "EDGE_BIN"):
        value = os.environ.get(env_name)
        if value and Path(value).exists():
            return Path(value)

    if os.name == "nt":
        for candidate in WINDOWS_BROWSER_CANDIDATES:
            path = Path(candidate)
            if path.exists():
                return path

    for command in BROWSER_COMMANDS:
        found = shutil.which(command)
        if found:
            return Path(found)
    return None


def build_screenshot_command(
    browser: Path,
    html_path: Path,
    output_path: Path,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
) -> List[str]:
    """Build the browser command without executing it."""
    html_uri = html_path.resolve().as_uri()
    return [
        str(browser),
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=4000",
        f"--window-size={width},{height}",
        f"--screenshot={output_path.resolve()}",
        html_uri,
    ]


def capture_screenshot(
    html_path: Path,
    output_path: Optional[Path] = None,
    browser_path: Optional[Path] = None,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    timeout: int = 30,
) -> Path:
    """Capture a long screenshot and return the resolved PNG path."""
    if not html_path.exists():
        raise ScreenshotError(f"HTML report not found: {html_path}")
    if width <= 0 or height <= 0:
        raise ScreenshotError("width and height must be positive")

    browser = resolve_browser(browser_path)
    if browser is None:
        raise ScreenshotError(
            "Chrome/Edge not found. Install Chrome/Edge or set STOCKSIGHT_BROWSER "
            "to the browser executable path."
        )

    output = output_path or html_path.with_suffix(".png")
    output.parent.mkdir(parents=True, exist_ok=True)
    command = build_screenshot_command(browser, html_path, output, width, height)

    try:
        completed = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise ScreenshotError(f"Browser screenshot timed out after {timeout}s") from exc

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise ScreenshotError(f"Browser screenshot failed: {detail or completed.returncode}")
    if not output.exists() or output.stat().st_size == 0:
        raise ScreenshotError(f"Browser finished but screenshot is empty: {output}")
    return output.resolve()


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    try:
        output = capture_screenshot(
            html_path=args.html,
            output_path=args.out,
            browser_path=args.browser,
            width=args.width,
            height=args.height,
            timeout=args.timeout,
        )
    except ScreenshotError as exc:
        print(f"StockSight screenshot failed: {exc}", file=sys.stderr)
        return 2
    print(f"Screenshot: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

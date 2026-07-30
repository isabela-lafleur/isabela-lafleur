from __future__ import annotations

import argparse
import base64
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

HERO_FILES = [
    ROOT / "assets/generated/hero-dark.svg",
    ROOT / "assets/generated/hero-light.svg",
    ROOT / "assets/generated/hero-mobile-dark.svg",
    ROOT / "assets/generated/hero-mobile-light.svg",
]


def extract_payload(svg_text: str) -> bytes | None:
    match = re.search(r"data:font/woff2;base64,([A-Za-z0-9+/=]+)", svg_text)
    if not match:
        return None
    return base64.b64decode(match.group(1), validate=True)


def summarize(path: Path) -> dict[str, bool]:
    text = path.read_text(encoding="utf-8")
    payload = extract_payload(text)
    return {
        "font_face": "@font-face" in text,
        "embedded_woff2": payload is not None,
        "atlas_display": "Atlas Display" in text,
        "valid_woff2": bool(payload and payload[:4] == b"wOF2"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify embedded custom-font state in generated hero SVGs.")
    parser.add_argument("--expect-fallback", action="store_true", help="Expect fallback-only heroes with no embedded font.")
    args = parser.parse_args()

    exit_code = 0
    for path in HERO_FILES:
        summary = summarize(path)
        print(f"{path.name}:")
        for key in ("font_face", "embedded_woff2", "atlas_display", "valid_woff2"):
            print(f"  {key}={summary[key]}")

        if args.expect_fallback:
            expected_ok = (
                not summary["font_face"]
                and not summary["embedded_woff2"]
                and summary["atlas_display"]
                and not summary["valid_woff2"]
            )
        else:
            expected_ok = all(summary.values())

        if not expected_ok:
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

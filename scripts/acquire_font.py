from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
import sys

import requests
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.common import DESIGN_DIR


@dataclass(frozen=True)
class FontDownload:
    name: str
    font_urls: tuple[str, ...]
    target_name: str
    license_urls: tuple[str, ...]
    license_name: str
    axis_location: dict[str, float] | None = None


GOOGLE_FONTS_COMMIT = "b9f111fdf9d01bb7f5c6b5b8d1b7dfcb1b5032d1"
ADOBE_SOURCE_SERIF_COMMIT = "c8f0b424f870275afcb0efef7f51a588f76fda2f"
IBM_PLEX_COMMIT = "d6c7f1d7d987e8f72f8bb0fd4fcb2272d4d3158a"

DOWNLOADS = [
    FontDownload(
        name="Playfair Display SemiBold",
        font_urls=(
            "https://raw.githubusercontent.com/google/fonts/"
            f"{GOOGLE_FONTS_COMMIT}/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf",
            "https://raw.githubusercontent.com/google/fonts/main/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf",
            "https://raw.githubusercontent.com/google/fonts/main/ofl/playfairdisplay/PlayfairDisplay%5Bopsz%2Cwght%5D.ttf",
        ),
        target_name="PlayfairDisplay-SemiBold.ttf",
        license_urls=(
            "https://raw.githubusercontent.com/google/fonts/"
            f"{GOOGLE_FONTS_COMMIT}/ofl/playfairdisplay/OFL.txt",
            "https://raw.githubusercontent.com/google/fonts/main/ofl/playfairdisplay/OFL.txt",
        ),
        license_name="OFL.txt",
        axis_location={"wght": 600},
    ),
    FontDownload(
        name="Source Serif 4 Regular",
        font_urls=(
            "https://raw.githubusercontent.com/adobe-fonts/source-serif/"
            f"{ADOBE_SOURCE_SERIF_COMMIT}/TTF/SourceSerif4-Regular.ttf",
            "https://raw.githubusercontent.com/adobe-fonts/source-serif/release/TTF/SourceSerif4-Regular.ttf",
        ),
        target_name="SourceSerif4-Regular.ttf",
        license_urls=(
            "https://raw.githubusercontent.com/adobe-fonts/source-serif/"
            f"{ADOBE_SOURCE_SERIF_COMMIT}/LICENSE.md",
            "https://raw.githubusercontent.com/adobe-fonts/source-serif/release/LICENSE.md",
        ),
        license_name="LICENSE-SourceSerif4.md",
    ),
    FontDownload(
        name="Source Serif 4 Semibold",
        font_urls=(
            "https://raw.githubusercontent.com/adobe-fonts/source-serif/"
            f"{ADOBE_SOURCE_SERIF_COMMIT}/TTF/SourceSerif4-Semibold.ttf",
            "https://raw.githubusercontent.com/adobe-fonts/source-serif/release/TTF/SourceSerif4-Semibold.ttf",
        ),
        target_name="SourceSerif4-Semibold.ttf",
        license_urls=(
            "https://raw.githubusercontent.com/adobe-fonts/source-serif/"
            f"{ADOBE_SOURCE_SERIF_COMMIT}/LICENSE.md",
            "https://raw.githubusercontent.com/adobe-fonts/source-serif/release/LICENSE.md",
        ),
        license_name="LICENSE-SourceSerif4.md",
    ),
    FontDownload(
        name="IBM Plex Mono Medium",
        font_urls=(
            "https://raw.githubusercontent.com/IBM/plex/"
            f"{IBM_PLEX_COMMIT}/packages/plex-mono/fonts/complete/ttf/IBMPlexMono-Medium.ttf",
            "https://raw.githubusercontent.com/IBM/plex/master/IBM-Plex-Mono/fonts/complete/ttf/IBMPlexMono-Medium.ttf",
            "https://raw.githubusercontent.com/IBM/plex/master/packages/plex-mono/fonts/complete/ttf/IBMPlexMono-Medium.ttf",
        ),
        target_name="IBMPlexMono-Medium.ttf",
        license_urls=(
            "https://raw.githubusercontent.com/IBM/plex/"
            f"{IBM_PLEX_COMMIT}/LICENSE.txt",
            "https://raw.githubusercontent.com/IBM/plex/master/LICENSE.txt",
        ),
        license_name="LICENSE-IBMPlex.txt",
    ),
]


def download(urls: tuple[str, ...], destination: Path) -> None:
    last_error: Exception | None = None
    for url in urls:
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
        except requests.RequestException as exc:
            last_error = exc
            continue
        destination.write_bytes(response.content)
        return
    if last_error is None:
        raise RuntimeError("No download URLs were provided.")
    raise last_error


def write_static_font(source: Path, target: Path, axis_location: dict[str, float] | None) -> None:
    if axis_location:
        font = TTFont(str(source))
        static_font = instantiateVariableFont(font, axis_location, inplace=False)
        static_font.save(str(target))
        return
    shutil.copyfile(source, target)


def main() -> int:
    fonts_dir = DESIGN_DIR / "fonts"
    fonts_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        for item in DOWNLOADS:
            source_font = temp_root / f"{item.target_name}.download"
            license_path = temp_root / item.license_name
            download(item.font_urls, source_font)
            write_static_font(source_font, fonts_dir / item.target_name, item.axis_location)

            license_target = fonts_dir / item.license_name
            if not license_target.exists():
                download(item.license_urls, license_path)
                shutil.copyfile(license_path, license_target)

    print("Downloaded and prepared:")
    for item in DOWNLOADS:
        print(f"  {fonts_dir / item.target_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

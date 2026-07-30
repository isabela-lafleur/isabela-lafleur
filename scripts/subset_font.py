from __future__ import annotations

import argparse
import base64
import io
from dataclasses import dataclass
from pathlib import Path
import sys

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.common import BODY_FONT, BODY_SEMIBOLD_FONT, DISPLAY_FONT, MONO_FONT, FontSource

SAFETY_CHARSET = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "0123456789"
    " &'-.(),/:+!?[]"
    "–—→"
)


@dataclass(frozen=True)
class EmbeddedFont:
    css_family: str
    source_path: Path
    weight: int
    style: str
    characters: str
    base64_woff2: str


def collect_charset(strings: list[str]) -> str:
    characters = set(SAFETY_CHARSET)
    for text in strings:
        characters.update(text)
    return "".join(sorted(characters))


def encode_embedded_font(payload: bytes | None, *, disabled: bool) -> str:
    if disabled or payload is None:
        return ""
    if not payload:
        raise ValueError("Generated font subset is empty.")
    if payload[:4] != b"wOF2":
        raise ValueError("Generated font subset is not a valid WOFF2 payload.")
    return base64.b64encode(payload).decode("ascii")


def subset_font_bytes(
    strings: list[str],
    font_path: Path | None = None,
    disable_custom_font: bool = False,
) -> bytes | None:
    if disable_custom_font:
        return None
    if font_path is None:
        font_path = DISPLAY_FONT.source_path
    if not font_path.exists():
        return None

    options = subset.Options()
    options.flavor = "woff2"
    options.layout_features = "*"
    options.desubroutinize = True
    options.drop_tables += ["meta"]
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(text=collect_charset(strings))

    font = TTFont(str(font_path))
    font.recalcTimestamp = False
    subsetter.subset(font)
    buffer = io.BytesIO()
    subset.save_font(font, buffer, options)
    return buffer.getvalue()


def subset_font_to_base64(
    strings: list[str],
    font_path: Path | None = None,
    disable_custom_font: bool = False,
) -> str | None:
    payload = subset_font_bytes(strings, font_path=font_path, disable_custom_font=disable_custom_font)
    encoded = encode_embedded_font(payload, disabled=disable_custom_font)
    return encoded or None


def build_font_face_css(fonts: str | EmbeddedFont | list[EmbeddedFont] | tuple[EmbeddedFont, ...] | None) -> str:
    if fonts is None or fonts == "":
        return ""
    if isinstance(fonts, str):
        return (
            "@font-face {\n"
            '  font-family: "Atlas Display";\n'
            "  font-style: normal;\n"
            "  font-weight: 600;\n"
            f"  src: url(data:font/woff2;base64,{fonts}) format('woff2');\n"
            "}\n"
        )
    if isinstance(fonts, EmbeddedFont):
        fonts = [fonts]

    blocks = []
    for font in fonts:
        blocks.append(
            "@font-face {\n"
            f'  font-family: "{font.css_family}";\n'
            f"  font-style: {font.style};\n"
            f"  font-weight: {font.weight};\n"
            f"  src: url(data:font/woff2;base64,{font.base64_woff2}) format('woff2');\n"
            "}\n"
        )
    return "".join(blocks)


def embed_font_faces(
    face_map: dict[FontSource, list[str]],
    *,
    disable_custom_font: bool = False,
) -> list[EmbeddedFont]:
    if disable_custom_font:
        return []
    embedded: list[EmbeddedFont] = []
    for font_source, strings in face_map.items():
        if not strings:
            continue
        if not font_source.source_path.exists():
            raise FileNotFoundError(f"Missing configured font source: {font_source.source_path}")
        encoded = subset_font_to_base64(strings, font_path=font_source.source_path, disable_custom_font=disable_custom_font)
        if not encoded:
            raise ValueError(f"Unable to embed font: {font_source.css_family}")
        embedded.append(
            EmbeddedFont(
                css_family=font_source.css_family,
                source_path=font_source.source_path,
                weight=font_source.weight,
                style=font_source.style,
                characters=collect_charset(strings),
                base64_woff2=encoded,
            )
        )
    return embedded


def default_face_map(strings: list[str]) -> dict[FontSource, list[str]]:
    return {
        DISPLAY_FONT: strings,
        BODY_FONT: strings,
        BODY_SEMIBOLD_FONT: strings,
        MONO_FONT: strings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Subset configured profile fonts into embedded WOFF2 payloads.")
    parser.add_argument("text", nargs="*", help="Strings that should be preserved in the subset.")
    parser.add_argument("--font-path", type=Path, default=DISPLAY_FONT.source_path)
    args = parser.parse_args()

    encoded = subset_font_to_base64(args.text or ["Isabela LaFleur"], args.font_path)
    if not encoded:
        print("No font subset generated.")
        return 0

    print(build_font_face_css(encoded))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

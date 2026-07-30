from __future__ import annotations

from pathlib import Path

from scripts.common import BODY_FONT, BODY_SEMIBOLD_FONT, DISPLAY_FONT, MONO_FONT, FontSource
from scripts.subset_font import build_font_face_css, embed_font_faces


DISPLAY_STACK = '"Atlas Display", "Iowan Old Style", Baskerville, "Palatino Linotype", Palatino, Georgia, "Times New Roman", serif'
BODY_STACK = '"Atlas Body", "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif'
BODY_SEMIBOLD_STACK = '"Atlas Body Semibold", "Atlas Body", "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif'
MONO_STACK = '"Atlas Mono", "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace'


def css_for_roles(
    role_text: dict[FontSource, list[str]],
    *,
    disable_custom_font: bool,
) -> str:
    fonts = embed_font_faces(role_text, disable_custom_font=disable_custom_font)
    return build_font_face_css(fonts)


def default_role_text(strings: list[str]) -> dict[FontSource, list[str]]:
    return {
        DISPLAY_FONT: strings,
        BODY_FONT: strings,
        BODY_SEMIBOLD_FONT: strings,
        MONO_FONT: strings,
    }

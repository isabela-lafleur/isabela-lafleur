from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fontTools.ttLib import TTFont

from scripts.common import DESIGN_DIR

DISPLAY_FONT_PATH = DESIGN_DIR / "fonts" / "PlayfairDisplay-SemiBold.ttf"

MONO_UPPER_FACTOR = 0.67
MONO_LOWER_FACTOR = 0.58
MONO_SPACE_FACTOR = 0.34
MONO_PUNCT_FACTOR = 0.38
MONO_DIGIT_FACTOR = 0.56


@lru_cache(maxsize=1)
def _display_font_metrics() -> tuple[dict[int, int], int, dict[int, str]]:
    font = TTFont(str(DISPLAY_FONT_PATH))
    cmap = font.getBestCmap()
    glyph_set = font.getGlyphSet()
    advances: dict[int, int] = {}
    glyph_map: dict[int, str] = {}
    for codepoint, glyph_name in cmap.items():
        glyph_map[codepoint] = glyph_name
        advances[codepoint] = int(glyph_set[glyph_name].width)
    return advances, int(font["head"].unitsPerEm), glyph_map


def measure_display_text(text: str, font_size: float) -> float:
    advances, units_per_em, _ = _display_font_metrics()
    total = 0
    for char in text:
        total += advances.get(ord(char), int(units_per_em * 0.52))
    return (total / units_per_em) * font_size


def measure_mono_text(text: str, font_size: float) -> float:
    width = 0.0
    for char in text:
        if char == " ":
            width += font_size * MONO_SPACE_FACTOR
        elif char.isdigit():
            width += font_size * MONO_DIGIT_FACTOR
        elif char.isupper():
            width += font_size * MONO_UPPER_FACTOR
        elif char.islower():
            width += font_size * MONO_LOWER_FACTOR
        else:
            width += font_size * MONO_PUNCT_FACTOR
    return width


def measure_text(text: str, font_size: float, kind: str) -> float:
    if kind == "display":
        return measure_display_text(text, font_size)
    return measure_mono_text(text, font_size)


def wrap_text_to_width(
    text: str,
    *,
    max_width: float,
    font_size: float,
    kind: str,
    max_lines: int,
) -> list[str]:
    words = text.split()
    if not words:
        return []

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if measure_text(candidate, font_size, kind) <= max_width:
            current = candidate
            continue
        lines.append(current)
        current = word
    lines.append(current)

    if len(lines) <= max_lines:
        return lines

    collapsed = lines[: max_lines - 1]
    collapsed.append(" ".join(lines[max_lines - 1 :]))
    return collapsed


def split_name_lines(name: str, *, max_width: float, font_size: float) -> list[str]:
    if measure_display_text(name, font_size) <= max_width:
        return [name]
    parts = name.split()
    if len(parts) <= 1:
        return [name]
    lines: list[str] = []
    current = parts[0]
    for part in parts[1:]:
        candidate = f"{current} {part}"
        if measure_display_text(candidate, font_size) <= max_width:
            current = candidate
            continue
        lines.append(current)
        current = part
    lines.append(current)
    return lines


def validate_lines_fit(
    lines: list[str],
    *,
    max_width: float,
    font_size: float,
    kind: str,
    label: str,
) -> None:
    for line in lines:
        if measure_text(line, font_size, kind) > max_width:
            raise ValueError(f"{label} line exceeds safe width: {line}")

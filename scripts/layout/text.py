from __future__ import annotations

import math
import re
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path

from PIL import ImageFont


WHITESPACE_RE = re.compile(r"[ \t]+")


@dataclass(frozen=True)
class TextStyle:
    font_path: Path
    font_size: float
    font_weight: int
    line_height: float
    letter_spacing: float = 0
    min_font_size: float | None = None


@dataclass(frozen=True)
class TextLine:
    text: str
    width: float


@dataclass(frozen=True)
class TextLayout:
    lines: tuple[TextLine, ...]
    width: float
    height: float
    font_size: float
    line_height: float


def normalize_text(text: str) -> str:
    parts = [WHITESPACE_RE.sub(" ", chunk.strip()) for chunk in text.splitlines()]
    return "\n".join(parts)


@lru_cache(maxsize=256)
def _load_font(font_path: str, font_size: float) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(font_path, size=max(1, int(round(font_size))))


def _font(style: TextStyle) -> ImageFont.FreeTypeFont:
    return _load_font(str(style.font_path), style.font_size)


def measure_text(text: str, style: TextStyle) -> float:
    if text == "":
        return 0.0
    font = _font(style)
    width = float(font.getlength(text))
    if len(text) > 1 and style.letter_spacing:
        width += (len(text) - 1) * style.letter_spacing
    return width


def _line_height(style: TextStyle) -> float:
    if style.line_height:
        return style.line_height
    font = _font(style)
    bbox = font.getbbox("Hg")
    return float(bbox[3] - bbox[1])


def font_metrics(style: TextStyle) -> tuple[float, float]:
    font = _font(style)
    ascent, descent = font.getmetrics()
    return float(ascent), float(descent)


def baseline_offset(style: TextStyle) -> float:
    ascent, _ = font_metrics(style)
    return ascent


def _layout_lines(lines: list[str], style: TextStyle) -> TextLayout:
    line_height = _line_height(style)
    measured = tuple(TextLine(text=line, width=measure_text(line, style)) for line in lines)
    width = max((line.width for line in measured), default=0.0)
    height = line_height * len(measured) if measured else 0.0
    return TextLayout(lines=measured, width=width, height=height, font_size=style.font_size, line_height=line_height)


def wrap_text(
    text: str,
    style: TextStyle,
    max_width: float,
    *,
    preserve_explicit_newlines: bool = True,
    break_words: bool = False,
) -> TextLayout:
    normalized = normalize_text(text)
    if normalized == "":
        return _layout_lines([], style)

    paragraphs = normalized.split("\n") if preserve_explicit_newlines else [normalized.replace("\n", " ")]
    wrapped_lines: list[str] = []
    for paragraph in paragraphs:
        if paragraph == "":
            wrapped_lines.append("")
            continue
        words = paragraph.split(" ")
        current = words[0]
        if not break_words and measure_text(current, style) > max_width:
            raise ValueError(f"Single token exceeds max width without break_words: {current}")
        for word in words[1:]:
            candidate = f"{current} {word}"
            if measure_text(candidate, style) <= max_width:
                current = candidate
                continue
            wrapped_lines.append(current)
            if not break_words and measure_text(word, style) > max_width:
                raise ValueError(f"Single token exceeds max width without break_words: {word}")
            current = word
        wrapped_lines.append(current)
    return _layout_lines(wrapped_lines, style)


def fit_text(
    text: str,
    style: TextStyle,
    max_width: float,
    max_height: float | None = None,
    *,
    min_font_size: float | None = None,
    allow_box_expansion: bool = True,
) -> TextLayout:
    active_style = style
    floor = min_font_size if min_font_size is not None else (style.min_font_size or style.font_size)
    while True:
        try:
            layout = wrap_text(text, active_style, max_width)
        except ValueError as exc:
            token = str(exc).split(": ", 1)[-1]
            token_width = measure_text(token, active_style)
            if active_style.font_size > floor:
                next_size = max(floor, active_style.font_size - 1)
                scale = next_size / active_style.font_size
                active_style = replace(active_style, font_size=next_size, line_height=active_style.line_height * scale)
                continue
            if allow_box_expansion:
                return wrap_text(text, active_style, token_width + 1)
            raise

        if max_height is None or layout.height <= max_height:
            return layout
        if active_style.font_size <= floor:
            if allow_box_expansion:
                return layout
            raise ValueError(
                f"Text did not fit height for font {active_style.font_path.name}: "
                f"height={layout.height} max_height={max_height}"
            )
        next_size = max(floor, active_style.font_size - 1)
        scale = next_size / active_style.font_size
        active_style = replace(active_style, font_size=next_size, line_height=active_style.line_height * scale)


def ensure_layout_within_width(
    widget: str,
    field: str,
    text: str,
    layout: TextLayout,
    max_width: float,
) -> None:
    if layout.width > max_width + 0.5:
        raise ValueError(
            f"{widget}:{field} exceeded width. text={text!r} max_width={max_width:.2f} measured={layout.width:.2f}"
        )

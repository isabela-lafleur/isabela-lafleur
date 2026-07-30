from __future__ import annotations

from dataclasses import dataclass

from scripts.layout.text import TextLayout


@dataclass(frozen=True)
class Padding:
    top: float
    right: float
    bottom: float
    left: float


@dataclass
class BoxLayout:
    x: float
    y: float
    width: float
    height: float
    content_width: float
    content_height: float

    @property
    def left(self) -> float:
        return self.x

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def top(self) -> float:
        return self.y

    @property
    def bottom(self) -> float:
        return self.y + self.height


def stack_height(*segments: float) -> float:
    return sum(segment for segment in segments if segment)


def box_from_content(
    *,
    x: float,
    y: float,
    width: float,
    padding: Padding,
    content_height: float,
    min_height: float = 0,
) -> BoxLayout:
    height = max(min_height, padding.top + content_height + padding.bottom)
    return BoxLayout(
        x=x,
        y=y,
        width=width,
        height=height,
        content_width=max(0.0, width - padding.left - padding.right),
        content_height=content_height,
    )


def box_for_title_body(
    *,
    x: float,
    y: float,
    width: float,
    padding: Padding,
    title_layout: TextLayout,
    body_layout: TextLayout,
    title_body_gap: float,
    extra_height: float = 0,
    min_height: float = 0,
) -> BoxLayout:
    content_height = stack_height(title_layout.height, title_body_gap, body_layout.height, extra_height)
    return box_from_content(x=x, y=y, width=width, padding=padding, content_height=content_height, min_height=min_height)


def equalize_row_heights(boxes: list[BoxLayout]) -> list[BoxLayout]:
    if not boxes:
        return boxes
    target = max(box.height for box in boxes)
    for box in boxes:
        box.height = target
    return boxes


def validate_text_in_box(
    *,
    box: BoxLayout,
    text_x: float,
    text_y: float,
    layout: TextLayout,
    tolerance: float = 0.5,
) -> None:
    right = text_x + layout.width
    bottom = text_y + layout.height
    if text_x < box.left - tolerance or right > box.right + tolerance:
        raise ValueError(f"Text exceeded horizontal bounds for box at ({box.x}, {box.y})")
    if text_y < box.top - tolerance or bottom > box.bottom + tolerance:
        raise ValueError(f"Text exceeded vertical bounds for box at ({box.x}, {box.y})")

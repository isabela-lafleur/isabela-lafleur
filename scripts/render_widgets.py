from __future__ import annotations

import sys
from html import escape
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.common import (
    BODY_FONT,
    BODY_SEMIBOLD_FONT,
    DISPLAY_FONT,
    MONO_FONT,
    TEMPLATE_DIR,
    with_project_urls,
)
from scripts.font_roles import BODY_SEMIBOLD_STACK, BODY_STACK, DISPLAY_STACK, MONO_STACK, css_for_roles
from scripts.layout.boxes import BoxLayout, Padding, box_for_title_body, equalize_row_heights, validate_text_in_box
from scripts.layout.text import TextLayout, TextStyle, baseline_offset, fit_text, measure_text


def _env() -> Environment:
    return Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=False, trim_blocks=True, lstrip_blocks=True)


def _frame(viewport: str) -> dict[str, float]:
    if viewport == "desktop":
        return {
            "width": 1000.0,
            "panel_x": 26.0,
            "panel_y": 24.0,
            "panel_width": 948.0,
            "panel_radius": 18.0,
            "padding_x": 32.0,
            "padding_top": 28.0,
            "padding_bottom": 28.0,
            "stack_gap": 24.0,
            "outer_bottom": 24.0,
        }
    return {
        "width": 390.0,
        "panel_x": 16.0,
        "panel_y": 16.0,
        "panel_width": 358.0,
        "panel_radius": 18.0,
        "padding_x": 16.0,
        "padding_top": 22.0,
        "padding_bottom": 22.0,
        "stack_gap": 18.0,
        "outer_bottom": 20.0,
    }


def _font_map(*, display: list[str], body: list[str], body_semibold: list[str], mono: list[str]) -> dict:
    return {
        DISPLAY_FONT: display,
        BODY_FONT: body,
        BODY_SEMIBOLD_FONT: body_semibold,
        MONO_FONT: mono,
    }


def _widget_style(tokens: dict, colors: dict, viewport: str, role_text: dict, disable_custom_font: bool) -> str:
    typography = tokens["typography"]["widget"][viewport]
    return (
        css_for_roles(role_text, disable_custom_font=disable_custom_font)
        + f"""
.widget-section {{ font-family: {MONO_STACK}; font-size: {typography['section_size']}px; letter-spacing: 0.12em; text-transform: uppercase; fill: {colors['muted']}; }}
.widget-heading {{ font-family: {DISPLAY_STACK}; font-size: {typography['heading_size']}px; font-weight: 600; fill: {colors['heading']}; }}
.widget-title {{ font-family: {BODY_SEMIBOLD_STACK}; font-size: {typography['card_title_size']}px; font-weight: 600; fill: {colors['indigo']}; }}
.widget-title-display {{ font-family: {DISPLAY_STACK}; font-size: {typography['card_title_size']}px; font-weight: 600; fill: {colors['heading']}; }}
.widget-title-featured {{ font-family: {DISPLAY_STACK}; font-size: {typography['card_title_size']}px; font-weight: 600; fill: {colors['indigo']}; }}
.widget-body {{ font-family: {BODY_STACK}; font-size: {typography['body_size']}px; fill: {colors['text']}; }}
.widget-meta {{ font-family: {MONO_STACK}; font-size: {typography['meta_size']}px; letter-spacing: 0.08em; text-transform: uppercase; fill: {colors['muted']}; }}
.widget-tag {{ font-family: {MONO_STACK}; font-size: {typography['tag_size']}px; letter-spacing: 0.05em; text-transform: uppercase; fill: {colors['heading']}; }}
"""
    ).strip()


def _block(layout: TextLayout, style: TextStyle, x: float, top: float) -> dict[str, object]:
    return {
        "x": x,
        "y": top + baseline_offset(style),
        "leading": layout.line_height,
        "lines": [escape(line.text) for line in layout.lines],
    }


def _heading_block(section_label: str, heading: str, frame: dict[str, float], styles: dict[str, TextStyle]) -> dict[str, object]:
    content_left = frame["panel_x"] + frame["padding_x"]
    content_width = frame["panel_width"] - frame["padding_x"] * 2
    section_top = frame["panel_y"] + frame["padding_top"]
    heading_top = section_top + styles["section"].line_height + 10
    heading_layout = fit_text(heading, styles["heading"], content_width, allow_box_expansion=False)
    return {
        "content_left": content_left,
        "content_width": content_width,
        "section_label": escape(section_label),
        "section_y": section_top + baseline_offset(styles["section"]),
        "heading": _block(heading_layout, styles["heading"], content_left, heading_top),
        "content_top": heading_top + heading_layout.height + 22,
    }


def _content_box(x: float, y: float, width: float, height: float, padding: Padding) -> BoxLayout:
    return BoxLayout(
        x=x,
        y=y,
        width=width,
        height=height,
        content_width=max(0.0, width - padding.left - padding.right),
        content_height=max(0.0, height - padding.top - padding.bottom),
    )


def _validate_block(box: BoxLayout, x: float, top: float, layout: TextLayout) -> None:
    validate_text_in_box(box=box, text_x=x, text_y=top, layout=layout)


def _tag_pills(tags: list[str], style: TextStyle, x: float, y: float, max_width: float) -> tuple[list[dict[str, float | str]], float]:
    pill_height = 20.0
    gap_x = 8.0
    gap_y = 8.0
    cursor_x = x
    cursor_y = y
    rows_bottom = y
    pills: list[dict[str, float | str]] = []
    for tag in tags:
        width = max(56.0, measure_text(tag, style) + 22.0)
        if cursor_x > x and cursor_x + width > x + max_width:
            cursor_x = x
            cursor_y += pill_height + gap_y
        text_top = cursor_y + (pill_height - style.line_height) / 2
        pills.append(
            {
                "x": cursor_x,
                "y": cursor_y,
                "width": width,
                "height": pill_height,
                "text": escape(tag),
                "text_x": cursor_x + width / 2,
                "text_y": text_top + baseline_offset(style),
            }
        )
        cursor_x += width + gap_x
        rows_bottom = max(rows_bottom, cursor_y + pill_height)
    return pills, rows_bottom - y if pills else 0.0


def _row_positions(count: int, width: float, gap: float, start_x: float) -> list[float]:
    card_width = (width - gap * (count - 1)) / count
    return [start_x + index * (card_width + gap) for index in range(count)]


def _fit_repository_layout(text: str, style: TextStyle, max_width: float) -> TextLayout:
    try:
        layout = fit_text(text, style, max_width, allow_box_expansion=False)
        if len(layout.lines) <= 2:
            return layout
    except ValueError:
        pass

    separator_indexes = [index for index, char in enumerate(text) if char in "/_-"]
    candidates = []
    for index in separator_indexes:
        left = text[: index + 1].strip()
        right = text[index + 1 :].strip()
        if left and right:
            candidates.append(f"{left}\n{right}")

    for candidate in candidates:
        try:
            layout = fit_text(candidate, style, max_width, allow_box_expansion=False)
        except ValueError:
            continue
        if len(layout.lines) <= 2:
            return layout

    raise ValueError(f"featured_work:repository could not fit within two lines: {text!r}")


def _styles(tokens: dict, viewport: str) -> dict[str, TextStyle]:
    typography = tokens["typography"]["widget"][viewport]
    return {
        "section": TextStyle(MONO_FONT.source_path, float(typography["section_size"]), 500, float(typography["section_size"]) * 1.3),
        "heading": TextStyle(DISPLAY_FONT.source_path, float(typography["heading_size"]), 600, float(typography["heading_size"]) * 1.15, min_font_size=float(typography["heading_size"]) - 2),
        "title": TextStyle(BODY_SEMIBOLD_FONT.source_path, float(typography["card_title_size"]), 600, float(typography["card_title_size"]) * 1.2, min_font_size=float(typography["card_title_size"]) - 1),
        "display_title": TextStyle(DISPLAY_FONT.source_path, float(typography["card_title_size"]), 600, float(typography["card_title_size"]) * 1.18, min_font_size=float(typography["card_title_size"]) - 2),
        "body": TextStyle(BODY_FONT.source_path, float(typography["body_size"]), 400, float(typography["body_size"]) * 1.38, min_font_size=float(typography["body_size"]) - 1),
        "meta": TextStyle(MONO_FONT.source_path, float(typography["meta_size"]), 500, float(typography["meta_size"]) * 1.25, min_font_size=max(8.0, float(typography["meta_size"]) - 2)),
        "tag": TextStyle(MONO_FONT.source_path, float(typography["tag_size"]), 500, float(typography["tag_size"]) * 1.2, min_font_size=max(8.0, float(typography["tag_size"]) - 1)),
    }


def render_identity(
    profile_data: dict,
    tokens: dict,
    theme: str,
    font_data_b64: str | None,
    viewport: str = "desktop",
    *,
    section_label: str = "01 / Research Identity",
) -> str:
    env = _env()
    template = env.get_template("identity.svg.j2")
    colors = tokens[theme]
    frame = _frame(viewport)
    styles = _styles(tokens, viewport)
    disable_custom_font = font_data_b64 is None
    heading_block = _heading_block(section_label, "Focus Areas", frame, styles)
    content_left = heading_block["content_left"]
    content_width = heading_block["content_width"]
    card_padding = Padding(16, 18, 16, 18)
    row_gap = 18.0 if viewport == "desktop" else 14.0
    cards: list[dict[str, object]] = []

    if viewport == "desktop":
        card_gap = 32.0
        card_width = (content_width - card_gap) / 2
        row_y = heading_block["content_top"]
        positions = _row_positions(2, content_width, card_gap, content_left)
        for row_start in range(0, min(4, len(profile_data["focus_areas"])), 2):
            row_cards = []
            for offset, area in enumerate(profile_data["focus_areas"][row_start:row_start + 2]):
                meta_layout = fit_text(f"Focus {row_start + offset + 1:02d}", styles["meta"], card_width - card_padding.left - card_padding.right, allow_box_expansion=False)
                title_layout = fit_text(area["title"], styles["title"], card_width - card_padding.left - card_padding.right, allow_box_expansion=False)
                body_layout = fit_text(area["description"], styles["body"], card_width - card_padding.left - card_padding.right, allow_box_expansion=False)
                row_cards.append(
                    {
                        "box": box_for_title_body(
                            x=positions[offset],
                            y=row_y,
                            width=card_width,
                            padding=card_padding,
                            title_layout=title_layout,
                            body_layout=body_layout,
                            title_body_gap=10,
                            extra_height=meta_layout.height + 8,
                        ),
                        "meta_layout": meta_layout,
                        "title_layout": title_layout,
                        "body_layout": body_layout,
                        "title": area["title"],
                    }
                )
            equalize_row_heights([item["box"] for item in row_cards])
            for item in row_cards:
                box = item["box"]
                content_box = _content_box(box.x, box.y, box.width, box.height, card_padding)
                meta_top = box.y + card_padding.top
                title_top = meta_top + item["meta_layout"].height + 8
                body_top = title_top + item["title_layout"].height + 10
                _validate_block(content_box, box.x + card_padding.left, meta_top, item["meta_layout"])
                _validate_block(content_box, box.x + card_padding.left, title_top, item["title_layout"])
                _validate_block(content_box, box.x + card_padding.left, body_top, item["body_layout"])
                cards.append(
                    {
                        "x": box.x,
                        "y": box.y,
                        "width": box.width,
                        "height": box.height,
                        "meta": _block(item["meta_layout"], styles["meta"], box.x + card_padding.left, meta_top),
                        "title": _block(item["title_layout"], styles["title"], box.x + card_padding.left, title_top),
                        "body": _block(item["body_layout"], styles["body"], box.x + card_padding.left, body_top),
                    }
                )
            row_y += max(item["box"].height for item in row_cards) + row_gap
        content_bottom = row_y - row_gap
    else:
        card_width = content_width
        current_y = heading_block["content_top"]
        for index, area in enumerate(profile_data["focus_areas"][:4]):
            meta_layout = fit_text(f"Focus {index + 1:02d}", styles["meta"], card_width - card_padding.left - card_padding.right, allow_box_expansion=False)
            title_layout = fit_text(area["title"], styles["title"], card_width - card_padding.left - card_padding.right, allow_box_expansion=False)
            body_layout = fit_text(area["description"], styles["body"], card_width - card_padding.left - card_padding.right, allow_box_expansion=False)
            box = box_for_title_body(
                x=content_left,
                y=current_y,
                width=card_width,
                padding=card_padding,
                title_layout=title_layout,
                body_layout=body_layout,
                title_body_gap=10,
                extra_height=meta_layout.height + 8,
            )
            content_box = _content_box(box.x, box.y, box.width, box.height, card_padding)
            meta_top = box.y + card_padding.top
            title_top = meta_top + meta_layout.height + 8
            body_top = title_top + title_layout.height + 10
            _validate_block(content_box, box.x + card_padding.left, meta_top, meta_layout)
            _validate_block(content_box, box.x + card_padding.left, title_top, title_layout)
            _validate_block(content_box, box.x + card_padding.left, body_top, body_layout)
            cards.append(
                {
                    "x": box.x,
                    "y": box.y,
                    "width": box.width,
                    "height": box.height,
                    "meta": _block(meta_layout, styles["meta"], box.x + card_padding.left, meta_top),
                    "title": _block(title_layout, styles["title"], box.x + card_padding.left, title_top),
                    "body": _block(body_layout, styles["body"], box.x + card_padding.left, body_top),
                }
            )
            current_y += box.height + row_gap
        content_bottom = current_y - row_gap

    panel_height = content_bottom - frame["panel_y"] + frame["padding_bottom"]
    svg_height = frame["panel_y"] + panel_height + frame["outer_bottom"]
    role_text = _font_map(
        display=["Focus Areas"],
        body=[area["description"] for area in profile_data["focus_areas"][:4]],
        body_semibold=[area["title"] for area in profile_data["focus_areas"][:4]],
        mono=[section_label, *[f"Focus {index + 1:02d}" for index in range(min(4, len(cards)))]],
    )

    return template.render(
        viewbox=f"0 0 {frame['width']:.0f} {svg_height:.0f}",
        width=frame["width"],
        height=svg_height,
        style_block=_widget_style(tokens, colors, viewport, role_text, disable_custom_font),
        colors=colors,
        panel={"x": frame["panel_x"], "y": frame["panel_y"], "width": frame["panel_width"], "height": panel_height, "radius": frame["panel_radius"]},
        section_label=heading_block["section_label"],
        section_y=heading_block["section_y"],
        heading=heading_block["heading"],
        cards=cards,
    )


def render_featured_work(
    profile_data: dict,
    tokens: dict,
    theme: str,
    font_data_b64: str | None,
    viewport: str = "desktop",
    *,
    section_label: str = "02 / Featured Work",
) -> str:
    env = _env()
    template = env.get_template("featured-work.svg.j2")
    colors = tokens[theme]
    frame = _frame(viewport)
    styles = _styles(tokens, viewport)
    disable_custom_font = font_data_b64 is None
    heading_block = _heading_block(section_label, "Selected Systems", frame, styles)
    content_left = heading_block["content_left"]
    content_width = heading_block["content_width"]
    card_padding = Padding(16, 18, 16, 18)
    projects = with_project_urls(profile_data)[:3]
    cards: list[dict[str, object]] = []

    def build_card(project: dict, x: float, y: float, width: float, index: int) -> tuple[BoxLayout, dict[str, object]]:
        inner_width = width - card_padding.left - card_padding.right
        meta_layout = fit_text(f"Project {index + 1:02d}", styles["meta"], inner_width, allow_box_expansion=False)
        title_layout = fit_text(project["title"], styles["display_title"], inner_width, allow_box_expansion=False)
        body_layout = fit_text(project["description"], styles["body"], inner_width, allow_box_expansion=False)
        repo_layout = _fit_repository_layout(project["repository"], styles["meta"], inner_width)
        _, tag_height = _tag_pills(project["topics"], styles["tag"], x + card_padding.left, y, inner_width)
        extra_height = meta_layout.height + 8 + repo_layout.height + 10 + tag_height + (8 if tag_height else 0)
        box = box_for_title_body(
            x=x,
            y=y,
            width=width,
            padding=card_padding,
            title_layout=title_layout,
            body_layout=body_layout,
            title_body_gap=10,
            extra_height=extra_height,
        )
        return box, {
            "meta_layout": meta_layout,
            "title_layout": title_layout,
            "body_layout": body_layout,
            "repo_layout": repo_layout,
            "project": project,
        }

    if viewport == "desktop":
        card_gap = 24.0
        card_width = (content_width - card_gap * 2) / 3
        row_y = heading_block["content_top"]
        row_cards = []
        for index, project in enumerate(projects):
            x = content_left + index * (card_width + card_gap)
            row_cards.append(build_card(project, x, row_y, card_width, index))
        equalize_row_heights([item[0] for item in row_cards])
        for index, (box, payload) in enumerate(row_cards):
            inner_width = box.width - card_padding.left - card_padding.right
            content_box = _content_box(box.x, box.y, box.width, box.height, card_padding)
            meta_top = box.y + card_padding.top
            title_top = meta_top + payload["meta_layout"].height + 8
            body_top = title_top + payload["title_layout"].height + 10
            repo_top = body_top + payload["body_layout"].height + 14
            tags_top = repo_top + payload["repo_layout"].height + 10
            tags, _ = _tag_pills(payload["project"]["topics"], styles["tag"], box.x + card_padding.left, tags_top, inner_width)
            _validate_block(content_box, box.x + card_padding.left, meta_top, payload["meta_layout"])
            _validate_block(content_box, box.x + card_padding.left, title_top, payload["title_layout"])
            _validate_block(content_box, box.x + card_padding.left, body_top, payload["body_layout"])
            _validate_block(content_box, box.x + card_padding.left, repo_top, payload["repo_layout"])
            cards.append(
                {
                    "x": box.x,
                    "y": box.y,
                    "width": box.width,
                    "height": box.height,
                    "meta": _block(payload["meta_layout"], styles["meta"], box.x + card_padding.left, meta_top),
                    "title": _block(payload["title_layout"], styles["display_title"], box.x + card_padding.left, title_top),
                    "body": _block(payload["body_layout"], styles["body"], box.x + card_padding.left, body_top),
                    "repository": _block(payload["repo_layout"], styles["meta"], box.x + card_padding.left, repo_top),
                    "topics": tags,
                }
            )
        content_bottom = row_y + max(item[0].height for item in row_cards)
    else:
        current_y = heading_block["content_top"]
        row_gap = 16.0
        for index, project in enumerate(projects):
            box, payload = build_card(project, content_left, current_y, content_width, index)
            inner_width = box.width - card_padding.left - card_padding.right
            content_box = _content_box(box.x, box.y, box.width, box.height, card_padding)
            meta_top = box.y + card_padding.top
            title_top = meta_top + payload["meta_layout"].height + 8
            body_top = title_top + payload["title_layout"].height + 10
            repo_top = body_top + payload["body_layout"].height + 14
            tags_top = repo_top + payload["repo_layout"].height + 10
            tags, _ = _tag_pills(payload["project"]["topics"], styles["tag"], box.x + card_padding.left, tags_top, inner_width)
            _validate_block(content_box, box.x + card_padding.left, meta_top, payload["meta_layout"])
            _validate_block(content_box, box.x + card_padding.left, title_top, payload["title_layout"])
            _validate_block(content_box, box.x + card_padding.left, body_top, payload["body_layout"])
            _validate_block(content_box, box.x + card_padding.left, repo_top, payload["repo_layout"])
            cards.append(
                {
                    "x": box.x,
                    "y": box.y,
                    "width": box.width,
                    "height": box.height,
                    "meta": _block(payload["meta_layout"], styles["meta"], box.x + card_padding.left, meta_top),
                    "title": _block(payload["title_layout"], styles["display_title"], box.x + card_padding.left, title_top),
                    "body": _block(payload["body_layout"], styles["body"], box.x + card_padding.left, body_top),
                    "repository": _block(payload["repo_layout"], styles["meta"], box.x + card_padding.left, repo_top),
                    "topics": tags,
                }
            )
            current_y += box.height + row_gap
        content_bottom = current_y - row_gap

    panel_height = content_bottom - frame["panel_y"] + frame["padding_bottom"]
    svg_height = frame["panel_y"] + panel_height + frame["outer_bottom"]
    role_text = _font_map(
        display=["Selected Systems", *[project["title"] for project in projects]],
        body=[project["description"] for project in projects],
        body_semibold=[],
        mono=[
            section_label,
            *[f"Project {index + 1:02d}" for index in range(len(projects))],
            *[project["repository"] for project in projects],
            *[topic for project in projects for topic in project["topics"]],
        ],
    )

    return template.render(
        viewbox=f"0 0 {frame['width']:.0f} {svg_height:.0f}",
        width=frame["width"],
        height=svg_height,
        style_block=_widget_style(tokens, colors, viewport, role_text, disable_custom_font),
        colors=colors,
        panel={"x": frame["panel_x"], "y": frame["panel_y"], "width": frame["panel_width"], "height": panel_height, "radius": frame["panel_radius"]},
        section_label=heading_block["section_label"],
        section_y=heading_block["section_y"],
        heading=heading_block["heading"],
        cards=cards,
    )


def render_signal_path(
    profile_data: dict,
    tokens: dict,
    theme: str,
    font_data_b64: str | None,
    viewport: str = "desktop",
    *,
    section_label: str = "03 / Signal Path",
) -> str:
    env = _env()
    template = env.get_template("signal-path.svg.j2")
    colors = tokens[theme]
    frame = _frame(viewport)
    styles = _styles(tokens, viewport)
    disable_custom_font = font_data_b64 is None
    steps = profile_data["signal_path"]
    heading_block = _heading_block(section_label, "Observe » Measure » Compute » Understand » Protect", frame, styles)
    content_left = heading_block["content_left"]
    content_width = heading_block["content_width"]
    box_padding = Padding(16, 14, 16, 14)
    row_gap = 18.0
    boxes: list[dict[str, object]] = []
    connectors: list[dict[str, float]] = []

    if viewport == "desktop":
        box_gap = 14.0
        box_width = (content_width - box_gap * (len(steps) - 1)) / len(steps)
        row_y = heading_block["content_top"]
        raw_boxes = []
        for index, step in enumerate(steps):
            title_layout = fit_text(step["title"], styles["title"], box_width - box_padding.left - box_padding.right, allow_box_expansion=False)
            body_layout = fit_text(step["description"], styles["body"], box_width - box_padding.left - box_padding.right, allow_box_expansion=False)
            box = box_for_title_body(
                x=content_left + index * (box_width + box_gap),
                y=row_y,
                width=box_width,
                padding=box_padding,
                title_layout=title_layout,
                body_layout=body_layout,
                title_body_gap=10,
            )
            raw_boxes.append((box, title_layout, body_layout))
        equalize_row_heights([item[0] for item in raw_boxes])
        for index, (box, title_layout, body_layout) in enumerate(raw_boxes):
            content_box = _content_box(box.x, box.y, box.width, box.height, box_padding)
            title_top = box.y + box_padding.top
            body_top = title_top + title_layout.height + 10
            _validate_block(content_box, box.x + box_padding.left, title_top, title_layout)
            _validate_block(content_box, box.x + box_padding.left, body_top, body_layout)
            boxes.append(
                {
                    "x": box.x,
                    "y": box.y,
                    "width": box.width,
                    "height": box.height,
                    "title": _block(title_layout, styles["title"], box.x + box_padding.left, title_top),
                    "body": _block(body_layout, styles["body"], box.x + box_padding.left, body_top),
                }
            )
            if index < len(raw_boxes) - 1:
                connectors.append(
                    {
                        "x1": box.x + box.width + 6,
                        "y1": box.y + box.height / 2,
                        "x2": raw_boxes[index + 1][0].x - 6,
                        "y2": raw_boxes[index + 1][0].y + raw_boxes[index + 1][0].height / 2,
                    }
                )
        content_bottom = row_y + max(item[0].height for item in raw_boxes)
    else:
        current_y = heading_block["content_top"]
        box_width = content_width - 12
        box_x = content_left + 6
        for index, step in enumerate(steps):
            title_layout = fit_text(step["title"], styles["title"], box_width - box_padding.left - box_padding.right, allow_box_expansion=False)
            body_layout = fit_text(step["description"], styles["body"], box_width - box_padding.left - box_padding.right, allow_box_expansion=False)
            box = box_for_title_body(
                x=box_x,
                y=current_y,
                width=box_width,
                padding=box_padding,
                title_layout=title_layout,
                body_layout=body_layout,
                title_body_gap=10,
            )
            content_box = _content_box(box.x, box.y, box.width, box.height, box_padding)
            title_top = box.y + box_padding.top
            body_top = title_top + title_layout.height + 10
            _validate_block(content_box, box.x + box_padding.left, title_top, title_layout)
            _validate_block(content_box, box.x + box_padding.left, body_top, body_layout)
            boxes.append(
                {
                    "x": box.x,
                    "y": box.y,
                    "width": box.width,
                    "height": box.height,
                    "title": _block(title_layout, styles["title"], box.x + box_padding.left, title_top),
                    "body": _block(body_layout, styles["body"], box.x + box_padding.left, body_top),
                }
            )
            if index < len(steps) - 1:
                connectors.append(
                    {
                        "x1": box.x + box.width / 2,
                        "y1": box.y + box.height + 4,
                        "x2": box.x + box.width / 2,
                        "y2": box.y + box.height + row_gap - 4,
                    }
                )
            current_y += box.height + row_gap
        content_bottom = current_y - row_gap

    panel_height = content_bottom - frame["panel_y"] + frame["padding_bottom"]
    svg_height = frame["panel_y"] + panel_height + frame["outer_bottom"]
    role_text = _font_map(
        display=["Observe » Measure » Compute » Understand » Protect"],
        body=[step["description"] for step in steps],
        body_semibold=[step["title"] for step in steps],
        mono=[section_label],
    )

    return template.render(
        viewbox=f"0 0 {frame['width']:.0f} {svg_height:.0f}",
        width=frame["width"],
        height=svg_height,
        style_block=_widget_style(tokens, colors, viewport, role_text, disable_custom_font),
        colors=colors,
        panel={"x": frame["panel_x"], "y": frame["panel_y"], "width": frame["panel_width"], "height": panel_height, "radius": frame["panel_radius"]},
        section_label=heading_block["section_label"],
        section_y=heading_block["section_y"],
        heading=heading_block["heading"],
        boxes=boxes,
        connectors=connectors,
    )


def render_skills(
    profile_data: dict,
    tokens: dict,
    theme: str,
    font_data_b64: str | None,
    viewport: str = "desktop",
    *,
    section_label: str = "04 / Tools and Methods",
) -> str:
    env = _env()
    template = env.get_template("skills.svg.j2")
    colors = tokens[theme]
    frame = _frame(viewport)
    styles = _styles(tokens, viewport)
    disable_custom_font = font_data_b64 is None
    heading_block = _heading_block(section_label, "Technical Stack", frame, styles)
    content_left = heading_block["content_left"]
    content_width = heading_block["content_width"]
    groups = list(profile_data["skills"].items())[:4]
    card_padding = Padding(16, 16, 16, 16)
    row_gap = 16.0
    cards: list[dict[str, object]] = []

    if viewport == "desktop":
        card_gap = 32.0
        card_width = (content_width - card_gap) / 2
        current_y = heading_block["content_top"]
        for row_start in range(0, len(groups), 2):
            row_cards = []
            for offset, (group, values) in enumerate(groups[row_start:row_start + 2]):
                title_layout = fit_text(group, styles["title"], card_width - card_padding.left - card_padding.right, allow_box_expansion=False)
                body_layout = fit_text(" · ".join(values), styles["body"], card_width - card_padding.left - card_padding.right, allow_box_expansion=False)
                row_cards.append(
                    (
                        box_for_title_body(
                            x=content_left + offset * (card_width + card_gap),
                            y=current_y,
                            width=card_width,
                            padding=card_padding,
                            title_layout=title_layout,
                            body_layout=body_layout,
                            title_body_gap=10,
                        ),
                        title_layout,
                        body_layout,
                    )
                )
            equalize_row_heights([item[0] for item in row_cards])
            for box, title_layout, body_layout in row_cards:
                content_box = _content_box(box.x, box.y, box.width, box.height, card_padding)
                title_top = box.y + card_padding.top
                body_top = title_top + title_layout.height + 10
                _validate_block(content_box, box.x + card_padding.left, title_top, title_layout)
                _validate_block(content_box, box.x + card_padding.left, body_top, body_layout)
                cards.append(
                    {
                        "x": box.x,
                        "y": box.y,
                        "width": box.width,
                        "height": box.height,
                        "title": _block(title_layout, styles["title"], box.x + card_padding.left, title_top),
                        "body": _block(body_layout, styles["body"], box.x + card_padding.left, body_top),
                    }
                )
            current_y += max(item[0].height for item in row_cards) + row_gap
        content_bottom = current_y - row_gap
    else:
        current_y = heading_block["content_top"]
        for group, values in groups:
            title_layout = fit_text(group, styles["title"], content_width - card_padding.left - card_padding.right, allow_box_expansion=False)
            body_layout = fit_text(" · ".join(values), styles["body"], content_width - card_padding.left - card_padding.right, allow_box_expansion=False)
            box = box_for_title_body(
                x=content_left,
                y=current_y,
                width=content_width,
                padding=card_padding,
                title_layout=title_layout,
                body_layout=body_layout,
                title_body_gap=10,
            )
            content_box = _content_box(box.x, box.y, box.width, box.height, card_padding)
            title_top = box.y + card_padding.top
            body_top = title_top + title_layout.height + 10
            _validate_block(content_box, box.x + card_padding.left, title_top, title_layout)
            _validate_block(content_box, box.x + card_padding.left, body_top, body_layout)
            cards.append(
                {
                    "x": box.x,
                    "y": box.y,
                    "width": box.width,
                    "height": box.height,
                    "title": _block(title_layout, styles["title"], box.x + card_padding.left, title_top),
                    "body": _block(body_layout, styles["body"], box.x + card_padding.left, body_top),
                }
            )
            current_y += box.height + row_gap
        content_bottom = current_y - row_gap

    panel_height = content_bottom - frame["panel_y"] + frame["padding_bottom"]
    svg_height = frame["panel_y"] + panel_height + frame["outer_bottom"]
    role_text = _font_map(
        display=["Technical Stack"],
        body=[" · ".join(values) for _, values in groups],
        body_semibold=[group for group, _ in groups],
        mono=[section_label],
    )

    return template.render(
        viewbox=f"0 0 {frame['width']:.0f} {svg_height:.0f}",
        width=frame["width"],
        height=svg_height,
        style_block=_widget_style(tokens, colors, viewport, role_text, disable_custom_font),
        colors=colors,
        panel={"x": frame["panel_x"], "y": frame["panel_y"], "width": frame["panel_width"], "height": panel_height, "radius": frame["panel_radius"]},
        section_label=heading_block["section_label"],
        section_y=heading_block["section_y"],
        heading=heading_block["heading"],
        cards=cards,
    )


def render_timeline(
    profile_data: dict,
    tokens: dict,
    theme: str,
    font_data_b64: str | None,
    viewport: str = "desktop",
    *,
    section_label: str = "05 / Field Chronicle",
) -> str:
    env = _env()
    template = env.get_template("timeline.svg.j2")
    colors = tokens[theme]
    frame = _frame(viewport)
    styles = _styles(tokens, viewport)
    disable_custom_font = font_data_b64 is None
    items = profile_data["timeline"]
    heading_block = _heading_block(section_label, "Timeline", frame, styles)
    content_left = heading_block["content_left"]
    content_width = heading_block["content_width"]
    line_x = content_left + (86 if viewport == "desktop" else 18)
    card_x = line_x + (46 if viewport == "desktop" else 30)
    card_width = content_left + content_width - card_x
    card_padding = Padding(14, 16, 14, 16)
    gap = 18.0
    entries: list[dict[str, object]] = []
    current_y = heading_block["content_top"]

    for item in items:
        title_layout = fit_text(item["title"], styles["display_title"], card_width - card_padding.left - card_padding.right, allow_box_expansion=False)
        org_layout = fit_text(item["organization"], styles["meta"], card_width - card_padding.left - card_padding.right, allow_box_expansion=False)
        body_layout = fit_text(item["description"], styles["body"], card_width - card_padding.left - card_padding.right, allow_box_expansion=False)
        box = box_for_title_body(
            x=card_x,
            y=current_y,
            width=card_width,
            padding=card_padding,
            title_layout=title_layout,
            body_layout=body_layout,
            title_body_gap=10 + org_layout.height,
        )
        content_box = _content_box(box.x, box.y, box.width, box.height, card_padding)
        title_top = box.y + card_padding.top
        org_top = title_top + title_layout.height + 6
        body_top = org_top + org_layout.height + 10
        _validate_block(content_box, box.x + card_padding.left, title_top, title_layout)
        _validate_block(content_box, box.x + card_padding.left, org_top, org_layout)
        _validate_block(content_box, box.x + card_padding.left, body_top, body_layout)
        dot_y = title_top + baseline_offset(styles["display_title"]) - 2
        entries.append(
            {
                "year": escape(str(item["year"])),
                "year_y": dot_y - 14,
                "title": _block(title_layout, styles["display_title"], box.x + card_padding.left, title_top),
                "organization": _block(org_layout, styles["meta"], box.x + card_padding.left, org_top),
                "body": _block(body_layout, styles["body"], box.x + card_padding.left, body_top),
                "x": box.x,
                "y": box.y,
                "width": box.width,
                "height": box.height,
                "dot_x": line_x,
                "dot_y": dot_y,
            }
        )
        current_y += box.height + gap

    content_bottom = current_y - gap if entries else heading_block["content_top"]
    panel_height = content_bottom - frame["panel_y"] + frame["padding_bottom"]
    svg_height = frame["panel_y"] + panel_height + frame["outer_bottom"]
    role_text = _font_map(
        display=["Timeline", *[item["title"] for item in items]],
        body=[item["description"] for item in items],
        body_semibold=[],
        mono=[section_label, *[item["organization"] for item in items], *[str(item["year"]) for item in items]],
    )

    return template.render(
        viewbox=f"0 0 {frame['width']:.0f} {svg_height:.0f}",
        width=frame["width"],
        height=svg_height,
        style_block=_widget_style(tokens, colors, viewport, role_text, disable_custom_font),
        colors=colors,
        panel={"x": frame["panel_x"], "y": frame["panel_y"], "width": frame["panel_width"], "height": panel_height, "radius": frame["panel_radius"]},
        section_label=heading_block["section_label"],
        section_y=heading_block["section_y"],
        heading=heading_block["heading"],
        entries=entries,
        line_x=line_x,
        line_top=entries[0]["dot_y"] if entries else 0,
        line_bottom=entries[-1]["dot_y"] if entries else 0,
    )


def render_contact(
    profile_data: dict,
    tokens: dict,
    theme: str,
    font_data_b64: str | None,
    viewport: str = "desktop",
    *,
    section_label: str = "06 / Contact",
) -> str:
    env = _env()
    template = env.get_template("contact.svg.j2")
    colors = tokens[theme]
    frame = _frame(viewport)
    styles = _styles(tokens, viewport)
    disable_custom_font = font_data_b64 is None
    heading_block = _heading_block(section_label, "Links and Location", frame, styles)
    content_left = heading_block["content_left"]
    content_width = heading_block["content_width"]

    raw_items = []
    for link in profile_data["contact"]["links"]:
        if link.get("url"):
            raw_items.append((link["label"], link["url"]))
    if profile_data["profile"].get("location"):
        raw_items.append(("Location", profile_data["profile"]["location"]))

    note_layout = fit_text(profile_data["contact"]["closing_note"], styles["body"], content_width, allow_box_expansion=False)
    note_top = heading_block["content_top"]
    cards_top = note_top + note_layout.height + 20
    cards: list[dict[str, object]] = []
    card_padding = Padding(12, 14, 12, 14)

    if viewport == "desktop":
        gap = 18.0
        cursor_x = content_left
        cursor_y = cards_top
        row_height = 0.0
        for label, value in raw_items:
            preferred_width = max(
                220.0,
                min(300.0, max(measure_text(label, styles["meta"]), measure_text(value, styles["body"])) + 28.0),
            )
            if cursor_x > content_left and cursor_x + preferred_width > content_left + content_width:
                cursor_x = content_left
                cursor_y += row_height + gap
                row_height = 0.0
            value_layout = fit_text(value, styles["body"], preferred_width - card_padding.left - card_padding.right, allow_box_expansion=False)
            box = box_for_title_body(
                x=cursor_x,
                y=cursor_y,
                width=preferred_width,
                padding=card_padding,
                title_layout=fit_text(label, styles["meta"], preferred_width - card_padding.left - card_padding.right, allow_box_expansion=False),
                body_layout=value_layout,
                title_body_gap=8,
            )
            label_layout = fit_text(label, styles["meta"], preferred_width - card_padding.left - card_padding.right, allow_box_expansion=False)
            content_box = _content_box(box.x, box.y, box.width, box.height, card_padding)
            label_top = box.y + card_padding.top
            value_top = label_top + label_layout.height + 8
            _validate_block(content_box, box.x + card_padding.left, label_top, label_layout)
            _validate_block(content_box, box.x + card_padding.left, value_top, value_layout)
            cards.append(
                {
                    "x": box.x,
                    "y": box.y,
                    "width": box.width,
                    "height": box.height,
                    "label": _block(label_layout, styles["meta"], box.x + card_padding.left, label_top),
                    "value": _block(value_layout, styles["body"], box.x + card_padding.left, value_top),
                }
            )
            cursor_x += box.width + gap
            row_height = max(row_height, box.height)
        content_bottom = cursor_y + row_height if cards else cards_top
    else:
        current_y = cards_top
        gap = 14.0
        for label, value in raw_items:
            label_layout = fit_text(label, styles["meta"], content_width - card_padding.left - card_padding.right, allow_box_expansion=False)
            value_layout = fit_text(value, styles["body"], content_width - card_padding.left - card_padding.right, allow_box_expansion=False)
            box = box_for_title_body(
                x=content_left,
                y=current_y,
                width=content_width,
                padding=card_padding,
                title_layout=label_layout,
                body_layout=value_layout,
                title_body_gap=8,
            )
            content_box = _content_box(box.x, box.y, box.width, box.height, card_padding)
            label_top = box.y + card_padding.top
            value_top = label_top + label_layout.height + 8
            _validate_block(content_box, box.x + card_padding.left, label_top, label_layout)
            _validate_block(content_box, box.x + card_padding.left, value_top, value_layout)
            cards.append(
                {
                    "x": box.x,
                    "y": box.y,
                    "width": box.width,
                    "height": box.height,
                    "label": _block(label_layout, styles["meta"], box.x + card_padding.left, label_top),
                    "value": _block(value_layout, styles["body"], box.x + card_padding.left, value_top),
                }
            )
            current_y += box.height + gap
        content_bottom = current_y - gap if cards else cards_top

    panel_height = content_bottom - frame["panel_y"] + frame["padding_bottom"]
    svg_height = frame["panel_y"] + panel_height + frame["outer_bottom"]
    role_text = _font_map(
        display=["Links and Location"],
        body=[profile_data["contact"]["closing_note"], *[value for _, value in raw_items]],
        body_semibold=[],
        mono=[section_label, *[label for label, _ in raw_items]],
    )

    return template.render(
        viewbox=f"0 0 {frame['width']:.0f} {svg_height:.0f}",
        width=frame["width"],
        height=svg_height,
        style_block=_widget_style(tokens, colors, viewport, role_text, disable_custom_font),
        colors=colors,
        panel={"x": frame["panel_x"], "y": frame["panel_y"], "width": frame["panel_width"], "height": panel_height, "radius": frame["panel_radius"]},
        section_label=heading_block["section_label"],
        section_y=heading_block["section_y"],
        heading=heading_block["heading"],
        note=_block(note_layout, styles["body"], content_left, note_top),
        cards=cards,
    )

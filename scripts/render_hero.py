from __future__ import annotations

import sys
from html import escape
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.common import BODY_FONT, BODY_SEMIBOLD_FONT, DISPLAY_FONT, MONO_FONT, TEMPLATE_DIR
from scripts.font_roles import BODY_SEMIBOLD_STACK, BODY_STACK, DISPLAY_STACK, MONO_STACK, css_for_roles
from scripts.layout.boxes import BoxLayout, Padding, validate_text_in_box
from scripts.layout.text import TextStyle, baseline_offset, ensure_layout_within_width, fit_text


def _panel_padding(layout: dict[str, object]) -> Padding:
    padding = layout["padding"]
    return Padding(
        top=float(padding["top"]),
        right=float(padding["right"]),
        bottom=float(padding["bottom"]),
        left=float(padding["left"]),
    )


def _line_block(layout_obj, x: float, y: float) -> dict[str, object]:
    return {
        "x": x,
        "y": y,
        "lines": [escape(line.text) for line in layout_obj.lines],
        "leading": layout_obj.line_height,
    }


def _discipline_lines(profile_data: dict) -> list[str]:
    lines = [line.strip() for line in profile_data["hero"].get("discipline_lines", []) if line.strip()]
    if len(lines) == 1:
        text = lines[0]
        for separator in (" · ", " • ", " / "):
            if separator in text:
                left, right = text.split(separator, 1)
                lines = [left.strip(), right.strip()]
                break
    return lines[:2]


def _fit_image_within(
    outer_x: float,
    outer_y: float,
    outer_width: float,
    outer_height: float,
    image_width: float,
    image_height: float,
) -> dict[str, float]:
    if image_width <= 0 or image_height <= 0:
        raise ValueError("Molecule of the Month image dimensions must be positive.")

    scale = min(outer_width / image_width, outer_height / image_height)
    render_width = image_width * scale
    render_height = image_height * scale
    return {
        "x": outer_x + (outer_width - render_width) / 2,
        "y": outer_y + (outer_height - render_height) / 2,
        "width": render_width,
        "height": render_height,
    }


def render_hero(
    profile_data: dict,
    tokens: dict,
    theme: str,
    font_data_b64: str | None,
    molecule_data: dict,
    viewport: str = "desktop",
) -> str:
    colors = tokens[theme]
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=False, trim_blocks=True, lstrip_blocks=True)
    template = env.get_template("hero.svg.j2")
    layout = tokens["layout"]["hero"][viewport]
    typography = tokens["typography"]["hero"][viewport]
    disable_custom_font = font_data_b64 is None

    text_width = float(layout["text_width"])
    molecule_link_text = f"{molecule_data.get('link_label', 'Original article')} ↗"
    note_lines = [
        f"By {molecule_data['author']} · {molecule_data['license_owner']} · {molecule_data['license']}",
        molecule_data["image_transform_note"],
    ]

    display_strings = [profile_data["profile"]["name"]]
    semibold_strings = [molecule_data["title"]]
    body_strings = [profile_data["hero"]["statement"], *note_lines]
    mono_strings = [
        profile_data["hero"].get("institution_label", ""),
        *profile_data["hero"]["discipline_lines"],
        *profile_data["hero"].get("metadata", []),
        molecule_data["label"],
        molecule_data["month_year"],
        molecule_link_text,
    ]
    font_css = css_for_roles(
        {
            DISPLAY_FONT: display_strings,
            BODY_SEMIBOLD_FONT: semibold_strings,
            BODY_FONT: body_strings,
            MONO_FONT: mono_strings,
        },
        disable_custom_font=disable_custom_font,
    )

    style_block = (
        font_css
        + f"""
.hero-top-label {{ font-family: {MONO_STACK}; font-size: {typography['metadata_size']}px; letter-spacing: 0.12em; text-transform: uppercase; fill: {colors['muted']}; }}
.hero-name {{ font-family: {DISPLAY_STACK}; font-size: {typography['name_size']}px; font-weight: 600; line-height: 1.08; fill: {colors['heading']}; }}
.hero-discipline {{ font-family: {MONO_STACK}; font-size: {typography['discipline_size']}px; letter-spacing: 0.05em; fill: {colors['indigo']}; }}
.hero-statement {{ font-family: {BODY_STACK}; font-size: {typography['statement_size']}px; font-weight: 400; fill: {colors['text']}; }}
.hero-meta {{ font-family: {MONO_STACK}; font-size: {typography['metadata_size']}px; letter-spacing: 0.08em; text-transform: uppercase; fill: {colors['muted']}; }}
.hero-feature-label {{ font-family: {MONO_STACK}; font-size: {typography['feature_label_size']}px; letter-spacing: 0.1em; text-transform: uppercase; fill: {colors['lavender']}; }}
.hero-feature-title {{ font-family: {BODY_SEMIBOLD_STACK}; font-size: {typography['feature_title_size']}px; font-weight: 600; fill: {colors['heading']}; }}
.hero-feature-meta {{ font-family: {MONO_STACK}; font-size: {typography['feature_meta_size']}px; letter-spacing: 0.06em; text-transform: uppercase; fill: {colors['muted']}; }}
.hero-feature-link {{ font-family: {MONO_STACK}; font-size: {typography['feature_meta_size']}px; letter-spacing: 0.04em; fill: {colors['periwinkle']}; text-decoration: underline; }}
.hero-feature-note {{ font-family: {BODY_STACK}; font-size: {typography['feature_note_size']}px; fill: {colors['muted']}; }}
"""
    ).strip()

    name_style = TextStyle(
        DISPLAY_FONT.source_path,
        float(typography["name_size"]),
        600,
        float(layout["name_line_gap"]),
        min_font_size=float(typography["name_size"]) - 8,
    )
    mono_style = TextStyle(
        MONO_FONT.source_path,
        float(typography["discipline_size"]),
        500,
        float(typography["discipline_leading"]),
        letter_spacing=float(typography["discipline_size"]) * 0.05,
    )
    meta_style = TextStyle(MONO_FONT.source_path, float(typography["metadata_size"]), 500, float(typography["metadata_size"]) * 1.25)
    statement_style = TextStyle(
        BODY_FONT.source_path,
        float(typography["statement_size"]),
        400,
        float(typography["statement_leading"]),
        min_font_size=float(typography["statement_size"]) - 2,
    )
    feature_label_style = TextStyle(
        MONO_FONT.source_path,
        float(typography["feature_label_size"]),
        500,
        float(typography["feature_label_size"]) * 1.35,
    )
    feature_title_style = TextStyle(
        BODY_SEMIBOLD_FONT.source_path,
        float(typography["feature_title_size"]),
        600,
        float(typography["feature_title_leading"]),
        min_font_size=float(typography["feature_title_size"]) - 3,
    )
    feature_meta_style = TextStyle(
        MONO_FONT.source_path,
        float(typography["feature_meta_size"]),
        500,
        float(typography["feature_meta_size"]) * 1.35,
    )
    feature_note_style = TextStyle(
        BODY_FONT.source_path,
        float(typography["feature_note_size"]),
        400,
        float(typography["feature_note_size"]) * 1.35,
    )

    name_layout = fit_text(profile_data["profile"]["name"], name_style, text_width, allow_box_expansion=False)
    if len(name_layout.lines) > 2:
        raise ValueError("hero:name exceeded the supported two-line layout")

    discipline_lines = [line.upper() for line in _discipline_lines(profile_data)]
    discipline_layouts = [fit_text(line, mono_style, text_width, allow_box_expansion=False) for line in discipline_lines]
    statement_layout = fit_text(
        profile_data["hero"]["statement"],
        statement_style,
        text_width,
        allow_box_expansion=False,
    )
    max_statement_lines = 4 if viewport == "mobile" else 3
    if len(statement_layout.lines) > max_statement_lines:
        raise ValueError("hero:statement exceeded supported line count")

    padding = _panel_padding(layout)
    panel_x = float(layout["panel"]["x"])
    panel_y = float(layout["panel"]["y"])
    panel_width = float(layout["panel"]["width"])

    top_label_top = panel_y + padding.top
    top_label_y = top_label_top + baseline_offset(meta_style)
    name_top = top_label_top + meta_style.line_height + 16
    name_y = name_top + baseline_offset(name_style)
    discipline_top = name_top + name_layout.height + 18
    discipline_y = discipline_top + baseline_offset(mono_style)
    statement_top = discipline_top + sum(item.height for item in discipline_layouts) + 18
    statement_y = statement_top + baseline_offset(statement_style)

    feature_x = float(layout["media_x"])
    feature_width = float(layout["media_width"])
    feature_padding = float(layout["media_padding"])
    feature_inner_width = feature_width - feature_padding * 2

    if viewport == "desktop":
        feature_top = float(layout["media_top"])
    else:
        feature_top = statement_top + statement_layout.height + float(layout["media_top_gap"])

    feature_label_y = feature_top + feature_padding + baseline_offset(feature_label_style)
    feature_title_top = feature_top + feature_padding + feature_label_style.line_height + float(layout["media_header_gap"])
    feature_title_layout = fit_text(
        molecule_data["title"],
        feature_title_style,
        feature_inner_width,
        allow_box_expansion=False,
    )
    feature_title_y = feature_title_top + baseline_offset(feature_title_style)

    feature_date_top = feature_title_top + feature_title_layout.height + float(layout["media_header_gap"])
    feature_date_layout = fit_text(molecule_data["month_year"], feature_meta_style, feature_inner_width, allow_box_expansion=False)
    feature_date_y = feature_date_top + baseline_offset(feature_meta_style)

    feature_link_top = feature_date_top + feature_date_layout.height + float(layout["media_link_gap"])
    feature_link_layout = fit_text(molecule_link_text, feature_meta_style, feature_inner_width, allow_box_expansion=False)
    feature_link_y = feature_link_top + baseline_offset(feature_meta_style)

    image_frame_top = feature_link_top + feature_link_layout.height + float(layout["media_image_top_gap"])
    image_frame = {
        "x": feature_x + feature_padding,
        "y": image_frame_top,
        "width": feature_inner_width,
        "height": float(layout["media_image_height"]),
        "radius": 14,
    }
    rendered_image = _fit_image_within(
        image_frame["x"],
        image_frame["y"],
        image_frame["width"],
        image_frame["height"],
        float(molecule_data["image_width"]),
        float(molecule_data["image_height"]),
    )

    note_layouts = [fit_text(line, feature_note_style, feature_inner_width, allow_box_expansion=False) for line in note_lines]
    note_1_top = image_frame["y"] + image_frame["height"] + float(layout["media_note_gap"])
    note_1_y = note_1_top + baseline_offset(feature_note_style)
    note_2_top = note_1_top + note_layouts[0].height + 4
    note_2_y = note_2_top + baseline_offset(feature_note_style)

    feature_box = {
        "x": feature_x,
        "y": feature_top,
        "width": feature_width,
        "height": (note_2_top + note_layouts[1].height + feature_padding) - feature_top,
        "radius": 16,
    }

    if viewport == "desktop":
        metadata_y = max(statement_top + statement_layout.height + 44, feature_box["y"] + feature_box["height"] - meta_style.line_height - 8)
        panel_height = max(
            metadata_y + meta_style.line_height + padding.bottom - panel_y,
            feature_box["y"] + feature_box["height"] + padding.bottom - panel_y,
        )
    else:
        metadata_y = feature_box["y"] + feature_box["height"] + 24
        panel_height = metadata_y + meta_style.line_height + padding.bottom - panel_y

    panel = {
        "x": panel_x,
        "y": panel_y,
        "width": panel_width,
        "height": panel_height,
        "radius": layout["panel"]["radius"],
    }
    svg_height = panel_y + panel_height + 22

    text_box = BoxLayout(
        x=float(layout["text_x"]),
        y=top_label_top,
        width=text_width,
        height=max(metadata_y + meta_style.line_height - top_label_top, statement_top + statement_layout.height - top_label_top),
        content_width=text_width,
        content_height=0,
    )
    ensure_layout_within_width("hero", "name", profile_data["profile"]["name"], name_layout, text_width)
    ensure_layout_within_width("hero", "statement", profile_data["hero"]["statement"], statement_layout, text_width)
    validate_text_in_box(box=text_box, text_x=float(layout["text_x"]), text_y=name_top, layout=name_layout)
    for index, item in enumerate(discipline_layouts):
        validate_text_in_box(box=text_box, text_x=float(layout["text_x"]), text_y=discipline_top + index * item.line_height, layout=item)
    validate_text_in_box(box=text_box, text_x=float(layout["text_x"]), text_y=statement_top, layout=statement_layout)

    metadata_items = []
    meta_texts = profile_data["hero"].get("metadata", [])
    if viewport == "desktop":
        gap = float(layout["metadata_gap"])
        for index, text in enumerate(meta_texts[:3]):
            metadata_items.append(
                {
                    "x": float(layout["text_x"]) + gap * index,
                    "y": metadata_y,
                    "anchor": "start",
                    "text": escape(text),
                    "class_name": "hero-meta",
                }
            )
    else:
        if meta_texts:
            metadata_items.append(
                {
                    "x": float(layout["text_x"]),
                    "y": metadata_y,
                    "anchor": "start",
                    "text": escape(meta_texts[0]),
                    "class_name": "hero-meta",
                }
            )
        if len(meta_texts) > 1:
            metadata_items.append(
                {
                    "x": float(layout["text_x"]) + text_width,
                    "y": metadata_y,
                    "anchor": "end",
                    "text": escape(meta_texts[1]),
                    "class_name": "hero-meta",
                }
            )
        if len(meta_texts) > 2:
            metadata_items.append(
                {
                    "x": float(layout["text_x"]),
                    "y": metadata_y + meta_style.line_height + 4,
                    "anchor": "start",
                    "text": escape(meta_texts[2]),
                    "class_name": "hero-meta",
                }
            )

    return template.render(
        viewbox=f"0 0 {int(layout['width'])} {svg_height:.0f}",
        width=layout["width"],
        height=svg_height,
        title=escape(f"{profile_data['profile']['name']} hero"),
        desc=escape(
            f"{profile_data['profile']['name']} — "
            f"{' / '.join(profile_data['hero']['discipline_lines'])}. "
            f"{profile_data['hero']['statement']} "
            f"Molecule of the Month: {molecule_data['title']} ({molecule_data['month_year']})."
        ),
        style_block=style_block,
        colors=colors,
        panel=panel,
        top_label=escape(profile_data["hero"].get("institution_label", "")),
        top_label_position={"x": layout["text_x"], "y": top_label_y},
        name_block=_line_block(name_layout, float(layout["text_x"]), name_y),
        discipline_blocks=[
            {
                "x": float(layout["text_x"]),
                "y": discipline_y + index * mono_style.line_height,
                "text": escape(line),
            }
            for index, line in enumerate(discipline_lines)
        ],
        statement_block=_line_block(statement_layout, float(layout["text_x"]), statement_y),
        metadata_items=metadata_items,
        molecule={
            "box": feature_box,
            "image_frame": image_frame,
            "image_render": rendered_image,
            "image_href": f"data:image/png;base64,{molecule_data['image_base64']}",
            "label": escape(molecule_data["label"]),
            "label_pos": {"x": feature_x + feature_padding, "y": feature_label_y},
            "title_block": _line_block(feature_title_layout, feature_x + feature_padding, feature_title_y),
            "date_block": _line_block(feature_date_layout, feature_x + feature_padding, feature_date_y),
            "link_href": escape(molecule_data["article_url"]),
            "link_block": _line_block(feature_link_layout, feature_x + feature_padding, feature_link_y),
            "note_1_block": _line_block(note_layouts[0], feature_x + feature_padding, note_1_y),
            "note_2_block": _line_block(note_layouts[1], feature_x + feature_padding, note_2_y),
        },
    )

from __future__ import annotations

import base64
import re
from pathlib import Path

from defusedxml import ElementTree as DET
import yaml


EXPECTED_DIMENSIONS = {
    "hero-light.svg": {"width": 1000.0, "min_height": 360.0},
    "hero-dark.svg": {"width": 1000.0, "min_height": 360.0},
    "hero-mobile-light.svg": {"width": 390.0, "min_height": 440.0},
    "hero-mobile-dark.svg": {"width": 390.0, "min_height": 440.0},
    "identity-light.svg": {"width": 1000.0, "min_height": 400.0},
    "identity-dark.svg": {"width": 1000.0, "min_height": 400.0},
    "identity-mobile-light.svg": {"width": 390.0, "min_height": 680.0},
    "identity-mobile-dark.svg": {"width": 390.0, "min_height": 680.0},
    "featured-work-light.svg": {"width": 1000.0, "min_height": 400.0},
    "featured-work-dark.svg": {"width": 1000.0, "min_height": 400.0},
    "featured-work-mobile-light.svg": {"width": 390.0, "min_height": 720.0},
    "featured-work-mobile-dark.svg": {"width": 390.0, "min_height": 720.0},
    "signal-path-light.svg": {"width": 1000.0, "min_height": 300.0},
    "signal-path-dark.svg": {"width": 1000.0, "min_height": 300.0},
    "signal-path-mobile-light.svg": {"width": 390.0, "min_height": 700.0},
    "signal-path-mobile-dark.svg": {"width": 390.0, "min_height": 700.0},
    "skills-light.svg": {"width": 1000.0, "min_height": 340.0},
    "skills-dark.svg": {"width": 1000.0, "min_height": 340.0},
    "skills-mobile-light.svg": {"width": 390.0, "min_height": 500.0},
    "skills-mobile-dark.svg": {"width": 390.0, "min_height": 500.0},
    "timeline-light.svg": {"width": 1000.0, "min_height": 560.0},
    "timeline-dark.svg": {"width": 1000.0, "min_height": 560.0},
    "timeline-mobile-light.svg": {"width": 390.0, "min_height": 600.0},
    "timeline-mobile-dark.svg": {"width": 390.0, "min_height": 600.0},
    "contact-light.svg": {"width": 1000.0, "min_height": 280.0},
    "contact-dark.svg": {"width": 1000.0, "min_height": 280.0},
    "contact-mobile-light.svg": {"width": 390.0, "min_height": 340.0},
    "contact-mobile-dark.svg": {"width": 390.0, "min_height": 340.0},
}


def extract_woff2_payload(svg_text: str) -> bytes:
    match = re.search(r"data:font/woff2;base64,([A-Za-z0-9+/=]+)", svg_text)
    assert match is not None
    payload = base64.b64decode(match.group(1), validate=True)
    assert len(payload) > 100
    return payload


def generated_svg_paths(built_profile: Path) -> list[Path]:
    return sorted((built_profile / "assets/generated").glob("*.svg"))


def parse_viewbox(root) -> tuple[float, float]:
    _, _, width, height = [float(value) for value in root.attrib["viewBox"].split()]
    return width, height


def test_generated_svgs_are_valid(built_profile) -> None:
    for path in generated_svg_paths(built_profile):
        text = path.read_text(encoding="utf-8")
        assert "<script" not in text
        sanitized = text.replace("http://www.w3.org/2000/svg", "")
        assert "http://" not in sanitized
        assert "fonts.googleapis.com" not in sanitized
        assert "fonts.gstatic.com" not in sanitized
        assert "@import" not in sanitized
        assert "{{" not in text and "}}" not in text
        root = DET.fromstring(text)
        assert root.tag.endswith("svg")


def test_generated_viewboxes(built_profile) -> None:
    for filename, expected in EXPECTED_DIMENSIONS.items():
        root = DET.fromstring((built_profile / "assets/generated" / filename).read_text(encoding="utf-8"))
        width, height = parse_viewbox(root)
        assert width == expected["width"]
        assert height >= expected["min_height"]


def test_widget_variants_are_generated(built_profile) -> None:
    for filename in EXPECTED_DIMENSIONS:
        assert (built_profile / "assets/generated" / filename).exists()


def test_display_assets_embed_custom_font(built_profile) -> None:
    sampled_assets = [
        "hero-light.svg",
        "identity-light.svg",
        "featured-work-light.svg",
        "signal-path-light.svg",
        "skills-light.svg",
        "timeline-light.svg",
        "contact-light.svg",
    ]
    for filename in sampled_assets:
        text = (built_profile / "assets/generated" / filename).read_text(encoding="utf-8")
        assert "@font-face" in text
        assert 'font-family: "Atlas Display"' in text or 'font-family: "Atlas Body Semibold"' in text
        assert 'font-family: "Atlas Body"' in text or 'font-family: "Atlas Body Semibold"' in text
        assert 'font-family: "Atlas Mono"' in text
        assert "data:font/woff2;base64," in text


def test_embedded_payload_is_valid_woff2(built_profile) -> None:
    for filename in ("hero-light.svg", "identity-light.svg", "featured-work-light.svg"):
        payload = extract_woff2_payload((built_profile / "assets/generated" / filename).read_text(encoding="utf-8"))
        assert payload[:4] == b"wOF2"


def test_generated_assets_do_not_contain_removed_phrases(built_profile) -> None:
    forbidden = ("ATLAS FIELD GUIDE", "DECORATIVE TRACE")
    for path in generated_svg_paths(built_profile):
        text = path.read_text(encoding="utf-8").upper()
        for phrase in forbidden:
            assert phrase not in text


def test_hero_labels_and_scientific_line_are_intact(built_profile) -> None:
    for filename in ("hero-light.svg", "hero-mobile-light.svg"):
        text = (built_profile / "assets/generated" / filename).read_text(encoding="utf-8")
        assert "Johns Hopkins University" in text
        assert "Molecule of the Month" in text
        assert "Original article" in text
        assert "CC BY 4.0" in text
        assert "Chemical &amp; Biomolecular Engineering" in text or "Chemical & Biomolecular Engineering" in text
        assert "Scientific Computing • Biosecurity" in text or "Scientific Computing &bull; Biosecurity" in text
        assert ">CIENTIFIC<" not in text
        assert ">OMPUTING<" not in text


def test_mobile_cards_are_taller_than_previous_layout(built_profile) -> None:
    hero_mobile = DET.fromstring((built_profile / "assets/generated/hero-mobile-light.svg").read_text(encoding="utf-8"))
    assert float(hero_mobile.attrib["viewBox"].split()[3]) > 300


def test_hero_embeds_molecule_image_and_clip_path(built_profile) -> None:
    hero = (built_profile / "assets/generated/hero-light.svg").read_text(encoding="utf-8")
    assert 'clipPath id="feature-image-clip"' in hero
    assert "data:image/png;base64," in hero
    assert "Image resized from the original TIFF." in hero or "Image used from the original TIFF without cropping." in hero


def test_geometry_tokens_are_centralized(repo_root) -> None:
    tokens = yaml.safe_load((repo_root / "design/tokens.yml").read_text(encoding="utf-8"))
    hero_desktop = tokens["layout"]["hero"]["desktop"]
    hero_mobile = tokens["layout"]["hero"]["mobile"]
    assert {"text_x", "text_width", "media_x", "media_width"} <= set(hero_desktop)
    assert {"text_x", "text_width", "media_x", "media_width"} <= set(hero_mobile)


def test_fallback_build_remains_valid(fallback_built_profile) -> None:
    for filename in ("hero-light.svg", "hero-mobile-light.svg", "identity-light.svg", "featured-work-light.svg"):
        text = (fallback_built_profile / "assets/generated" / filename).read_text(encoding="utf-8")
        assert "Atlas Display" in text
        assert "@font-face" not in text
        assert "data:font/woff2" not in text
        root = DET.fromstring(text)
        assert root.tag.endswith("svg")


def test_generated_assets_have_no_absolute_paths(built_profile) -> None:
    for path in generated_svg_paths(built_profile):
        assert "/Users/" not in path.read_text(encoding="utf-8")


def test_text_coordinates_stay_inside_viewboxes(built_profile) -> None:
    for filename in EXPECTED_DIMENSIONS:
        path = built_profile / "assets/generated" / filename
        root = DET.fromstring(path.read_text(encoding="utf-8"))
        width, height = parse_viewbox(root)
        for element in root.findall(".//{http://www.w3.org/2000/svg}text"):
            x = float(element.attrib.get("x", "0"))
            y = float(element.attrib.get("y", "0"))
            assert 0 <= x <= width
            assert 0 <= y <= height


def test_signal_path_uses_fixed_size_markers_and_container_ids(built_profile) -> None:
    text = (built_profile / "assets/generated/signal-path-light.svg").read_text(encoding="utf-8")
    assert 'markerUnits="userSpaceOnUse"' in text
    assert 'vector-effect="non-scaling-stroke"' in text
    assert 'data-container-id="signal-box-0"' in text

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from defusedxml import ElementTree as DET

from scripts.common import DATA_DIR, load_tokens, load_yaml
from scripts.layout.text import TextStyle, wrap_text
from scripts.render_widgets import render_featured_work


def test_wrap_text_preserves_word_boundaries_and_newlines() -> None:
    style = TextStyle(
        font_path=Path("design/fonts/SourceSerif4-Regular.ttf"),
        font_size=14,
        font_weight=400,
        line_height=19,
        min_font_size=12,
    )
    layout = wrap_text("Scientific Computing\nBiosecurity Systems", style, max_width=120)
    lines = [line.text for line in layout.lines]
    assert "Scientific" in lines
    assert "Computing" in lines
    assert "Biosecurity" in lines
    assert "Systems" in lines
    assert all(part not in {"S", "CIENTIFIC", "COMPUT", "ING"} for part in lines)


def test_featured_work_height_grows_with_longer_copy() -> None:
    profile = load_yaml(DATA_DIR / "profile.yml")
    tokens = load_tokens()
    baseline_svg = render_featured_work(profile, tokens, "light", None, viewport="mobile")
    baseline_height = float(DET.fromstring(baseline_svg).attrib["viewBox"].split()[3])

    stressed = deepcopy(profile)
    stressed["featured_projects"][1]["title"] = "Biosecurity Evidence Pipeline for Sequence Provenance Mapping"
    stressed["featured_projects"][1]["description"] = (
        "Structured collection of sequence relationships, provenance, laboratory context, "
        "screening annotations, and risk-relevant evidence for safer science analysis "
        "that still needs to remain readable in a single mobile card."
    )
    stressed_svg = render_featured_work(stressed, tokens, "light", None, viewport="mobile")
    stressed_height = float(DET.fromstring(stressed_svg).attrib["viewBox"].split()[3])

    assert stressed_height > baseline_height
    assert "Biosecurity Evidence Pipeline" in stressed_svg
    assert "Sequence Provenance" in stressed_svg
    assert "Mapping" in stressed_svg


def test_featured_work_repository_can_wrap_to_second_line() -> None:
    profile = load_yaml(DATA_DIR / "profile.yml")
    tokens = load_tokens()
    stressed = deepcopy(profile)
    stressed["featured_projects"][0]["repository"] = "isabela-lafleur/really-long-repository_name-for-layout-testing"

    svg = render_featured_work(stressed, tokens, "light", None, viewport="desktop")
    assert "isabela-lafleur/" in svg
    assert "really-long-repository_name-for-layout-testing" in svg

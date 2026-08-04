from __future__ import annotations

from scripts.sections import enabled_readme_sections, load_section_config


def test_readme_is_widget_based_and_generated(built_profile) -> None:
    readme = (built_profile / "README.md").read_text(encoding="utf-8")
    assert readme.startswith("<!-- Generated file.")

    asset_map = {
        "hero": "./assets/generated/hero-light.svg",
        "identity": "./assets/generated/identity-light.svg",
        "featured_work": "./assets/generated/featured-work-light.svg",
        "signal_path": "./assets/generated/signal-path-light.svg",
        "skills": "./assets/generated/skills-light.svg",
        "timeline": "./assets/generated/timeline-light.svg",
        "contact": "./assets/generated/contact-light.svg",
    }
    for section in enabled_readme_sections(load_section_config()):
        asset = asset_map.get(section)
        if asset is None:
            continue
        assert asset in readme

    assert "## Research Identity" not in readme
    assert "## Featured Work" not in readme
    assert "## Field Chronicle" not in readme


def test_readme_uses_theme_aware_picture_elements_for_widgets(built_profile) -> None:
    readme = (built_profile / "README.md").read_text(encoding="utf-8")
    assert "./assets/generated/hero-mobile-dark.svg" in readme
    assert "./assets/generated/featured-work-mobile-dark.svg" in readme
    assert "./assets/generated/contact-mobile-dark.svg" in readme
    assert "(max-width: 600px)" in readme


def test_readme_preserves_accessible_real_text_links(built_profile) -> None:
    readme = (built_profile / "README.md").read_text(encoding="utf-8")
    assert "Automated XRD Analysis" in readme
    assert "Biosecurity Evidence Pipeline" in readme
    assert "Clinical Workflow Automation" in readme
    assert '<a href="https://github.com/isabela-lafleur">GitHub</a>' in readme
    assert "> **Baltimore, MD / New York, NY**" in readme

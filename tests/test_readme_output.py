from __future__ import annotations


def test_readme_is_widget_based_and_generated(built_profile) -> None:
    readme = (built_profile / "README.md").read_text(encoding="utf-8")
    assert readme.startswith("<!-- Generated file.")
    for asset in (
        "./assets/generated/hero-light.svg",
        "./assets/generated/identity-light.svg",
        "./assets/generated/featured-work-light.svg",
        "./assets/generated/signal-path-light.svg",
        "./assets/generated/skills-light.svg",
        "./assets/generated/timeline-light.svg",
        "./assets/generated/contact-light.svg",
    ):
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

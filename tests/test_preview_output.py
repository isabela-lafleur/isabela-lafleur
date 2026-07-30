from __future__ import annotations


def test_preview_sections_are_preserved_and_extended(built_profile) -> None:
    preview_index = (built_profile / "preview/index.html").read_text(encoding="utf-8")
    required = [
        "Profile Preview",
        "README picture element",
        "Hero variants",
        "Narrow-width asset preview",
        "Widget gallery",
        "Complete README preview",
        "Desktop README",
        "Mobile README",
    ]
    for section in required:
        assert section in preview_index


def test_generated_readme_preview_documents_exist_and_match_widget_readme(built_profile) -> None:
    readme = (built_profile / "README.md").read_text(encoding="utf-8")
    assert "./assets/generated/identity-light.svg" in readme
    for name in ("readme-light.html", "readme-dark.html", "readme-system.html"):
        text = (built_profile / "preview/generated" / name).read_text(encoding="utf-8")
        assert "<base href=\"../../\">" in text
        assert "GitHub Profile README Preview" in text
        assert "Atlas Field Guide" not in text
        assert "featured-work-light.svg" in text or "featured-work-dark.svg" in text
        assert "timeline-light.svg" in text or "timeline-dark.svg" in text


def test_preview_uses_mobile_and_desktop_frames_with_theme_control_hooks(built_profile) -> None:
    preview_index = (built_profile / "preview/index.html").read_text(encoding="utf-8")
    assert 'data-readme-frame="desktop"' in preview_index
    assert 'data-readme-frame="mobile"' in preview_index
    assert "readme-light.html" in preview_index
    assert "readme-dark.html" in preview_index
    assert "readme-system.html" in preview_index
    assert "identity-mobile-light.svg" in preview_index
    assert "featured-work-mobile-light.svg" in preview_index
    assert "overflow-x: clip;" in preview_index


def test_theme_specific_preview_documents_select_correct_assets(built_profile) -> None:
    light_doc = (built_profile / "preview/generated/readme-light.html").read_text(encoding="utf-8")
    dark_doc = (built_profile / "preview/generated/readme-dark.html").read_text(encoding="utf-8")
    system_doc = (built_profile / "preview/generated/readme-system.html").read_text(encoding="utf-8")

    assert "hero-mobile-light.svg" in light_doc
    assert "featured-work-mobile-light.svg" in light_doc
    assert "hero-mobile-dark.svg" not in light_doc
    assert "hero-mobile-dark.svg" in dark_doc
    assert "featured-work-mobile-dark.svg" in dark_doc
    assert "prefers-color-scheme: dark" in system_doc

from __future__ import annotations

from scripts.sections import default_section_config, enabled_readme_sections, numbered_section_labels


def test_numbered_sections_shift_when_a_numbered_widget_is_disabled() -> None:
    config = default_section_config()
    config["featured_work"] = False
    labels = numbered_section_labels(config)

    assert labels["identity"] == "01 / Research Identity"
    assert labels["signal_path"] == "02 / Signal Path"
    assert labels["skills"] == "03 / Tools and Methods"
    assert labels["timeline"] == "04 / Field Chronicle"
    assert labels["contact"] == "05 / Contact"


def test_non_numbered_sections_do_not_affect_numbered_widget_labels() -> None:
    config = default_section_config()
    config["hero"] = False
    config["intro"] = False
    labels = numbered_section_labels(config)

    assert labels["identity"] == "01 / Research Identity"
    assert labels["featured_work"] == "02 / Featured Work"
    assert labels["signal_path"] == "03 / Signal Path"


def test_enabled_readme_sections_follow_config_order() -> None:
    config = default_section_config()
    config["intro"] = False
    config["skills"] = False

    assert enabled_readme_sections(config) == [
        "hero",
        "identity",
        "featured_work",
        "signal_path",
        "timeline",
        "contact",
    ]

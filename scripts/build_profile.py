from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.common import (
    DATA_DIR,
    GENERATED_ASSET_DIR,
    GENERATED_DATA_DIR,
    GENERATED_PREVIEW_DIR,
    TEMPLATE_DIR,
    collect_placeholders,
    ensure_directories,
    infer_github_username,
    load_tokens,
    load_yaml,
    validate_profile,
    with_project_urls,
    write_json,
    write_text,
)
from scripts.fetch_molecule_of_month import fetch_molecule_of_the_month
from scripts.render_hero import render_hero
from scripts.render_preview import render_preview_documents
from scripts.render_widgets import (
    render_contact,
    render_featured_work,
    render_identity,
    render_signal_path,
    render_skills,
    render_timeline,
)
from scripts.sections import enabled_readme_sections, load_section_config, numbered_section_labels


def validate_svg(path: Path, expected_width: float, minimum_height: float = 120.0) -> dict[str, float]:
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    viewbox = root.attrib.get("viewBox", "")
    parts = viewbox.split()
    if len(parts) != 4:
        raise ValueError(f"{path.name} has invalid viewBox: {viewbox!r}")
    _, _, width, height = [float(value) for value in parts]
    if abs(width - expected_width) > 0.01:
        raise ValueError(f"{path.name} has incorrect viewBox width: {width}")
    if height < minimum_height:
        raise ValueError(f"{path.name} has unexpectedly small viewBox height: {height}")
    if root.findall(".//{http://www.w3.org/2000/svg}script"):
        raise ValueError(f"{path.name} contains disallowed script elements.")
    return {"width": width, "height": height}


STALE_GENERATED_FILES = (
    GENERATED_ASSET_DIR / "activity-light.svg",
    GENERATED_ASSET_DIR / "activity-dark.svg",
    GENERATED_ASSET_DIR / "activity-mobile-light.svg",
    GENERATED_ASSET_DIR / "activity-mobile-dark.svg",
    GENERATED_DATA_DIR / "github_activity.json",
)


def render_readme(profile_data: dict, mobile_breakpoint: int, section_config: dict[str, bool]) -> str:
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=False, trim_blocks=True, lstrip_blocks=True)
    template = env.get_template("README.md.j2")

    placeholders = collect_placeholders(profile_data)
    contact_links = [link for link in profile_data["contact"]["links"] if link.get("url")]
    featured_projects = with_project_urls(profile_data)
    hero_alt = f"{profile_data['profile']['name']} introductory hero with an RCSB PDB-101 Molecule of the Month feature."

    return template.render(
        profile=profile_data,
        featured_projects=featured_projects,
        contact_links=contact_links,
        placeholders=placeholders,
        hero_alt=hero_alt,
        mobile_breakpoint=mobile_breakpoint,
        enabled_sections=set(enabled_readme_sections(section_config)),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the GitHub profile README and generated SVG assets.")
    parser.add_argument("--offline", action="store_true", help="Reuse cached generated data when available.")
    parser.add_argument(
        "--disable-custom-font",
        action="store_true",
        help="Build the hero using fallback fonts only.",
    )
    parser.add_argument(
        "--debug-layout",
        action="store_true",
        help="Write computed SVG viewBox metadata to assets/generated/layout-debug.json.",
    )
    args = parser.parse_args()

    ensure_directories()

    profile_path = DATA_DIR / "profile.yml"
    profile_data = load_yaml(profile_path)
    profile_data["profile"]["github_username"] = infer_github_username(
        profile_data.get("profile", {}).get("github_username")
    )

    errors = validate_profile(profile_data)
    if errors:
        raise ValueError("Profile validation failed:\n- " + "\n- ".join(errors))

    tokens = load_tokens()
    section_config = load_section_config()
    section_labels = numbered_section_labels(section_config)
    mobile_breakpoint = int(tokens["meta"]["mobile_breakpoint"])
    font_data_b64 = None if args.disable_custom_font else "embedded-fonts"

    molecule_data = fetch_molecule_of_the_month(
        profile_data.get("hero", {}).get("molecule_of_the_month", {}),
        offline=args.offline,
    )

    hero_light = render_hero(profile_data, tokens, "light", font_data_b64, molecule_data, viewport="desktop")
    hero_dark = render_hero(profile_data, tokens, "dark", font_data_b64, molecule_data, viewport="desktop")
    hero_mobile_light = render_hero(profile_data, tokens, "light", font_data_b64, molecule_data, viewport="mobile")
    hero_mobile_dark = render_hero(profile_data, tokens, "dark", font_data_b64, molecule_data, viewport="mobile")
    identity_light = render_identity(
        profile_data,
        tokens,
        "light",
        font_data_b64,
        viewport="desktop",
        section_label=section_labels["identity"],
    )
    identity_dark = render_identity(
        profile_data,
        tokens,
        "dark",
        font_data_b64,
        viewport="desktop",
        section_label=section_labels["identity"],
    )
    identity_mobile_light = render_identity(
        profile_data,
        tokens,
        "light",
        font_data_b64,
        viewport="mobile",
        section_label=section_labels["identity"],
    )
    identity_mobile_dark = render_identity(
        profile_data,
        tokens,
        "dark",
        font_data_b64,
        viewport="mobile",
        section_label=section_labels["identity"],
    )
    featured_work_light = render_featured_work(
        profile_data,
        tokens,
        "light",
        font_data_b64,
        viewport="desktop",
        section_label=section_labels["featured_work"],
    )
    featured_work_dark = render_featured_work(
        profile_data,
        tokens,
        "dark",
        font_data_b64,
        viewport="desktop",
        section_label=section_labels["featured_work"],
    )
    featured_work_mobile_light = render_featured_work(
        profile_data,
        tokens,
        "light",
        font_data_b64,
        viewport="mobile",
        section_label=section_labels["featured_work"],
    )
    featured_work_mobile_dark = render_featured_work(
        profile_data,
        tokens,
        "dark",
        font_data_b64,
        viewport="mobile",
        section_label=section_labels["featured_work"],
    )
    signal_path_light = render_signal_path(
        profile_data,
        tokens,
        "light",
        font_data_b64,
        viewport="desktop",
        section_label=section_labels["signal_path"],
    )
    signal_path_dark = render_signal_path(
        profile_data,
        tokens,
        "dark",
        font_data_b64,
        viewport="desktop",
        section_label=section_labels["signal_path"],
    )
    signal_path_mobile_light = render_signal_path(
        profile_data,
        tokens,
        "light",
        font_data_b64,
        viewport="mobile",
        section_label=section_labels["signal_path"],
    )
    signal_path_mobile_dark = render_signal_path(
        profile_data,
        tokens,
        "dark",
        font_data_b64,
        viewport="mobile",
        section_label=section_labels["signal_path"],
    )
    skills_light = render_skills(
        profile_data,
        tokens,
        "light",
        font_data_b64,
        viewport="desktop",
        section_label=section_labels["skills"],
    )
    skills_dark = render_skills(
        profile_data,
        tokens,
        "dark",
        font_data_b64,
        viewport="desktop",
        section_label=section_labels["skills"],
    )
    skills_mobile_light = render_skills(
        profile_data,
        tokens,
        "light",
        font_data_b64,
        viewport="mobile",
        section_label=section_labels["skills"],
    )
    skills_mobile_dark = render_skills(
        profile_data,
        tokens,
        "dark",
        font_data_b64,
        viewport="mobile",
        section_label=section_labels["skills"],
    )
    timeline_light = render_timeline(
        profile_data,
        tokens,
        "light",
        font_data_b64,
        viewport="desktop",
        section_label=section_labels["timeline"],
    )
    timeline_dark = render_timeline(
        profile_data,
        tokens,
        "dark",
        font_data_b64,
        viewport="desktop",
        section_label=section_labels["timeline"],
    )
    timeline_mobile_light = render_timeline(
        profile_data,
        tokens,
        "light",
        font_data_b64,
        viewport="mobile",
        section_label=section_labels["timeline"],
    )
    timeline_mobile_dark = render_timeline(
        profile_data,
        tokens,
        "dark",
        font_data_b64,
        viewport="mobile",
        section_label=section_labels["timeline"],
    )
    contact_light = render_contact(
        profile_data,
        tokens,
        "light",
        font_data_b64,
        viewport="desktop",
        section_label=section_labels["contact"],
    )
    contact_dark = render_contact(
        profile_data,
        tokens,
        "dark",
        font_data_b64,
        viewport="desktop",
        section_label=section_labels["contact"],
    )
    contact_mobile_light = render_contact(
        profile_data,
        tokens,
        "light",
        font_data_b64,
        viewport="mobile",
        section_label=section_labels["contact"],
    )
    contact_mobile_dark = render_contact(
        profile_data,
        tokens,
        "dark",
        font_data_b64,
        viewport="mobile",
        section_label=section_labels["contact"],
    )
    readme = render_readme(profile_data, mobile_breakpoint, section_config)
    preview_documents = render_preview_documents(readme, tokens)

    write_text(GENERATED_ASSET_DIR / "hero-light.svg", hero_light)
    write_text(GENERATED_ASSET_DIR / "hero-dark.svg", hero_dark)
    write_text(GENERATED_ASSET_DIR / "hero-mobile-light.svg", hero_mobile_light)
    write_text(GENERATED_ASSET_DIR / "hero-mobile-dark.svg", hero_mobile_dark)
    write_text(GENERATED_ASSET_DIR / "identity-light.svg", identity_light)
    write_text(GENERATED_ASSET_DIR / "identity-dark.svg", identity_dark)
    write_text(GENERATED_ASSET_DIR / "identity-mobile-light.svg", identity_mobile_light)
    write_text(GENERATED_ASSET_DIR / "identity-mobile-dark.svg", identity_mobile_dark)
    write_text(GENERATED_ASSET_DIR / "featured-work-light.svg", featured_work_light)
    write_text(GENERATED_ASSET_DIR / "featured-work-dark.svg", featured_work_dark)
    write_text(GENERATED_ASSET_DIR / "featured-work-mobile-light.svg", featured_work_mobile_light)
    write_text(GENERATED_ASSET_DIR / "featured-work-mobile-dark.svg", featured_work_mobile_dark)
    write_text(GENERATED_ASSET_DIR / "signal-path-light.svg", signal_path_light)
    write_text(GENERATED_ASSET_DIR / "signal-path-dark.svg", signal_path_dark)
    write_text(GENERATED_ASSET_DIR / "signal-path-mobile-light.svg", signal_path_mobile_light)
    write_text(GENERATED_ASSET_DIR / "signal-path-mobile-dark.svg", signal_path_mobile_dark)
    write_text(GENERATED_ASSET_DIR / "skills-light.svg", skills_light)
    write_text(GENERATED_ASSET_DIR / "skills-dark.svg", skills_dark)
    write_text(GENERATED_ASSET_DIR / "skills-mobile-light.svg", skills_mobile_light)
    write_text(GENERATED_ASSET_DIR / "skills-mobile-dark.svg", skills_mobile_dark)
    write_text(GENERATED_ASSET_DIR / "timeline-light.svg", timeline_light)
    write_text(GENERATED_ASSET_DIR / "timeline-dark.svg", timeline_dark)
    write_text(GENERATED_ASSET_DIR / "timeline-mobile-light.svg", timeline_mobile_light)
    write_text(GENERATED_ASSET_DIR / "timeline-mobile-dark.svg", timeline_mobile_dark)
    write_text(GENERATED_ASSET_DIR / "contact-light.svg", contact_light)
    write_text(GENERATED_ASSET_DIR / "contact-dark.svg", contact_dark)
    write_text(GENERATED_ASSET_DIR / "contact-mobile-light.svg", contact_mobile_light)
    write_text(GENERATED_ASSET_DIR / "contact-mobile-dark.svg", contact_mobile_dark)
    write_text(GENERATED_PREVIEW_DIR / "readme-light.html", preview_documents["light"])
    write_text(GENERATED_PREVIEW_DIR / "readme-dark.html", preview_documents["dark"])
    write_text(GENERATED_PREVIEW_DIR / "readme-system.html", preview_documents["system"])
    write_text(ROOT / "README.md", readme)
    for stale_file in STALE_GENERATED_FILES:
        stale_file.unlink(missing_ok=True)

    expected_widths = {
        "hero-light.svg": 1000.0,
        "hero-dark.svg": 1000.0,
        "hero-mobile-light.svg": 390.0,
        "hero-mobile-dark.svg": 390.0,
        "identity-light.svg": 1000.0,
        "identity-dark.svg": 1000.0,
        "identity-mobile-light.svg": 390.0,
        "identity-mobile-dark.svg": 390.0,
        "featured-work-light.svg": 1000.0,
        "featured-work-dark.svg": 1000.0,
        "featured-work-mobile-light.svg": 390.0,
        "featured-work-mobile-dark.svg": 390.0,
        "signal-path-light.svg": 1000.0,
        "signal-path-dark.svg": 1000.0,
        "signal-path-mobile-light.svg": 390.0,
        "signal-path-mobile-dark.svg": 390.0,
        "skills-light.svg": 1000.0,
        "skills-dark.svg": 1000.0,
        "skills-mobile-light.svg": 390.0,
        "skills-mobile-dark.svg": 390.0,
        "timeline-light.svg": 1000.0,
        "timeline-dark.svg": 1000.0,
        "timeline-mobile-light.svg": 390.0,
        "timeline-mobile-dark.svg": 390.0,
        "contact-light.svg": 1000.0,
        "contact-dark.svg": 1000.0,
        "contact-mobile-light.svg": 390.0,
        "contact-mobile-dark.svg": 390.0,
    }
    layout_debug: dict[str, dict[str, float]] = {}
    for filename, expected_width in expected_widths.items():
        layout_debug[filename] = validate_svg(GENERATED_ASSET_DIR / filename, expected_width)
    if args.debug_layout:
        write_json(GENERATED_ASSET_DIR / "layout-debug.json", layout_debug)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

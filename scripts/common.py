from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from dataclasses import dataclass

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
GENERATED_DATA_DIR = DATA_DIR / "generated"
DESIGN_DIR = ROOT / "design"
TEMPLATE_DIR = ROOT / "templates"
ASSET_DIR = ROOT / "assets"
GENERATED_ASSET_DIR = ASSET_DIR / "generated"
PREVIEW_DIR = ROOT / "preview"
GENERATED_PREVIEW_DIR = PREVIEW_DIR / "generated"


@dataclass(frozen=True)
class FontSource:
    css_family: str
    source_path: Path
    weight: int
    style: str = "normal"


DISPLAY_FONT = FontSource(
    css_family="Atlas Display",
    source_path=DESIGN_DIR / "fonts" / "PlayfairDisplay-SemiBold.ttf",
    weight=600,
)
BODY_FONT = FontSource(
    css_family="Atlas Body",
    source_path=DESIGN_DIR / "fonts" / "SourceSerif4-Regular.ttf",
    weight=400,
)
BODY_SEMIBOLD_FONT = FontSource(
    css_family="Atlas Body Semibold",
    source_path=DESIGN_DIR / "fonts" / "SourceSerif4-Semibold.ttf",
    weight=600,
)
MONO_FONT = FontSource(
    css_family="Atlas Mono",
    source_path=DESIGN_DIR / "fonts" / "IBMPlexMono-Medium.ttf",
    weight=500,
)

PROJECT_MOTIFS = {"diffraction", "network", "workflow", "structure"}
ICON_NAMES = {
    "flask",
    "code",
    "shield",
    "workflow",
    "sample",
    "measure",
    "compute",
    "understand",
    "protect",
}
PLACEHOLDER_VALUES = {"", "YOUR_GITHUB_USERNAME"}


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a top-level mapping.")
    return data


def load_tokens() -> dict[str, Any]:
    return load_yaml(DESIGN_DIR / "tokens.yml")


def ensure_directories() -> None:
    GENERATED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_ASSET_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_PREVIEW_DIR.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = content.rstrip() + "\n"
    path.write_text(normalized, encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def is_valid_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def git_remote_url() -> str:
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""
    return result.stdout.strip()


def infer_github_username(configured: str | None = None) -> str:
    if configured and configured not in PLACEHOLDER_VALUES:
        return configured

    remote = git_remote_url()
    match = re.search(r"github\.com[:/]([^/]+)/([^/.]+)(?:\.git)?$", remote)
    if not match:
        raise ValueError("Unable to infer GitHub username from data/profile.yml or git remote.")

    owner, repo = match.group(1), match.group(2)
    return repo if owner == repo else owner


def validate_profile(profile_data: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    required_sections = [
        "profile",
        "hero",
        "intro",
        "focus_areas",
        "featured_projects",
        "signal_path",
        "skills",
        "timeline",
        "contact",
    ]
    for section in required_sections:
        if section not in profile_data:
            errors.append(f"Missing required section: {section}")

    profile = profile_data.get("profile", {})
    if not profile.get("name"):
        errors.append("profile.name is required.")

    molecule_config = profile_data.get("hero", {}).get("molecule_of_the_month", {})
    if molecule_config:
        mode = str(molecule_config.get("mode", "auto")).strip().lower()
        if mode not in {"auto", "fixed"}:
            errors.append("hero.molecule_of_the_month.mode must be either 'auto' or 'fixed'.")
        if mode == "fixed" and molecule_config.get("article_id") in (None, ""):
            errors.append("hero.molecule_of_the_month.article_id is required when mode is 'fixed'.")

    project_ids: set[str] = set()
    for project in profile_data.get("featured_projects", []):
        if not project.get("title"):
            errors.append("featured_projects entries must include a nonempty title.")
        if not isinstance(project.get("topics", []), list) or any(
            not isinstance(topic, str) or not topic.strip()
            for topic in project.get("topics", [])
        ):
            errors.append(f"{project.get('title', 'Unnamed project')} has invalid topics.")
        motif = project.get("motif")
        if motif not in PROJECT_MOTIFS:
            errors.append(f"Unknown featured project motif: {motif}")
        project_url = project.get("url", "")
        if project_url and not is_valid_url(project_url):
            errors.append(f"Invalid project url for {project.get('title', 'Unnamed project')}: {project_url}")
        identifier = slugify(project.get("repository") or project.get("title", ""))
        if identifier in project_ids:
            errors.append(f"Duplicate featured project identifier: {identifier}")
        project_ids.add(identifier)

    for area in profile_data.get("focus_areas", []):
        if area.get("icon") not in ICON_NAMES:
            errors.append(f"Unknown focus area icon: {area.get('icon')}")

    for step in profile_data.get("signal_path", []):
        if step.get("icon") not in ICON_NAMES:
            errors.append(f"Unknown signal path icon: {step.get('icon')}")

    for item in profile_data.get("timeline", []):
        if not isinstance(item.get("year"), (str, int)):
            errors.append(f"Timeline year must be a string or integer: {item}")

    for field_name in ("linkedin", "resume_url"):
        value = profile.get(field_name, "")
        if value and not is_valid_url(value):
            errors.append(f"profile.{field_name} must be empty or a valid URL.")

    for link in profile_data.get("contact", {}).get("links", []):
        value = link.get("url", "")
        if value and not is_valid_url(value):
            errors.append(f"Contact link {link.get('label', 'unknown')} must be empty or a valid URL.")

    return errors


def collect_placeholders(profile_data: dict[str, Any]) -> list[str]:
    profile = profile_data.get("profile", {})
    placeholders: list[str] = []
    if not profile.get("email"):
        placeholders.append("profile.email")
    if not profile.get("linkedin"):
        placeholders.append("profile.linkedin")
    if not profile.get("resume_url"):
        placeholders.append("profile.resume_url")
    return placeholders


def with_project_urls(profile_data: dict[str, Any]) -> list[dict[str, Any]]:
    projects: list[dict[str, Any]] = []
    for project in profile_data.get("featured_projects", []):
        display_url = project.get("url") or f"https://github.com/{project['repository']}"
        enriched = dict(project)
        enriched["display_url"] = display_url
        projects.append(enriched)
    return projects


def display_font_strings(profile_data: dict[str, Any]) -> list[str]:
    strings = [
        profile_data["profile"]["name"],
        "Focus Areas",
        "Selected Systems",
        "Observe Measure Compute Understand Protect",
        "Technical Stack",
        "Timeline",
        "Links and Location",
    ]
    strings.extend(profile_data["hero"].get("discipline_lines", []))
    strings.extend(project.get("title", "") for project in profile_data.get("featured_projects", []))
    return strings


def all_font_sources() -> tuple[FontSource, ...]:
    return (DISPLAY_FONT, BODY_FONT, BODY_SEMIBOLD_FONT, MONO_FONT)

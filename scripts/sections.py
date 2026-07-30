from __future__ import annotations

from pathlib import Path

import yaml

from scripts.common import DATA_DIR


SECTION_ORDER = (
    "hero",
    "intro",
    "identity",
    "featured_work",
    "signal_path",
    "skills",
    "timeline",
    "contact",
)

NUMBERED_WIDGETS = (
    "identity",
    "featured_work",
    "signal_path",
    "skills",
    "timeline",
    "contact",
)

SECTION_TITLES = {
    "identity": "Research Identity",
    "featured_work": "Featured Work",
    "signal_path": "Signal Path",
    "skills": "Tools and Methods",
    "timeline": "Field Chronicle",
    "contact": "Contact",
}

SECTION_CONFIG_PATH = DATA_DIR / "sections.yml"


def normalize_section_key(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def default_section_config() -> dict[str, bool]:
    return {key: True for key in SECTION_ORDER}


def load_section_config(path: Path | None = None) -> dict[str, bool]:
    active_path = path or SECTION_CONFIG_PATH
    if not active_path.exists():
        return default_section_config()

    raw = yaml.safe_load(active_path.read_text(encoding="utf-8")) or {}
    raw_sections = raw.get("sections", raw)
    config = default_section_config()
    for key, value in raw_sections.items():
        normalized = normalize_section_key(key)
        if normalized in config:
            config[normalized] = bool(value)
    return config


def write_section_config(config: dict[str, bool], path: Path | None = None) -> None:
    active_path = path or SECTION_CONFIG_PATH
    payload = {"sections": {key: bool(config.get(key, False)) for key in SECTION_ORDER}}
    active_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def enabled_readme_sections(config: dict[str, bool]) -> list[str]:
    return [key for key in SECTION_ORDER if config.get(key, False)]


def numbered_section_labels(config: dict[str, bool]) -> dict[str, str]:
    labels: dict[str, str] = {}
    enabled_numbered = [key for key in NUMBERED_WIDGETS if config.get(key, False)]
    for index, key in enumerate(enabled_numbered, start=1):
        labels[key] = f"{index:02d} / {SECTION_TITLES[key]}"
    for index, key in enumerate(NUMBERED_WIDGETS, start=1):
        labels.setdefault(key, f"{index:02d} / {SECTION_TITLES[key]}")
    return labels

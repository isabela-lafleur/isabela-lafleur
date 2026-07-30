from __future__ import annotations

from copy import deepcopy

from scripts.common import DATA_DIR, load_yaml, validate_profile


def test_profile_data_is_valid() -> None:
    profile = load_yaml(DATA_DIR / "profile.yml")
    assert validate_profile(profile) == []


def test_duplicate_project_identifier_is_rejected() -> None:
    profile = load_yaml(DATA_DIR / "profile.yml")
    duplicate = deepcopy(profile)
    duplicate["featured_projects"].append(deepcopy(duplicate["featured_projects"][0]))
    errors = validate_profile(duplicate)
    assert any("Duplicate featured project identifier" in error for error in errors)


def test_unknown_motif_is_rejected() -> None:
    profile = load_yaml(DATA_DIR / "profile.yml")
    broken = deepcopy(profile)
    broken["featured_projects"][0]["motif"] = "unknown"
    errors = validate_profile(broken)
    assert any("Unknown featured project motif" in error for error in errors)

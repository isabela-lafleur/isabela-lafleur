from __future__ import annotations

import os
import subprocess
import sys
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return ROOT


def _build_snapshot(
    repo_root: Path,
    snapshot_dir: Path,
    *,
    disable_custom_font: bool,
) -> Path:
    env = os.environ.copy()
    env["PROFILE_BUILD_DATE"] = "2026-07-30"
    command = [sys.executable, str(repo_root / "scripts/build_profile.py"), "--offline"]
    if disable_custom_font:
        command.append("--disable-custom-font")

    subprocess.run(
        command,
        cwd=repo_root,
        env=env,
        check=True,
    )

    if snapshot_dir.exists():
        shutil.rmtree(snapshot_dir)
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(repo_root / "assets", snapshot_dir / "assets")
    shutil.copytree(repo_root / "data", snapshot_dir / "data")
    shutil.copytree(repo_root / "preview", snapshot_dir / "preview")
    shutil.copy(repo_root / "README.md", snapshot_dir / "README.md")
    return snapshot_dir


@pytest.fixture(scope="session")
def built_profile(repo_root: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    snapshot_dir = tmp_path_factory.mktemp("profile-builds") / "normal-build"
    return _build_snapshot(repo_root, snapshot_dir, disable_custom_font=False)


@pytest.fixture(scope="session")
def fallback_built_profile(repo_root: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    snapshot_dir = tmp_path_factory.mktemp("profile-builds") / "fallback-build"
    snapshot = _build_snapshot(repo_root, snapshot_dir, disable_custom_font=True)
    _build_snapshot(repo_root, tmp_path_factory.mktemp("profile-builds") / "normal-restored", disable_custom_font=False)
    return snapshot

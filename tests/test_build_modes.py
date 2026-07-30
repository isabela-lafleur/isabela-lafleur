from __future__ import annotations

import os
import subprocess
import sys


def test_normal_build_is_deterministic(repo_root) -> None:
    env = os.environ.copy()
    env["PROFILE_BUILD_DATE"] = "2026-07-30"
    command = [sys.executable, str(repo_root / "scripts/build_profile.py"), "--offline"]

    subprocess.run(command, cwd=repo_root, env=env, check=True)
    first = (repo_root / "assets/generated/hero-light.svg").read_text(encoding="utf-8")
    subprocess.run(command, cwd=repo_root, env=env, check=True)
    second = (repo_root / "assets/generated/hero-light.svg").read_text(encoding="utf-8")

    assert first == second

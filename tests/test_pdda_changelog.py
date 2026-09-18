"""Exercise the real shell checker, including a witnessed old-matcher regression."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "utils/pdda/pdda.sh"


def check(tmp_path, heading, script=SCRIPT):
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(heading + "\n")
    env = dict(os.environ, PDDA_REPO_ROOT=str(tmp_path), PDDA_CHANGELOG=str(changelog),
               PDDA_MODE="observe", PDDA_FORMAT="text", PDDA_ACTIVITY_LOG=str(tmp_path / "activity.jsonl"))
    result = subprocess.run(["bash", str(script), "changelog"], env=env,
                            capture_output=True, text=True, check=True)
    return result.stdout


@pytest.mark.parametrize("heading", ["## 2026-09-17", "## [2.0.12] - 2026-09-17",
    "## 2.0.12 - 2026-09-17", "## 2.0.12.1 - 2026-09-17",
    "## 2.0.12 – 2026-09-17", "## [2020-01-01] - 2026-09-17"])
def test_supported_headings(tmp_path, heading):
    assert "WARN" not in check(tmp_path, heading)


@pytest.mark.parametrize("heading", ["## Notes", "## 2026-02-30"])
def test_invalid_headings_warn(tmp_path, heading):
    assert "WARN" in check(tmp_path, heading)


def test_old_matcher_witnessed_red(tmp_path):
    source = SCRIPT.read_text().splitlines()
    matches = [i for i, line in enumerate(source) if line.startswith("  cl_line=")]
    assert len(matches) == 1
    source[matches[0]] = r'''  cl_line="$(grep -Em1 '^##[[:space:]]+(\[[^][]*\][[:space:]]*[-–][[:space:]]*)?[0-9]{4}-[0-9]{2}-[0-9]{2}' "$PDDA_CHANGELOG" 2>/dev/null || true)"'''
    mutated = tmp_path / "pdda.sh"
    mutated.write_text("\n".join(source) + "\n")
    shutil.copyfile(SCRIPT.with_name("pdda-lib.sh"), tmp_path / "pdda-lib.sh")
    assert "WARN" in check(tmp_path, "## 2.0.12 - 2026-09-17", mutated)
    assert "WARN" not in check(tmp_path, "## 2.0.12 - 2026-09-17")

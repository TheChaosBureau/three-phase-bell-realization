from __future__ import annotations

import json
import os
import platform
from pathlib import Path
import subprocess
import sys
from importlib import metadata

import allure
import matplotlib
import matplotlib.pyplot as plt
import pytest

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ALLURE_RESULTS_DIR = ROOT / "artifacts" / "tests" / "allure-results"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

matplotlib.use("Agg")


def _sh(*args: str) -> str:
    try:
        return subprocess.check_output(
            args,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return ""


def _git_info() -> dict[str, str]:
    repo_root = _sh("git", "rev-parse", "--show-toplevel")
    if not repo_root:
        return {}

    return {
        "git.repo_root": repo_root,
        "git.remote": _sh("git", "remote", "get-url", "origin"),
        "git.branch": _sh("git", "rev-parse", "--abbrev-ref", "HEAD"),
        "git.sha": _sh("git", "rev-parse", "HEAD"),
        "git.short_sha": _sh("git", "rev-parse", "--short", "HEAD"),
        "git.tag": _sh("git", "describe", "--tags", "--exact-match"),
        "git.describe": _sh("git", "describe", "--tags", "--dirty", "--always"),
        "git.dirty": "true" if _sh("git", "status", "--porcelain") else "false",
    }


def _runtime_info() -> dict[str, str]:
    info = {
        "python.version": sys.version.split()[0],
        "python.implementation": platform.python_implementation(),
        "os": platform.system(),
        "os.release": platform.release(),
        "os.machine": platform.machine(),
    }
    for package_name, key in (
        ("pytest", "pytest"),
        ("allure-pytest", "allure-pytest"),
    ):
        try:
            info[key] = metadata.version(package_name)
        except metadata.PackageNotFoundError:
            continue
    return info


def _ci_info() -> dict[str, str]:
    env = os.environ
    if env.get("GITHUB_ACTIONS") != "true":
        return {}
    return {
        "ci.system": "GitHub Actions",
        "ci.repo": f"{env.get('GITHUB_SERVER_URL', '')}/{env.get('GITHUB_REPOSITORY', '')}".rstrip("/"),
        "ci.run_id": env.get("GITHUB_RUN_ID", ""),
        "ci.run_number": env.get("GITHUB_RUN_NUMBER", ""),
        "ci.workflow": env.get("GITHUB_WORKFLOW", ""),
        "ci.job": env.get("GITHUB_JOB", ""),
        "ci.ref": env.get("GITHUB_REF", ""),
        "ci.ref_name": env.get("GITHUB_REF_NAME", ""),
        "ci.sha": env.get("GITHUB_SHA", ""),
    }


def _executor_info() -> dict[str, str]:
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return {}

    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    run_number = os.environ.get("GITHUB_RUN_NUMBER", "")
    run_url = f"{server}/{repo}/actions/runs/{run_id}" if repo and run_id else ""

    return {
        "name": "GitHub Actions",
        "type": "github",
        "url": f"{server}/{repo}" if repo else "",
        "buildName": f"Run #{run_number}" if run_number else "",
        "buildUrl": run_url,
    }


@pytest.fixture(scope="session", autouse=True)
def write_allure_metadata(request: pytest.FixtureRequest) -> None:
    alluredir = request.config.getoption("--alluredir", default=None)
    if alluredir:
        results_dir = Path(alluredir)
        if not results_dir.is_absolute():
            results_dir = ROOT / results_dir
    else:
        results_dir = DEFAULT_ALLURE_RESULTS_DIR
    results_dir.mkdir(parents=True, exist_ok=True)

    data: dict[str, str] = {}
    data.update(_git_info())
    data.update(_runtime_info())
    data.update(_ci_info())

    env_file = results_dir / "environment.properties"
    env_file.write_text(
        "".join(f"{key}={value}\n" for key, value in sorted(data.items()) if value),
        encoding="utf-8",
    )

    executor = _executor_info()
    if executor:
        (results_dir / "executor.json").write_text(
            json.dumps(executor, indent=2),
            encoding="utf-8",
        )


@pytest.fixture
def artifact_root() -> Path:
    path = Path("artifacts/tests/visual")
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture
def save_visual(artifact_root: Path):
    def _save(name: str, figure_or_path) -> Path:
        path = artifact_root / f"{name}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        if hasattr(figure_or_path, "savefig"):
            figure_or_path.savefig(path, dpi=150, bbox_inches="tight")
            plt.close(figure_or_path)
        else:
            source = Path(figure_or_path)
            path.write_bytes(source.read_bytes())
        allure.attach.file(
            str(path),
            name=name,
            attachment_type=allure.attachment_type.PNG,
        )
        return path

    return _save
from __future__ import annotations

import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
TOOLBOX_PROJECT = ROOT / "src" / "poelis_matlab" / "toolbox.prj"
README = ROOT / "src" / "poelis_matlab" / "README.md"


def test_toolbox_version_matches_python_package_version() -> None:
    pyproject = tomllib.loads(PYPROJECT.read_text())
    toolbox_version = ET.parse(TOOLBOX_PROJECT).getroot().findtext("./metadata/version")
    assert toolbox_version == pyproject["project"]["version"]


def test_toolbox_project_references_current_toolbox_files() -> None:
    project_root = ET.parse(TOOLBOX_PROJECT).getroot()
    files = {
        node.text
        for node in project_root.findall("./files/file")
        if node.text is not None
    }

    assert files == {
        "README.md",
        "+poelis_sdk/PoelisClient.m",
        "+poelis_sdk/checkInstallation.m",
        "poelis-logo.png",
        "try_poelis_matlab.m",
    }

    for relative_path in files:
        assert (ROOT / "src" / "poelis_matlab" / relative_path).exists()


def test_matlab_toolbox_readme_documents_release_and_install_flow() -> None:
    readme = README.read_text()
    assert "installToolbox" in readme
    assert "pip install -U poelis-sdk" in readme
    assert "package_matlab_toolbox" in readme
    assert "terminate(pyenv)" in readme

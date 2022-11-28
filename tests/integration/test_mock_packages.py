import subprocess
import sys

import pytest


@pytest.fixture
def venv(tmp_path):
    venv_path = tmp_path / "venv"
    subprocess.run(
        [sys.executable, "-m", "venv", str(venv_path)],
        capture_output=True,
        check=True,
    )
    return venv_path


@pytest.fixture
def venv_interpreter(venv):
    return venv / "bin" / "python"


def test_package_server(package_server, venv_interpreter):
    install = subprocess.run(
        [
            venv_interpreter,
            "-m",
            "pip",
            "install",
            "-i",
            package_server,
            "--trusted-host",
            "localhost",
            "mock_pkg_quuc",
        ],
        encoding="utf-8",
        capture_output=True,
        check=True,
    )
    print(install.stdout)
    freeze = subprocess.run(
        [venv_interpreter, "-m", "pip", "freeze"],
        encoding="utf-8",
        capture_output=True,
        check=True,
    )
    print(freeze.stdout)

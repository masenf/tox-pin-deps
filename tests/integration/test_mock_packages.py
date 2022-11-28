import subprocess
import sys

import pytest

from . import mock_packages


@pytest.fixture
def pkg_path(tmp_path):
    return tmp_path / "packages"


@pytest.fixture
def mock_pkg_foo(tmp_path, pkg_path):
    project_path = tmp_path / "mock_pkg_foo"
    mock_packages.mock_setup_py_package("mock_pkg_foo", "0.0.1", [], project_path)
    mock_packages.wheel(project_path, pkg_path)


@pytest.fixture
def mock_pkg_bar(tmp_path, pkg_path):
    project_path = tmp_path / "mock_pkg_bar"
    mock_packages.mock_setup_py_package("mock_pkg_bar", "0.0.1", [], project_path)
    mock_packages.wheel(project_path, pkg_path)


@pytest.fixture
def package_server(pkg_path, mock_pkg_foo, mock_pkg_bar):
    http_server = mock_packages.dumb_pypi_server(pkg_path, 8081)
    yield "http://localhost:8081/index/simple"
    http_server.terminate()


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
            "mock_pkg_foo",
            "mock_pkg_bar",
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

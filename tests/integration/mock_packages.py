from hashlib import sha256
import json
from itertools import chain
import logging
from pathlib import Path
import subprocess
import sys


logger = logging.getLogger(__name__)


def pypi_sha_hash(package_file: Path):
    d = sha256(package_file.read_bytes())
    return f"sha256={d.hexdigest()}"


def dumb_pypi_repo(pkg_path: Path):
    """Create a dumb pypi index"""
    pkg_path.mkdir(parents=True, exist_ok=True)
    packages = []
    for package_file in chain(pkg_path.glob("*.tar.gz"), pkg_path.glob("*.whl")):
        packages.append(
            json.dumps(
                {
                    "filename": package_file.name,
                    "hash": pypi_sha_hash(package_file),
                }
            )
        )
    package_json = pkg_path / "packages.json"
    package_json.write_text("\n".join(packages))
    output_dir = pkg_path / "index"
    logger.info(
        f"Creating dumb-pypi repo at {output_dir} with {len(packages)} entries."
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "dumb_pypi.main",
            "--package-list-json",
            str(package_json),
            "--packages-url",
            "../../../",
            "--output-dir",
            str(pkg_path / "index"),
        ],
        capture_output=True,
        check=True,
    )
    return f"file://{pkg_path}/index/simple"


def mock_setup_py_package(name, version, install_requires, dest):
    """Create a mock setup.py package and build a wheel from it."""
    logger.debug(f"Create mock setup.py package '{name}-{version}'")
    dest.mkdir(parents=True, exist_ok=True)
    setup_py = dest / "setup.py"
    setup_py.write_text(
        f"""
from setuptools import setup

setup(
    name={name!r},
    version={version!r},
    install_requires={install_requires!r},
)
"""
    )


def mock_pyproject_toml_package(name, version, install_requires, dest):
    """Create a mock setup.py package and build a wheel from it."""
    logger.debug(f"Create mock pyproject.toml package '{name}-{version}'")
    dest.mkdir(parents=True, exist_ok=True)
    pyproject_toml = dest / "pyproject.toml"
    pyproject_toml.write_text(
        f"""
[build-system]
requires = ["setuptools >= 40.0.4", "wheel >= 0.29.0"]
build-backend = 'setuptools.build_meta'

[project]
name = {name!r}
dependencies = {install_requires!r}
version = {version!r}
    """
    )
    return pyproject_toml


def wheel(project_dir, package_dir, isolation=True):
    logger.info(f"Building wheel for {project_dir} -> {package_dir}")
    return subprocess.run(
        [sys.executable, "-m", "build", "--outdir", str(package_dir)]
        + (["--no-isolation"] if not isolation else []),
        cwd=project_dir,
        capture_output=True,
        check=True,
    )

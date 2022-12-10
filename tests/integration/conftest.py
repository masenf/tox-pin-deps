"""Module-scope fixtures for testing real tox"""
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid
import warnings

import pytest

from . import mock_packages

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def pkg_path(tmp_path_factory):
    return tmp_path_factory.mktemp("packages")


def mock_package_maker(
    pkg_name,
    versions,
    tmp_path_factory,
    pkg_path,
    install_requires=None,
    mock_package_func=mock_packages.mock_setup_py_package,
    isolation=False,
):
    project_path = tmp_path_factory.mktemp(pkg_name)
    for version in versions:
        mock_package_func(pkg_name, version, install_requires or [], project_path)
        mock_packages.wheel(project_path, pkg_path, isolation=isolation)
    return pkg_name, dict(
        versions=versions,
        project_path=project_path,
    )


@pytest.fixture(scope="session")
def mock_pkg_foo(tmp_path_factory, pkg_path):
    pkg_name = "mock_pkg_foo"
    versions = ["0.0.1", "0.1.0", "1.0b2"]
    return mock_package_maker(pkg_name, versions, tmp_path_factory, pkg_path)


@pytest.fixture(scope="session")
def mock_pkg_bar(tmp_path_factory, pkg_path, mock_pkg_foo):
    pkg_name = "mock_pkg_bar"
    versions = ["0.1.1", "1.1.0", "1.2", "1.5"]
    return mock_package_maker(
        pkg_name,
        versions,
        tmp_path_factory,
        pkg_path,
        install_requires=[mock_pkg_foo[0]],
    )


@pytest.fixture(scope="session")
def mock_pkg_quuc(tmp_path_factory, pkg_path, mock_pkg_bar):
    pkg_name = "mock_pkg_quuc"
    versions = ["2.1.1", "2.0", "2.2", "2.1.0"]
    return mock_package_maker(
        pkg_name,
        versions,
        tmp_path_factory,
        pkg_path,
        install_requires=[mock_pkg_bar[0]],
        mock_package_func=mock_packages.mock_pyproject_toml_package,
    )


@pytest.fixture(scope="session")
def all_mock_packages(mock_pkg_foo, mock_pkg_bar, mock_pkg_quuc):
    return dict([mock_pkg_foo, mock_pkg_bar, mock_pkg_quuc])


@pytest.fixture(scope="session")
def save_pip_vars():
    save = {
        v: os.environ.get(v)
        for v in ["PIP_INDEX_URL", "PIP_EXTRA_INDEX_URL", "PIP_TRUSTED_HOST"]
    }
    yield
    for var, val in save.items():
        if val is not None:
            os.environ[var] = val


@pytest.fixture(scope="session")
def package_server(pkg_path, all_mock_packages, save_pip_vars):
    index = mock_packages.dumb_pypi_repo(pkg_path)
    # os.environ["PIP_INDEX_URL"] = index
    os.environ["PIP_EXTRA_INDEX_URL"] = index
    yield index


@pytest.fixture(scope="module")
def mod_id():
    return str(uuid.uuid4())[:5]


@pytest.fixture(
    scope="module",
    params=[
        ("examples", "env-pins"),
        ("examples", "pyproject-toml-pkg"),
        ("examples", "setup-py-pkg"),
    ],
    ids=["examples/env-pins", "examples/pyproject-toml-pkg", "examples/setup-py-pkg"],
)
def _example_environment_root(request):
    return Path(Path(__file__).resolve().parent.parent.parent, *request.param)


@pytest.fixture(
    scope="module",
    params=[
        "examples/skipsdist",
        "examples/pyproj",
    ],
)
def example_project_name(request):
    return request.param


@pytest.fixture(scope="module")
def example_environment_root(example_project_name, package_server):
    p = example_project_name.split("/")
    return Path(Path(__file__).resolve().parent, *p)


@pytest.fixture(
    scope="module",
    params=["tox==3.27.1", "tox==4.0.5"],
)
def tox_version(request):
    return request.param


@pytest.fixture(scope="module")
def tox_major(tox_version):
    return "4" if "4" in tox_version else "3"


@pytest.fixture(scope="module")
def toxinidir(tmp_path_factory, mod_id, tox_version, example_environment_root):
    """Copy the example environment to tmp_path."""
    project_dir = tmp_path_factory.mktemp(f"examples_{mod_id}_{tox_version}")
    toxinidir = project_dir / example_environment_root.name
    shutil.copytree(
        example_environment_root,
        toxinidir,
        ignore=shutil.ignore_patterns(".tox", "__pycache__", "*.pyc"),
    )
    return toxinidir


@pytest.fixture(scope="module")
def tox_venv(tmp_path_factory, mod_id, tox_version):
    tox_version_number = tox_version.partition("==")[2]
    tox_venv_path = tmp_path_factory.mktemp(f"tox_venv_{tox_version_number}_{mod_id}")
    subprocess.run(
        [sys.executable, "-m", "venv", tox_venv_path],
    )
    import pkg_resources

    pytest_cov_dist = pkg_resources.get_distribution("pytest-cov")
    subprocess.run(
        [
            tox_venv_path / "bin" / "python",
            "-m",
            "pip",
            "install",
            tox_version,
            f"pytest-cov=={pytest_cov_dist.parsed_version}",
        ],
        cwd=tox_venv_path,
    )
    return tox_venv_path


@pytest.fixture(scope="module")
def tox_testenv_passenv_all():
    orig_tox_testenv_passenv = os.environ.get("TOX_TESTENV_PASSENV")
    os.environ["TOX_TESTENV_PASSENV"] = "COV* PIP*"  # for coverage.py
    yield
    if orig_tox_testenv_passenv is not None:
        # monkeypatch doesn't work at module scope
        os.environ["TOX_TESTENV_PASSENV"] = orig_tox_testenv_passenv


@pytest.fixture(scope="module")
def tox_venv_python(tox_venv, tox_testenv_passenv_all):
    return tox_venv / "bin" / "python"


@pytest.fixture(scope="module")
def tox_venv_site_packages_dir(tox_venv_python):
    return Path(
        subprocess.run(
            [
                tox_venv_python,
                "-c",
                "from distutils.sysconfig import get_python_lib;"
                "print(get_python_lib())",
            ],
            stdout=subprocess.PIPE,
            check=True,
            encoding="utf-8",
        ).stdout.strip()
    )


@pytest.fixture(scope="module")
def link_tox_pin_deps(tox_venv, tox_venv_site_packages_dir):
    import tox_pin_deps
    import pkg_resources

    dist = pkg_resources.get_distribution("tox-pin-deps")
    egg_path = Path(dist.egg_info)
    top_level_pths = set(Path(p).parent for p in tox_pin_deps.__path__)
    pth_path = tox_venv_site_packages_dir / "tox-pin-deps.pth"
    pth_path.write_text("\n".join(str(p) for p in top_level_pths))
    (tox_venv_site_packages_dir / egg_path.name).symlink_to(
        egg_path, target_is_directory=True
    )
    yield
    pth_path.unlink()
    (tox_venv_site_packages_dir / egg_path.name).unlink()


@pytest.fixture(scope="module")
def tox_runner(tox_venv_python, link_tox_pin_deps, toxinidir):
    def run_tox_cmd(*args):
        return subprocess.run(
            [tox_venv_python, "-m", "tox", *args],
            cwd=toxinidir,
            capture_output=True,
            encoding="utf-8",
            check=True,
        )

    return run_tox_cmd


@pytest.fixture(scope="module")
def tox_run(tox_runner):
    return tox_runner()


@pytest.fixture(scope="module")
def pip_compile_tox_run(tox_runner, package_server):
    return tox_runner(
        "--pip-compile",
        "--pip-compile-opts",
        f" --extra-index-url {package_server}",
    )


@pytest.fixture(scope="module")
def ignore_pins_tox_run(tox_runner):
    return tox_runner("--ignore-pins")


@pytest.fixture(scope="module")
def tox_run_recreate(tox_runner):
    return tox_runner("--recreate")


@pytest.fixture(scope="module")
def tox_run_3(tox_runner):
    return tox_runner()


def assert_output_ordered(output, exp_output):
    output_lines = output.splitlines()
    last_line = 0
    for needle in exp_output:
        for ix, line in enumerate(output_lines[last_line:]):
            if hasattr(needle, "match"):
                if needle.match(line):
                    break
            elif line.startswith(needle):
                break
        else:
            raise AssertionError(
                f"Remains unmatched: {needle!r} in {output_lines[last_line:]!r}"
            )
        last_line += ix + 1
        logger.debug(f"Matched {needle!r} on line {last_line}")


def get_exp_output(path):
    if not path.exists():
        warnings.warn(f"No validation for {path}")
        return []
    return [
        re.compile(line[3:]) if line.startswith("~re") else line
        for line in path.read_text().splitlines()
    ]


@pytest.fixture
def exp_no_lock(tox_major, example_environment_root):
    return get_exp_output(example_environment_root / f"exp_no_lock_{tox_major}.txt")


@pytest.fixture
def exp_lock(tox_major, example_environment_root):
    return get_exp_output(example_environment_root / f"exp_lock_{tox_major}.txt")


@pytest.fixture
def exp_pip_compile(tox_major, example_environment_root):
    return get_exp_output(example_environment_root / f"exp_pip_compile_{tox_major}.txt")


@pytest.fixture
def exp_reuse(tox_major, example_environment_root):
    return get_exp_output(example_environment_root / f"exp_reuse_{tox_major}.txt")

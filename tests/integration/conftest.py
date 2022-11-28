"""Module-scope fixtures for testing real tox"""
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import uuid

import pytest

from . import mock_packages


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
def package_server_port():
    return 8080 + random.randint(1, 512)


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
def package_server(package_server_port, pkg_path, all_mock_packages, save_pip_vars):
    http_server = mock_packages.dumb_pypi_server(pkg_path, package_server_port)
    host = "localhost"
    index = f"http://{host}:{package_server_port}/index/simple"
    # os.environ["PIP_INDEX_URL"] = index
    os.environ["PIP_EXTRA_INDEX_URL"] = index
    os.environ["PIP_TRUSTED_HOST"] = host
    yield index
    http_server.terminate()


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
        pytest.param(("examples", "skipsdist"), id="examples/skipsdist"),
        pytest.param(
            ("examples", "pyproj"),
            id="examples/pyproj",
            marks=[pytest.mark.skip("nodeps does NOT find transitives")],
        ),
    ],
)
def example_environment_root(request, package_server):
    return Path(Path(__file__).resolve().parent, *request.param)


@pytest.fixture(
    scope="module",
    params=["tox==3.27.1", "tox==4.0.0b2"],
)
def tox_version(request):
    return request.param


@pytest.fixture(scope="module")
def toxinidir(tmp_path_factory, mod_id, example_environment_root):
    """Copy the example environment to tmp_path."""
    project_dir = tmp_path_factory.mktemp(f"examples_{mod_id}")
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
    if "==4" in tox_version:
        # XXX: until a tox4 release includes my hashes fix, install from a local checkout
        tox_version = Path(__file__).parent.parent.parent.parent / "tox-rewrite"
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
def tox_run(tox_venv_python, link_tox_pin_deps, toxinidir):
    return subprocess.run(
        [tox_venv_python, "-m", "tox"],
        cwd=toxinidir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        check=True,
    )


@pytest.fixture(scope="module")
def pip_compile_tox_run(tox_venv_python, link_tox_pin_deps, toxinidir, package_server):
    return subprocess.run(
        [
            tox_venv_python,
            "-m",
            "tox",
            "--pip-compile",
            "--pip-compile-opts",
            f" --extra-index-url {package_server}",
        ],
        cwd=toxinidir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        check=True,
    )


@pytest.fixture(scope="module")
def ignore_pins_tox_run(tox_venv_python, link_tox_pin_deps, toxinidir):
    return subprocess.run(
        [tox_venv_python, "-m", "tox", "--ignore-pins"],
        cwd=toxinidir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        check=True,
    )


@pytest.fixture(scope="module")
def tox_run_recreate(tox_venv_python, link_tox_pin_deps, toxinidir):
    return subprocess.run(
        [tox_venv_python, "-m", "tox", "--recreate"],
        cwd=toxinidir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        check=True,
    )


@pytest.fixture(scope="module")
def tox_run_3(tox_venv_python, link_tox_pin_deps, toxinidir):
    return subprocess.run(
        [tox_venv_python, "-m", "tox"],
        cwd=toxinidir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        check=True,
    )

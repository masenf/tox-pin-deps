from unittest import mock

import pytest

from . import tox_mocks

# reset ShimBaseMock after every test
_fx_reset = pytest.fixture(autouse=True)(tox_mocks.ShimBaseMock._fx_reset)


@pytest.fixture
def venv_name():
    return "mock-venv"


@pytest.fixture
def options():
    options = mock.Mock()
    options.pip_compile_opts = None
    options.pip_compile = True
    options.ignore_pins = False
    return options


@pytest.fixture
def toxinidir(tmp_path):
    toxinidir = tmp_path / "project_directory"
    toxinidir.mkdir()
    return toxinidir


@pytest.fixture(params=[True, False], ids=["pip_compile", "no_pip_compile"])
def pip_compile(request, options):
    options.pip_compile = request.param
    return request.param


@pytest.fixture(params=[True, False], ids=["ignore_pins", "no_ignore_pins"])
def ignore_pins(request, options):
    options.ignore_pins = request.param
    return request.param


@pytest.fixture(
    params=[[], ["foo"]],
    ids=["deps=[]", "deps=[foo]"],
)
def deps(request):
    return request.param


@pytest.fixture
def deps_present():
    return ["foo"]


@pytest.fixture
def envname(venv):
    if not isinstance(venv.name, mock.Mock):
        return venv.name  # tox4
    return venv.envconfig.envname  # tox3


@pytest.fixture(
    params=[None, True],
    ids=["no_env_requirements", "env_requirements"],
)
def env_requirements(request, envname, toxinidir):
    if request.param:
        rdir = toxinidir / "requirements"
        rdir.mkdir()
        requirements = (rdir / envname).with_suffix(".txt")
        requirements.touch()
        return requirements


@pytest.fixture
def parser():
    return mock.Mock()


@pytest.fixture(
    params=[None, "-v"], ids=["no_PIP_COMPILE_OPTS", "PIP_COMPILE_OPTS='-v'"]
)
def pip_compile_opts_env(request, monkeypatch):
    if request.param:
        monkeypatch.setenv("PIP_COMPILE_OPTS", request.param)
    return request.param


@pytest.fixture(
    params=[None, "--quiet"],
    ids=["no_--pip-compile-opts", "--pip-compile-opts='--quiet'"],
)
def pip_compile_opts_cli(request, options):
    if request.param:
        options.pip_compile_opts = request.param
    return request.param


@pytest.fixture(
    params=[None, "--generate-hashes -v"],
    ids=["no_pip_compile_opts", "pip_compile_opts = --generate-hashes"],
)
def pip_compile_opts_testenv(request):
    return request.param


@pytest.fixture(params=[True, False], ids=["skipsdist", "noskipsdist"])
def skipsdist(request):
    return request.param


@pytest.fixture(params=[True, False], ids=["skip_install", "no_skip_install"])
def skip_install(request):
    return request.param


@pytest.fixture(params=[True, False], ids=["pip_pre", "no_pip_pre"])
def pip_pre(request):
    return request.param


@pytest.fixture(params=[[], ["ex1", "ex2"]], ids=["noextra", "extras"])
def extras(request):
    return request.param


@pytest.fixture(params=[True, False], ids=["setup.py", "no_setup.py"])
def setup_py(request, toxinidir):
    if request.param:
        setup_py = toxinidir / "setup.py"
        setup_py.touch()
        return setup_py


@pytest.fixture(params=[True, False], ids=["setup.cfg", "no_setup.cfg"])
def setup_cfg(request, toxinidir):
    if request.param:
        setup_cfg = toxinidir / "setup.cfg"
        setup_cfg.touch()
        return setup_cfg


@pytest.fixture(params=[True, False], ids=["pyproject.toml", "no_pyproject.toml"])
def pyproject_toml(request, toxinidir):
    if request.param:
        pyproject_toml = toxinidir / "pyproject.toml"
        pyproject_toml.touch()
        return pyproject_toml

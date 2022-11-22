from unittest import mock

import pytest


@pytest.fixture
def venv_name():
    return "mock-venv"


@pytest.fixture
def config(tmp_path):
    config = mock.Mock()
    config.toxinidir = tmp_path / "project_directory"
    config.toxinidir.mkdir()
    config.option.pip_compile_opts = None
    config.option.pip_compile = True
    config.option.ignore_pins = False
    config.envconfigs = {}
    config.envlist = []
    return config


@pytest.fixture(params=[True, False], ids=["pip_compile", "no_pip_compile"])
def pip_compile(request, config):
    config.option.pip_compile = request.param
    return request.param


@pytest.fixture(params=[True, False], ids=["ignore_pins", "no_ignore_pins"])
def ignore_pins(request, config):
    config.option.ignore_pins = request.param
    return request.param


@pytest.fixture
def envconfig(venv_name, config):
    envconfig = mock.Mock()
    envconfig.config = config
    envconfig.envname = venv_name
    envconfig.pip_compile_opts = None
    config.envconfigs[venv_name] = envconfig
    config.envlist.append(venv_name)
    return envconfig


@pytest.fixture
def venv(envconfig):
    venv = mock.Mock()
    venv.envconfig = envconfig
    venv.path = venv.envconfig.config.toxinidir / "dot-tox" / envconfig.envname
    venv.path.mkdir(parents=True)
    return venv


@pytest.fixture
def mock_get_resolved_dependencies(venv):
    def get_resolved_dependencies():
        return venv.envconfig.deps

    venv.get_resolved_dependencies = mock.Mock(side_effect=get_resolved_dependencies)


@pytest.fixture(
    params=[[], [mock.Mock(name="foo")]],
    ids=["deps=[]", "deps=[foo]"],
)
def deps(request, venv, mock_get_resolved_dependencies):
    venv.envconfig.deps = request.param
    return request.param


@pytest.fixture
def deps_present(venv, mock_get_resolved_dependencies):
    venv.envconfig.deps = [mock.Mock(name="foo")]
    return venv.envconfig.deps


@pytest.fixture(
    params=[None, True],
    ids=["no_env_requirements", "env_requirements"],
)
def env_requirements(request, venv):
    if request.param:
        rdir = venv.envconfig.config.toxinidir / "requirements"
        rdir.mkdir()
        requirements = (rdir / venv.envconfig.envname).with_suffix(".txt")
        requirements.touch()
        return requirements


@pytest.fixture
def action():
    return mock.Mock()


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
def pip_compile_opts_cli(request, venv):
    if request.param:
        venv.envconfig.config.option.pip_compile_opts = request.param
    return request.param


@pytest.fixture(
    params=[None, "--generate-hashes -v"],
    ids=["no_pip_compile_opts", "pip_compile_opts = --generate-hashes"],
)
def pip_compile_opts_testenv(request, venv):
    if request.param:
        venv.envconfig.pip_compile_opts = request.param
    return request.param


@pytest.fixture(params=[True, False], ids=["skipsdist", "noskipsdist"])
def skipsdist(request, config):
    config.skipsdist = request.param
    return request.param


@pytest.fixture(params=[True, False], ids=["skip_install", "no_skip_install"])
def skip_install(request, envconfig):
    envconfig.skip_install = request.param
    return request.param


@pytest.fixture(params=[True, False], ids=["setup.py", "no_setup.py"])
def setup_py(request, config):
    if request.param:
        setup_py = config.toxinidir / "setup.py"
        setup_py.touch()
        return setup_py


@pytest.fixture(params=[True, False], ids=["setup.cfg", "no_setup.cfg"])
def setup_cfg(request, config):
    if request.param:
        setup_cfg = config.toxinidir / "setup.cfg"
        setup_cfg.touch()
        return setup_cfg


@pytest.fixture(params=[True, False], ids=["pyproject.toml", "no_pyproject.toml"])
def pyproject_toml(request, config):
    if request.param:
        pyproject_toml = config.toxinidir / "pyproject.toml"
        pyproject_toml.touch()
        return pyproject_toml

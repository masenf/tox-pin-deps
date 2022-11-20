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
    return envconfig


@pytest.fixture
def venv(envconfig):
    venv = mock.Mock()
    venv.envconfig = envconfig
    venv.path = venv.envconfig.config.toxinidir / "dot-tox" / envconfig.envname
    venv.path.mkdir(parents=True)
    return venv


@pytest.fixture(
    params=[[], [mock.Mock(name="foo")]],
    ids=["deps=[]", "deps=[foo]"],
)
def deps(request, venv):
    venv.envconfig.deps = request.param

    def get_resolved_dependencies():
        return venv.envconfig.deps

    venv.get_resolved_dependencies = mock.Mock(side_effect=get_resolved_dependencies)
    return request.param


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

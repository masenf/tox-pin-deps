from pathlib import Path
import shlex
from unittest import mock

import pytest

import tox_pin_deps.plugin


@pytest.fixture
def config(tmp_path, toxinidir, options):
    """tox3 global config"""
    config = mock.Mock()
    config.toxinidir = toxinidir
    config.option = options
    config.envconfigs = {}
    config.envlist = []
    return config


@pytest.fixture
def envconfig(venv_name, config):
    """tox3 per-testenv config."""
    envconfig = mock.Mock()
    envconfig.config = config
    envconfig.envname = venv_name
    envconfig.pip_compile_opts = None
    envconfig.recreate = False
    config.envconfigs[venv_name] = envconfig
    config.envlist.append(venv_name)
    return envconfig


@pytest.fixture
def venv(envconfig):
    """tox3 VirtualEnv."""
    venv = mock.Mock()
    venv.envconfig = envconfig
    venv.path = venv.envconfig.config.toxinidir / "dot-tox" / envconfig.envname
    venv.path.mkdir(parents=True)
    return venv


@pytest.fixture
def dot_venv(config, envconfig, venv):
    """Modified tox3 venv to start with a period."""
    envconfig.envname = ".package"
    config.envconfigs[envconfig.envname] = envconfig
    config.envlist = [envconfig.envname]
    return venv


@pytest.fixture
def mock_get_resolved_dependencies(venv):
    def get_resolved_dependencies():
        return venv.envconfig.deps

    venv.get_resolved_dependencies = mock.Mock(side_effect=get_resolved_dependencies)


@pytest.fixture
def deps(deps, envconfig, mock_get_resolved_dependencies):
    """Set `deps` in the tox3 envconfig."""
    envconfig.deps = deps
    return deps


@pytest.fixture
def deps_present(deps_present, envconfig, mock_get_resolved_dependencies):
    """Set `deps_present` in the tox3 envconfig."""
    envconfig.deps = deps_present
    return deps_present


@pytest.fixture
def pip_compile_opts_testenv(envconfig, pip_compile_opts_testenv):
    """Set pip_compile_opts in the tox3 envconfig"""
    if pip_compile_opts_testenv:
        envconfig.pip_compile_opts = pip_compile_opts_testenv
    return pip_compile_opts_testenv


@pytest.fixture
def skipsdist(skipsdist, config):
    config.skipsdist = skipsdist
    return skipsdist


@pytest.fixture
def skip_install(skip_install, envconfig):
    envconfig.skip_install = skip_install
    return skip_install


@pytest.fixture
def action():
    return mock.Mock()


def test_tox_addoption(parser):
    tox_pin_deps.plugin.tox_addoption(parser)
    assert parser.add_argument.call_args_list[0][0] == ("--pip-compile",)
    assert parser.add_argument.call_args_list[1][0] == ("--ignore-pins",)


def test_tox_configure(
    venv,
    config,
    ignore_pins,
    pip_compile,
    deps,
    env_requirements,
):
    assert tox_pin_deps.plugin.tox_configure(config) is None
    venv.get_resolved_dependencies.assert_not_called()
    if env_requirements and not (ignore_pins or pip_compile):
        assert venv.envconfig.deps[0].name == f"-r{env_requirements}"
        assert len(venv.envconfig.deps) == 1
    else:
        assert venv.envconfig.deps == deps
    if pip_compile and not ignore_pins:
        assert venv.envconfig.recreate
    else:
        assert not venv.envconfig.recreate


def test_tox_configure_dot_envname(
    dot_venv,
    config,
    action,
    deps_present,
    pip_compile,
):
    assert tox_pin_deps.plugin.tox_configure(config) is None
    dot_venv.get_resolved_dependencies.assert_not_called()
    dot_venv._pcall.assert_not_called()
    assert dot_venv.envconfig.deps == deps_present
    assert not dot_venv.envconfig.recreate


def test_tox_testenv_install_deps(
    venv,
    action,
    ignore_pins,
    pip_compile,
    deps,
    env_requirements,
):
    assert tox_pin_deps.plugin.tox_testenv_install_deps(venv, action) is None
    if ignore_pins:
        venv.get_resolved_dependencies.assert_not_called()
        assert venv.envconfig.deps == deps
    else:
        venv.get_resolved_dependencies.assert_called_once()
        if pip_compile and deps:
            if env_requirements is None:
                env_requirements = tox_pin_deps.requirements_file(
                    toxinidir=venv.envconfig.config.toxinidir,
                    envname=venv.envconfig.envname,
                )
            assert venv.envconfig.deps[0].name == f"-r{env_requirements}"
            assert len(venv.envconfig.deps) == 1
            assert len(venv._pcall.mock_calls) == 2
            assert venv._pcall.mock_calls[0][1] == (["pip", "install", "pip-tools"],)
            cmd = venv._pcall.mock_calls[1][1][0]
            assert cmd[0] == "pip-compile"
            # not mocking tempfile at this time
            # assert cmd[1] == tf.name
            start_idx = cmd.index("--output-file")
            assert cmd[start_idx:] == ["--output-file", str(env_requirements)]
        else:
            assert venv.envconfig.deps == deps
            venv._pcall.assert_not_called()


def test_tox_testenv_install_deps_will_install(
    venv,
    action,
    pip_compile_opts_env,
    pip_compile_opts_cli,
    pip_compile_opts_testenv,
    deps_present,
    skipsdist,
    skip_install,
    setup_py,
    setup_cfg,
    pyproject_toml,
):
    assert tox_pin_deps.plugin.tox_testenv_install_deps(venv, action) is None
    venv.get_resolved_dependencies.assert_called_once()
    assert len(venv._pcall.mock_calls) == 2
    assert venv._pcall.mock_calls[0][1] == (["pip", "install", "pip-tools"],)
    cmd = venv._pcall.mock_calls[1][1][0]
    assert cmd[0] == "pip-compile"
    # not mocking tempfile at this time
    # assert cmd[1] == tf.name
    exp_files = []
    if not skipsdist and not skip_install:
        if pyproject_toml:
            exp_files.append(str(pyproject_toml))
        if setup_cfg:
            exp_files.append(str(setup_cfg))
        if setup_py:
            exp_files.append(str(setup_py))
    start_idx = cmd.index("--output-file")
    assert cmd[2:start_idx] == exp_files
    for path_should_exist in cmd[2:start_idx]:
        assert Path(path_should_exist).exists()
    env_requirements = tox_pin_deps.requirements_file(
        toxinidir=venv.envconfig.config.toxinidir,
        envname=venv.envconfig.envname,
    )
    exp_opts = ["--output-file", str(env_requirements)]
    if pip_compile_opts_testenv:
        exp_opts.extend(shlex.split(pip_compile_opts_testenv))
    if pip_compile_opts_cli:
        exp_opts.extend(shlex.split(pip_compile_opts_cli))
    if pip_compile_opts_env:
        exp_opts.extend(shlex.split(pip_compile_opts_env))
    assert cmd[start_idx:] == exp_opts


def test_tox_testenv_install_deps_dot_envname(
    dot_venv,
    action,
    deps_present,
):
    assert tox_pin_deps.plugin.tox_testenv_install_deps(dot_venv, action) is None
    dot_venv.get_resolved_dependencies.assert_not_called()
    dot_venv._pcall.assert_not_called()
    assert dot_venv.envconfig.deps == deps_present

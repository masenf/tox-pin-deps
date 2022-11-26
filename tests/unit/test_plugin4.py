from pathlib import Path
import shlex
from unittest import mock

import pytest

import tox_pin_deps.plugin4

from .conftest import ShimBaseMock


@pytest.fixture
def core(toxinidir):
    """tox4 global config"""
    return dict(toxinidir=toxinidir, skipsdist=False)


@pytest.fixture
def options(options):
    options.verbosity = 0
    return options


@pytest.fixture
def conf():
    """tox4 per-testenv config."""
    return dict(pip_compile_opts=None, skip_install=False)


@pytest.fixture
def executor():
    class Outcome:
        def __init__(self, success, *args, **kwargs):
            self.success = success

        def assert_success(self):
            assert self.success

    return mock.Mock(return_value=Outcome(True))


@pytest.fixture
def venv(venv_name, core, conf, options, toxinidir, executor):
    """tox4 VirtualEnvRunner."""
    venv = mock.Mock()
    venv.name = venv_name
    venv.core = core
    venv.conf = conf
    venv.options = options
    venv.execute = executor
    venv.toxinidir = toxinidir
    venv.path = toxinidir / "dot-tox" / venv_name
    venv.path.mkdir(parents=True)
    return venv


@pytest.fixture
def dot_venv(venv, toxinidir):
    """Modified tox4 venv to start with a period."""
    venv.name = ".package"
    venv.path = toxinidir / "dot-tox" / venv.name
    venv.path.mkdir(parents=True)
    return venv


@pytest.fixture
def deps(deps):
    """`deps` for tox4 Installer[Python].install function."""
    if deps:
        return tox_pin_deps.plugin4.PythonDeps(raw="\n".join(deps))
    return None  # TODO: what does tox4 really do when there are no deps


@pytest.fixture
def deps_present(deps_present):
    """Set `deps_present` in the tox4 envconfig."""
    return tox_pin_deps.plugin4.PythonDeps(raw="\n".join(deps_present))


@pytest.fixture
def pip_compile_opts_testenv(conf, pip_compile_opts_testenv):
    """Set pip_compile_opts in the tox4 envconfig"""
    if pip_compile_opts_testenv:
        conf["pip_compile_opts"] = pip_compile_opts_testenv
    return pip_compile_opts_testenv


@pytest.fixture
def skipsdist(skipsdist, core):
    if skipsdist:
        core["skipsdist"] = skipsdist
    return skipsdist


@pytest.fixture
def skip_install(skip_install, conf):
    if skip_install:
        conf["skip_install"] = skip_install
    return skip_install


def test_install(
    toxinidir,
    venv_name,
    venv,
    ignore_pins,
    pip_compile,
    deps,
    env_requirements,
):
    pip_compile_installer = tox_pin_deps.plugin4.PipCompileInstaller(venv)
    assert pip_compile_installer.install(deps, None, None) is None
    pip_mock = ShimBaseMock._get_last_instance_and_reset(assert_n_instances=1)
    if ignore_pins:
        pip_mock._install_mock.assert_called_once_with(
            arguments=deps, section=None, of_type=None
        )
        venv.execute.assert_not_called()
    elif pip_compile:
        if env_requirements is None:
            env_requirements = tox_pin_deps.requirements_file(
                toxinidir=toxinidir,
                envname=venv_name,
            )
        exp_deps = tox_pin_deps.plugin4.PythonDeps(
            f"-r{env_requirements}", env_requirements.parent
        )
        pip_mock._install_mock.assert_called_once_with(
            arguments=exp_deps, section=None, of_type=None
        )
        assert len(venv.execute.mock_calls) == 2
        assert venv.execute.mock_calls[0][2]["cmd"] == ["pip", "install", "pip-tools"]
        cmd = venv.execute.mock_calls[1][2]["cmd"]
        assert cmd[0] == "pip-compile"
        # not mocking tempfile at this time
        # assert cmd[1] == tf.name
        start_idx = cmd.index("--output-file")
        assert cmd[start_idx:] == ["--output-file", str(env_requirements)]
    elif env_requirements:
        exp_deps = tox_pin_deps.plugin4.PythonDeps(
            f"-r{env_requirements}",
            env_requirements.parent,
        )
        pip_mock._install_mock.assert_called_once_with(
            arguments=exp_deps,
            section=None,
            of_type=None,
        )
        venv.execute.assert_not_called()
    else:
        pip_mock._install_mock.assert_called_once_with(
            arguments=deps,
            section=None,
            of_type=None,
        )
        venv.execute.assert_not_called()


def test_install_will_install(
    venv,
    venv_name,
    toxinidir,
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
    pip_compile_installer = tox_pin_deps.plugin4.PipCompileInstaller(venv)
    assert pip_compile_installer.install(deps_present, None, None) is None
    pip_mock = ShimBaseMock._get_last_instance_and_reset(assert_n_instances=1)
    pip_mock._install_mock.assert_called_once()
    assert len(venv.execute.mock_calls) == 2
    assert venv.execute.mock_calls[0][2]["cmd"] == ["pip", "install", "pip-tools"]
    cmd = venv.execute.mock_calls[1][2]["cmd"]
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
        toxinidir=toxinidir,
        envname=venv_name,
    )
    exp_opts = ["--output-file", str(env_requirements)]
    if pip_compile_opts_testenv:
        exp_opts.extend(shlex.split(pip_compile_opts_testenv))
    if pip_compile_opts_cli:
        exp_opts.extend(shlex.split(pip_compile_opts_cli))
    if pip_compile_opts_env:
        exp_opts.extend(shlex.split(pip_compile_opts_env))
    assert cmd[start_idx:] == exp_opts


def test_install_dot_in_name(
    dot_venv,
    deps_present,
):
    pip_compile_installer = tox_pin_deps.plugin4.PipCompileInstaller(dot_venv)
    assert pip_compile_installer.install(deps_present, None, None) is None
    pip_mock = ShimBaseMock._get_last_instance_and_reset(assert_n_instances=1)
    pip_mock._install_mock.assert_called_once_with(
        arguments=deps_present, section=None, of_type=None
    )
    dot_venv.execute.assert_not_called()


def test_tox_register_tox_env():
    register = mock.Mock()
    tox_pin_deps.plugin4.tox_register_tox_env(register)
    # TODO: assert


def test_register_config(venv):
    inst = tox_pin_deps.plugin4.PinDepsVirtualEnvRunner(None)
    inst.name = venv.name
    inst.core = venv.core
    inst.conf = mock.Mock()
    inst.register_config()
    assert isinstance(inst.installer, tox_pin_deps.plugin4.PipCompileInstaller)
    # TODO: assert


def test_tox_add_option(parser):
    tox_pin_deps.plugin4.tox_add_option(parser)
    # TODO: assert

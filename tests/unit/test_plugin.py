from pathlib import Path
import shlex

import tox_pin_deps.plugin


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

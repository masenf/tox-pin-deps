import tox_pin_deps.plugin


def test_tox_addoption(parser):
    tox_pin_deps.plugin.tox_addoption(parser)
    assert parser.add_argument.call_args_list[0][0] == ("--pip-compile",)
    assert parser.add_argument.call_args_list[1][0] == ("--ignore-pins",)


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
        if env_requirements:
            assert venv.envconfig.deps[0].name == f"-r{env_requirements}"
            assert len(venv.envconfig.deps) == 1
        else:
            assert venv.envconfig.deps == deps
        if pip_compile and deps:
            if env_requirements is None:
                env_requirements = tox_pin_deps.plugin._requirements_file(venv)
            assert len(venv._pcall.mock_calls) == 2
            assert venv._pcall.mock_calls[0][1] == (["pip", "install", "pip-tools"],)
            cmd = venv._pcall.mock_calls[1][1][0]
            assert cmd[0] == "pip-compile"
            # not mocking tempfile at this time
            # assert cmd[1] == tf.name
            assert cmd[2:] == ["--output-file", env_requirements]
        else:
            venv._pcall.assert_not_called()

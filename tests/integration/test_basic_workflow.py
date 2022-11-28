import pytest

pytest_plugins = ["pytester"]


def test_initial_tox_run(tox_run):
    print(tox_run.stdout)
    print(tox_run.stderr)


@pytest.mark.usefixtures("tox_run")
def test_pip_compile(pip_compile_tox_run):
    print(pip_compile_tox_run.stdout)
    print(pip_compile_tox_run.stderr)


@pytest.mark.usefixtures("tox_run")
@pytest.mark.usefixtures("pip_compile_tox_run")
def test_ignore_pins(ignore_pins_tox_run):
    print(ignore_pins_tox_run.stdout)
    print(ignore_pins_tox_run.stderr)


@pytest.mark.usefixtures("tox_run")
@pytest.mark.usefixtures("pip_compile_tox_run")
@pytest.mark.usefixtures("ignore_pins_tox_run")
def test_tox_run_recreate(tox_run_recreate):
    print(tox_run_recreate.stdout)
    print(tox_run_recreate.stderr)


@pytest.mark.usefixtures("tox_run")
@pytest.mark.usefixtures("pip_compile_tox_run")
@pytest.mark.usefixtures("ignore_pins_tox_run")
@pytest.mark.usefixtures("tox_run_recreate")
def test_third_tox_run(tox_run_3):
    print(tox_run_3.stdout)
    print(tox_run_3.stderr)

import pytest

pytest_plugins = ["pytester"]


def test_initial_tox_run(tox_run, exp_no_lock):
    assert_output_ordered(tox_run.stdout, exp_no_lock)


@pytest.mark.usefixtures("tox_run")
def test_pip_compile(pip_compile_tox_run, exp_pip_compile):
    assert_output_ordered(pip_compile_tox_run.stdout, exp_pip_compile)


@pytest.mark.usefixtures("tox_run")
@pytest.mark.usefixtures("pip_compile_tox_run")
def test_ignore_pins(ignore_pins_tox_run, exp_no_lock):
    assert_output_ordered(ignore_pins_tox_run.stdout, exp_no_lock)


def test_tox_run_recreate(
    tox_run,
    pip_compile_tox_run,
    ignore_pins_tox_run,
    tox_run_recreate,
    exp_lock,
):
    assert_output_ordered(tox_run_recreate.stdout, exp_lock)


def test_third_tox_run(
    tox_run,
    pip_compile_tox_run,
    ignore_pins_tox_run,
    tox_run_recreate,
    tox_run_3,
    exp_reuse,
):
    assert_output_ordered(tox_run_3.stdout, exp_reuse)

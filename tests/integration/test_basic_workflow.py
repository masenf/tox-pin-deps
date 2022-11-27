pytest_plugins = ["pytester"]


def test_initial_tox_run(tox_run):
    print(tox_run.stdout)
    print(tox_run.stderr)


def test_pip_compile(pip_compile_tox_run):
    print(pip_compile_tox_run.stdout)
    print(pip_compile_tox_run.stderr)


def test_ignore_pins(ignore_pins_tox_run):
    print(ignore_pins_tox_run.stdout)
    print(ignore_pins_tox_run.stderr)

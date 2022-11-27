import pytest

from . import tox_mocks

with tox_mocks.MockTox3Context():
    import tox_pin_deps.plugin
with tox_mocks.MockTox4Context():
    import tox_pin_deps.plugin4


@pytest.fixture(
    params=[tox_pin_deps.plugin.tox_addoption, tox_pin_deps.plugin4.tox_add_option],
    ids=["tox_addoption(tox3)", "tox_add_option(tox4)"],
)
def add_option_hook(request):
    return request.param


def test_tox_add_option(parser, add_option_hook):
    add_option_hook(parser)
    added_args = [cal[0][0] for cal in parser.add_argument.call_args_list]
    assert added_args == ["--pip-compile", "--ignore-pins", "--pip-compile-opts"]

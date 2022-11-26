import pytest

import tox_pin_deps.plugin
import tox_pin_deps.plugin4


@pytest.fixture(
    params=[tox_pin_deps.plugin.tox_addoption, tox_pin_deps.plugin4.tox_add_option]
)
def add_option_hook(request):
    return request.param


def test_tox_add_option(parser, add_option_hook):
    add_option_hook(parser)
    assert parser.add_argument.call_args_list[0][0] == ("--pip-compile",)
    assert parser.add_argument.call_args_list[1][0] == ("--ignore-pins",)

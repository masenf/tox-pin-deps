"""Loader should identify the tox plugin version needed."""
import sys

from pkg_resources import DistributionNotFound, get_distribution
import pytest

from .tox_mocks import MockNoToxContext, MockTox3Context, MockTox4Context


@pytest.fixture
def _del_loader_module():
    """allow re-import of test modules as-if they had not been imported."""
    sys.modules.pop("tox", None)
    sys.modules.pop("tox.hookimpl", None)
    sys.modules.pop("tox.plugin.impl", None)
    sys.modules.pop("tox_pin_deps.loader", None)


@pytest.mark.parametrize(
    "context,exp_TOX",
    (
        (MockNoToxContext, None),
        (MockTox3Context, 3),
        (MockTox4Context, 4),
    ),
)
@pytest.mark.usefixtures("_del_loader_module")
def test_loader(context, exp_TOX):
    with context():
        if exp_TOX is None:
            with pytest.raises(
                ImportError,
                match=r"This plugin requires tox 3 or tox 4\.",
            ):
                import tox_pin_deps.loader
        else:
            import tox_pin_deps.loader

            assert tox_pin_deps.loader.TOX == exp_TOX
    assert "tox" not in sys.modules


@pytest.mark.usefixtures("_del_loader_module")
def test_loader_no_mock():
    """Use whatever the local test environment has and check it!"""
    try:
        installed_tox = get_distribution("tox")
    except DistributionNotFound:
        with pytest.raises(
            ImportError,
            match=r"This plugin requires tox 3 or tox 4\.",
        ):
            import tox_pin_deps.loader
    else:
        import tox_pin_deps.loader

        assert tox_pin_deps.loader.TOX == installed_tox.parsed_version.major

"""Loads the right version of the plugin for your environment."""

try:
    from tox.plugin import impl
except ImportError:
    try:
        from tox import hookimpl
    except ImportError as ie2:
        raise
        raise RuntimeError("This plugin requires tox 3 or tox 4.") from ie2
    else:
        TOX = 3
        from .plugin import tox_addoption, tox_configure, tox_testenv_install_deps
else:
    TOX = 4
    from .plugin4 import tox_add_option, tox_register_tox_env

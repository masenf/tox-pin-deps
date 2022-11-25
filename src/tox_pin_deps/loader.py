"""Loads the right version of the plugin for your environment."""

try:
    from tox.plugin import impl  # type: ignore # noqa: F401
except ImportError:
    try:
        from tox import hookimpl  # type: ignore # noqa: F401
    except ImportError as ie2:
        raise RuntimeError("This plugin requires tox 3 or tox 4.") from ie2
    else:
        TOX = 3
        from .plugin import (  # noqa: F401
            tox_addoption,
            tox_configure,
            tox_testenv_install_deps,
        )
else:
    TOX = 4
    from .plugin4 import (  # noqa: F401
        tox_add_option,
        tox_register_tox_env,
    )

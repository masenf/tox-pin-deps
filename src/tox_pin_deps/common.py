"""Common elements for tox3 and tox4."""
from . import DEFAULT_REQUIREMENTS_DIRECTORY

try:
    from tox.config.cli.parser import ToxParser  # type: ignore
except ImportError:
    from tox.config import Parser as ToxParser  # type: ignore


def tox_add_argument(parser: ToxParser) -> None:
    """Add plugin arguments to an ArgumentParser."""
    parser.add_argument(
        "--pip-compile",
        action="store_true",
        default=False,
        help=(
            "Run `pip-compile` on the deps, and copy the result to "
            "{toxinidir}/%s/{envname}.txt" % DEFAULT_REQUIREMENTS_DIRECTORY
        ),
    )
    parser.add_argument(
        "--ignore-pins",
        action="store_true",
        default=False,
        help="Do not replace deps with `requirements` files",
    )
    parser.add_argument(
        "--pip-compile-opts",
        action="store",
        default="",
        help=(
            "Custom options passed to `pip-compile` when --pip-compile is used. "
            "Also specify via environment variable PIP_COMPILE_OPTS."
        ),
    )

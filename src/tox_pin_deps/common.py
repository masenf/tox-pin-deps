"""Common elements for tox3 and tox4."""
from pathlib import Path
import typing as t

try:
    from tox.config.cli.parser import ToxParser
except ImportError:  # pragma: no cover
    from tox.config import Parser as ToxParser  # type: ignore

DIST_REQUIREMENTS_SOURCES = ["pyproject.toml", "setup.cfg", "setup.py"]
DEFAULT_REQUIREMENTS_DIRECTORY = "requirements"


def requirements_file(
    toxinidir: t.Union[str, Path],
    envname: str,
    requirements_directory: t.Optional[t.Union[str, Path]] = None,
) -> Path:
    """The environment-specific requirements file for `envname`."""
    return Path(
        toxinidir,
        requirements_directory or DEFAULT_REQUIREMENTS_DIRECTORY,
        f"{envname}.txt",
    )


def other_sources(root: t.Union[str, Path]) -> t.Sequence[Path]:
    """Any other requirements files under `root` that exist."""
    return [
        path
        for path in [
            Path(root, source_file) for source_file in DIST_REQUIREMENTS_SOURCES
        ]
        if path.exists()
    ]


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
        default="--upgrade",
        help=(
            "Custom options passed to `pip-compile` when --pip-compile is used. "
            "Also specify via environment variable PIP_COMPILE_OPTS."
        ),
    )

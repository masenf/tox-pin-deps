"""A tox plugin for pinning dependencies."""
from pathlib import Path
import shlex
import typing as t

try:
    from tox.config.cli.parser import ToxParser  # type: ignore
except ImportError:
    from tox.config import Parser as ToxParser  # type: ignore


ENV_PIP_COMPILE_OPTS = "PIP_COMPILE_OPTS"
CUSTOM_COMPILE_COMMAND = "tox -e {envname} --pip-compile"
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


def custom_command(envname: str, pip_compile_opts: t.Optional[str] = None) -> str:
    """The custom command to include in pip-compile output header."""
    cmd = CUSTOM_COMPILE_COMMAND.format(envname=envname)
    if pip_compile_opts:
        cmd += f" --pip-compile-opts {shlex.quote(pip_compile_opts)}"
    return cmd


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
        default="",
        help=(
            "Custom options passed to `pip-compile` when --pip-compile is used. "
            "Also specify via environment variable PIP_COMPILE_OPTS."
        ),
    )

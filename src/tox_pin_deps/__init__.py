"""A tox plugin for pinning dependencies."""
from pathlib import Path
import shlex
import typing as t


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

"""Generic plugin implementation."""
import abc
from argparse import Namespace
from pathlib import Path
import os
import shlex
import tempfile
import typing as t

from .common import (
    requirements_file,
    other_sources,
)


ENV_PIP_COMPILE_OPTS = "PIP_COMPILE_OPTS"
CUSTOM_COMPILE_COMMAND = "tox -e {envname} --pip-compile"


def custom_command(envname: str, pip_compile_opts: t.Optional[str] = None) -> str:
    """The custom command to include in pip-compile output header."""
    cmd = CUSTOM_COMPILE_COMMAND.format(envname=envname)
    if pip_compile_opts:
        cmd += f" --pip-compile-opts {shlex.quote(pip_compile_opts)}"
    return cmd


class PipCompile(abc.ABC):
    """
    Generic tox4-like installer that uses `pip-compile` or env-specific lock files.

    * `pip_compile` - primary entry point; given a list of deps returns either None
        or the path to an env-specific requirements.txt file.

    Several key abstractmethods / properties must be implemented to have a working
    installer.

    See `tox_pin_deps.plugin4` for the tox4 implementation which subclasses
    this along with `tox.tox_env.python.pip.pip_install.Pip` and passes it
    as the Installer in a new type of execution environment `PinDepsVirtualEnvRunner`.

    See `tox_pin_deps.plugin` for the tox3 implementation which subclasses this
    along with a shim, and instantiates it during `tox_testenv_install_deps`.
    """

    def __init__(self, venv: t.Any, *args: t.Any, **kwargs: t.Any):
        self.venv = venv
        self.env_requirements = requirements_file(
            toxinidir=self.toxinidir,
            envname=self.envname,
        )
        super().__init__(venv, *args, **kwargs)  # type: ignore

    @property
    @abc.abstractmethod
    def options(self) -> Namespace:  # pragma: no cover
        """A Namespace of parsed CLI options."""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def envname(self) -> str:  # pragma: no cover
        """The current testenv's name."""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def toxinidir(self) -> Path:  # pragma: no cover
        """Directory containing `tox.ini` (or similar)."""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def skipsdist(self) -> bool:  # pragma: no cover
        """True if the project has no dist."""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def env_pip_compile_opts_env(self) -> t.Optional[str]:  # pragma: no cover
        """CLI options string from [testenv] pip_compile_opts key."""
        raise NotImplementedError

    @abc.abstractmethod
    def execute(
        self,
        cmd: t.Sequence[str],
        run_id: str,
        env: t.Optional[t.Dict[str, str]] = None,
    ) -> None:  # pragma: no cover
        """Execute the given cmd in the context of `run_id`."""
        raise NotImplementedError

    @property
    def ignore_pins(self) -> bool:
        """True for dot environments or when session used --ignore-pins."""
        return self.options.ignore_pins or self.envname.startswith(".")

    @property
    def want_pip_compile(self) -> bool:
        """True when session used --pip-compile."""
        return bool(self.options.pip_compile)

    @property
    def other_sources(self) -> t.Sequence[Path]:
        """Other project requirements originating from dist files."""
        if not self.skipsdist:
            return other_sources(self.toxinidir)
        return []

    @property
    def pip_compile_opts(self) -> t.Iterable[str]:
        """
        Combined and shlex'd options from 3 pip_compile_opts sources.

        * specified in [testenv] pip_compile_opts
        * specified on cli as --pip-compile-opts
        * specified in the environment as PIP_COMPILE_OPTS

        Options are combined in the order above.
        """
        sources = [
            self.env_pip_compile_opts_env,
            self.options.pip_compile_opts,
            os.environ.get(ENV_PIP_COMPILE_OPTS),
        ]
        return [opt for source in sources for opt in shlex.split(source or "")]

    @property
    def _has_pinned_deps(self) -> bool:
        """True if the per-environment requirements file exists."""
        return self.env_requirements.exists()

    @property
    def _pinned_deps(self) -> str:
        """The deps line for per-environment requirements file."""
        return f"-r{self.env_requirements}"

    def pip_compile(self, deps: t.Sequence[str]) -> t.Optional[str]:
        """
        Lock `deps` using `pip-compile` under certain circumstances.

        If a per-environment requirements file exists and `--pip-compile` was not given, then
        return the existing lock file for pip to install.

        Otherwise, install `pip-tools` and proceed to `pip-compile` the given `deps`
        and any project dist sources (setup.py or pyproject.toml), then return the
        new lock file for pip to install.

        If --ignore-pins if given, then the deps list is not modified.

        :return: replacement item for the `deps` list
        """
        if self.ignore_pins:
            return None
        if not self.want_pip_compile:
            if self._has_pinned_deps:
                # if we have a lock file, use it
                return self._pinned_deps
            # otherwise, regular deps processing
            return None
        self.execute(
            cmd=["pip", "install", "pip-tools"],
            run_id="tox-pin-deps",
        )
        cmd = ["pip-compile"]
        opts = [str(s) for s in self.other_sources] + [
            "--output-file",
            str(self.env_requirements),
            *self.pip_compile_opts,
        ]
        self.env_requirements.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            prefix=f".tox-pin-deps-{self.envname}-requirements.",
            suffix=".in",
            dir=self.toxinidir,
        ) as tf:
            if deps:
                tf.write("\n".join(deps).encode())
                tf.flush()
                cmd.append(tf.name)
            self.execute(
                cmd=cmd + opts,
                run_id="tox-pin-deps",
                env={
                    "CUSTOM_COMPILE_COMMAND": custom_command(
                        envname=self.envname,
                        pip_compile_opts=self.options.pip_compile_opts,
                    )
                },
            )
            # replace environment deps with the new lock file
            return self._pinned_deps

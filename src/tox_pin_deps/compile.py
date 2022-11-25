"""Generic plugin implementation."""
import abc
from argparse import Namespace
from pathlib import Path
import os
import shlex
import tempfile
import typing as t

from . import (
    ENV_PIP_COMPILE_OPTS,
    custom_command,
    requirements_file,
    other_sources,
)


class PipCompile(abc.ABC):
    """Installer that uses `pip-compile` or env-specific lock files."""

    def __init__(self, venv, *args, **kwargs):
        self.venv = venv
        self.env_requirements = requirements_file(
            toxinidir=self.toxinidir,
            envname=self.envname,
        )
        super().__init__(venv, *args, **kwargs)

    @property
    @abc.abstractmethod
    def options(self) -> Namespace:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def envname(self) -> str:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def toxinidir(self) -> Path:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def skipsdist(self) -> bool:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def env_pip_compile_opts_env(self) -> t.Optional[str]:
        raise NotImplementedError

    @abc.abstractmethod
    def execute(self, cmd, run_id, env=None) -> None:
        raise NotImplementedError

    @property
    def ignore_pins(self) -> bool:
        return self.options.ignore_pins or self.envname.startswith(".")

    @property
    def want_pip_compile(self) -> bool:
        return self.options.pip_compile

    @property
    def _has_pinned_deps(self) -> bool:
        return self.env_requirements.exists()

    @property
    def _pinned_deps(self) -> t.Optional[str]:
        return f"-r{self.env_requirements}"

    @property
    def other_sources(self) -> t.Sequence[Path]:
        if not self.skipsdist:
            return other_sources(self.toxinidir)
        return []

    @property
    def pip_compile_opts(self) -> t.Iterable[str]:
        sources = [
            self.env_pip_compile_opts_env,
            self.options.pip_compile_opts,
            os.environ.get(ENV_PIP_COMPILE_OPTS),
        ]
        return [opt for source in sources for opt in shlex.split(source or "")]

    def pip_compile(self, deps: t.Sequence[str]) -> t.Optional[str]:
        if self.ignore_pins:
            return
        if self._has_pinned_deps and not self.want_pip_compile:
            return self._pinned_deps  # if we have a lock file, use it
        if not self.want_pip_compile or not deps or deps == [self._pinned_deps]:
            return
        self.execute(
            cmd=["pip", "install", "pip-tools"],
            run_id="tox-pin-deps",
        )
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
            tf.write("\n".join(deps).encode())
            tf.flush()
            self.execute(
                cmd=["pip-compile", tf.name] + opts,
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

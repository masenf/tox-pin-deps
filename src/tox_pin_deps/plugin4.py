"""Tox 4 implementation."""
import tempfile
import typing as t

from tox.config.cli.parser import DEFAULT_VERBOSITY
from tox.execute.request import StdinSource
from tox.plugin import impl
from tox.tox_env.python.pip.pip_install import Pip
from tox.tox_env.python.pip.req_file import PythonDeps
from tox.tox_env.python.virtual_env.runner import VirtualEnvRunner
from tox.tox_env.register import ToxEnvRegister

from . import (
    custom_command,
    other_sources,
    requirements_file,
    tox_add_argument,
    pip_compile_opts,
)


def _other_sources(toxinidir, pkg_type):
    if pkg_type == "skip":
        return []
    return other_sources(toxinidir)


class PipCompile(Pip):
    """Installer that uses `pip-compile` or env-specific lock files."""

    def __init__(self, venv, *args, **kwargs):
        self.venv = venv
        self.toxinidir = self.venv.core["toxinidir"]
        self.env_requirements = requirements_file(
            toxinidir=self.toxinidir,
            envname=self.venv.name,
        )
        super().__init__(venv, *args, **kwargs)

    @property
    def _pinned_deps(self) -> t.Optional[PythonDeps]:
        if not self.env_requirements.exists():
            return None
        return PythonDeps(
            raw=f"-r{self.env_requirements}",
            root=self.env_requirements.parent,
        )

    def _pip_compile(
        self, arguments: t.Any
    ) -> t.Optional[t.Union[PythonDeps, t.Sequence[PythonDeps]]]:
        if self.venv.options.ignore_pins or self.venv.name.startswith("."):
            return
        if not isinstance(arguments, PythonDeps):
            return
        pinned_deps = self._pinned_deps
        if pinned_deps and not self.venv.options.pip_compile:
            return pinned_deps  # if we have a lock file, use it
        if not self.venv.options.pip_compile or arguments == pinned_deps:
            return
        result = self.venv.execute(
            cmd=["pip", "install", "pip-tools"],
            stdin=StdinSource.OFF,
            run_id="tox-pin-deps",
            show=self.venv.options.verbosity > DEFAULT_VERBOSITY,
        )
        result.assert_success()
        opts = [str(s) for s in _other_sources(self.toxinidir, self.venv.pkg_type)] + [
            "--output-file",
            str(self.env_requirements),
            *pip_compile_opts(envconfig=self.venv.conf, option=self.venv.options),
        ]
        self.env_requirements.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            prefix=f".tox-pin-deps-{self.venv.name}-requirements.",
            suffix=".in",
            dir=self.toxinidir,
        ) as tf:
            if not isinstance(arguments, t.Sequence):
                arguments = [arguments]
            tf.write(
                "\n".join(
                    line for pydeps in arguments for line in pydeps.lines()
                ).encode(),
            )
            tf.flush()
            self.venv.environment_variables["CUSTOM_COMPILE_COMMAND"] = custom_command(
                envname=self.venv.name,
                pip_compile_opts=None,
            )
            result = self.venv.execute(
                cmd=["pip-compile", tf.name] + opts,
                stdin=StdinSource.OFF,
                run_id="tox-pin-deps",
                show=self.venv.options.verbosity > DEFAULT_VERBOSITY,
            )
            result.assert_success()
            # replace environment deps with the new lock file
            return self._pinned_deps

    def install(self, arguments: t.Any, section: str, of_type: str) -> None:
        return super().install(
            arguments=self._pip_compile(arguments) or arguments,
            section=section,
            of_type=of_type,
        )


class PinDepsVirtualEnvRunner(VirtualEnvRunner):
    """Runner that uses PipCompile installer."""

    @staticmethod
    def id() -> str:
        return "virtualenv-pin-deps"

    def register_config(self) -> None:
        super().register_config()
        self.conf.add_config(
            "pip_compile_opts",
            default="",
            of_type=str,
            desc="Custom options passed to `pip-compile` when --pip-compile is used",
        )

    @property
    def installer(self) -> Pip:
        if self._installer is None:
            self._installer = PipCompile(self)
        return self._installer


@impl
def tox_add_option(parser):
    tox_add_argument(parser)


@impl
def tox_register_tox_env(register: ToxEnvRegister) -> None:
    register.add_run_env(PinDepsVirtualEnvRunner)
    register.default_env_runner = PinDepsVirtualEnvRunner.id()

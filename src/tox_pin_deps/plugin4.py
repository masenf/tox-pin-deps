"""Tox 4 implementation."""
from argparse import Namespace
from pathlib import Path
import typing as t

from tox.config.cli.parser import DEFAULT_VERBOSITY
from tox.execute.request import StdinSource
from tox.plugin import impl
from tox.tox_env.python.pip.pip_install import Pip
from tox.tox_env.python.pip.req_file import PythonDeps
from tox.tox_env.python.virtual_env.runner import VirtualEnvRunner
from tox.tox_env.register import ToxEnvRegister

from . import tox_add_argument
from .compile import PipCompile


class PipCompileInstaller(PipCompile, Pip):
    """Installer that uses `pip-compile` or env-specific lock files."""

    @property
    def toxinidir(self) -> Path:
        return self.venv.core["toxinidir"]

    @property
    def skipsdist(self) -> bool:
        return self.venv.pkg_type == "skip"

    @property
    def envname(self) -> str:
        return self.venv.name

    @property
    def options(self) -> Namespace:
        return self.venv.options

    @property
    def env_pip_compile_opts_env(self) -> t.Optional[str]:
        return self.venv.conf["pip_compile_opts"]

    @staticmethod
    def _deps(arguments: t.Any) -> t.Sequence[str]:
        if not isinstance(arguments, t.Sequence):
            arguments = [arguments]
        return [line for pydeps in arguments for line in pydeps.lines()]

    def execute(self, cmd, run_id, env=None) -> None:
        orig_env = self.venv.environment_variables.copy()
        if env:
            self.venv.environment_variables.update(env)
        result = self.venv.execute(
            cmd=cmd,
            stdin=StdinSource.user_only(),
            run_id=run_id,
            show=self.venv.options.verbosity > DEFAULT_VERBOSITY,
        )
        if orig_env:
            # XXX: slight bug here if env vars were Added, they are not removed
            self.venv.environment_variables.update(orig_env)
        result.assert_success()

    def install(self, arguments: t.Any, section: str, of_type: str) -> None:
        pinned_deps = None
        if isinstance(arguments, PythonDeps):
            pinned_deps_spec = self.pip_compile(deps=self._deps(arguments))
            if pinned_deps_spec:
                pinned_deps = PythonDeps(
                    raw=pinned_deps_spec,
                    root=self.env_requirements.parent,
                )
        return super().install(
            arguments=pinned_deps or arguments,
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
            self._installer = PipCompileInstaller(self)
        return self._installer


@impl
def tox_add_option(parser):
    tox_add_argument(parser)


@impl
def tox_register_tox_env(register: ToxEnvRegister) -> None:
    register.add_run_env(PinDepsVirtualEnvRunner)
    register.default_env_runner = PinDepsVirtualEnvRunner.id()

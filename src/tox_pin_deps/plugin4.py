"""Tox 4 implementation."""
from argparse import Namespace
from pathlib import Path
import typing as t

from tox.config.cli.parser import DEFAULT_VERBOSITY, ToxParser  # type: ignore
from tox.execute.request import StdinSource  # type: ignore
from tox.plugin import impl  # type: ignore
from tox.tox_env.api import ToxEnvCreateArgs  # type: ignore
from tox.tox_env.python.pip.pip_install import Pip  # type: ignore
from tox.tox_env.python.pip.req_file import PythonDeps  # type: ignore
from tox.tox_env.python.virtual_env.runner import VirtualEnvRunner  # type: ignore
from tox.tox_env.register import ToxEnvRegister  # type: ignore

from .common import tox_add_argument
from .compile import PipCompile


class PipCompileInstaller(PipCompile, Pip):  # type: ignore
    """tox4 Installer that uses `pip-compile` or env-specific lock files."""

    @property
    def toxinidir(self) -> Path:
        return Path(self.venv.core["toxinidir"])

    @property
    def skipsdist(self) -> bool:
        return bool(
            self.venv.pkg_type == "skip"
            or self.venv.core.get("skipsdist")
            or self.venv.conf.get("skip_install")
        )

    @property
    def envname(self) -> str:
        return str(self.venv.name)

    @property
    def options(self) -> Namespace:
        return t.cast(Namespace, self.venv.options)

    @property
    def env_pip_compile_opts_env(self) -> t.Optional[str]:
        pip_compile_opts = self.venv.conf["pip_compile_opts"]
        if pip_compile_opts:
            return str(pip_compile_opts)
        return None

    @staticmethod
    def _deps(arguments: t.Any) -> t.Sequence[str]:
        if not isinstance(arguments, t.Sequence):
            arguments = [arguments]
        return [line for pydeps in arguments for line in pydeps.lines()]

    def execute(
        self,
        cmd: t.Sequence[str],
        run_id: str,
        env: t.Optional[t.Dict[str, str]] = None,
    ) -> None:
        orig_env = self.venv.environment_variables.copy()
        if env:
            self.venv.environment_variables.update(env)
        result = self.venv.execute(
            cmd=cmd,
            stdin=StdinSource.user_only(),
            run_id=run_id,
            show=self.venv.options.verbosity > DEFAULT_VERBOSITY,
        )
        if orig_env and env:
            for key in env:
                self.venv.environment_variables.pop(key, None)
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
        super().install(
            arguments=pinned_deps or arguments,
            section=section,
            of_type=of_type,
        )


class PinDepsVirtualEnvRunner(VirtualEnvRunner):  # type: ignore
    """EnvRunner that uses PipCompileInstaller."""

    def __init__(self, create_args: ToxEnvCreateArgs):
        self._installer: t.Optional[PipCompileInstaller] = None
        super().__init__(create_args=create_args)

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


@impl  # type: ignore
def tox_add_option(parser: ToxParser) -> None:
    tox_add_argument(parser)


@impl  # type: ignore
def tox_register_tox_env(register: ToxEnvRegister) -> None:
    """tox4 entry point: set PinDepsVirtualEnvRunner as default_env_runner."""
    register.add_run_env(PinDepsVirtualEnvRunner)
    register.default_env_runner = PinDepsVirtualEnvRunner.id()

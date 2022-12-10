"""Tox 4 implementation."""
from argparse import Namespace
from pathlib import Path
import typing as t

from tox.config.cli.parser import DEFAULT_VERBOSITY, ToxParser
from tox.execute.request import StdinSource
from tox.plugin import impl
from tox.tox_env.api import ToxEnvCreateArgs
from tox.tox_env.python.pip.pip_install import Pip
from tox.tox_env.python.pip.req_file import PythonDeps
from tox.tox_env.python.virtual_env.runner import VirtualEnvRunner
from tox.tox_env.register import ToxEnvRegister

from .common import tox_add_argument
from .compile import PipCompile


class PipCompileInstaller(PipCompile, Pip):
    """tox4 Installer that uses `pip-compile` or env-specific lock files."""

    @property
    def toxinidir(self) -> Path:
        return Path(self.venv.core["toxinidir"])

    @property
    def skipsdist(self) -> bool:
        return bool(
            self.venv.pkg_type == "skip"
            or self.venv.core["skipsdist"]
            or self.venv.conf["skip_install"]
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

    @property
    def env_pip_pre(self) -> bool:
        """[testenv] pip_pre value."""
        return bool(self.venv.conf["pip_pre"])

    @staticmethod
    def _deps(pydeps: PythonDeps) -> t.Sequence[str]:
        return pydeps.lines()

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
        compile_deps = None
        if isinstance(arguments, PythonDeps):
            compile_deps = self._deps(arguments)
        elif arguments is None:
            compile_deps = []

        pinned_deps = None
        if compile_deps is not None:
            pinned_deps_spec = self.pip_compile(deps=compile_deps)
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


class PinDepsVirtualEnvRunner(VirtualEnvRunner):
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


@impl
def tox_add_option(parser: ToxParser) -> None:
    tox_add_argument(parser)


@impl
def tox_register_tox_env(register: ToxEnvRegister) -> None:
    """tox4 entry point: set PinDepsVirtualEnvRunner as default_env_runner."""
    register.add_run_env(PinDepsVirtualEnvRunner)
    register.default_env_runner = PinDepsVirtualEnvRunner.id()

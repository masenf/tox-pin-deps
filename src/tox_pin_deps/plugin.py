"""Tox 3 implementation."""
from argparse import Namespace
from pathlib import Path
import typing as t

from tox import hookimpl
from tox.config import DepConfig

from . import requirements_file, tox_add_argument
from .compile import PipCompile


class ShimBase:
    def __init__(self, *args, **kwargs):
        """allow the constructor to ignore arbitrary args"""


class PipCompileTox3(PipCompile, ShimBase):
    def __init__(self, venv, action):
        self.action = action
        super().__init__(venv)

    @property
    def toxinidir(self) -> Path:
        return Path(self.venv.envconfig.config.toxinidir)

    @property
    def skipsdist(self) -> bool:
        return self.venv.envconfig.skip_install or self.venv.envconfig.config.skipsdist

    @property
    def envname(self) -> str:
        return self.venv.envconfig.envname

    @property
    def options(self) -> Namespace:
        return self.venv.envconfig.config.option

    @property
    def env_pip_compile_opts_env(self) -> t.Optional[str]:
        return self.venv.envconfig.pip_compile_opts

    def execute(self, cmd, run_id, env=None) -> None:
        self.action.setactivity(run_id, str(cmd))
        self.venv._pcall(
            cmd,
            cwd=self.venv.path,
            action=self.action,
            env=env,
        )


@hookimpl
def tox_addoption(parser):
    tox_add_argument(parser)
    parser.add_testenv_attribute(
        "pip_compile_opts",
        type="string",
        default=None,
        help="Custom options passed to `pip-compile` when --pip-compile is used",
    )


def _deps(venv):
    try:
        return venv.get_resolved_dependencies()
    except AttributeError:  # pragma: no cover
        # _getresolvedeps was deprecated on tox 3.7.0 in favor of get_resolved_dependencies
        return venv._getresolvedeps()


@hookimpl
def tox_configure(config):
    if config.option.ignore_pins:
        return
    for envconfig in (
        config.envconfigs[envname]
        for envname in config.envlist
        if not envname.startswith(".")  # avoid "internal" environments
    ):
        if config.option.pip_compile:
            # compile mode: --recreate to ensure install_deps will run
            envconfig.recreate = True
        else:
            # normal mode: use per-env lock file, if it exists
            env_requirements = requirements_file(
                toxinidir=config.toxinidir,
                envname=envconfig.envname,
            )
            if env_requirements.exists():
                envconfig.deps = [DepConfig(f"-r{env_requirements}")]


@hookimpl
def tox_testenv_install_deps(venv, action):
    pct3 = PipCompileTox3(venv, action)
    if pct3.ignore_pins:
        return
    pinned_deps_spec = pct3.pip_compile(
        deps=[str(d) for d in _deps(venv)],
    )
    if pinned_deps_spec and pct3.want_pip_compile:
        venv.envconfig.deps = [DepConfig(pinned_deps_spec)]
    return None  # let the next plugin run

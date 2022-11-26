"""Tox 3 implementation."""
from argparse import Namespace
from pathlib import Path
import typing as t

from tox import hookimpl  # type: ignore
from tox.action import Action  # type: ignore
from tox.config import Config, DepConfig, Parser  # type: ignore
from tox.venv import VirtualEnv  # type: ignore

from . import requirements_file
from .common import tox_add_argument
from .compile import PipCompile


class ShimBase:
    def __init__(self, *args: t.Any, **kwargs: t.Any):
        """allow the constructor to ignore arbitrary args"""


class PipCompileTox3(PipCompile, ShimBase):
    """Tox 3-specific implementation of PipCompile."""

    def __init__(self, venv: VirtualEnv, action: Action):
        self.action = action
        super().__init__(venv)

    @property
    def toxinidir(self) -> Path:
        return Path(self.venv.envconfig.config.toxinidir)

    @property
    def skipsdist(self) -> bool:
        return bool(self.venv.envconfig.skip_install) or bool(
            self.venv.envconfig.config.skipsdist
        )

    @property
    def envname(self) -> str:
        return str(self.venv.envconfig.envname)

    @property
    def options(self) -> Namespace:
        return t.cast(Namespace, self.venv.envconfig.config.option)

    @property
    def env_pip_compile_opts_env(self) -> t.Optional[str]:
        if self.venv.envconfig.pip_compile_opts:
            return str(self.venv.envconfig.pip_compile_opts)
        return None

    def execute(
        self,
        cmd: t.Sequence[str],
        run_id: str,
        env: t.Optional[t.Dict[str, str]] = None,
    ) -> None:
        self.action.setactivity(run_id, str(cmd))
        self.venv._pcall(
            cmd,
            cwd=self.venv.path,
            action=self.action,
            env=env,
        )


def _deps(venv: VirtualEnv) -> t.Sequence[DepConfig]:
    try:
        return t.cast(t.Sequence[DepConfig], venv.get_resolved_dependencies())
    except AttributeError:  # pragma: no cover
        # _getresolvedeps was deprecated on tox 3.7.0 in favor of get_resolved_dependencies
        return t.cast(t.Sequence[DepConfig], venv._getresolvedeps())


@hookimpl  # type: ignore
def tox_addoption(parser: Parser) -> None:
    tox_add_argument(parser)
    parser.add_testenv_attribute(
        "pip_compile_opts",
        type="string",
        default=None,
        help="Custom options passed to `pip-compile` when --pip-compile is used",
    )


@hookimpl  # type: ignore
def tox_configure(config: Config) -> None:
    """
    Update envconfigs early if env-specific requirements exist.

    Force `--recreate` when `--pip-compile` is specified.

    Note: this is tox3-only functionality!
        In tox4, the virtualenv re-usability check is more robust,
        allowing for just-in-time replacement of deps without
        triggering environment recreation (as long as the deps match).
    """
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


@hookimpl  # type: ignore
def tox_testenv_install_deps(venv: VirtualEnv, action: Action) -> None:
    """
    tox3 entry point: install deps.

    Always returns `None`, so that the default pip install_deps logic will
    run using the new `deps` updated by this plugin.
    """
    pct3 = PipCompileTox3(venv, action)
    if pct3.ignore_pins:
        return
    pinned_deps_spec = pct3.pip_compile(deps=[str(d) for d in _deps(venv)])
    if pinned_deps_spec and pct3.want_pip_compile:
        # only set the deps if the caller requested `--pip-compile`
        venv.envconfig.deps = [DepConfig(pinned_deps_spec)]
    return None  # let the next plugin run

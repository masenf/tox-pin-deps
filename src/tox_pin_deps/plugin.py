"""Tox 3 implementation."""
import tempfile

from tox import hookimpl
from tox.config import DepConfig

from . import (
    custom_command,
    other_sources,
    pip_compile_opts,
    requirements_file,
    tox_add_argument,
)


def _requirements_file(envconfig):
    return requirements_file(
        envconfig.config.toxinidir,
        envconfig.envname,
    )


def _other_sources(envconfig):
    if envconfig.skip_install or envconfig.config.skipsdist:
        return []
    return other_sources(envconfig.config.toxinidir)


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
            env_requirements = _requirements_file(envconfig)
            if env_requirements.exists():
                envconfig.deps = [DepConfig(f"-r{env_requirements}")]


@hookimpl
def tox_testenv_install_deps(venv, action):
    g_config = venv.envconfig.config
    if g_config.option.ignore_pins:
        return
    if venv.envconfig.envname.startswith("."):
        return
    deps = _deps(venv)
    if g_config.option.pip_compile and deps:
        action.setactivity("installdeps", "pip-tools")
        venv._pcall(
            ["pip", "install", "pip-tools"],
            cwd=venv.path,
            action=action,
        )
        env_requirements = _requirements_file(venv.envconfig)
        opts = [str(s) for s in _other_sources(venv.envconfig)] + [
            "--output-file",
            str(env_requirements),
            *pip_compile_opts(envconfig=venv.envconfig, option=g_config.option),
        ]
        action.setactivity("pip-compile", str(opts))
        env_requirements.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            prefix=f".tox-pin-deps-{venv.envconfig.envname}-requirements.",
            suffix=".in",
            dir=g_config.toxinidir,
        ) as tf:
            tf.write("\n".join(str(d) for d in deps).encode())
            tf.flush()
            venv._pcall(
                ["pip-compile", tf.name] + opts,
                cwd=venv.path,
                action=action,
                env={
                    "CUSTOM_COMPILE_COMMAND": custom_command(
                        envname=venv.envconfig.envname,
                        pip_compile_opts=venv.envconfig.config.option.pip_compile_opts,
                    )
                },
            )
            # replace environment deps with the new lock file
            venv.envconfig.deps = [DepConfig(f"-r{env_requirements}")]
    return None  # let the next plugin run

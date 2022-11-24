import os
from pathlib import Path
import shlex
import tempfile

from tox import hookimpl
from tox.config import DepConfig

ENV_PIP_COMPILE_OPTS = "PIP_COMPILE_OPTS"
CUSTOM_COMPILE_COMMAND = "tox -e {envname} --pip-compile"
DIST_REQUIREMENTS_SOURCES = ["pyproject.toml", "setup.cfg", "setup.py"]


def _requirements_file(envconfig):
    return Path(
        envconfig.config.toxinidir,
        "requirements",
        f"{envconfig.envname}.txt",
    )


def _other_sources(envconfig):
    if envconfig.skip_install or envconfig.config.skipsdist:
        return []
    return [
        path
        for path in [
            Path(envconfig.config.toxinidir, source_file)
            for source_file in DIST_REQUIREMENTS_SOURCES
        ]
        if path.exists()
    ]


@hookimpl
def tox_addoption(parser):
    parser.add_argument(
        "--pip-compile",
        action="store_true",
        default=False,
        help=(
            "Run `pip-compile` on the deps, and copy the result to "
            "{toxinidir}/requirements/{envname}.txt"
        ),
    )
    parser.add_argument(
        "--ignore-pins",
        action="store_true",
        default=False,
        help="Do not replace deps with `requirements` files",
    )
    parser.add_argument(
        "--pip-compile-opts",
        action="store",
        default=None,
        help=(
            "Custom options passed to `pip-compile` when --pip-compile is used. "
            "Also specify via environment variable PIP_COMPILE_OPTS."
        ),
    )
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


def _custom_command(venv):
    cmd = CUSTOM_COMPILE_COMMAND.format(envname=venv.envconfig.envname)
    pip_compile_opts_cli = venv.envconfig.config.option.pip_compile_opts
    if pip_compile_opts_cli:
        cmd += f" --pip-compile-opts {shlex.quote(pip_compile_opts_cli)}"
    return cmd


def _opts(venv):
    sources = [
        venv.envconfig.pip_compile_opts,
        venv.envconfig.config.option.pip_compile_opts,
        os.environ.get(ENV_PIP_COMPILE_OPTS),
    ]
    return [opt for source in sources for opt in shlex.split(source or "")]


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
            *_opts(venv),
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
                env={"CUSTOM_COMPILE_COMMAND": _custom_command(venv)},
            )
            # replace environment deps with the new lock file
            venv.envconfig.deps = [DepConfig(f"-r{env_requirements}")]
    return None  # let the next plugin run

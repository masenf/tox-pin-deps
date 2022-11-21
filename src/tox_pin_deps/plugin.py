import os
from pathlib import Path
import shlex
import tempfile

from tox import hookimpl
from tox.config import DepConfig

ENV_PIP_COMPILE_OPTS = "PIP_COMPILE_OPTS"
CUSTOM_COMPILE_COMMAND = "tox -e {envname} --recreate --pip-compile"


def _requirements_file(venv):
    return Path(
        venv.envconfig.config.toxinidir,
        "requirements",
        f"{venv.envconfig.envname}.txt",
    )


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
def tox_testenv_install_deps(venv, action):
    g_config = venv.envconfig.config
    if g_config.option.ignore_pins:
        return
    env_requirements = _requirements_file(venv)
    deps = _deps(venv)
    if g_config.option.pip_compile and deps:
        action.setactivity("installdeps", "pip-tools")
        venv._pcall(
            ["pip", "install", "pip-tools"],
            cwd=venv.path,
            action=action,
        )
        opts = _opts(venv)
        action.setactivity(
            "pip-compile",
            str(["--output-file", str(env_requirements)] + opts),
        )
        env_requirements.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            prefix=f".tox-pin-deps-{venv.envconfig.envname}-requirements.",
            suffix=".in",
            dir=g_config.toxinidir,
        ) as tf:
            tf.write("\n".join(str(d) for d in deps).encode())
            tf.flush()
            venv._pcall(
                ["pip-compile", tf.name, "--output-file", env_requirements] + opts,
                cwd=venv.path,
                action=action,
                env={"CUSTOM_COMPILE_COMMAND": _custom_command(venv)},
            )
    if env_requirements.exists():
        venv.envconfig.deps = [DepConfig(f"-r{env_requirements}")]

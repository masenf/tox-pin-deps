from pathlib import Path
import tempfile

from tox import hookimpl
from tox.config import DepConfig

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


def _deps(venv):
    try:
        return venv.get_resolved_dependencies()
    except AttributeError:  # pragma: no cover
        # _getresolvedeps was deprecated on tox 3.7.0 in favor of get_resolved_dependencies
        return venv._getresolvedeps()


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
        action.setactivity("pip-compile", "--output-file {}".format(env_requirements))
        env_requirements.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            prefix=f".tox-pin-deps-{venv.envconfig.envname}-requirements.",
            suffix=".in",
            dir=g_config.toxinidir,
        ) as tf:
            tf.write("\n".join(str(d) for d in deps).encode())
            tf.flush()
            venv._pcall(
                ["pip-compile", tf.name, "--output-file", env_requirements],
                cwd=venv.path,
                action=action,
                env={
                    "CUSTOM_COMPILE_COMMAND": CUSTOM_COMPILE_COMMAND.format(
                        envname=venv.envconfig.envname
                    ),
                },
            )
    if env_requirements.exists():
        venv.envconfig.deps = [DepConfig(f"-r{env_requirements}")]

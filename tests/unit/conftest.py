from collections import namedtuple
import re
import sys
import types
from unittest import mock

import attr
import pytest


class ShimBaseMock:
    _instances = []

    def __init__(self, *args, **kwargs):
        self._instances.append(self)
        self._mocks = {}

    def __getattr__(self, name):
        return self._mocks.setdefault(name, mock.Mock())

    @property
    def _install_mock(self):
        return self.__getattr__("install")

    def install(self, *args, **kwargs):
        return self._install_mock(*args, **kwargs)

    @classmethod
    def _get_last_instance_and_reset(cls, assert_n_instances=None):
        if assert_n_instances:
            assert len(cls._instances) == assert_n_instances
        last, cls._instances[:] = cls._instances[-1], []
        return last


def noop_decorator(f, *args, **kwargs):
    if args or kwargs:

        def _noop_decorator_inner():
            return f()

        return _noop_decorator_inner
    return f


@attr.s(frozen=True)
class DepConfig:
    name = attr.ib()


@attr.s(frozen=True)
class PythonDeps:
    raw = attr.ib()
    root = attr.ib(default=None)

    def lines(self):
        return self.raw.splitlines()


SpecialMockSpec = namedtuple("SpecialMockSpec", ["module", "objname", "mockobj"])
MOCK_MODULES = [r"tox(\..+|$)"]
_ORIGINAL_MODULES = []
SPECIAL_MOCKS = [
    SpecialMockSpec("tox.tox_env.python.pip.pip_install", "Pip", ShimBaseMock),
    SpecialMockSpec("tox.plugin", "impl", noop_decorator),
    SpecialMockSpec("tox.config", "DepConfig", DepConfig),
    SpecialMockSpec("tox.tox_env.python.pip.req_file", "PythonDeps", PythonDeps),
    SpecialMockSpec("tox", "hookimpl", noop_decorator),
    SpecialMockSpec("tox.config.cli.parser", "DEFAULT_VERBOSITY", 2),
]


def _save_original_modules():
    for module_pat in MOCK_MODULES:
        module_patc = re.compile(module_pat)
        for module_name in sys.modules:
            if module_patc.match(module_name):
                _ORIGINAL_MODULES.append((module_name, sys.modules.get(module_name)))


@pytest.hookimpl(hookwrapper=True)
def pytest_collection(session):
    """No test module will import tox during collection."""
    _save_original_modules()

    orig_import = __import__

    def import_mock(name, globals_=None, locals_=None, fromlist=(), level=0):
        for module_pat in MOCK_MODULES:
            if re.match(module_pat, name):
                mock_module = mock.MagicMock(__name__=name, spec=types.ModuleType)
                print("mock module: {}".format(mock_module))
                for objname in fromlist or []:
                    for special_mock in SPECIAL_MOCKS:
                        if (
                            name == special_mock.module
                            and objname == special_mock.objname
                        ):
                            setattr(mock_module, objname, special_mock.mockobj)
                            break
                    else:
                        # if we don't find a special mock, then set a regular one
                        setattr(mock_module, objname, mock.Mock(__name__=objname))
                return mock_module
        return orig_import(name, globals_, locals_, fromlist, level)

    with mock.patch("builtins.__import__", side_effect=import_mock):
        yield

    for module_name, orig_module in _ORIGINAL_MODULES:
        if orig_module:
            sys.modules[module_name] = orig_module


@pytest.fixture
def venv_name():
    return "mock-venv"


@pytest.fixture
def options():
    options = mock.Mock()
    options.pip_compile_opts = None
    options.pip_compile = True
    options.ignore_pins = False
    return options


@pytest.fixture
def toxinidir(tmp_path):
    toxinidir = tmp_path / "project_directory"
    toxinidir.mkdir()
    return toxinidir


@pytest.fixture(params=[True, False], ids=["pip_compile", "no_pip_compile"])
def pip_compile(request, options):
    options.pip_compile = request.param
    return request.param


@pytest.fixture(params=[True, False], ids=["ignore_pins", "no_ignore_pins"])
def ignore_pins(request, options):
    options.ignore_pins = request.param
    return request.param


@pytest.fixture(
    params=[[], ["foo"]],
    ids=["deps=[]", "deps=[foo]"],
)
def deps(request):
    return request.param


@pytest.fixture
def deps_present():
    return ["foo"]


@pytest.fixture
def envname(venv):
    if not isinstance(venv.name, mock.Mock):
        return venv.name  # tox4
    return venv.envconfig.envname  # tox3


@pytest.fixture(
    params=[None, True],
    ids=["no_env_requirements", "env_requirements"],
)
def env_requirements(request, envname, toxinidir):
    if request.param:
        rdir = toxinidir / "requirements"
        rdir.mkdir()
        requirements = (rdir / envname).with_suffix(".txt")
        requirements.touch()
        return requirements


@pytest.fixture
def parser():
    return mock.Mock()


@pytest.fixture(
    params=[None, "-v"], ids=["no_PIP_COMPILE_OPTS", "PIP_COMPILE_OPTS='-v'"]
)
def pip_compile_opts_env(request, monkeypatch):
    if request.param:
        monkeypatch.setenv("PIP_COMPILE_OPTS", request.param)
    return request.param


@pytest.fixture(
    params=[None, "--quiet"],
    ids=["no_--pip-compile-opts", "--pip-compile-opts='--quiet'"],
)
def pip_compile_opts_cli(request, options):
    if request.param:
        options.pip_compile_opts = request.param
    return request.param


@pytest.fixture(
    params=[None, "--generate-hashes -v"],
    ids=["no_pip_compile_opts", "pip_compile_opts = --generate-hashes"],
)
def pip_compile_opts_testenv(request):
    return request.param


@pytest.fixture(params=[True, False], ids=["skipsdist", "noskipsdist"])
def skipsdist(request):
    return request.param


@pytest.fixture(params=[True, False], ids=["skip_install", "no_skip_install"])
def skip_install(request):
    return request.param


@pytest.fixture(params=[True, False], ids=["setup.py", "no_setup.py"])
def setup_py(request, toxinidir):
    if request.param:
        setup_py = toxinidir / "setup.py"
        setup_py.touch()
        return setup_py


@pytest.fixture(params=[True, False], ids=["setup.cfg", "no_setup.cfg"])
def setup_cfg(request, toxinidir):
    if request.param:
        setup_cfg = toxinidir / "setup.cfg"
        setup_cfg.touch()
        return setup_cfg


@pytest.fixture(params=[True, False], ids=["pyproject.toml", "no_pyproject.toml"])
def pyproject_toml(request, toxinidir):
    if request.param:
        pyproject_toml = toxinidir / "pyproject.toml"
        pyproject_toml.touch()
        return pyproject_toml

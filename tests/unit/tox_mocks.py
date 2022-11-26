"""The unit tests do NOT depend on tox."""
from collections import namedtuple
import re
import sys
import types
from unittest import mock

import attr


class ShimBaseMock:
    _instances = []

    def __init__(self, *args, **kwargs):
        self._instances.append(self)
        self._mocks = {}

    def __getattr__(self, name):
        return self._mocks.setdefault(name, mock.Mock())

    @classmethod
    def _reset(cls):
        cls._instances[:] = []

    @classmethod
    def _get_last_instance_and_reset(cls, assert_n_instances=None):
        if assert_n_instances:
            assert len(cls._instances) == assert_n_instances
        if cls._instances:
            return cls._instances[-1]
        cls._reset()

    @classmethod
    def _fx_reset(cls):
        yield
        cls._reset()


SpecialMockSpec = namedtuple("SpecialMockSpec", ["module", "objname"])


@attr.s
class MockImportContext:
    MOCK_MODULES = []
    SPECIAL_MOCKS = {}
    __original_import__ = __import__
    _original_modules = attr.ib()
    _mock_modules = attr.ib(factory=list)
    _patch_import_ctx = attr.ib(default=None)

    @_original_modules.default
    def _save_original_modules(self):
        save = []
        for module_pat in self.MOCK_MODULES:
            module_patc = re.compile(module_pat)
            for module_name in sys.modules:
                if module_patc.match(module_name):
                    save.append((module_name, sys.modules.get(module_name)))
        return save

    def import_mock(self, name, globals_=None, locals_=None, fromlist=(), level=0):
        for module_pat in self.MOCK_MODULES:
            if not re.match(module_pat, name):
                continue
            mock_module = mock.MagicMock(__name__=name, spec=types.ModuleType)
            for objname in fromlist or []:
                obj = self.SPECIAL_MOCKS.get(
                    SpecialMockSpec(name, objname),
                    mock.Mock(__name__=objname),
                )
                if isinstance(obj, Exception):
                    raise obj
                setattr(mock_module, objname, obj)
            self._mock_modules.append(mock_module)
            return mock_module
        return self.__original_import__(name, globals_, locals_, fromlist, level)

    def __enter__(self):
        self._patch_import_ctx = mock.patch(
            "builtins.__import__", side_effect=self.import_mock
        )
        self._patch_import_ctx.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._patch_import_ctx.__exit__(exc_type, exc_val, exc_tb)

    def restore(self):
        for module_name, orig_module in self._original_modules:
            if orig_module:
                sys.modules[module_name] = orig_module


def noop_decorator(f, *args, **kwargs):
    if args or kwargs:

        def _noop_decorator_inner(*fargs, **fkwargs):
            return f(*fargs, **fkwargs)

        return _noop_decorator_inner
    return f


@attr.s(frozen=True)
class DepConfig:
    name = attr.ib()


class MockTox3Context(MockImportContext):
    MOCK_MODULES = [r"tox(\..+|$)"]
    SPECIAL_MOCKS = {
        SpecialMockSpec("tox.config", "DepConfig"): DepConfig,
        SpecialMockSpec("tox", "hookimpl"): noop_decorator,
        SpecialMockSpec("tox.plugin", "impl"): ImportError("No tox.plugin in tox3"),
    }


class InstallShim(ShimBaseMock):
    @property
    def _install_mock(self):
        return self.__getattr__("install")

    def install(self, *args, **kwargs):
        return self._install_mock(*args, **kwargs)


class TestEnvShim(ShimBaseMock):
    @property
    def _register_config_mock(self):
        return self.__getattr__("register_config")

    def register_config(self, *args, **kwargs):
        return self._register_config_mock(*args, **kwargs)


@attr.s(frozen=True)
class PythonDeps:
    raw = attr.ib()
    root = attr.ib(default=None)

    def lines(self):
        return self.raw.splitlines()


class MockTox4Context(MockImportContext):
    MOCK_MODULES = [r"tox(\..+|$)"]
    SPECIAL_MOCKS = {
        SpecialMockSpec("tox", "hookimpl"): ImportError("No tox.hookimpl in tox4"),
        SpecialMockSpec("tox.config.cli.parser", "DEFAULT_VERBOSITY"): 2,
        SpecialMockSpec("tox.plugin", "impl"): noop_decorator,
        SpecialMockSpec("tox.tox_env.python.pip.pip_install", "Pip"): InstallShim,
        SpecialMockSpec("tox.tox_env.python.pip.req_file", "PythonDeps"): PythonDeps,
        SpecialMockSpec(
            "tox.tox_env.python.virtual_env.runner", "VirtualEnvRunner"
        ): TestEnvShim,
    }


class MockNoToxContext(MockImportContext):
    MOCK_MODULES = [r"tox(\..+|$)"]
    SPECIAL_MOCKS = {
        SpecialMockSpec("tox", "hookimpl"): ImportError("No tox"),
        SpecialMockSpec("tox.plugin", "impl"): ImportError("No tox"),
    }

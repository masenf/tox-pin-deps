# tox-pin-deps

Run `tox` environments with **_strictly pinned_ dependencies** using simple,
well-maintained tools (you're probably using already) with **no project or code changes.**

This plugin
uses [jazzband/pip-tools](https://github.com/jazzband/pip-tools)' `pip-compile`
to freeze test and project dependencies, save a lock file per-testenv, and have
the locked deps installed, in the usual way via `pip`, on subsequent invocations.

## Usage

1. Install `tox-pin-deps` in the same environment as `tox`.
2. Run `tox --pip-compile` to pin deps for the default `envlist`.
3. Commit files under `{toxinidir}/requirements/*.txt` to version control.
4. Subsequent runs of `tox` will install from the lock file.

* Run `tox --pip-compile` at any time to re-lock dependencies based on:
  * `deps` named in `tox.ini` for the environment
  * Project ("dist") dependencies named in `pyproject.toml`,
    `setup.cfg`, or `setup.py`.
    * Unless `skip_install` or `skipsdist` is true
* Run `tox --ignore-pins` to use the dependencies named in `deps` without
  any special behavior.
* Set `pip_compile_opts = --generate-hashes` in the `testenv` config to enable
  hash-checking mode.
* To always use this plugin, specify `requires = tox-pin-deps` in the `[tox]` section
  of `tox.ini`

## Motivation

This project is designed to enable reproducible test (and runtime) environments without
changing project structure or requiring the use of non-standard tools.

* Use the `deps` and `install_requires`/`[project.dependencies]` that the project already specifies
* Only need `pip-compile` at lock time, not at runtime
* Uses standard, well-supported tooling: `pip` and `virtualenv`

### Why not...?

#### [`tox-constraints`](https://pypi.org/project/tox-constraints/)

* Requires the user to bring their own `constraints.txt`
* `constraints.txt` is a newer concept in the python packaging, which may be unfamiliar.
* `constraints.txt` with hash checking has
  had [serveral](https://github.com/pypa/pip/issues/8792) [issues](https://github.com/pypa/pip/issues/9243)
  since the 2020 pip resolver which make it unsuitable for this use.

#### [`poetry`](https://pypi.org/project/poetry/) / [`tox-poetry`](https://pypi.org/project/tox-poetry/)

* `poetry` is a newer tool that most python programmers haven't worked with.
* `poetry` is a runtime dependency for developing/testing projects.
* Requirements are specified in non-standard `[tool.poetry]` section of `pyproject.toml`.
* If a project isn't already using `poetry`, adopting it for the sole purpose
  of controlling and pinning dependencies constitutes a significant change to
  development and packaging workflows.

#### [`pipenv`](https://pypi.org/project/pipenv/) / [`tox-pipenv`](https://pypi.org/project/tox-pipenv/)

* `pipenv` is slow, non-standard, and _does NOT work for dist projects_
* `pipenv` is older, but still a tool that most python programmers haven't worked with.
* `pipenv` is a runtime dependency for developing/testing projects.
* Requirements are specified in a non-standard `Pipfile` and `Pipfile.lock`.
* If a project isn't already using `pipenv`, adopting it for the sole purpose
  of controlling and pinning dependencies constitutes a significant change to
  development and packaging workflows.
* `tox-pipenv` has behavioral edge cases that make it uncomfortable to work with.

#### [`pip-compile`](https://github.com/jazzband/pip-tools) (directly)

* Need scripts to handle updating / re-locking deps for multiple python versions
* Missing tox `deps` integration for locking test environments

##### [`pip-compile-multi`](https://github.com/peterdemin/pip-compile-multi)

`tox-pin-deps` does essentially the same thing as `pip-compile-multi`, except using the
environment `deps` section as the layer on top of the project's `setup.py`
or `pyproject.toml`, instead of a separate text file.

If a project didn't want to use `tox` for managing test environments,
then `pip-compile-multi` is a great choice for achieving similar ends.



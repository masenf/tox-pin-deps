# tox-pin-deps

Work with per-environment pinned dependencies using simple,
maintainable tools that you already use.

## Usage

if `{toxinidir}/requirements/{envname}-requirements.txt` exists,
then those deps will be used instead of the deps named in tox.ini

unless `--pip-compile` is specified; in that case pass the deps
off to `pip-compile`, write the lock file to the above-mentioned
path and proceed.

if `--ignore-pins` is specified, then this plugin does nothing.
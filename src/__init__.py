"""Neloaica application package.

The package version defined here is the single source of truth.
It is consumed by:

* ``src/main.py`` to set the Qt ``QApplication.applicationVersion()``.
* ``pyproject.toml`` via ``[tool.setuptools.dynamic]`` so ``pip``/``setuptools``
  read the same value when building or installing the package.
* The (future) auto-update service to compare the running version against the
  latest GitHub release.

When cutting a release, bump ``__version__`` here and tag the commit with the
matching ``vX.Y.Z`` tag. The release CI workflow verifies that the tag and the
in-code version match before producing artifacts.
"""

__version__ = "1.0.1"

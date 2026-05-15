"""Verify that a release tag ``vX.Y.Z`` matches ``src.__version__``.

The release workflow runs this between ``actions/checkout`` and the
PyInstaller build to fail fast when someone tags a commit without
bumping ``__version__`` (or vice-versa). Keeping these two in sync is
the contract the auto-updater (PR #4-6) will rely on when it compares
the running version against the latest release.

Exit codes:
    0  the tag matches the package version
    1  mismatch (the workflow step fails)
    2  invalid arguments / cannot read the version

Usage:
    python scripts/verify_tag_matches_version.py vX.Y.Z

Designed to be importable from tests too:

    from scripts.verify_tag_matches_version import normalize_tag, check
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Tuple

SEMVER_RE = re.compile(r"^v?\d+\.\d+\.\d+$")


def normalize_tag(tag: str) -> str:
    """Return the bare ``X.Y.Z`` form of a ``vX.Y.Z`` tag.

    Whitespace is stripped; leading ``v`` is removed if present so the
    result can be compared directly with ``src.__version__``.
    """
    tag = (tag or "").strip()
    if tag.startswith("v"):
        tag = tag[1:]
    return tag


def check(tag: str, package_version: str) -> Tuple[bool, str]:
    """Compare a tag string with the package's ``__version__``.

    Returns ``(ok, message)``. ``message`` is human-readable and is
    suitable for printing to stderr / GitHub Actions logs.
    """
    if not tag or not SEMVER_RE.match(tag.strip()):
        return False, f"Tag {tag!r} is not a SemVer (expected v?X.Y.Z)."
    normalized = normalize_tag(tag)
    if normalized != package_version:
        return (
            False,
            f"Tag {tag} (normalized {normalized}) does not match "
            f"src.__version__ {package_version}.",
        )
    return True, f"Tag {tag} matches src.__version__ {package_version}."


def _read_package_version() -> str:
    """Import ``src.__version__`` without invoking the rest of the package.

    A direct ``from src import __version__`` would import every page,
    pull in PySide6, and slow CI down for no reason. We read the
    ``src/__init__.py`` file directly and pull out the literal.
    """
    init = Path(__file__).resolve().parent.parent / "src" / "__init__.py"
    if not init.is_file():
        raise FileNotFoundError(f"Cannot locate {init}")
    text = init.read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', text)
    if not match:
        raise ValueError(f"Cannot find __version__ in {init}")
    return match.group(1)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: verify_tag_matches_version.py <tag>", file=sys.stderr)
        return 2

    tag = argv[1]
    try:
        package_version = _read_package_version()
    except (OSError, ValueError) as exc:
        print(f"Cannot read package version: {exc}", file=sys.stderr)
        return 2

    ok, message = check(tag, package_version)
    print(message, file=sys.stderr if not ok else sys.stdout)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))

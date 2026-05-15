"""SemVer version representation for the auto-updater.

The updater works with strict ``MAJOR.MINOR.PATCH`` versions — the same
format the release pipeline enforces in
``scripts/verify_tag_matches_version.py``. Any additional SemVer
metadata (pre-release tags, build identifiers) is rejected on purpose
to keep comparisons unambiguous in the field. If we ever need beta /
release-candidate channels they will live in ``UpdateChannel`` instead.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Union

_SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


@dataclass(frozen=True, order=True)
class Version:
    """Immutable ``MAJOR.MINOR.PATCH`` triple with natural ordering.

    ``dataclass(order=True)`` synthesises ``__lt__`` / ``__le__`` etc.
    using the declared field order, which is exactly the SemVer
    precedence we want (major first, then minor, then patch). The
    instance is hashable thanks to ``frozen=True`` so :class:`Version`
    can be used as a dict key in tests.
    """

    major: int
    minor: int
    patch: int

    # ---------------------------------------------------------------
    # Parsing
    # ---------------------------------------------------------------

    @classmethod
    def parse(cls, text: str) -> "Version":
        """Build a :class:`Version` from a string.

        Accepts both ``1.2.3`` and ``v1.2.3``. Whitespace is stripped.
        Anything else (pre-release tags, four-component versions,
        non-numeric segments) raises :class:`ValueError`.
        """
        if not isinstance(text, str):
            raise TypeError(f"Version.parse expects str, got {type(text).__name__}")
        match = _SEMVER_RE.match(text.strip())
        if not match:
            raise ValueError(
                f"Not a SemVer X.Y.Z version: {text!r}. "
                "Pre-release / build metadata is not supported."
            )
        return cls(int(match.group(1)), int(match.group(2)), int(match.group(3)))

    @classmethod
    def coerce(cls, value: Union["Version", str]) -> "Version":
        """Return a :class:`Version` from either an instance or a string.

        Useful at API boundaries where the input could come from
        ``src.__version__`` (string) or from another piece of updater
        code (already-parsed :class:`Version`).
        """
        if isinstance(value, cls):
            return value
        return cls.parse(value)

    # ---------------------------------------------------------------
    # Convenience
    # ---------------------------------------------------------------

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def with_v_prefix(self) -> str:
        """Return the tag-shaped representation: ``vX.Y.Z``."""
        return f"v{self}"

    def is_newer_than(self, other: Union["Version", str]) -> bool:
        """Strict greater-than against another version (string or instance)."""
        return self > Version.coerce(other)

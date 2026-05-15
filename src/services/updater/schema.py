"""Data classes and exceptions shared by every stage of the updater.

The release manifest lives at a stable URL (see ``check.DEFAULT_MANIFEST_URL``)
and has the shape::

    {
      "stable": {
        "version": "1.2.3",
        "download_url": "https://.../Neloaica-v1.2.3-windows.zip",
        "sha256": "abc...",
        "mandatory": false,
        "min_required_version": "1.0.0",
        "release_url": "https://github.com/.../releases/tag/v1.2.3",
        "release_notes_url": "https://github.com/.../releases/tag/v1.2.3"
      },
      "beta": { ... }
    }

Only ``version`` and ``download_url`` are required; everything else has
sensible defaults so the manifest stays forward-compatible with future
fields without breaking older clients.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Optional

from .version import Version


class UpdateChannel(str, Enum):
    """Release channel selector.

    Stored as the lowercase string used in the manifest so it can be
    serialised straight back to JSON.
    """

    STABLE = "stable"
    BETA = "beta"

    @classmethod
    def from_value(cls, value: str) -> "UpdateChannel":
        """Case-insensitive lookup with a friendly error message."""
        try:
            return cls(value.lower().strip())
        except (AttributeError, ValueError) as exc:
            valid = ", ".join(m.value for m in cls)
            raise ValueError(f"Unknown update channel {value!r}. Valid: {valid}.") from exc


class UpdateError(Exception):
    """Base class for everything the updater can raise."""


class UpdateCheckError(UpdateError):
    """Raised when the manifest cannot be fetched or parsed.

    Network errors, malformed JSON, missing channel, malformed version
    strings — all surface as this single type so the caller has one
    ``except`` clause to write.
    """


class UpdateDownloadError(UpdateError):
    """Raised when the release archive cannot be downloaded or verified."""


class UpdateApplyError(UpdateError):
    """Raised when the downloaded archive cannot be applied on disk."""


@dataclass(frozen=True)
class UpdateInfo:
    """Resolved release metadata for a single channel.

    :class:`UpdateInfo` is what :class:`~updater.check.UpdateChecker`
    returns and what the download / apply stages consume. The fields
    mirror the manifest one-to-one with stricter types.
    """

    version: Version
    channel: UpdateChannel
    download_url: str
    sha256: Optional[str] = None
    mandatory: bool = False
    min_required_version: Optional[Version] = None
    release_url: Optional[str] = None
    release_notes_url: Optional[str] = None
    raw: Mapping[str, Any] = field(default_factory=dict)

    # ---------------------------------------------------------------
    # Construction from manifest JSON
    # ---------------------------------------------------------------

    @classmethod
    def from_manifest_entry(cls, channel: UpdateChannel, entry: Mapping[str, Any]) -> "UpdateInfo":
        """Build an :class:`UpdateInfo` from the manifest sub-object.

        Raises :class:`UpdateCheckError` if required fields are missing
        or any version string is malformed. Unknown fields are
        preserved in ``raw`` so callers can read them without losing
        information.
        """
        if not isinstance(entry, Mapping):
            raise UpdateCheckError(
                f"Channel {channel.value!r} entry must be a JSON object, "
                f"got {type(entry).__name__}."
            )

        try:
            version_text = entry["version"]
            download_url = entry["download_url"]
        except KeyError as exc:
            raise UpdateCheckError(
                f"Channel {channel.value!r} is missing required field " f"{exc.args[0]!r}."
            ) from exc

        try:
            version = Version.parse(version_text)
        except (TypeError, ValueError) as exc:
            raise UpdateCheckError(
                f"Channel {channel.value!r} has invalid version " f"{version_text!r}: {exc}"
            ) from exc

        min_required_raw = entry.get("min_required_version")
        min_required: Optional[Version] = None
        if min_required_raw is not None:
            try:
                min_required = Version.parse(min_required_raw)
            except (TypeError, ValueError) as exc:
                raise UpdateCheckError(
                    f"Channel {channel.value!r} has invalid "
                    f"min_required_version {min_required_raw!r}: {exc}"
                ) from exc

        if not isinstance(download_url, str) or not download_url.strip():
            raise UpdateCheckError(f"Channel {channel.value!r} has empty download_url.")

        return cls(
            version=version,
            channel=channel,
            download_url=download_url.strip(),
            sha256=_coerce_sha256(entry.get("sha256")),
            mandatory=bool(entry.get("mandatory", False)),
            min_required_version=min_required,
            release_url=_coerce_optional_str(entry.get("release_url")),
            release_notes_url=_coerce_optional_str(entry.get("release_notes_url")),
            raw=dict(entry),
        )

    # ---------------------------------------------------------------
    # Predicates the UI / bootstrap will rely on
    # ---------------------------------------------------------------

    def is_newer_than(self, current: Version) -> bool:
        """``True`` if this update advances the version number."""
        return self.version > current

    def requires_upgrade_from(self, current: Version) -> bool:
        """``True`` if the user is below ``min_required_version``.

        Used to surface mandatory upgrades in the UI even when the
        publishing side forgot to flip the ``mandatory`` flag.
        """
        if self.min_required_version is None:
            return False
        return current < self.min_required_version


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------


def _coerce_optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    raise UpdateCheckError(f"Expected string, got {type(value).__name__}: {value!r}")


def _coerce_sha256(value: Any) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise UpdateCheckError(f"sha256 must be a hex string, got {type(value).__name__}")
    text = value.strip().lower()
    if not text:
        return None
    if len(text) != 64 or any(c not in "0123456789abcdef" for c in text):
        raise UpdateCheckError(f"sha256 must be 64 lowercase hex characters, got {text!r}")
    return text


__all__ = [
    "UpdateChannel",
    "UpdateError",
    "UpdateCheckError",
    "UpdateDownloadError",
    "UpdateApplyError",
    "UpdateInfo",
]

"""Fetch and interpret the release manifest.

The manifest lives at a stable raw GitHub URL. Hosting it inside the
repository means a new release simply has to ``git commit`` an
updated ``update-manifest.json`` (PR #7 wires this up automatically
from the release workflow) and every client picks up the change on
its next check.

We deliberately avoid the GitHub Releases API because:

* unauthenticated calls are rate-limited to 60/hour/IP — fine for the
  current single-user install but it does not scale,
* the API cannot express "mandatory" updates or release channels.

The whole module is built around dependency injection: the HTTP
fetcher is a callable that the constructor stores as-is. Tests pass a
fake fetcher; production code uses the default :func:`_urllib_fetcher`
backed by :mod:`urllib.request`.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable, Mapping, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

from .schema import UpdateChannel, UpdateCheckError, UpdateInfo
from .version import Version

logger = logging.getLogger(__name__)

#: URL the in-app updater consults when no override is configured.
#: Lives on ``main`` so a release pipeline run (PR #7) only has to
#: ``git push`` the refreshed manifest to publish a new version.
BUILTIN_MANIFEST_URL = (
    "https://raw.githubusercontent.com/eduard2276/neloaica/main/update-manifest.json"
)

#: Environment variable that overrides :data:`BUILTIN_MANIFEST_URL`.
#: Set this when running an unreleased build against a manifest hosted
#: on a feature branch / local file:// path / staging server. Read on
#: every call to :func:`default_manifest_url` so a change at runtime is
#: honoured by the next ``UpdateChecker`` instance.
MANIFEST_URL_ENV_VAR = "NELOAICA_UPDATE_MANIFEST_URL"

DEFAULT_TIMEOUT = 10.0  # seconds
DEFAULT_USER_AGENT = "Neloaica-Updater"

# Backwards-compatible alias for code that imported the original
# constant. New code should call :func:`default_manifest_url` so the
# env override is picked up automatically.
DEFAULT_MANIFEST_URL = BUILTIN_MANIFEST_URL

ManifestFetcher = Callable[[str, float], bytes]


def default_manifest_url() -> str:
    """Resolve the manifest URL, honoring :data:`MANIFEST_URL_ENV_VAR`.

    Called by :class:`UpdateChecker` whenever the caller did not pass
    an explicit ``manifest_url``. Always reads the environment so
    tooling (and tests) can flip the value at runtime.
    """
    override = os.environ.get(MANIFEST_URL_ENV_VAR)
    if override is not None and override.strip():
        return override.strip()
    return BUILTIN_MANIFEST_URL


def _urllib_fetcher(url: str, timeout: float) -> bytes:
    """Default HTTP fetcher built on the standard library.

    Kept tiny and side-effect-free so it can be replaced wholesale in
    tests. The User-Agent is set explicitly because GitHub returns a
    plain 403 for unidentified clients on some endpoints.
    """
    request = Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 (trusted URL)
        return response.read()


class UpdateChecker:
    """Resolve ``current_version`` against the published manifest.

    The constructor only stores configuration; nothing happens until
    :meth:`check` is called. This makes the object cheap to create at
    application boot and easy to unit-test without a network.
    """

    def __init__(
        self,
        current_version: Version,
        *,
        manifest_url: Optional[str] = None,
        channel: UpdateChannel = UpdateChannel.STABLE,
        timeout: float = DEFAULT_TIMEOUT,
        fetcher: Optional[ManifestFetcher] = None,
    ) -> None:
        self._current = current_version
        self._manifest_url = manifest_url or default_manifest_url()
        self._channel = channel
        self._timeout = timeout
        self._fetcher = fetcher or _urllib_fetcher

    # ---------------------------------------------------------------
    # Public surface
    # ---------------------------------------------------------------

    @property
    def current_version(self) -> Version:
        return self._current

    @property
    def channel(self) -> UpdateChannel:
        return self._channel

    @property
    def manifest_url(self) -> str:
        return self._manifest_url

    def check(self) -> Optional[UpdateInfo]:
        """Return :class:`UpdateInfo` if a newer release exists, else None.

        Raises :class:`UpdateCheckError` for any unrecoverable problem
        (network, JSON, schema). Callers performing an automatic check
        on startup should wrap this in ``try/except UpdateCheckError``
        and log the error — a failed check must never crash the app.
        """
        manifest = self._fetch_manifest()
        info = self._resolve_channel(manifest)
        if not info.is_newer_than(self._current):
            logger.debug(
                "No update available for channel %s: latest %s, current %s",
                self._channel.value,
                info.version,
                self._current,
            )
            return None
        logger.info(
            "Update available on channel %s: %s -> %s (mandatory=%s)",
            self._channel.value,
            self._current,
            info.version,
            info.mandatory or info.requires_upgrade_from(self._current),
        )
        return info

    def fetch_manifest(self) -> Mapping[str, Any]:
        """Return the parsed manifest without comparing versions.

        Public for callers that want to surface release notes for *all*
        channels (e.g. a future "Beta available" banner). Same error
        semantics as :meth:`check`.
        """
        return self._fetch_manifest()

    # ---------------------------------------------------------------
    # Internals
    # ---------------------------------------------------------------

    def _fetch_manifest(self) -> Mapping[str, Any]:
        try:
            payload = self._fetcher(self._manifest_url, self._timeout)
        except URLError as exc:
            raise UpdateCheckError(f"Cannot reach manifest at {self._manifest_url}: {exc}") from exc
        except OSError as exc:
            raise UpdateCheckError(f"Network error reaching {self._manifest_url}: {exc}") from exc

        if not payload:
            raise UpdateCheckError(f"Manifest at {self._manifest_url} is empty.")

        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise UpdateCheckError(
                f"Manifest at {self._manifest_url} is not valid JSON: {exc}"
            ) from exc

        if not isinstance(data, Mapping):
            raise UpdateCheckError(
                f"Manifest root must be a JSON object, got " f"{type(data).__name__}."
            )
        return data

    def _resolve_channel(self, manifest: Mapping[str, Any]) -> UpdateInfo:
        try:
            entry = manifest[self._channel.value]
        except KeyError as exc:
            raise UpdateCheckError(
                f"Manifest has no entry for channel {self._channel.value!r}. "
                f"Available: {sorted(manifest.keys())}."
            ) from exc
        return UpdateInfo.from_manifest_entry(self._channel, entry)


__all__ = [
    "BUILTIN_MANIFEST_URL",
    "DEFAULT_MANIFEST_URL",
    "DEFAULT_TIMEOUT",
    "DEFAULT_USER_AGENT",
    "MANIFEST_URL_ENV_VAR",
    "ManifestFetcher",
    "UpdateChecker",
    "default_manifest_url",
]

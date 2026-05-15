#!/usr/bin/env python3
"""Update ``update-manifest.json`` for a freshly published release.

Invoked by ``.github/workflows/release.yml`` once the GitHub Release
has been created and the artifact uploaded:

    python scripts/update_manifest.py \
        --version 1.2.3 \
        --channel stable \
        --sha256 <hex> \
        --owner eduard2276 \
        --repo neloaica \
        --asset Neloaica-v1.2.3-windows.zip \
        --manifest update-manifest.json

The script is intentionally side-effect-light: it ONLY rewrites the
manifest file. The workflow handles ``git commit`` / ``git push``
separately. Re-running with the same arguments is a no-op (idempotent)
so a workflow re-run after a transient failure is safe.

Exit codes:
    0 - manifest written (or already up to date).
    1 - validation / input error.
    2 - manifest file missing or unreadable.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Mapping

VALID_CHANNELS = ("stable", "beta")
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update the release manifest after a successful build.",
    )
    parser.add_argument("--version", required=True, help="New version, X.Y.Z.")
    parser.add_argument(
        "--channel",
        default="stable",
        choices=VALID_CHANNELS,
        help="Manifest channel to update (default: stable).",
    )
    parser.add_argument("--sha256", required=True, help="SHA-256 of the asset (hex).")
    parser.add_argument("--owner", required=True, help="GitHub owner / user.")
    parser.add_argument("--repo", required=True, help="GitHub repository name.")
    parser.add_argument(
        "--asset",
        required=True,
        help="Asset filename uploaded to the release (e.g. Neloaica-v1.2.3-windows.zip).",
    )
    parser.add_argument(
        "--manifest",
        default="update-manifest.json",
        help="Path to the manifest file (default: ./update-manifest.json).",
    )
    parser.add_argument(
        "--mandatory",
        action="store_true",
        help="Mark this release as mandatory (clients are forced to upgrade).",
    )
    parser.add_argument(
        "--min-required-version",
        default=None,
        help="If set, oldest version allowed to keep running (X.Y.Z).",
    )
    return parser.parse_args(argv)


def normalize_version(value: str) -> str:
    text = value.strip().lstrip("v")
    if not _SEMVER_RE.match(text):
        raise ValueError(f"Not a SemVer X.Y.Z version: {value!r}")
    return text


def normalize_sha256(value: str) -> str:
    text = value.strip().lower()
    if not _SHA256_RE.match(text):
        raise ValueError(f"Not a 64-character lowercase hex SHA-256: {value!r}")
    return text


def build_entry(args: argparse.Namespace) -> dict:
    """Render the manifest entry for the given release arguments."""
    version = normalize_version(args.version)
    sha256 = normalize_sha256(args.sha256)
    min_required = (
        normalize_version(args.min_required_version) if args.min_required_version else "0.0.0"
    )

    base = f"https://github.com/{args.owner}/{args.repo}/releases"
    download_url = f"{base}/download/v{version}/{args.asset}"
    release_url = f"{base}/tag/v{version}"

    return {
        "version": version,
        "download_url": download_url,
        "sha256": sha256,
        "mandatory": bool(args.mandatory),
        "min_required_version": min_required,
        "release_url": release_url,
        "release_notes_url": release_url,
    }


def update_manifest(manifest_path: Path, channel: str, entry: Mapping) -> bool:
    """Write ``entry`` under ``channel`` in ``manifest_path``.

    Returns ``True`` if the file content changed. Existing other
    channels and unrelated top-level keys (e.g. ``$schema``) are
    preserved verbatim.
    """
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    text_before = manifest_path.read_text(encoding="utf-8")
    try:
        data = json.loads(text_before)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Manifest is not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("Manifest root must be a JSON object.")

    data[channel] = dict(entry)
    text_after = json.dumps(data, indent=2, sort_keys=False) + "\n"

    if text_after == text_before:
        return False

    manifest_path.write_text(text_after, encoding="utf-8")
    return True


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        entry = build_entry(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    manifest_path = Path(args.manifest)
    try:
        changed = update_manifest(manifest_path, args.channel, entry)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if changed:
        print(f"Updated {manifest_path} channel={args.channel} version={entry['version']}")
    else:
        print(f"No changes for {manifest_path} channel={args.channel} version={entry['version']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

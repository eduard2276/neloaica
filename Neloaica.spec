# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Neloaica desktop application.

Onedir layout (instead of onefile) on purpose:
  * Faster startup — no per-launch unpack of an embedded zip into a
    temp folder.
  * Friendlier auto-update — replacing a single `Neloaica.exe`
    inside an already-extracted directory is much simpler than
    swapping a self-extracting executable while it is running.

The release CI workflow (.github/workflows/release.yml) zips the
contents of dist/Neloaica/ and uploads the archive as a GitHub
Release asset on every `vX.Y.Z` tag.
"""

from pathlib import Path

block_cipher = None

PROJECT_ROOT = Path(".").resolve()


def _data_files():
    """Bundle templates and template assets next to the executable.

    PyInstaller's `datas` is a list of `(src, dest)` tuples where dest
    is *relative to the bundle root*. We mirror the dev-mode layout
    (`templates/Template-deviz.xlsx`, `templates/images/...`) so
    `paths.get_bundle_dir() / "templates" / "Template-deviz.xlsx"`
    keeps working under both modes.
    """
    items = [
        (str(PROJECT_ROOT / "templates" / "Template-deviz.xlsx"), "templates"),
    ]
    images_dir = PROJECT_ROOT / "templates" / "images"
    if images_dir.is_dir():
        items.append((str(images_dir), "templates/images"))
    return items


a = Analysis(
    [str(PROJECT_ROOT / "src" / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=_data_files(),
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Neloaica",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Neloaica",
)

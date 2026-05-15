"""Build / release helper scripts.

These modules are not part of the runtime package ``src`` — they are
invoked from CI workflows (e.g. release tag verification, PyInstaller
post-processing). Kept as a package so tests can import them without
``sys.path`` gymnastics.
"""

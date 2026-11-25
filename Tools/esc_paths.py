"""
Where the data are. Notebooks and generators find every data file through these functions, so they work from
any folder and do not depend on where they themselves are stored.

    ROOT                 the repository root
    DATA                 ROOT / 'data' (one subfolder per experiment, see README.md)
    data_folder(name)    DATA / name, created if it does not exist yet (where a generator writes)
    data_file(name)      full path of a data file, found by its file name anywhere under DATA

MATLAB version: esc_paths.m.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'


def data_folder(name: str, create: bool = True) -> Path:
    """DATA / name (for example 'OTO-paired'); created if missing unless create=False."""
    folder = DATA / name
    if create:
        folder.mkdir(parents=True, exist_ok=True)
    return folder


def data_file(name) -> Path:
    """Full path of a data file.

    An absolute path is returned unchanged. Otherwise the file name is looked up anywhere under DATA (it must be
    unique there); if it is not found there, a path relative to the current folder is accepted as a fallback.
    """
    path = Path(name)
    if path.is_absolute():
        return path
    found = sorted(DATA.rglob(path.name))
    if len(found) == 1:
        return found[0]
    if len(found) > 1:
        raise FileNotFoundError(f'{path.name} exists more than once under {DATA}: {[str(p) for p in found]}')
    if path.exists():
        return path
    raise FileNotFoundError(f'{path.name} not found under {DATA}')

"""Create and verify a consistent SQLite snapshot, including live WAL state."""
import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.config import DB_PATH


def backup(destination: Path) -> None:
    destination = destination.expanduser().resolve()
    if destination == DB_PATH.resolve():
        raise ValueError('The backup destination must differ from the live database')
    if destination.exists():
        raise FileExistsError('Backup already exists; choose a new filename')
    if not DB_PATH.exists():
        raise FileNotFoundError('Configured database does not exist')
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sqlite3.connect(DB_PATH) as source, sqlite3.connect(destination) as target:
            source.backup(target)
            if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise RuntimeError('Backup integrity check failed')
        destination.chmod(0o600)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    print(f'Verified database snapshot: {destination}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    backup(parser.parse_args().destination)

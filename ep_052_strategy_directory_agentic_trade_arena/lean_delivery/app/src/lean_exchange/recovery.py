# VERSION HISTORY v1.0.0 · 2026-09-02 · Online SQLite backup and non-overwriting restore with integrity and content-hash verification.
import argparse
from contextlib import closing, contextmanager
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
from uuid import UUID


@contextmanager
def read_only(path):
    source = Path(path).resolve(strict=True)
    if not source.is_file():
        raise ValueError('DATABASE_FILE_REQUIRED')
    db = sqlite3.connect(source.as_uri() + '?mode=ro', uri=True, timeout=15)
    try:
        yield db
    finally:
        db.close()


def manifest(path):
    with read_only(path) as db:
        db.execute('BEGIN')
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or db.execute('PRAGMA foreign_key_check').fetchone():
            raise ValueError('DATABASE_INTEGRITY_FAILED')
        version = db.execute('PRAGMA user_version').fetchone()[0]
        if version != 5:
            raise ValueError('UNSUPPORTED_BACKUP_SCHEMA')
        row = db.execute("SELECT value FROM metadata WHERE key='instance_id'").fetchone()
        if not row:
            raise ValueError('INSTANCE_ID_REQUIRED')
        instance = str(UUID(row[0]))
        tables = {}
        for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall():
            quoted = '"' + name.replace('"', '""') + '"'
            rows = [json.dumps(list(record), ensure_ascii=True, separators=(',', ':'),
                               default=lambda value: {'blob_hex': value.hex()}) for record in db.execute('SELECT * FROM ' + quoted)]
            tables[name] = {'rows': len(rows), 'sha256': sha256('\n'.join(sorted(rows)).encode()).hexdigest()}
        return {'schema_version': version, 'instance_id': instance, 'integrity': 'ok', 'tables': tables,
                'notice': 'Database contains private participant records and credential hashes. Keep it private; one active writer only.'}


def copy_database(source, destination):
    source, destination = Path(source).resolve(strict=True), Path(destination).resolve()
    if source == destination:
        raise ValueError('DISTINCT_DESTINATION_REQUIRED')
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation avoids replacing a live or earlier recovery database.
    descriptor = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    with read_only(source) as origin, closing(sqlite3.connect(destination)) as target:
        origin.backup(target)
    return destination


def backup(source, destination):
    # Validate identity/schema before creating any output. Hash the actual backup, not a later live state.
    manifest(source)
    output = copy_database(source, destination)
    return manifest(output)


def restore(source, destination):
    expected = manifest(source)
    output = copy_database(source, destination)
    actual = manifest(output)
    if actual != expected:
        raise ValueError('RESTORE_CONTENT_MISMATCH')
    return actual


def main():
    parser = argparse.ArgumentParser(description='EP052 private database recovery; never run two writable copies as separate exchanges.')
    parser.add_argument('action', choices=('backup', 'restore', 'inspect'))
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--destination', type=Path)
    args = parser.parse_args()
    if args.action != 'inspect' and args.destination is None:
        parser.error('--destination is required and must not already exist')
    operation = {'backup': backup, 'restore': restore, 'inspect': manifest}[args.action]
    result = operation(args.source) if args.action == 'inspect' else operation(args.source, args.destination)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

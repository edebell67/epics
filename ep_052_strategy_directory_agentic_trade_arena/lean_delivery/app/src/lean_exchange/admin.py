# VERSION HISTORY v1.0.0 · 2026-09-02 · Local-owner bootstrap writes credentials to a new private artifact, never terminal output.
import argparse
import json
import os
from pathlib import Path

from .auth import Authority
from .config import load_settings
from .records import Store


def main():
    parser = argparse.ArgumentParser(description='Local simulation owner provisioning. Requires host filesystem access.')
    parser.add_argument('command', choices=['create-owner'])
    parser.add_argument('--name', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if not args.name.strip() or len(args.name) > 128:
        parser.error('Owner name must contain 1–128 characters')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # O_EXCL refuses accidental overwrite of existing credentials; no credential is printed.
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        credential = Authority(Store(), load_settings()).create_owner(args.name)
        json.dump(credential, stream)
    print('Created local owner credential file:', args.output.resolve())


if __name__ == '__main__':
    main()

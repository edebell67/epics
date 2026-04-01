#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIRECTORIES=(
  "solution"
  "solution/backend"
  "solution/frontend"
  "verification"
  "verification/artifacts"
  "verification/artifacts/exports"
)

printf 'Bootstrapping local MVP quarterly export workspace at %s\n' "$ROOT_DIR"

for relative_path in "${DIRECTORIES[@]}"; do
  target_path="$ROOT_DIR/$relative_path"
  if [[ ! -d "$target_path" ]]; then
    mkdir -p "$target_path"
    printf 'Created %s\n' "$relative_path"
  else
    printf 'Exists   %s\n' "$relative_path"
  fi
done

if [[ -f "$ROOT_DIR/.env.example" && ! -f "$ROOT_DIR/.env" ]]; then
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
  printf 'Created .env from .env.example\n'
elif [[ -f "$ROOT_DIR/.env" ]]; then
  printf 'Exists   .env\n'
else
  printf '.env.example was not found; skipping .env creation.\n' >&2
fi

cat <<'EOF'

Planned API base path: /api/v1
Future backend startup hook:
  - solution/backend should expose the bank-feed, import, and quarterly export services.
Future frontend startup hook:
  - solution/frontend should host the mobile/web client that calls /api/v1.
EOF

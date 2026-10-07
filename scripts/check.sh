#!/usr/bin/env bash
# Run every quality gate for the repository. Used before each phase commit.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Backend"
cd "$ROOT/backend"
if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi
ruff check .
ruff format --check .
pytest

echo "==> Frontend"
cd "$ROOT/frontend"
npm run lint
npm run typecheck
npm test
npm run build

echo "==> All checks passed"

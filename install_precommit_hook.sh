#!/usr/bin/env bash
# install_precommit_hook.sh — copies hooks/pre-commit into .git/hooks/pre-commit.
# Git hooks are never version-controlled themselves, so this copy step is
# required after a fresh clone or whenever hooks/pre-commit changes.
#
# Usage: ./install_precommit_hook.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE="$SCRIPT_DIR/hooks/pre-commit"
TARGET="$SCRIPT_DIR/.git/hooks/pre-commit"

if [[ -f "$TARGET" ]] && ! grep -q "business_owner_map.json" "$TARGET" 2>/dev/null; then
  echo "SKIP — existing .git/hooks/pre-commit doesn't reference our check; back it up and merge by hand: $TARGET"
  exit 1
fi

cp "$SOURCE" "$TARGET"
chmod +x "$TARGET"
echo "OK installed -> $TARGET"

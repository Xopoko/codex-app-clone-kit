#!/bin/zsh
set -euo pipefail
ROOT="${0:A:h:h}"
CONFIG="${CONFIG:-$ROOT/configs/example.variants.json}"
exec "$ROOT/bin/codex-variant" verify --config "$CONFIG" "$@"

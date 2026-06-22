#!/bin/zsh
set -euo pipefail
ROOT="${0:A:h:h}"
CONFIG="${CONFIG:-$ROOT/configs/example.variants.json}"

# Refreshing the model catalog is part of the OpenRouter build path. This
# compatibility wrapper rebuilds only the OpenRouter variant config/model data
# and app bundle through the supported entrypoint.
exec "$ROOT/bin/codex-variant" build --config "$CONFIG" --variant openrouter --replace "$@"

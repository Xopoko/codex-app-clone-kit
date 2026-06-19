#!/bin/zsh
set -euo pipefail
exec "${0:A:h}/openrouter/refresh-model-catalog.zsh" "$@"


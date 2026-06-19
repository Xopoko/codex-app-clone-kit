#!/bin/zsh
set -euo pipefail

APP="${APP:-/Applications/Codex OpenRouter Models.app}"
CODEX_HOME_TARGET="${CODEX_HOME_TARGET:-/Users/max/.codex-openrouter}"
ENV_FILE="${ENV_FILE:-/Users/max/Projects/.env}"

if [[ ! -d "$APP" ]]; then
  print -u2 "App not found: $APP"
  exit 1
fi

if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

print "== codesign =="
codesign --verify --deep --strict --verbose=2 "$APP"

print "== identity =="
plutil -extract CFBundleDisplayName raw -o - "$APP/Contents/Info.plist"
print
plutil -extract CFBundleIdentifier raw -o - "$APP/Contents/Info.plist"
print
plutil -extract CrProductDirName raw -o - "$APP/Contents/Info.plist"
print

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

print "== app.asar patches =="
npx --yes @electron/asar extract "$APP/Contents/Resources/app.asar" "$tmp"
LC_ALL=C grep -abo 's=!1' "$tmp/webview/assets"/model-list-filter-*.js
LC_ALL=C grep -abo 'var w=1000' "$tmp/webview/assets"/model-queries-*.js
LC_ALL=C grep -abo 'limit:1000' "$tmp/webview/assets"/read-service-tier-for-request-*.js

print "== model catalog =="
jq '.models | length' "$CODEX_HOME_TARGET/model-catalog.json"

print "== app-server model/list =="
mkdir -p /Users/max/Documents/Codex/doctor-neutral
CODEX_HOME="$CODEX_HOME_TARGET" node "$(dirname "$0")/probe-model-list.mjs"


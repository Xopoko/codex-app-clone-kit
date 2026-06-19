#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
PROJECT_ROOT="${SCRIPT_DIR:h}"

SOURCE_APP="${SOURCE_APP:-/Applications/Codex.app}"
TARGET_APP="${TARGET_APP:-/Applications/Codex OpenRouter Models.app}"
APP_NAME="${APP_NAME:-Codex OpenRouter Models}"
BUNDLE_ID="${BUNDLE_ID:-com.openai.codex.openrouter}"
URL_SCHEME="${URL_SCHEME:-codex-openrouter}"
CODEX_HOME_TARGET="${CODEX_HOME_TARGET:-/Users/max/.codex-openrouter}"
ENV_FILE="${ENV_FILE:-/Users/max/Projects/.env}"

replace=0
if [[ "${1:-}" == "--replace" ]]; then
  replace=1
fi

if [[ ! -d "$SOURCE_APP" ]]; then
  print -u2 "Source app not found: $SOURCE_APP"
  exit 1
fi

if [[ -d "$TARGET_APP" ]]; then
  if [[ "$replace" != "1" ]]; then
    print -u2 "Target app already exists: $TARGET_APP"
    print -u2 "Re-run with --replace to rebuild it."
    exit 1
  fi
  osascript -e "quit app \"$APP_NAME\"" >/dev/null 2>&1 || true
  sleep 2
  rm -rf "$TARGET_APP"
fi

mkdir -p "$CODEX_HOME_TARGET"

print "== copy app =="
ditto "$SOURCE_APP" "$TARGET_APP"

plist="$TARGET_APP/Contents/Info.plist"
exe="$TARGET_APP/Contents/MacOS/Codex"
bin="$TARGET_APP/Contents/MacOS/Codex.bin"

print "== patch Info.plist =="
/usr/libexec/PlistBuddy -c "Set :CFBundleDisplayName $APP_NAME" "$plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleName $APP_NAME" "$plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier $BUNDLE_ID" "$plist"
/usr/libexec/PlistBuddy -c "Set :CrProductDirName $BUNDLE_ID" "$plist" 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Add :CrProductDirName string $BUNDLE_ID" "$plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleURLTypes:0:CFBundleURLName $APP_NAME" "$plist" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Set :CFBundleURLTypes:0:CFBundleURLSchemes:0 $URL_SCHEME" "$plist" 2>/dev/null || true

print "== install launcher wrapper =="
if [[ ! -f "$bin" ]]; then
  mv "$exe" "$bin"
fi
cat > "$exe" <<EOF
#!/bin/zsh
set -euo pipefail

ENV_FILE="$ENV_FILE"
if [[ -f "\\$ENV_FILE" ]]; then
  set -a
  source "\\$ENV_FILE"
  set +a
fi

export CODEX_HOME="$CODEX_HOME_TARGET"
exec "\\$(dirname "\\$0")/Codex.bin" "\\$@"
EOF
chmod +x "$exe"

print "== write CODEX_HOME config =="
config="$CODEX_HOME_TARGET/config.toml"
if [[ -f "$config" ]]; then
  cp "$config" "$config.backup.$(date -u +%Y%m%dT%H%M%SZ)"
fi
cat > "$config" <<EOF
model = "openrouter/pareto-code"
model_provider = "openrouter"
model_catalog_json = "$CODEX_HOME_TARGET/model-catalog.json"
model_reasoning_effort = "medium"
approval_policy = "never"
sandbox_mode = "danger-full-access"
project_doc_max_bytes = 10485760
personality = "pragmatic"
suppress_unstable_features_warning = true
check_for_update_on_startup = false

[features]
runtime_metrics = false
memories = true
prevent_idle_sleep = true
default_mode_request_user_input = true
artifact = true
goals = true
js_repl = false

[analytics]
enabled = false

[otel]
metrics_exporter = "none"
trace_exporter = "none"

[shell_environment_policy]
inherit = "all"
exclude = ["OPENROUTER_API_KEY"]

[model_providers.openrouter]
name = "OpenRouter"
base_url = "https://openrouter.ai/api/v1"
env_key = "OPENROUTER_API_KEY"
env_key_instructions = "Set OPENROUTER_API_KEY in $ENV_FILE"
wire_api = "responses"
supports_websockets = false
stream_idle_timeout_ms = 300000
http_headers = { "HTTP-Referer" = "https://chatgpt.com/codex-openrouter-local", "X-Title" = "$APP_NAME" }

[projects."/Users/max"]
trust_level = "trusted"

[projects."/Users/max/Projects"]
trust_level = "trusted"

[projects."/Users/max/.codex-care"]
trust_level = "trusted"
EOF

print "== refresh model catalog =="
ENV_FILE="$ENV_FILE" \
CODEX_BIN="$SOURCE_APP/Contents/Resources/codex" \
CODEX_HOME_TARGET="$CODEX_HOME_TARGET" \
"$SCRIPT_DIR/refresh-model-catalog.zsh"

print "== patch app.asar =="
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
npx --yes @electron/asar extract "$TARGET_APP/Contents/Resources/app.asar" "$tmp"
assets="$tmp/webview/assets"

filter_file="$(find "$assets" -maxdepth 1 -name 'model-list-filter-*.js' -type f | head -1)"
queries_file="$(find "$assets" -maxdepth 1 -name 'model-queries-*.js' -type f | head -1)"
service_file="$(find "$assets" -maxdepth 1 -name 'read-service-tier-for-request-*.js' -type f | head -1)"

if [[ -z "$filter_file" || -z "$queries_file" || -z "$service_file" ]]; then
  print -u2 "Could not find expected webview asset files."
  exit 1
fi

perl -0pi -e 's/s=i&&e!==`amazonBedrock`/s=!1/g' "$filter_file"
perl -0pi -e 's/var w=100,T=/var w=1000,T=/g' "$queries_file"
perl -0pi -e 's/limit:100\}\)/limit:1000})/g; s/limit:100,/limit:1000,/g' "$service_file"

grep -q 's=!1' "$filter_file"
grep -q 'var w=1000' "$queries_file"
grep -q 'limit:1000' "$service_file"

npx --yes @electron/asar pack "$tmp" "$TARGET_APP/Contents/Resources/app.asar"
hash="$(shasum -a 256 "$TARGET_APP/Contents/Resources/app.asar" | awk '{print $1}')"
/usr/libexec/PlistBuddy -c "Set :ElectronAsarIntegrity:Resources/app.asar:hash $hash" "$plist"

print "== codesign =="
codesign --force --deep --sign - "$TARGET_APP"
codesign --verify --deep --strict --verbose=2 "$TARGET_APP"

print "== register app =="
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$TARGET_APP" >/dev/null 2>&1 || true

print "Rebuilt $TARGET_APP"
print "ASAR hash: $hash"


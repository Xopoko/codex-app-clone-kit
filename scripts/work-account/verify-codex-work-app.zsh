#!/bin/zsh
set -euo pipefail

APP="${APP:-/Applications/Codex Work.app}"
WORK_HOME="${WORK_HOME:-/Users/max/.codex-work}"
CODEX_BIN="${CODEX_BIN:-$APP/Contents/Resources/codex}"

if [[ ! -d "$APP" ]]; then
  print -u2 "App not found: $APP"
  exit 1
fi

print "== codesign =="
codesign --verify --deep --strict --verbose=2 "$APP"

print "== identity =="
display_name="$(plutil -extract CFBundleDisplayName raw -o - "$APP/Contents/Info.plist")"
bundle_id="$(plutil -extract CFBundleIdentifier raw -o - "$APP/Contents/Info.plist")"
product_dir="$(plutil -extract CrProductDirName raw -o - "$APP/Contents/Info.plist")"
scheme="$(plutil -extract CFBundleURLTypes.0.CFBundleURLSchemes.0 raw -o - "$APP/Contents/Info.plist")"
print "display_name=$display_name"
print "bundle_id=$bundle_id"
print "product_dir=$product_dir"
print "scheme=$scheme"

[[ "$display_name" == "Codex Work" ]]
[[ "$bundle_id" == "com.openai.codex.work" ]]
[[ "$product_dir" == "com.openai.codex.work" ]]
[[ "$scheme" == "codex-work" ]]

print "== wrapper =="
grep -q 'CODEX_HOME="/Users/max/.codex-work"' "$APP/Contents/MacOS/Codex"
test -x "$APP/Contents/MacOS/Codex"
test -x "$APP/Contents/MacOS/Codex.bin"

print "== work home =="
test -f "$WORK_HOME/config.toml"
test -d "$WORK_HOME/plugins"
test -d "$WORK_HOME/skills"
if [[ -f "$WORK_HOME/auth.json" ]]; then
  print "auth_json=present"
else
  print "auth_json=absent"
fi

print "== secret scan =="
if grep -R -E -n '(sk-or-v1-[A-Za-z0-9]{20,}|FIRECRAWL_API_KEY\\s*=\\s*\"[^\\$]|TAVILY_API_KEY\\s*=\\s*\"[^\\$])' "$WORK_HOME/config.toml" "$WORK_HOME"/chrome-native-hosts*.json 2>/dev/null; then
  print -u2 "Unexpected inline secret-like value found in work profile config."
  exit 1
fi

print "== login status =="
set +e
CODEX_HOME="$WORK_HOME" "$CODEX_BIN" login status
login_status=$?
set -e
print "login_status_exit=$login_status"

print "Verification complete. Non-zero login status is expected before work login; zero is expected after work login."

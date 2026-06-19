#!/bin/zsh
set -euo pipefail
setopt NULL_GLOB

SCRIPT_DIR="${0:A:h}"
SOURCE_APP="${SOURCE_APP:-/Applications/Codex.app}"
TARGET_APP="${TARGET_APP:-/Applications/Codex Work.app}"
APP_NAME="${APP_NAME:-Codex Work}"
BUNDLE_ID="${BUNDLE_ID:-com.openai.codex.work}"
URL_SCHEME="${URL_SCHEME:-codex-work}"
PERSONAL_HOME="${PERSONAL_HOME:-/Users/max/.codex}"
WORK_HOME="${WORK_HOME:-/Users/max/.codex-work}"

replace=0
if [[ "${1:-}" == "--replace" ]]; then
  replace=1
fi

if [[ ! -d "$SOURCE_APP" ]]; then
  print -u2 "Source app not found: $SOURCE_APP"
  exit 1
fi

if [[ ! -d "$PERSONAL_HOME" ]]; then
  print -u2 "Personal CODEX_HOME not found: $PERSONAL_HOME"
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

print "== install CODEX_HOME wrapper =="
if [[ ! -f "$bin" ]]; then
  mv "$exe" "$bin"
fi
tmp_wrapper="$(mktemp)"
cat > "$tmp_wrapper" <<'EOF'
#!/bin/zsh
set -euo pipefail

export CODEX_HOME="__WORK_HOME__"
exec "$(dirname "$0")/Codex.bin" "$@"
EOF
perl -0pi -e "s#__WORK_HOME__#${WORK_HOME//\\/\\\\}#g" "$tmp_wrapper"
mv "$tmp_wrapper" "$exe"
chmod +x "$exe"

print "== seed work CODEX_HOME =="
mkdir -p "$WORK_HOME"

for item in AGENTS.md instructions.md config.json models_cache.json version.json cloud-config-bundle-cache.json cloud-requirements-cache.json chrome-native-hosts.json chrome-native-hosts-v2.json; do
  if [[ -e "$PERSONAL_HOME/$item" ]]; then
    rsync -a --delete "$PERSONAL_HOME/$item" "$WORK_HOME/$item"
  fi
done

for dir in skills skills.disabled plugins vendor_imports tools prompts rules mcp-data computer-use; do
  if [[ -d "$PERSONAL_HOME/$dir" ]]; then
    rsync -a --delete "$PERSONAL_HOME/$dir/" "$WORK_HOME/$dir/"
  fi
done

print "== write sanitized config.toml =="
python3 "$SCRIPT_DIR/sanitize-config.py" \
  "$PERSONAL_HOME/config.toml" \
  "$WORK_HOME/config.toml" \
  "$PERSONAL_HOME" \
  "$WORK_HOME"

print "== ensure private state is absent =="
rm -f "$WORK_HOME/auth.json" \
  "$WORK_HOME/history.json" \
  "$WORK_HOME/history.jsonl" \
  "$WORK_HOME/session_index.jsonl" \
  "$WORK_HOME/transcription-history.jsonl" \
  "$WORK_HOME/.codex-global-state.json" \
  "$WORK_HOME/.codex-global-state.json.bak" \
  "$WORK_HOME"/state_*.sqlite* \
  "$WORK_HOME"/logs_*.sqlite* \
  "$WORK_HOME"/memories_*.sqlite* \
  "$WORK_HOME"/goals_*.sqlite*

for dir in sessions archived_sessions shell_snapshots log memories automations attachments generated_images ambient-suggestions browser node_repl process_manager sqlite state-db-backups tmp worktrees; do
  rm -rf "$WORK_HOME/$dir"
done

print "== update copied paths =="
if [[ -f "$WORK_HOME/chrome-native-hosts-v2.json" ]]; then
  perl -0pi -e 's#/Users/max/\\.codex-openrouter#/Users/max/.codex-work#g; s#/Users/max/\\.codex#/Users/max/.codex-work#g; s#/Applications/Codex\\.app#/Applications/Codex Work.app#g; s#/Applications/Codex OpenRouter Models\\.app#/Applications/Codex Work.app#g' "$WORK_HOME/chrome-native-hosts-v2.json"
fi
if [[ -f "$WORK_HOME/chrome-native-hosts.json" ]]; then
  perl -0pi -e 's#/Users/max/\\.codex-openrouter#/Users/max/.codex-work#g; s#/Users/max/\\.codex#/Users/max/.codex-work#g; s#/Applications/Codex\\.app#/Applications/Codex Work.app#g; s#/Applications/Codex OpenRouter Models\\.app#/Applications/Codex Work.app#g' "$WORK_HOME/chrome-native-hosts.json"
fi

print "== codesign =="
codesign --force --deep --sign - "$TARGET_APP"
codesign --verify --deep --strict --verbose=2 "$TARGET_APP"

print "== register app =="
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$TARGET_APP" >/dev/null 2>&1 || true

print "Rebuilt $TARGET_APP"
print "Work CODEX_HOME: $WORK_HOME"

#!/bin/zsh
set -euo pipefail

root="${0:A:h}"

print "== OpenRouter variant =="
if [[ -d "/Applications/Codex OpenRouter Models.app" ]]; then
  "$root/verify-openrouter.zsh"
else
  print "Skipped: /Applications/Codex OpenRouter Models.app is not installed."
fi

print
print "== Work account variant =="
if [[ -d "/Applications/Codex Work.app" ]]; then
  "$root/verify-work-account.zsh"
else
  print "Skipped: /Applications/Codex Work.app is not installed."
fi


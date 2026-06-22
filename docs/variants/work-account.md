# Variant: Work Account

This variant creates a separate Codex app and `CODEX_HOME` for a work login.

Recommended local identity:

```json
{
  "id": "work",
  "display_name": "Codex Work",
  "bundle_id": "com.example.codex.work",
  "url_scheme": "codex-work",
  "dest_app": "/Applications/Codex Work.app",
  "codex_home": "~/.codex-work"
}
```

Build and verify:

```zsh
bin/codex-variant build --config configs/my.variants.json --variant work --replace
bin/codex-variant verify --config configs/my.variants.json --variant work
```

The kit does not copy personal auth/session state. Log in with the intended
account on first launch.

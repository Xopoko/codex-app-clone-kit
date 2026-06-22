# Configuration

`bin/codex-variant` reads a JSON config with one `variants` array.

Minimal variant:

```json
{
  "id": "work",
  "display_name": "Codex Work",
  "bundle_id": "com.example.codex.work",
  "url_scheme": "codex-work",
  "dest_app": "/Applications/Codex Work.app",
  "codex_home": "~/.codex-work",
  "asar_patches": []
}
```

Important fields:

- `source_app`: official source app. Defaults to `/Applications/Codex.app`.
- `display_name`: app name shown by macOS.
- `bundle_id`: unique bundle identifier. Do not reuse `com.openai.codex`.
- `url_scheme`: unique URL scheme.
- `dest_app`: destination `.app`.
- `codex_home`: separate Codex config/state root.
- `env_file`: optional file sourced by the launcher wrapper.
- `env`: extra environment variables exported by the launcher wrapper.
- `codex_config_template`: optional TOML template rendered into
  `<codex_home>/config.toml`.
- `asar_patches`: optional known patches.
- `icon`: optional icon recipe.

Known `asar_patches`:

- `openrouter_model_picker`: shows custom catalog models in the model menu.
- `openrouter_model_limit_1000`: raises model-list related limits from 100 to
  1000 where the current app bundle contains those known minified assets.

Local configs can be ignored with:

```text
configs/*.local.json
configs/local*.json
```

Use local configs for private bundle ids, company logos, usernames, and paths.

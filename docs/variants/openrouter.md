# Variant: OpenRouter

This variant turns Codex into a separate app backed by OpenRouter models.

Recommended local identity:

```json
{
  "id": "openrouter",
  "display_name": "Codex OpenRouter Models",
  "bundle_id": "com.example.codex.openrouter",
  "url_scheme": "codex-openrouter",
  "dest_app": "/Applications/Codex OpenRouter Models.app",
  "codex_home": "~/.codex-openrouter"
}
```

Required:

- `OPENROUTER_API_KEY` in the configured `env_file`.
- `codex_config_template` set to `templates/openrouter-config.toml`.
- `asar_patches` containing:
  - `openrouter_model_picker`
  - `openrouter_model_limit_1000`

Build and verify:

```zsh
bin/codex-variant build --config configs/my.variants.json --variant openrouter --replace
bin/codex-variant verify --config configs/my.variants.json --variant openrouter
```

See [../openrouter.md](../openrouter.md) for implementation details.

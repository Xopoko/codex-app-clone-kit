# OpenRouter Variant

The example OpenRouter variant builds a separate app such as:

```text
/Applications/Codex OpenRouter Models.app
~/.codex-openrouter
```

It expects an env file containing:

```zsh
OPENROUTER_API_KEY=<your-openrouter-api-key>
```

Build:

```zsh
bin/codex-variant build --config configs/my.variants.json --variant openrouter --replace
```

Verify:

```zsh
bin/codex-variant verify --config configs/my.variants.json --variant openrouter
```

What happens during build:

1. `templates/openrouter-config.toml` is rendered into the variant
   `CODEX_HOME`.
2. The OpenRouter model catalog is fetched from
   `https://openrouter.ai/api/v1/models`.
3. The installed Codex bundled model definition is used as a template for
   required model metadata.
4. `model-catalog.json` is written into the variant `CODEX_HOME`.
5. `app.asar` is patched so the custom catalog is visible in the UI.
6. The app is signed ad-hoc and registered with LaunchServices.

The script does not print the API key.

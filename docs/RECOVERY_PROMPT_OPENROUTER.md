# OpenRouter Recovery Prompt

```text
Use this repository to rebuild my local OpenRouter Codex variant.

1. Read README.md, docs/configuration.md, and docs/openrouter.md.
2. Use my local config if I provide one; otherwise copy
   configs/example.variants.json to configs/openrouter.local.json and edit:
   - bundle_id
   - dest_app
   - codex_home
   - env_file containing OPENROUTER_API_KEY
3. Do not print or commit the API key.
4. Build:
   bin/codex-variant build --config configs/openrouter.local.json --variant openrouter --replace
5. Verify:
   bin/codex-variant verify --config configs/openrouter.local.json --variant openrouter
6. Report the installed app path, CODEX_HOME, and any manual login/restart step.
```

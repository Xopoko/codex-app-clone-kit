# Work Variant Recovery Prompt

```text
Use this repository to rebuild my local work Codex variant.

1. Read README.md and docs/configuration.md.
2. Use my local config if I provide one; otherwise copy
   configs/example.variants.json to configs/work.local.json and edit:
   - display_name
   - bundle_id
   - url_scheme
   - dest_app
   - codex_home
   - optional icon recipe
3. Do not copy personal auth/session/history files.
4. Build:
   bin/codex-variant build --config configs/work.local.json --variant work --replace
5. Verify:
   bin/codex-variant verify --config configs/work.local.json --variant work
6. Report the installed app path, CODEX_HOME, and remind me to log in with the
   intended account on first launch.
```

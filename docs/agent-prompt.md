# Agent Prompt

Use this prompt with a coding agent that has local shell access:

```text
You are helping me create a separate local macOS Codex desktop variant.

Use the repository at ./codex-app-clone-kit.

1. Read README.md and docs/configuration.md.
2. Copy configs/example.variants.json to configs/<my-name>.local.json.
3. Create or edit exactly one variant:
   - display name:
   - bundle id:
   - URL scheme:
   - destination app:
   - CODEX_HOME:
   - optional env file:
   - optional icon recipe:
4. Do not copy secrets into the repo.
5. Build with:
   bin/codex-variant build --config configs/<my-name>.local.json --variant <id> --replace
6. Verify with:
   bin/codex-variant verify --config configs/<my-name>.local.json --variant <id>
7. Report the installed app path, CODEX_HOME, and anything I must do manually,
   such as logging in or creating an API key.
```

# Codex App Clone Kit

Canonical local project for creating separate macOS Codex App clones/profiles.

This is the shared home for the same class of work:

- one Codex app for the personal account;
- one Codex app for a work account;
- one Codex app wired to OpenRouter models;
- future app/profile variants with their own `CODEX_HOME`, bundle identity,
  settings, auth, plugin set, and recovery docs.

The original app remains:

```text
/Applications/Codex.app
/Users/max/.codex
```

Each clone should have its own:

- app bundle in `/Applications`;
- `CFBundleIdentifier`;
- display name;
- URL scheme;
- Chromium app data under `~/Library/Application Support/<Display Name>`;
- `CODEX_HOME`;
- rebuild script;
- verify script;
- variant documentation.

## Current Variants

### OpenRouter Models

Purpose: a Codex clone backed by OpenRouter models through a custom model
provider and `model_catalog_json`.

```bash
cd /Users/max/Projects/codex-app-clone-kit
./scripts/rebuild-openrouter.zsh --replace
./scripts/verify-openrouter.zsh
open -a "/Applications/Codex OpenRouter Models.app"
```

Docs:

- [OpenRouter variant](docs/variants/openrouter.md)
- [OpenRouter recovery prompt](docs/RECOVERY_PROMPT_OPENROUTER.md)

Current paths:

```text
App:        /Applications/Codex OpenRouter Models.app
CODEX_HOME: /Users/max/.codex-openrouter
Env:        /Users/max/Projects/.env, OPENROUTER_API_KEY
```

### Work Account

Purpose: a Codex clone for the work ChatGPT/Codex account, with separate OAuth
auth/session state from the personal Codex app.

```bash
cd /Users/max/Projects/codex-app-clone-kit
./scripts/rebuild-work-account.zsh --replace
./scripts/verify-work-account.zsh
open -a "/Applications/Codex Work.app"
```

Docs:

- [Work account variant](docs/variants/work-account.md)
- [Work account recovery prompt](docs/RECOVERY_PROMPT_WORK_ACCOUNT.md)

Current paths:

```text
App:        /Applications/Codex Work.app
CODEX_HOME: /Users/max/.codex-work
Auth:       user logs in manually with the work account
```

## Verify All

```bash
cd /Users/max/Projects/codex-app-clone-kit
./scripts/verify-all.zsh
```

`verify-all` checks all known variants that are currently installed. It does not
log in, mutate accounts, or rebuild apps.

## Adding A New Variant

Use this project instead of creating another one-off clone kit.

Recommended structure:

```text
docs/variants/<variant-name>.md
docs/RECOVERY_PROMPT_<VARIANT_NAME>.md
scripts/<variant-name>/rebuild-*.zsh
scripts/<variant-name>/verify-*.zsh
scripts/rebuild-<variant-name>.zsh
scripts/verify-<variant-name>.zsh
```

Minimum implementation contract:

1. Do not modify `/Applications/Codex.app` or `/Users/max/.codex`.
2. Use a distinct `CODEX_HOME`.
3. Use a distinct bundle id and display name.
4. Do not copy auth/session/history/logs unless the variant explicitly requires
   it and the user asked for it.
5. Keep secrets out of docs, scripts, commits, and shell output.
6. Add a verify script that checks the app identity, wrapper, config, auth
   boundary, and any variant-specific patches.
7. Document what the user must do manually, especially OAuth/login.

## Common Pattern

Most variants are built by:

1. Copying `/Applications/Codex.app` to a new `.app`.
2. Editing `Contents/Info.plist`:
   - `CFBundleDisplayName`
   - `CFBundleName`
   - `CFBundleIdentifier`
   - `CrProductDirName`
   - `CFBundleURLTypes`
3. Moving `Contents/MacOS/Codex` to `Contents/MacOS/Codex.bin`.
4. Replacing `Contents/MacOS/Codex` with a small wrapper that exports the
   variant `CODEX_HOME`.
5. Seeding that `CODEX_HOME` with safe config/plugin/skill state.
6. Applying variant-specific app or config patches.
7. Re-signing the app:

```bash
codesign --force --deep --sign - "/Applications/<Variant>.app"
```

8. Verifying with a variant-specific script.

## Existing Historical Kits

These were the first one-off kits and are now historical snapshots:

```text
/Users/max/Projects/codex-openrouter-models-clone-kit
/Users/max/Projects/codex-work-account-clone-kit
```

The canonical project for future work is now this directory:

```text
/Users/max/Projects/codex-app-clone-kit
```


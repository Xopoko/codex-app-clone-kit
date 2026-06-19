# Codex Work Account Clone Kit

Canonical location: `/Users/max/Projects/codex-app-clone-kit`.
This file documents the `work-account` variant inside the shared Codex App clone
project. Future variants should be added beside it rather than as separate
one-off projects.

Этот проект создаёт отдельный локальный macOS-клон Codex App для рабочего
ChatGPT/Codex аккаунта.

Идея: основной `/Applications/Codex.app` остаётся персональным и использует
`/Users/max/.codex`; рабочий клон `/Applications/Codex Work.app` запускается с
`CODEX_HOME=/Users/max/.codex-work`. Поэтому OAuth/login, сессии, плагины,
скиллы, history и состояние могут жить отдельно.

Проверено локально: 2026-06-19, Codex app `26.616.32156`,
Codex CLI `codex-cli 0.142.0-alpha.1`.

## Быстрое восстановление

```bash
cd /Users/max/Projects/codex-app-clone-kit
./scripts/rebuild-work-account.zsh --replace
./scripts/verify-work-account.zsh
open -a "/Applications/Codex Work.app"
```

После первого запуска нужно вручную войти рабочим аккаунтом через обычный
Codex login/OAuth flow. Этот kit не копирует персональную авторизацию.

## Что создаётся

```text
Source app:       /Applications/Codex.app
Work app:         /Applications/Codex Work.app
Personal home:    /Users/max/.codex
Work home:        /Users/max/.codex-work
Bundle id:        com.openai.codex.work
URL scheme:       codex-work
Display name:     Codex Work
```

## Что копируется из персонального профиля

Копируется стартовый снимок рабочих поверхностей:

- `config.toml`, но с заменой путей на `.codex-work` и без персональных inline
  MCP secrets.
- `config.json`, `AGENTS.md`, `instructions.md`, model/version cache files,
  если они есть.
- `skills/`
- `skills.disabled/`
- `plugins/`
- `vendor_imports/`
- `tools/`
- `prompts/`
- `rules/`
- `mcp-data/`
- `computer-use/`
- browser/chrome native host json files, если они есть.

## Что не копируется

Не копируется личное состояние:

- `auth.json`
- `sessions/`
- `archived_sessions/`
- `session_index.jsonl`
- `history.json`, `history.jsonl`
- `shell_snapshots/`
- `log/`
- sqlite-state files
- `memories/`
- `automations/`
- `attachments/`
- generated images/audio/transcription history
- `.codex-global-state.json`

Цель: рабочий профиль стартует с теми же возможностями и локальными плагинами,
но не наследует персональный аккаунт и личные thread/session данные.

## Config sanitizer

Персональный `config.toml` может содержать inline credentials для MCP, например
`[mcp_servers.*.env]`. Скрипт переносит конфиг, но удаляет env-блоки с
ключами, если внутри есть строки вида:

```text
API_KEY
TOKEN
SECRET
PASSWORD
```

MCP server entry при этом остаётся. Если рабочему профилю нужен тот же MCP с
отдельным рабочим ключом, добавь его уже в `/Users/max/.codex-work/config.toml`
или через переменные окружения рабочего профиля.

## Проверка

```bash
./scripts/verify-work-account.zsh
```

Проверяет:

- `codesign`;
- `CFBundleDisplayName`, `CFBundleIdentifier`, `CrProductDirName`, URL scheme;
- wrapper executable;
- наличие `/Users/max/.codex-work/config.toml`;
- состояние `/Users/max/.codex-work/auth.json`: до первого рабочего login он
  отсутствует, после ручного login он появляется уже как рабочий auth;
- что `CODEX_HOME=/Users/max/.codex-work codex login status` не использует
  персональный home.

До ручного входа рабочим аккаунтом login status ожидаемо будет unauthenticated.
После входа `login status` должен стать authenticated, а `auth.json` в
`.codex-work` уже является нормальным рабочим состоянием.

## Ручной вход рабочим аккаунтом

Открой:

```bash
open -a "/Applications/Codex Work.app"
```

Дальше войди через обычный login в UI. Если UI откроет браузер, выбирай рабочий
аккаунт/организацию. Основной `/Applications/Codex.app` при этом не трогается.

## Если login callback открыл основной Codex

Codex CLI обычно использует локальный callback server для login, но app bundle
также имеет URL scheme. Work-клон регистрирует `codex-work`. Если после
будущего обновления login всё же возвращается в основной Codex:

1. Закрой основной Codex.
2. Запусти только `/Applications/Codex Work.app`.
3. Повтори login.
4. Если не помогло, проверь в новой версии Codex, не стал ли callback scheme
   жёстко `codex://`. Тогда понадобится дополнительный app.asar/CLI-level
   патч, аналогично OpenRouter-клону.

## Recovery prompt

Для будущего Codex:

```text
Прочитай /Users/max/Projects/codex-app-clone-kit/README.md и
восстанови мне /Applications/Codex Work.app. Основной /Applications/Codex.app
и /Users/max/.codex не трогай. Рабочий профиль должен использовать
/Users/max/.codex-work и не копировать auth.json из персонального профиля.
```

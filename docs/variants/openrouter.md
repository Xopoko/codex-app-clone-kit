# Codex OpenRouter Models Clone Kit

Canonical location: `/Users/max/Projects/codex-app-clone-kit`.
This file documents the `openrouter` variant inside the shared Codex App clone
project. Future variants should be added beside it rather than as separate
one-off projects.

Этот проект фиксирует, как был сделан локальный macOS-клон Codex App
`Codex OpenRouter Models.app`, который использует отдельный `CODEX_HOME` и
модели OpenRouter.

Главная цель: если приложение удалится, сломается после обновления Codex или
нужно будет повторить работу на другой машине, будущий Codex должен прочитать
этот документ и восстановить всё без повторного исследования UI и app-server.

Проверено локально: 2026-06-19, macOS, Codex app `26.616.32156`,
Codex CLI `codex-cli 0.142.0-alpha.1`.

## Что получилось

- Основной Codex остаётся в `/Applications/Codex.app`.
- Отдельный клон живёт в `/Applications/Codex OpenRouter Models.app`.
- Клон имеет отдельный bundle id: `com.openai.codex.openrouter`.
- Клон имеет отдельную URL scheme: `codex-openrouter`.
- Клон использует отдельный home: `/Users/max/.codex-openrouter`.
- OpenRouter key берётся из `/Users/max/Projects/.env` через переменную
  `OPENROUTER_API_KEY`.
- Модели берутся из `/Users/max/.codex-openrouter/model-catalog.json`.
- Текущий OpenRouter API на момент проверки отдавал 341 текстовую модель.

## Быстрое восстановление

Если надо заново собрать клон:

```bash
cd /Users/max/Projects/codex-app-clone-kit
./scripts/rebuild-openrouter.zsh --replace
./scripts/verify-openrouter.zsh
open -a "/Applications/Codex OpenRouter Models.app"
```

`--replace` удаляет только целевое приложение
`/Applications/Codex OpenRouter Models.app` и создаёт его заново из
`/Applications/Codex.app`.

## Важные пути

```text
Source app:      /Applications/Codex.app
Clone app:       /Applications/Codex OpenRouter Models.app
Clone CODEX_HOME:/Users/max/.codex-openrouter
OpenRouter env:  /Users/max/Projects/.env
Model catalog:   /Users/max/.codex-openrouter/model-catalog.json
Config:          /Users/max/.codex-openrouter/config.toml
```

## Почему простой config был недостаточен

Backend Codex уже умел возвращать OpenRouter-модели через `model/list`, если
задать `model_provider`, `model_catalog_json` и OpenRouter provider в
`config.toml`.

Но UI Codex App дополнительно фильтровал модели:

1. Через OpenAI/Statsig allowlist `available_models`.
2. Через дефолтный client-side лимит `100` моделей в dropdown.
3. Через отдельный lookup service-tier, который тоже смотрел только первые
   `100` моделей.

Из-за этого:

- сначала подменю `Model` было пустым;
- после отключения allowlist появились модели, но только первая страница;
- после подъёма лимитов до `1000` UI увидел весь текущий каталог OpenRouter.

## Минимальный config.toml

Файл создаётся скриптом в `/Users/max/.codex-openrouter/config.toml`.
Секреты в него не пишутся.

```toml
model = "openrouter/pareto-code"
model_provider = "openrouter"
model_catalog_json = "/Users/max/.codex-openrouter/model-catalog.json"
model_reasoning_effort = "medium"
approval_policy = "never"
sandbox_mode = "danger-full-access"
project_doc_max_bytes = 10485760
personality = "pragmatic"
suppress_unstable_features_warning = true
check_for_update_on_startup = false

[features]
runtime_metrics = false
memories = true
prevent_idle_sleep = true
default_mode_request_user_input = true
artifact = true
goals = true
js_repl = false

[analytics]
enabled = false

[otel]
metrics_exporter = "none"
trace_exporter = "none"

[shell_environment_policy]
inherit = "all"
exclude = ["OPENROUTER_API_KEY"]

[model_providers.openrouter]
name = "OpenRouter"
base_url = "https://openrouter.ai/api/v1"
env_key = "OPENROUTER_API_KEY"
env_key_instructions = "Set OPENROUTER_API_KEY in /Users/max/Projects/.env"
wire_api = "responses"
supports_websockets = false
stream_idle_timeout_ms = 300000
http_headers = { "HTTP-Referer" = "https://chatgpt.com/codex-openrouter-local", "X-Title" = "Codex OpenRouter Models" }
```

Почему `shell_environment_policy.exclude` важен: приложение само может читать
`OPENROUTER_API_KEY` из process env, но агентские shell-команды не должны
унаследовать ключ и случайно записать его в shell snapshots или session logs.

## Каталог моделей

Каталог строится из OpenRouter endpoint:

```text
https://openrouter.ai/api/v1/models
```

Скрипт `scripts/refresh-model-catalog.zsh`:

- читает `/Users/max/Projects/.env`;
- требует `OPENROUTER_API_KEY`;
- берёт bundled model template из `codex debug models --bundled`;
- оставляет только модели с text output;
- сортирует coding/strong-модели выше остальных;
- пишет `/Users/max/.codex-openrouter/model-catalog.json`.

На 2026-06-19 результат был 341 модель.

## App bundle clone

Сборка клона делает следующее:

1. Копирует `/Applications/Codex.app` в
   `/Applications/Codex OpenRouter Models.app`.
2. Меняет `Info.plist`:
   - `CFBundleDisplayName = Codex OpenRouter Models`
   - `CFBundleName = Codex OpenRouter Models`
   - `CFBundleIdentifier = com.openai.codex.openrouter`
   - `CrProductDirName = com.openai.codex.openrouter`
   - URL scheme = `codex-openrouter`
3. Перемещает оригинальный executable:
   - `Contents/MacOS/Codex` -> `Contents/MacOS/Codex.bin`
4. Создаёт wrapper `Contents/MacOS/Codex`, который:
   - source-ит `/Users/max/Projects/.env`;
   - экспортирует `CODEX_HOME=/Users/max/.codex-openrouter`;
   - запускает `Codex.bin`.
5. Создаёт/обновляет `/Users/max/.codex-openrouter/config.toml`.
6. Обновляет каталог моделей.
7. Патчит `Contents/Resources/app.asar`.
8. Обновляет `ElectronAsarIntegrity`.
9. Переподписывает приложение ad-hoc подписью:

```bash
codesign --force --deep --sign - "/Applications/Codex OpenRouter Models.app"
```

## UI patches inside app.asar

Файлы лежат в `webview/assets/` и имеют hash в имени, поэтому после обновления
Codex имена могут измениться. Важно искать по содержимому.

### 1. Отключить OpenAI allowlist

Файл текущей сборки:

```text
model-list-filter-BOpqDcyc.js
```

Суть патча:

```js
s=i&&e!==`amazonBedrock`
```

заменить на:

```js
s=!1
```

Иначе UI при `use_hidden_models=true` показывает только модели из OpenAI
`available_models`, а OpenRouter-модели исчезают.

### 2. Поднять лимит dropdown

Файл текущей сборки:

```text
model-queries-DmmJqKhY.js
```

Суть патча:

```js
var w=100
```

заменить на:

```js
var w=1000
```

Иначе меню Model видит только первые 100 моделей.

### 3. Поднять лимит service-tier lookup

Файл текущей сборки:

```text
read-service-tier-for-request-ha_6r50P.js
```

Суть патча:

```js
limit:100
```

заменить на:

```js
limit:1000
```

Иначе модель за пределами первой сотни может не находиться вспомогательной
логикой service-tier/model lookup.

## Проверка после сборки

```bash
cd /Users/max/Projects/codex-app-clone-kit
./scripts/verify-openrouter.zsh
```

Ожидаемые признаки:

- `codesign` проходит.
- `Info.plist` показывает `CFBundleIdentifier = com.openai.codex.openrouter`.
- В распакованном `app.asar` есть:
  - `s=!1`
  - `var w=1000`
  - `limit:1000`
- `model/list` с `limit=1000` возвращает полный каталог и `nextCursor=null`.

## Диагностика вручную

Проверить список моделей через app-server:

```bash
set -a
source /Users/max/Projects/.env
set +a
CODEX_HOME=/Users/max/.codex-openrouter node ./scripts/probe-model-list.mjs
```

Проверить CLI health из нейтральной папки:

```bash
mkdir -p /Users/max/Documents/Codex/doctor-neutral
cd /Users/max/Documents/Codex/doctor-neutral
set -a
source /Users/max/Projects/.env
set +a
CODEX_HOME=/Users/max/.codex-openrouter \
  /Applications/Codex.app/Contents/Resources/codex doctor --json
```

В неинтерактивном shell `doctor` может показывать overall fail из-за terminal
TTY/env, но `auth` и `reachability` должны быть ok.

## Если после обновления Codex патчи не применяются

Вероятная причина: minified asset filenames или код изменились. Тогда:

1. Распаковать `app.asar`:

```bash
npx --yes @electron/asar extract \
  "/Applications/Codex OpenRouter Models.app/Contents/Resources/app.asar" \
  /tmp/codex-openrouter-asar-debug
```

2. Найти места:

```bash
rg -n "available_models|use_hidden_models|list-models-for-host|limit:100|var w=100|amazonBedrock" \
  /tmp/codex-openrouter-asar-debug/webview/assets
```

3. Повторить три смысла патча:
   - не применять OpenAI allowlist к OpenRouter-каталогу;
   - dropdown должен запрашивать больше 100 моделей;
   - service-tier lookup должен искать больше 100 моделей.

4. Перепаковать, обновить `ElectronAsarIntegrity`, подписать.

## Безопасность

- Никогда не вставлять raw OpenRouter key в README, скрипты, отчёты или логи.
- Не запускать broad `grep` так, чтобы он печатал `.env`.
- После диагностики можно проверить отсутствие raw key pattern:

```bash
grep -R -E -l 'sk-or-v1-[A-Za-z0-9]{20,}' \
  /Users/max/.codex/sessions/2026/06/19 \
  /Users/max/.codex-openrouter 2>/dev/null
```

Эта команда выводит только имена файлов, не значения секретов.

## Что сказать будущему Codex

Можно написать:

```text
Прочитай /Users/max/Projects/codex-app-clone-kit/README.md
и восстанови мне Codex OpenRouter Models app. Ключ лежит в
/Users/max/Projects/.env как OPENROUTER_API_KEY.
```

Если нужно не только восстановить приложение, а ещё понять предыдущую
диагностику, см. также:

```text
/Users/max/.codex/worktrees/3231/.codex-care/reports/2026-06-19T10-47-27Z.md
```

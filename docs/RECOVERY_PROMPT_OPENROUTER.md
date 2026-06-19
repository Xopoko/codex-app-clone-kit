# Recovery prompt

Скопируй этот текст в новый Codex thread, если нужно восстановить приложение:

```text
Прочитай /Users/max/Projects/codex-app-clone-kit/README.md и
восстанови мне локальный macOS-клон Codex OpenRouter Models app.

Ключ OpenRouter уже лежит в /Users/max/Projects/.env как OPENROUTER_API_KEY.
Основной Codex app должен остаться нетронутым в /Applications/Codex.app.
Целевой клон: /Applications/Codex OpenRouter Models.app.

После восстановления проверь:
- codesign;
- Info.plist identity;
- app.asar patches: s=!1, var w=1000, limit:1000;
- app-server model/list с CODEX_HOME=/Users/max/.codex-openrouter возвращает полный каталог OpenRouter.

Не печатай raw key в ответ или логи.
```


# Recovery prompt

```text
Прочитай /Users/max/Projects/codex-app-clone-kit/README.md и
восстанови мне отдельный Codex Work app.

Требования:
- основной /Applications/Codex.app не трогать;
- персональный /Users/max/.codex не менять;
- целевой app: /Applications/Codex Work.app;
- целевой CODEX_HOME: /Users/max/.codex-work;
- скопировать стартовые config/plugins/skills из персонального профиля;
- не копировать auth.json, sessions, history, logs, sqlite-state, memories;
- не переносить inline personal MCP API keys в work config;
- после сборки проверить codesign, Info.plist identity, wrapper, work config и login status.

После этого я сам войду рабочим аккаунтом через обычный Codex login/OAuth.
```


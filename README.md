# Codex Variant Kit

![Codex Variant Kit app variants](assets/readme/hero.png)

Build separate local macOS variants of the Codex desktop app from your official
`/Applications/Codex.app` install.

Use it for:

- a work Codex app with its own login/session state;
- an OpenRouter-backed Codex app with OpenRouter models in the model picker;
- any other local profile with a separate `CODEX_HOME`, bundle id, URL scheme,
  app icon, config, and updater behavior.

The official app stays untouched. Variants are rebuilt from the current
official app and then re-signed ad-hoc.

## What This Does

For each variant, the kit can:

1. copy `/Applications/Codex.app` to a new `.app`;
2. set a unique app name, bundle id, URL scheme, and Chromium profile name;
3. install a wrapper that exports a variant-specific `CODEX_HOME`;
4. optionally source an env file, such as `OPENROUTER_API_KEY`;
5. write a Codex config template;
6. patch `app.asar` for OpenRouter model visibility and model list limits;
7. disable the embedded Sparkle updater in the clone;
8. generate and install variant icons;
9. sign, register, and verify the clone.

## Requirements

- macOS
- official `Codex.app` installed in `/Applications`
- Python 3
- Node.js with `npx`
- Xcode command line tools for `sips`, `iconutil`, `codesign`, and `PlistBuddy`
- Pillow when using composed badge icons:

```zsh
python3 -m pip install --user pillow
```

OpenRouter variants also need an OpenRouter API key in an env file:

```zsh
mkdir -p ~/Projects
printf 'OPENROUTER_API_KEY=<your-openrouter-api-key>\\n' > ~/Projects/.env
chmod 600 ~/Projects/.env
```

Do not commit `.env` or local config files containing private paths or secrets.

## Quickstart

Clone this repo, copy the example config, and edit bundle ids before using it:

```zsh
git clone https://github.com/Xopoko/codex-app-clone-kit.git
cd codex-app-clone-kit
cp configs/example.variants.json configs/my.variants.json
$EDITOR configs/my.variants.json
```

Build one variant:

```zsh
bin/codex-variant build --config configs/my.variants.json --variant openrouter --replace
```

Verify it:

```zsh
bin/codex-variant verify --config configs/my.variants.json --variant openrouter
```

Open it:

```zsh
open -a "Codex OpenRouter Models"
```

After the official Codex app updates, rebuild variants:

```zsh
bin/codex-variant build --config configs/my.variants.json --replace
```

## Commands

```zsh
bin/codex-variant list --config configs/my.variants.json
bin/codex-variant build --config configs/my.variants.json --variant work --replace
bin/codex-variant build --config configs/my.variants.json --variant openrouter --replace
bin/codex-variant verify --config configs/my.variants.json --variant openrouter
bin/codex-variant apply-icon --config configs/my.variants.json --variant openrouter
```

`apply-icon` updates icon resources in an already installed variant without
rebuilding the full app.

## Icon Workflow

You can use a ready 1024x1024 PNG:

```json
"icon": {
  "master_png": "~/Pictures/my-codex-work-icon.png",
  "icns_targets": ["electron.icns", "app.icns", "icon.icns"],
  "png_targets": ["icon-codex-dark.png"]
}
```

Or compose a badge from the local Codex icon at build time:

```json
"icon": {
  "compose_badge": {
    "base_resource_png": "icon-codex-light.png",
    "overlay_png": "assets/openrouter/open-router-dark.png",
    "badge_bg": "#111111",
    "badge_size": 360,
    "logo_size": 280,
    "margin": 42,
    "radius": 82
  }
}
```

See [docs/icons.md](docs/icons.md).

## OpenRouter

The OpenRouter example:

- writes a Codex config using `templates/openrouter-config.toml`;
- fetches `https://openrouter.ai/api/v1/models`;
- builds `model-catalog.json` from the installed Codex bundled model template;
- patches the UI model filter so custom catalog entries appear;
- raises relevant model-list limits from `100` to `1000`;
- installs an OpenRouter badge icon.

See [docs/openrouter.md](docs/openrouter.md).

## Updating

Because variants are modified and ad-hoc signed, the built-in updater cannot
validate official OpenAI update packages for those variants. Update the
official `/Applications/Codex.app` normally, then rebuild variants with this
kit.

## Legal

This project is an unofficial local automation kit. It is not affiliated with
or endorsed by OpenAI, Codex, OpenRouter, or any company whose logo you use.

OpenRouter icon assets in `assets/openrouter/` are from
[`homarr-labs/dashboard-icons`](https://github.com/homarr-labs/dashboard-icons)
under Apache-2.0. Product names and trademarks remain the property of their
owners.

## License

MIT for this kit's scripts and documentation. Third-party assets keep their own
licenses; see their local `NOTICE.md` files.

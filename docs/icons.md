# Icons

The kit supports two icon modes.

## Use A Finished Master PNG

Provide a 1024x1024 PNG:

```json
"icon": {
  "master_png": "~/Pictures/codex-work-master.png",
  "icns_targets": ["electron.icns", "app.icns", "icon.icns"],
  "png_targets": ["icon-codex-dark.png"]
}
```

This is the best option for private company branding because you keep company
assets out of the public repo.

## Compose A Badge At Build Time

Use a PNG overlay plus a base icon from the local Codex bundle:

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

This avoids committing derivative Codex icons to the repo. The final app icon
is generated on the user's machine.

## Make A Master PNG Manually

`icon-badge` can create a 1024x1024 master and small-size preview:

```zsh
bin/codex-variant icon-badge \
  --base-png /Applications/Codex.app/Contents/Resources/icon-codex-dark.png \
  --overlay-png ~/Pictures/company-logo.png \
  --out ~/Pictures/codex-work-company-master.png \
  --preview ~/Pictures/codex-work-company-preview.png \
  --crop-overlay
```

This command requires Pillow.

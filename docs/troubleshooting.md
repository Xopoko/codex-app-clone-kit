# Troubleshooting

## The Clone Cannot Auto-Update

Expected. Variants are modified and re-signed ad-hoc. Update the official
`/Applications/Codex.app`, then rebuild variants:

```zsh
bin/codex-variant build --config configs/my.variants.json --replace
```

## The App Is Still Running

Full rebuild needs to replace the `.app`. Close the variant or let the script
quit it. For icon-only changes, use:

```zsh
bin/codex-variant apply-icon --config configs/my.variants.json --variant <id>
```

## OpenRouter Models Do Not Show Up

Run:

```zsh
bin/codex-variant verify --config configs/my.variants.json --variant openrouter
```

Check that:

- `OPENROUTER_API_KEY` exists in the configured env file;
- `model-catalog.json` exists in the variant `CODEX_HOME`;
- `openrouter_model_picker` is present in `asar_patches`;
- the clone has been restarted after rebuild.

## macOS Shows The Old Icon

macOS caches icons aggressively. Restart the clone first. If Finder or Dock is
still stale, run:

```zsh
touch "/Applications/<Your Variant>.app"
qlmanage -r cache
```

Logging out/in also clears stubborn Dock icon cache entries.

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def run(cmd: list[str], *, check: bool = True, capture: bool = False, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=check,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        env=env,
    )


def require(command: str) -> None:
    if shutil.which(command) is None:
        fail(f"missing required command: {command}")


def expand_path(value: str | None, *, base_dir: Path | None = None) -> Path | None:
    if value is None or value == "":
        return None
    expanded = Path(os.path.expandvars(os.path.expanduser(value)))
    if not expanded.is_absolute() and base_dir is not None:
        expanded = base_dir / expanded
    return expanded


def load_config(path: Path) -> tuple[dict[str, Any], Path]:
    config_path = path.expanduser().resolve()
    with config_path.open("r", encoding="utf-8") as f:
        return json.load(f), config_path.parent


def variants_by_id(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    variants = config.get("variants")
    if not isinstance(variants, list):
        fail("config must contain a variants array")
    out: dict[str, dict[str, Any]] = {}
    for variant in variants:
        variant_id = variant.get("id")
        if not variant_id:
            fail("each variant must have an id")
        out[variant_id] = variant
    return out


def select_variants(config: dict[str, Any], variant_id: str | None) -> list[dict[str, Any]]:
    all_variants = variants_by_id(config)
    if variant_id:
        if variant_id not in all_variants:
            fail(f"unknown variant: {variant_id}")
        return [all_variants[variant_id]]
    return list(all_variants.values())


def plist_read(plist: Path, key: str) -> str:
    res = run(["/usr/libexec/PlistBuddy", "-c", f"Print :{key}", str(plist)], capture=True)
    return res.stdout.strip()


def plist_set(plist: Path, key: str, type_name: str, value: str) -> None:
    set_res = run(["/usr/libexec/PlistBuddy", "-c", f"Set :{key} {value}", str(plist)], check=False, capture=True)
    if set_res.returncode == 0:
        return
    add_res = run(["/usr/libexec/PlistBuddy", "-c", f"Add :{key} {type_name} {value}", str(plist)], check=False, capture=True)
    if add_res.returncode != 0:
        fail(f"failed to set Info.plist key {key}: {add_res.stderr.strip()}")


def plist_set_bool(plist: Path, key: str, value: bool) -> None:
    plist_set(plist, key, "bool", "true" if value else "false")


def verify_source_app(source_app: Path) -> None:
    plist = source_app / "Contents/Info.plist"
    binary = source_app / "Contents/MacOS/Codex"
    if not source_app.is_dir():
        fail(f"source app not found: {source_app}")
    if not plist.is_file():
        fail(f"source Info.plist not found: {plist}")
    if plist_read(plist, "CFBundleIdentifier") != "com.openai.codex":
        fail("source app must be the official com.openai.codex bundle")
    if not os.access(binary, os.X_OK):
        fail(f"source Codex binary is missing or not executable: {binary}")


def variant_paths(config: dict[str, Any], variant: dict[str, Any], base_dir: Path) -> dict[str, Path | None]:
    source_app = expand_path(variant.get("source_app") or config.get("source_app") or "/Applications/Codex.app", base_dir=base_dir)
    dest_app = expand_path(variant.get("dest_app"), base_dir=base_dir)
    codex_home = expand_path(variant.get("codex_home"), base_dir=base_dir)
    env_file = expand_path(variant.get("env_file"), base_dir=base_dir)
    if source_app is None or dest_app is None or codex_home is None:
        fail(f"variant {variant.get('id')} requires source_app, dest_app, and codex_home")
    return {"source_app": source_app, "dest_app": dest_app, "codex_home": codex_home, "env_file": env_file}


def quit_if_running(dest_app: Path, bundle_id: str, display_name: str, *, timeout_s: float = 15.0) -> None:
    run(["/usr/bin/osascript", "-e", f'tell application id "{bundle_id}" to quit'], check=False, capture=True)
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        res = run(["/usr/bin/pgrep", "-f", f"{dest_app}/Contents/"], check=False, capture=True)
        if res.returncode != 0:
            return
        time.sleep(0.5)
    fail(f"{display_name} is still running; close it and rerun with --replace")


def write_launcher(app: Path, variant: dict[str, Any], codex_home: Path, env_file: Path | None) -> None:
    launcher = app / "Contents/MacOS/Codex"
    real_binary = app / "Contents/MacOS/Codex.bin"
    user_data_dir = expand_path(
        variant.get("user_data_dir") or (Path.home() / "Library/Application Support" / variant["display_name"]),
        base_dir=Path.cwd(),
    )
    assert user_data_dir is not None
    if not launcher.exists():
        fail(f"source launcher missing: {launcher}")
    if real_binary.exists():
        real_binary.unlink()
    launcher.rename(real_binary)

    env_lines: list[str] = []
    if env_file is not None:
        env_lines.extend(
            [
                f'ENV_FILE="{env_file}"',
                'if [[ -f "$ENV_FILE" ]]; then',
                "  set -a",
                '  source "$ENV_FILE"',
                "  set +a",
                "fi",
                "",
            ]
        )

    for key, value in (variant.get("env") or {}).items():
        env_lines.append(f'export {key}="{value}"')
    env_lines.append(f'export CODEX_HOME="{codex_home}"')
    env_lines.append(f'CHROMIUM_USER_DATA_DIR="{user_data_dir}"')

    content = "\n".join(
        [
            "#!/bin/zsh",
            "set -euo pipefail",
            "",
            *env_lines,
            "has_user_data_dir=0",
            'for arg in "$@"; do',
            '  case "$arg" in',
            "    --user-data-dir|--user-data-dir=*) has_user_data_dir=1 ;;",
            "  esac",
            "done",
            "",
            'if [[ "$has_user_data_dir" == "1" ]]; then',
            '  exec "$(dirname "$0")/Codex.bin" "$@"',
            "else",
            '  exec "$(dirname "$0")/Codex.bin" --user-data-dir="$CHROMIUM_USER_DATA_DIR" "$@"',
            "fi",
            "",
        ]
    )
    launcher.write_text(content, encoding="utf-8")
    launcher.chmod(0o755)
    real_binary.chmod(0o755)


def render_template(template: str, values: dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    return rendered


def write_codex_config(variant: dict[str, Any], paths: dict[str, Path | None], base_dir: Path) -> None:
    config_template = variant.get("codex_config_template")
    if not config_template:
        return
    template_path = expand_path(config_template, base_dir=base_dir)
    if template_path is None or not template_path.is_file():
        fail(f"codex_config_template not found: {config_template}")

    codex_home = paths["codex_home"]
    assert codex_home is not None
    codex_home.mkdir(parents=True, exist_ok=True)

    env_file = paths["env_file"]
    values = {
        "APP_NAME": str(variant["display_name"]),
        "BUNDLE_ID": str(variant["bundle_id"]),
        "URL_SCHEME": str(variant["url_scheme"]),
        "CODEX_HOME": str(codex_home),
        "ENV_FILE": "" if env_file is None else str(env_file),
        "MODEL_CATALOG_JSON": str(codex_home / "model-catalog.json"),
    }
    rendered = render_template(template_path.read_text(encoding="utf-8"), values)
    out = codex_home / "config.toml"
    if out.exists():
        backup = out.with_name(f"config.toml.backup.{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}")
        shutil.copy2(out, backup)
    out.write_text(rendered, encoding="utf-8")


def parse_env_file(path: Path | None) -> dict[str, str]:
    if path is None or not path.exists():
        return {}
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        result[key] = value
    return result


def refresh_openrouter_catalog(variant: dict[str, Any], paths: dict[str, Path | None]) -> None:
    openrouter = variant.get("openrouter") or {}
    if not openrouter.get("refresh_model_catalog"):
        return
    env_file = paths["env_file"]
    env_values = parse_env_file(env_file)
    api_key = os.environ.get("OPENROUTER_API_KEY") or env_values.get("OPENROUTER_API_KEY")
    if not api_key:
        fail("OPENROUTER_API_KEY is required to refresh the OpenRouter model catalog")

    source_app = paths["source_app"]
    codex_home = paths["codex_home"]
    assert source_app is not None and codex_home is not None
    codex_bin = source_app / "Contents/Resources/codex"
    bundled = run([str(codex_bin), "debug", "models", "--bundled"], capture=True)
    bundled_json = json.loads(bundled.stdout)
    template = bundled_json["models"][0]

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/models",
        headers={
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": openrouter.get("http_referer", "https://chatgpt.com/codex-openrouter-local"),
            "X-Title": variant["display_name"],
        },
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))

    def has_text_output(model: dict[str, Any]) -> bool:
        return "text" in ((model.get("architecture") or {}).get("output_modalities") or [])

    def has_image_input(model: dict[str, Any]) -> bool:
        return "image" in ((model.get("architecture") or {}).get("input_modalities") or [])

    def rank(model: dict[str, Any]) -> tuple[int, str, str]:
        model_id = model.get("id", "")
        name = model.get("name", model_id)
        if model_id == openrouter.get("default_model", "openrouter/pareto-code"):
            priority = 0
        elif model_id == "openrouter/fusion":
            priority = 1
        elif re.search(r"codex|pareto|code|coder", model_id, re.I):
            priority = 10
        elif re.search(r"sonnet|claude|gpt-5|glm|kimi|qwen|deepseek", model_id, re.I):
            priority = 20
        else:
            priority = 100
        return (priority, name, model_id)

    catalog_models: list[dict[str, Any]] = []
    for priority, model in enumerate(sorted([m for m in payload.get("data", []) if has_text_output(m)], key=rank)):
        context = int(model.get("context_length") or 128000)
        pricing = model.get("pricing") or {}
        description = f"OpenRouter model | context: {context} tokens"
        if pricing.get("prompt") and pricing.get("completion"):
            description += f" | prompt: {pricing['prompt']}, completion: {pricing['completion']}"
        image_input = has_image_input(model)
        catalog_models.append(
            {
                "slug": model["id"],
                "display_name": model.get("name") or model["id"],
                "description": description,
                "default_reasoning_level": "medium",
                "supported_reasoning_levels": [
                    {"effort": "low", "description": "Lighter reasoning"},
                    {"effort": "medium", "description": "Balanced reasoning"},
                    {"effort": "high", "description": "Deeper reasoning"},
                ],
                "shell_type": "shell_command",
                "visibility": "list",
                "supported_in_api": True,
                "priority": priority,
                "base_instructions": template.get("base_instructions"),
                "model_messages": template.get("model_messages"),
                "supports_reasoning_summaries": False,
                "support_verbosity": False,
                "truncation_policy": {"mode": "tokens", "limit": 10000},
                "supports_parallel_tool_calls": True,
                "supports_image_detail_original": image_input,
                "context_window": context,
                "max_context_window": context,
                "effective_context_window_percent": 95,
                "experimental_supported_tools": [],
                "input_modalities": ["text", "image"] if image_input else ["text"],
                "supports_search_tool": False,
                "use_responses_lite": False,
            }
        )

    out = codex_home / "model-catalog.json"
    out.write_text(json.dumps({"models": catalog_models}, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out} with {len(catalog_models)} models")


def update_package_json(unpacked: Path) -> None:
    package_json = unpacked / "package.json"
    data = json.loads(package_json.read_text(encoding="utf-8"))
    data["codexSparkleFeedUrl"] = ""
    data["codexSparklePublicKey"] = ""
    data["codexCloneUpdateMode"] = "manual"
    package_json.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def patch_file_once(path: Path, replacements: list[tuple[str, str]], required_marker: str) -> None:
    data = path.read_text(encoding="utf-8")
    changed = False
    for old, new in replacements:
        if old in data:
            data = data.replace(old, new)
            changed = True
    if changed:
        path.write_text(data, encoding="utf-8")
    if required_marker not in path.read_text(encoding="utf-8"):
        fail(f"patch marker {required_marker!r} missing in {path}")


def first_match(root: Path, pattern: str) -> Path:
    matches = list(root.glob(pattern))
    if len(matches) != 1:
        fail(f"expected one {pattern} under {root}, found {len(matches)}")
    return matches[0]


def try_patch_js_asset_once(
    root: Path,
    *,
    glob_pattern: str = "*.js",
    marker: str,
    replacements: list[tuple[str, str]],
    required_marker: str,
) -> bool:
    matches = [path for path in root.glob(glob_pattern) if marker in path.read_text(encoding="utf-8")]
    if not matches:
        return False
    if len(matches) != 1:
        fail(f"expected one JS asset containing {marker!r} under {root}, found {len(matches)}")
    patch_file_once(matches[0], replacements, required_marker)
    return True


def patch_js_asset_once(
    root: Path,
    *,
    glob_pattern: str = "*.js",
    marker: str,
    replacements: list[tuple[str, str]],
    required_marker: str,
) -> None:
    if not try_patch_js_asset_once(
        root,
        glob_pattern=glob_pattern,
        marker=marker,
        replacements=replacements,
        required_marker=required_marker,
    ):
        fail(f"expected one JS asset containing {marker!r} under {root}, found 0")


def patch_asar(app: Path, variant: dict[str, Any], tmp_root: Path) -> None:
    asar = app / "Contents/Resources/app.asar"
    plist = app / "Contents/Info.plist"
    if not asar.is_file():
        fail(f"app.asar missing: {asar}")
    unpacked = tmp_root / f"asar-{variant['id']}"
    run(["npx", "--yes", "@electron/asar", "extract", str(asar), str(unpacked)])
    update_package_json(unpacked)

    patches = set(variant.get("asar_patches") or [])
    assets = unpacked / "webview/assets"
    if "openrouter_model_picker" in patches:
        if not try_patch_js_asset_once(
            assets,
            glob_pattern="model-list-filter-*.js",
            marker="s=i&&e!==`amazonBedrock`",
            replacements=[
                ("let a=[],o=null,s=i&&e!==`amazonBedrock`;", "let a=[],o=null,s=!1;"),
                ("s=i&&e!==`amazonBedrock`", "s=!1"),
            ],
            required_marker="s=!1",
        ):
            patch_js_asset_once(
                assets,
                marker="l=o&&e!==`amazonBedrock`",
                replacements=[("l=o&&e!==`amazonBedrock`", "l=!1")],
                required_marker="l=!1",
            )
    if "openrouter_model_limit_1000" in patches:
        if not try_patch_js_asset_once(
            assets,
            glob_pattern="model-queries-*.js",
            marker="var w=100,T=",
            replacements=[("var w=100,T=", "var w=1000,T=")],
            required_marker="var w=1000",
        ):
            patch_js_asset_once(
                assets,
                marker="on=100,sn=[`models`,`list`]",
                replacements=[("on=100,sn=[`models`,`list`]", "on=1000,sn=[`models`,`list`]")],
                required_marker="on=1000",
            )
        if not try_patch_js_asset_once(
            assets,
            glob_pattern="read-service-tier-for-request-*.js",
            marker="limit:100",
            replacements=[("limit:100})", "limit:1000})"), ("limit:100,", "limit:1000,")],
            required_marker="limit:1000",
        ):
            patch_js_asset_once(
                assets,
                marker="Failed to read service tier model",
                replacements=[("includeHidden:!0,cursor:null,limit:100})", "includeHidden:!0,cursor:null,limit:1000})")],
                required_marker="limit:1000",
            )

    asar.unlink()
    run(["npx", "--yes", "@electron/asar", "pack", str(unpacked), str(asar)])
    digest = run(["/usr/bin/shasum", "-a", "256", str(asar)], capture=True).stdout.split()[0]
    plist_set(plist, "ElectronAsarIntegrity:Resources/app.asar:hash", "string", digest)


def make_icns(master_png: Path, dest_icns: Path, tmp_root: Path) -> None:
    iconset = tmp_root / f"{dest_icns.stem}.iconset"
    iconset.mkdir(parents=True, exist_ok=True)
    specs = [
        (16, "icon_16x16.png"),
        (32, "icon_16x16@2x.png"),
        (32, "icon_32x32.png"),
        (64, "icon_32x32@2x.png"),
        (128, "icon_128x128.png"),
        (256, "icon_128x128@2x.png"),
        (256, "icon_256x256.png"),
        (512, "icon_256x256@2x.png"),
        (512, "icon_512x512.png"),
        (1024, "icon_512x512@2x.png"),
    ]
    for size, name in specs:
        run(["/usr/bin/sips", "-z", str(size), str(size), str(master_png), "--out", str(iconset / name)], capture=True)
    run(["/usr/bin/iconutil", "-c", "icns", str(iconset), "-o", str(dest_icns)])


def apply_icon_to_app(app: Path, variant: dict[str, Any], base_dir: Path, tmp_root: Path) -> None:
    icon = variant.get("icon") or {}
    master = resolve_icon_master(app, variant, base_dir, tmp_root)
    if master is None:
        return
    if not master.is_file():
        fail(f"icon master not found: {master}")
    resources = app / "Contents/Resources"
    generated_icns = tmp_root / f"{variant['id']}.icns"
    make_icns(master, generated_icns, tmp_root)
    for name in icon.get("icns_targets") or ["electron.icns", "app.icns", "icon.icns"]:
        target = resources / name
        if target.parent.exists():
            shutil.copy2(generated_icns, target)
    for name in icon.get("png_targets") or []:
        target = resources / name
        if target.parent.exists():
            shutil.copy2(master, target)


def resolve_icon_master(app: Path, variant: dict[str, Any], base_dir: Path, tmp_root: Path) -> Path | None:
    icon = variant.get("icon") or {}
    master = expand_path(icon.get("master_png"), base_dir=base_dir)
    if master is not None:
        return master
    badge = icon.get("compose_badge")
    if not badge:
        return None
    base_resource = app / "Contents/Resources" / badge.get("base_resource_png", "icon.png")
    overlay = expand_path(badge.get("overlay_png"), base_dir=base_dir)
    if overlay is None:
        fail(f"variant {variant['id']} compose_badge requires overlay_png")
    out = tmp_root / f"{variant['id']}-master.png"
    compose_badge_icon(
        base_resource,
        overlay,
        out,
        badge_bg=badge.get("badge_bg", "#ffffff"),
        badge_size=int(badge.get("badge_size", 370)),
        logo_size=int(badge.get("logo_size", 318)),
        margin=int(badge.get("margin", 40)),
        radius=int(badge.get("radius", 82)),
        crop_overlay=bool(badge.get("crop_overlay", False)),
    )
    return out


def compose_badge_icon(
    base_png: Path,
    overlay_png: Path,
    out: Path,
    *,
    badge_bg: str,
    badge_size: int,
    logo_size: int,
    margin: int,
    radius: int,
    crop_overlay: bool,
) -> None:
    try:
        from PIL import Image, ImageDraw, ImageFilter
    except Exception as exc:
        fail(f"Pillow is required for composed badge icons: {exc}")

    if not base_png.is_file():
        fail(f"base icon resource not found: {base_png}")
    if not overlay_png.is_file():
        fail(f"badge overlay not found: {overlay_png}")

    base = Image.open(base_png).convert("RGBA").resize((1024, 1024), Image.LANCZOS)
    overlay_src = Image.open(overlay_png).convert("RGBA")
    if crop_overlay:
        overlay_src = crop_light_border(overlay_src)

    badge_x = 1024 - badge_size - margin
    badge_y = 1024 - badge_size - margin
    shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle((badge_x + 8, badge_y + 14, badge_x + badge_size + 8, badge_y + badge_size + 14), radius=radius, fill=(0, 0, 0, 115))
    shadow = shadow.filter(ImageFilter.GaussianBlur(20))

    badge = Image.new("RGBA", (badge_size, badge_size), (0, 0, 0, 0))
    bd = ImageDraw.Draw(badge)
    bd.rounded_rectangle((0, 0, badge_size, badge_size), radius=radius, fill=badge_bg)
    overlay = overlay_src.resize((logo_size, logo_size), Image.LANCZOS)
    badge.alpha_composite(overlay, ((badge_size - logo_size) // 2, (badge_size - logo_size) // 2))

    result = base.copy()
    result.alpha_composite(shadow)
    result.alpha_composite(badge, (badge_x, badge_y))
    result.save(out)


def crop_light_border(image: Any, *, threshold: int = 250, padding: int = 1) -> Any:
    rgb = image.convert("RGB")
    width, height = rgb.size
    xs: list[int] = []
    ys: list[int] = []
    for y in range(height):
        for x in range(width):
            r, g, b = rgb.getpixel((x, y))
            if not (r > threshold and g > threshold and b > threshold):
                xs.append(x)
                ys.append(y)
    if not xs:
        return image
    return image.crop((max(min(xs) - padding, 0), max(min(ys) - padding, 0), min(max(xs) + padding + 1, width), min(max(ys) + padding + 1, height)))


def customize_plist(app: Path, variant: dict[str, Any]) -> None:
    plist = app / "Contents/Info.plist"
    plist_set(plist, "CFBundleDisplayName", "string", variant["display_name"])
    plist_set(plist, "CFBundleName", "string", variant["display_name"])
    plist_set(plist, "CFBundleIdentifier", "string", variant["bundle_id"])
    plist_set(plist, "CrProductDirName", "string", variant["bundle_id"])
    plist_set(plist, "CFBundleURLTypes:0:CFBundleURLName", "string", variant["display_name"])
    plist_set(plist, "CFBundleURLTypes:0:CFBundleURLSchemes:0", "string", variant["url_scheme"])
    for key in ["SUEnableAutomaticChecks", "SUAutomaticallyUpdate", "SUAllowsAutomaticUpdates", "SUEnableInstallerLauncherService"]:
        plist_set_bool(plist, key, False)
    run(["/usr/bin/plutil", "-lint", str(plist)])


def clear_caches(variant: dict[str, Any]) -> None:
    cache_root = Path.home() / "Library/Caches"
    if not cache_root.is_dir():
        return
    display_name = variant["display_name"]
    bundle_id = variant["bundle_id"]
    for child in cache_root.iterdir():
        if child.name.startswith(bundle_id) or child.name.startswith(display_name):
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            else:
                child.unlink(missing_ok=True)


def register_app(app: Path) -> None:
    lsregister = Path("/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister")
    if lsregister.exists():
        run([str(lsregister), "-f", str(app)], check=False, capture=True)
    run(["/usr/bin/xattr", "-dr", "com.apple.quarantine", str(app)], check=False, capture=True)
    run(["/usr/bin/touch", str(app)], check=False)


def build_variant(config: dict[str, Any], variant: dict[str, Any], base_dir: Path, *, replace: bool) -> None:
    paths = variant_paths(config, variant, base_dir)
    source_app = paths["source_app"]
    dest_app = paths["dest_app"]
    codex_home = paths["codex_home"]
    assert source_app is not None and dest_app is not None and codex_home is not None
    verify_source_app(source_app)

    if dest_app.exists() and not replace:
        fail(f"target app already exists: {dest_app}; rerun with --replace")
    if dest_app.exists():
        quit_if_running(dest_app, variant["bundle_id"], variant["display_name"])

    codex_home.mkdir(parents=True, exist_ok=True)
    write_codex_config(variant, paths, base_dir)
    refresh_openrouter_catalog(variant, paths)

    with tempfile.TemporaryDirectory(prefix="codex-variant-") as tmp:
        tmp_root = Path(tmp)
        build_app = tmp_root / dest_app.name
        print(f"Building {variant['display_name']} from {source_app}")
        run(["/usr/bin/ditto", str(source_app), str(build_app)])
        customize_plist(build_app, variant)
        write_launcher(build_app, variant, codex_home, paths["env_file"])
        patch_asar(build_app, variant, tmp_root)
        apply_icon_to_app(build_app, variant, base_dir, tmp_root)
        run(["/usr/bin/codesign", "--force", "--deep", "--sign", "-", str(build_app)])
        run(["/usr/bin/codesign", "--verify", "--deep", str(build_app)])

        backup = tmp_root / f"backup-{dest_app.name}"
        if dest_app.exists():
            dest_app.rename(backup)
        try:
            build_app.rename(dest_app)
        except Exception:
            if backup.exists():
                backup.rename(dest_app)
            raise

    clear_caches(variant)
    register_app(dest_app)
    print(f"Installed {dest_app}")


def verify_variant(config: dict[str, Any], variant: dict[str, Any], base_dir: Path) -> None:
    paths = variant_paths(config, variant, base_dir)
    app = paths["dest_app"]
    codex_home = paths["codex_home"]
    assert app is not None and codex_home is not None
    if not app.is_dir():
        fail(f"app not found: {app}")
    plist = app / "Contents/Info.plist"
    checks = {
        "CFBundleDisplayName": variant["display_name"],
        "CFBundleIdentifier": variant["bundle_id"],
        "CrProductDirName": variant["bundle_id"],
        "CFBundleURLTypes:0:CFBundleURLSchemes:0": variant["url_scheme"],
    }
    for key, expected in checks.items():
        actual = plist_read(plist, key)
        if actual != expected:
            fail(f"{variant['id']} {key}: expected {expected}, got {actual}")

    launcher = app / "Contents/MacOS/Codex"
    if f'CODEX_HOME="{codex_home}"' not in launcher.read_text(encoding="utf-8"):
        fail(f"launcher does not point to CODEX_HOME={codex_home}")

    run(["/usr/bin/codesign", "--verify", "--deep", str(app)])

    asar = app / "Contents/Resources/app.asar"
    actual_hash = run(["/usr/bin/shasum", "-a", "256", str(asar)], capture=True).stdout.split()[0]
    plist_hash = plist_read(plist, "ElectronAsarIntegrity:Resources/app.asar:hash")
    if actual_hash != plist_hash:
        fail("app.asar hash does not match ElectronAsarIntegrity")

    with tempfile.TemporaryDirectory(prefix="codex-variant-verify-") as tmp:
        unpacked = Path(tmp) / "asar"
        run(["npx", "--yes", "@electron/asar", "extract", str(asar), str(unpacked)])
        package_json = json.loads((unpacked / "package.json").read_text(encoding="utf-8"))
        if package_json.get("codexSparkleFeedUrl") not in ("", None):
            fail("embedded Sparkle feed is still enabled")
        patches = set(variant.get("asar_patches") or [])
        assets = unpacked / "webview/assets"
        if "openrouter_model_picker" in patches:
            picker_patched = any(
                marker in path.read_text(encoding="utf-8")
                for marker in ("s=!1", "l=!1")
                for path in assets.glob("*.js")
            )
            if not picker_patched:
                fail("OpenRouter model picker patch missing")
        if "openrouter_model_limit_1000" in patches:
            model_limit_patched = any(
                marker in path.read_text(encoding="utf-8")
                for marker in ("var w=1000", "on=1000,sn=[`models`,`list`]")
                for path in assets.glob("*.js")
            )
            if not model_limit_patched:
                fail("OpenRouter model query limit patch missing")
            service_tier_patched = any(
                "Failed to read service tier model" in data and "limit:1000" in data
                for data in (path.read_text(encoding="utf-8") for path in assets.glob("*.js"))
            )
            if not service_tier_patched:
                fail("OpenRouter service-tier limit patch missing")

    print(f"Verified {variant['display_name']} at {app}")


def apply_icon(config: dict[str, Any], variant: dict[str, Any], base_dir: Path) -> None:
    paths = variant_paths(config, variant, base_dir)
    app = paths["dest_app"]
    assert app is not None
    if not app.is_dir():
        fail(f"app not found: {app}")
    with tempfile.TemporaryDirectory(prefix="codex-variant-icon-") as tmp:
        apply_icon_to_app(app, variant, base_dir, Path(tmp))
    run(["/usr/bin/codesign", "--force", "--sign", "-", str(app)])
    run(["/usr/bin/codesign", "--verify", "--deep", str(app)])
    register_app(app)
    print(f"Applied icon to {app}")


def icon_badge(args: argparse.Namespace) -> None:
    try:
        from PIL import Image, ImageDraw, ImageFilter
    except Exception as exc:
        fail(f"Pillow is required for icon-badge: {exc}")

    base = Image.open(args.base_png).convert("RGBA").resize((1024, 1024), Image.LANCZOS)
    overlay_src = Image.open(args.overlay_png).convert("RGBA")
    if args.crop_overlay:
        rgb = overlay_src.convert("RGB")
        width, height = rgb.size
        xs: list[int] = []
        ys: list[int] = []
        threshold = args.crop_threshold
        for y in range(height):
            for x in range(width):
                r, g, b = rgb.getpixel((x, y))
                if not (r > threshold and g > threshold and b > threshold):
                    xs.append(x)
                    ys.append(y)
        if xs:
            pad = args.crop_padding
            overlay_src = overlay_src.crop(
                (
                    max(min(xs) - pad, 0),
                    max(min(ys) - pad, 0),
                    min(max(xs) + pad + 1, width),
                    min(max(ys) + pad + 1, height),
                )
            )

    badge_size = args.badge_size
    logo_size = args.logo_size
    margin = args.margin
    badge_x = 1024 - badge_size - margin
    badge_y = 1024 - badge_size - margin
    radius = args.radius

    shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle(
        (badge_x + args.shadow_x, badge_y + args.shadow_y, badge_x + badge_size + args.shadow_x, badge_y + badge_size + args.shadow_y),
        radius=radius,
        fill=(0, 0, 0, args.shadow_alpha),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(args.shadow_blur))

    badge = Image.new("RGBA", (badge_size, badge_size), (0, 0, 0, 0))
    bd = ImageDraw.Draw(badge)
    bd.rounded_rectangle((0, 0, badge_size, badge_size), radius=radius, fill=args.badge_bg)
    overlay = overlay_src.resize((logo_size, logo_size), Image.LANCZOS)
    badge.alpha_composite(overlay, ((badge_size - logo_size) // 2, (badge_size - logo_size) // 2))

    result = base.copy()
    result.alpha_composite(shadow)
    result.alpha_composite(badge, (badge_x, badge_y))
    result.save(args.out)
    if args.preview:
        make_preview(result, Path(args.preview))


def make_preview(image: Any, path: Path) -> None:
    from PIL import Image, ImageDraw

    sizes = [512, 256, 128, 64, 32, 16]
    tiles = []
    for size in sizes:
        img = image.resize((size, size), Image.LANCZOS)
        tile = Image.new("RGBA", (max(size, 100), max(size + 36, 100)), (238, 238, 238, 255))
        tile.alpha_composite(img, ((tile.width - size) // 2, 8))
        ImageDraw.Draw(tile).text((8, tile.height - 24), f"{size}px", fill=(0, 0, 0, 255))
        tiles.append(tile)
    preview = Image.new("RGBA", (sum(t.width for t in tiles), max(t.height for t in tiles)), (225, 225, 225, 255))
    x = 0
    for tile in tiles:
        preview.alpha_composite(tile, (x, 0))
        x += tile.width
    preview.save(path)


def list_variants(config: dict[str, Any]) -> None:
    for variant in config.get("variants", []):
        print(f"{variant['id']}\t{variant['display_name']}\t{variant['dest_app']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and maintain local Codex.app variants on macOS.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def add_config_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("--config", default=str(ROOT / "configs/example.variants.json"))
        p.add_argument("--variant")

    p_list = sub.add_parser("list")
    add_config_args(p_list)

    p_build = sub.add_parser("build")
    add_config_args(p_build)
    p_build.add_argument("--replace", action="store_true")

    p_verify = sub.add_parser("verify")
    add_config_args(p_verify)

    p_apply = sub.add_parser("apply-icon")
    add_config_args(p_apply)

    p_badge = sub.add_parser("icon-badge")
    p_badge.add_argument("--base-png", required=True)
    p_badge.add_argument("--overlay-png", required=True)
    p_badge.add_argument("--out", required=True)
    p_badge.add_argument("--preview")
    p_badge.add_argument("--badge-bg", default="#ffffff")
    p_badge.add_argument("--badge-size", type=int, default=370)
    p_badge.add_argument("--logo-size", type=int, default=318)
    p_badge.add_argument("--margin", type=int, default=40)
    p_badge.add_argument("--radius", type=int, default=82)
    p_badge.add_argument("--shadow-x", type=int, default=8)
    p_badge.add_argument("--shadow-y", type=int, default=14)
    p_badge.add_argument("--shadow-alpha", type=int, default=115)
    p_badge.add_argument("--shadow-blur", type=int, default=20)
    p_badge.add_argument("--crop-overlay", action="store_true")
    p_badge.add_argument("--crop-threshold", type=int, default=250)
    p_badge.add_argument("--crop-padding", type=int, default=1)

    args = parser.parse_args()

    if args.cmd == "icon-badge":
        icon_badge(args)
        return

    require("npx")
    require("node")
    config, base_dir = load_config(Path(args.config))
    if args.cmd == "list":
        list_variants(config)
        return

    for variant in select_variants(config, args.variant):
        if args.cmd == "build":
            build_variant(config, variant, base_dir, replace=args.replace)
        elif args.cmd == "verify":
            verify_variant(config, variant, base_dir)
        elif args.cmd == "apply-icon":
            apply_icon(config, variant, base_dir)


if __name__ == "__main__":
    main()

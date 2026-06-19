#!/bin/zsh
set -euo pipefail

ENV_FILE="${ENV_FILE:-/Users/max/Projects/.env}"
CODEX_BIN="${CODEX_BIN:-/Applications/Codex.app/Contents/Resources/codex}"
CODEX_HOME_TARGET="${CODEX_HOME_TARGET:-/Users/max/.codex-openrouter}"
OUT="${OUT:-$CODEX_HOME_TARGET/model-catalog.json}"

if ! command -v jq >/dev/null 2>&1; then
  print -u2 "jq is required."
  exit 1
fi

if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
  print -u2 "OPENROUTER_API_KEY is not set. Expected it in $ENV_FILE."
  exit 1
fi

if [[ ! -x "$CODEX_BIN" ]]; then
  print -u2 "Codex CLI not found or not executable: $CODEX_BIN"
  exit 1
fi

mkdir -p "$(dirname "$OUT")"

tmp_models="$(mktemp)"
tmp_template="$(mktemp)"
tmp_out="$(mktemp)"
trap 'rm -f "$tmp_models" "$tmp_template" "$tmp_out"' EXIT

curl -fsS \
  -H "Authorization: Bearer ${OPENROUTER_API_KEY}" \
  -H "HTTP-Referer: https://chatgpt.com/codex-openrouter-local" \
  -H "X-Title: Codex OpenRouter Models" \
  "https://openrouter.ai/api/v1/models" > "$tmp_models"

"$CODEX_BIN" debug models --bundled | jq '.models[0] | {base_instructions, model_messages}' > "$tmp_template"

jq --slurpfile template "$tmp_template" '
  def has_text_output:
    ((.architecture.output_modalities // []) | index("text")) != null;
  def has_image_input:
    ((.architecture.input_modalities // []) | index("image")) != null;
  def preferred_rank:
    if .id == "openrouter/pareto-code" then 0
    elif .id == "openrouter/fusion" then 1
    elif (.id | test("codex|pareto|code|coder"; "i")) then 10
    elif (.id | test("sonnet|claude|gpt-5|glm|kimi|qwen|deepseek"; "i")) then 20
    else 100 end;
  {
    models: (
      .data
      | map(select(has_text_output))
      | sort_by(preferred_rank, .name, .id)
      | to_entries
      | map({
          slug: .value.id,
          display_name: (.value.name // .value.id),
          description: (
            "OpenRouter model"
            + (if .value.context_length then " | context: \(.value.context_length) tokens" else "" end)
            + (if (.value.pricing.prompt? and .value.pricing.completion?) then " | prompt: \(.value.pricing.prompt), completion: \(.value.pricing.completion)" else "" end)
          ),
          default_reasoning_level: "medium",
          supported_reasoning_levels: [
            { effort: "low", description: "Lighter reasoning" },
            { effort: "medium", description: "Balanced reasoning" },
            { effort: "high", description: "Deeper reasoning" }
          ],
          shell_type: "shell_command",
          visibility: "list",
          supported_in_api: true,
          priority: .key,
          base_instructions: $template[0].base_instructions,
          model_messages: $template[0].model_messages,
          supports_reasoning_summaries: false,
          support_verbosity: false,
          truncation_policy: { mode: "tokens", limit: 10000 },
          supports_parallel_tool_calls: true,
          supports_image_detail_original: has_image_input,
          context_window: ((.value.context_length // 128000) | tonumber),
          max_context_window: ((.value.context_length // 128000) | tonumber),
          effective_context_window_percent: 95,
          experimental_supported_tools: [],
          input_modalities: (if has_image_input then ["text", "image"] else ["text"] end),
          supports_search_tool: false,
          use_responses_lite: false
        })
    )
  }
' "$tmp_models" > "$tmp_out"

jq empty "$tmp_out"
mv "$tmp_out" "$OUT"
print "Wrote $OUT with $(jq '.models | length' "$OUT") models."


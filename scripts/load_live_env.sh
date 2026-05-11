#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_DIR="$ROOT_DIR/env"
ENV_FILE="$ENV_DIR/live.env"
ENV_TEMPLATE="$ENV_DIR/live.env.example"

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$ENV_TEMPLATE" "$ENV_FILE"
  cat <<'EOF'
Created env/live.env from template.

Next:
1) Edit env/live.env and replace all replace_me values.
2) Load into current shell with:
   source scripts/load_live_env.sh
3) Verify without exposing secrets:
   env | grep -E '^(RENDER_API_KEY|QDRANT_API_KEY|ALETHEIA_DEMO_KEY|VERCEL_TOKEN)=' | sed 's/=.*/=[set]/'
EOF
  return 0 2>/dev/null || exit 0
fi

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

missing=0
for key in RENDER_API_KEY QDRANT_API_KEY ALETHEIA_DEMO_KEY VERCEL_TOKEN; do
  value="${!key:-}"
  if [[ -z "$value" || "$value" == "replace_me" ]]; then
    echo "WARN: $key is missing or still set to replace_me"
    missing=1
  fi
done

if [[ "$missing" -eq 0 ]]; then
  echo "Live service environment loaded from env/live.env"
else
  echo "Loaded with warnings. Update env/live.env placeholders and run again."
fi

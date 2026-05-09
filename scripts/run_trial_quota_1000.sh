#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   scripts/run_trial_quota_1000.sh <TRIAL_KEY> [BASE_URL]
# Example:
#   scripts/run_trial_quota_1000.sh sk_trial_xxx https://aletheia-core.onrender.com

KEY="${1:-}"
BASE_URL="${2:-https://aletheia-core.onrender.com}"
TOTAL="${TOTAL_REQUESTS:-1000}"

if [[ -z "$KEY" ]]; then
  echo "Usage: $0 <TRIAL_KEY> [BASE_URL]"
  exit 2
fi

ok_count=0
deny_count=0
rate_count=0
other_count=0
first_429_at=0

for i in $(seq 1 "$TOTAL"); do
  body='{"payload":"Retrieve the latest system health report for the monitoring dashboard.","origin":"quota-probe","action":"read_config"}'

  tmp_file="$(mktemp)"
  status=$(curl -sS --connect-timeout 5 --max-time 15 -o "$tmp_file" -w "%{http_code}" \
    -X POST "$BASE_URL/v1/audit" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $KEY" \
    -d "$body" || true)

  if [[ "$status" == "200" ]]; then
    ok_count=$((ok_count + 1))
  elif [[ "$status" == "403" ]]; then
    deny_count=$((deny_count + 1))
  elif [[ "$status" == "429" ]]; then
    rate_count=$((rate_count + 1))
    if [[ "$first_429_at" -eq 0 ]]; then
      first_429_at="$i"
    fi
  else
    other_count=$((other_count + 1))
  fi

  if (( i % 100 == 0 )); then
    echo "Progress: $i/$TOTAL 200=$ok_count 403=$deny_count 429=$rate_count other=$other_count"
  fi

  rm -f "$tmp_file"
done

echo "--- Summary ---"
echo "Total requests: $TOTAL"
echo "HTTP 200: $ok_count"
echo "HTTP 403: $deny_count"
echo "HTTP 429: $rate_count"
echo "Other status: $other_count"

if [[ "$first_429_at" -gt 0 ]]; then
  echo "First 429 observed at request: $first_429_at"
else
  echo "No 429 observed in first $TOTAL requests"
fi

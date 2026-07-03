#!/usr/bin/env bash
# Push local keys into AWS Secrets Manager. Run AFTER `cdk deploy` creates the
# (empty) secrets. Reads .env + credentials.json/token.json — none of which are
# committed. Usage: AWS_PROFILE=<personal> ./scripts/seed-secrets.sh
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] || { echo "No .env — copy .env.example to .env and fill it in."; exit 1; }
set -a; . ./.env; set +a

put() { aws secretsmanager put-secret-value --secret-id "$1" --secret-string "$2" >/dev/null && echo "  ✓ $1"; }

echo "Seeding secrets..."

[ -n "${ANTHROPIC_API_KEY:-}" ] && put "career-copilot/anthropic" "$ANTHROPIC_API_KEY" || echo "  - skip anthropic (ANTHROPIC_API_KEY unset)"
[ -n "${APIFY_TOKEN:-}" ]       && put "career-copilot/apify"     "$APIFY_TOKEN"       || echo "  - skip apify (APIFY_TOKEN unset)"

if [ -f credentials.json ] && [ -f token.json ]; then
  gmail_json=$(python3 -c 'import json,sys; print(json.dumps({"credentials":json.load(open("credentials.json")),"token":json.load(open("token.json"))}))')
  put "career-copilot/gmail" "$gmail_json"
else
  echo "  - skip gmail (need credentials.json + token.json; authorize locally first)"
fi

echo "Done."

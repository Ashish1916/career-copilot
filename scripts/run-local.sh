#!/usr/bin/env bash
# Run the full daily pipeline locally — no AWS, no keys required.
#
#   - Jobs come from the local job-apply (ja) SQLite DB if present.
#   - Storage uses a local JSON file instead of DynamoDB.
#   - Gmail is included only if credentials.json + token.json exist; otherwise
#     it renders an empty-inbox briefing (--no-gmail).
#   - Claude drafting / Apify stay off unless their keys are in the environment.
#
# Usage: ./scripts/run-local.sh
set -euo pipefail
cd "$(dirname "$0")/.."

[ -d .venv ] && . .venv/bin/activate

export JA_DB_PATH="${JA_DB_PATH:-$HOME/projects/job-apply/data/jobs.db}"
export LOCAL_DB="${LOCAL_DB:-/tmp/career-copilot-local.json}"
OUT="${OUT:-/tmp/briefing.md}"

echo "job-apply DB : $JA_DB_PATH $( [ -f "$JA_DB_PATH" ] && echo '(found)' || echo '(missing — no job matches)')"
echo "local store  : $LOCAL_DB"
echo

if [ -f credentials.json ] && [ -f token.json ]; then
  echo "Gmail creds found — pulling recent mail."
  copilot briefing --out "$OUT"
else
  echo "No Gmail creds — rendering inbox-free briefing (add credentials.json to enable)."
  copilot briefing --no-gmail --out "$OUT"
fi

echo
echo "Briefing written to $OUT"
